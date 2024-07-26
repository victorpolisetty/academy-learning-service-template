# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This package contains round behaviours of LearningAbciApp."""
from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype
import json
import tempfile
import tenacity
from enum import Enum, auto
from abc import ABC
from typing import Generator, Set, Type, cast, Optional, Dict, Any
from subgrounds import Subgrounds, FieldPath
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.skills.abstract_round_abci.models import ApiSpecs

from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.transaction_settlement_abci.rounds import TX_HASH_LENGTH
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.skills.learning_abci.graph_tooling.queries.large_data_query import (
    large_data as large_data_query,
)
from packages.valory.skills.abstract_round_abci.io_.ipfs import IPFSInteract
from packages.valory.skills.learning_abci.models import Params, SharedState
from packages.valory.skills.learning_abci.payloads import (
    APICheckPayload,
    LargeDataCheckPayload,
    DecisionMakingPayload,
    TxPreparationPayload,
)
from packages.valory.skills.learning_abci.rounds import (
    APICheckRound,
    LargeDataCheckRound,
    DecisionMakingRound,
    Event,
    LearningAbciApp,
    SynchronizedData,
    TxPreparationRound,
)
from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)


HTTP_OK = 200
GNOSIS_CHAIN_ID = "gnosis"
TX_DATA = b"0x"
SAFE_GAS = 0
VALUE_KEY = "value"
TO_ADDRESS_KEY = "to_address"
ETHER_VALUE = 1
call_data = {VALUE_KEY: ETHER_VALUE, TO_ADDRESS_KEY: "0xbDcc35821DAA3a15047615773E14c77a1042d317"}
MAX_LOG_SIZE = 1000


def to_content(query: str) -> bytes:
    """Convert the given query string to payload content, i.e., add it under a `queries` key and convert it to bytes."""
    finalized_query = {"query": query}
    encoded_query = json.dumps(finalized_query, sort_keys=True).encode("utf-8")

    return encoded_query


class FetchStatus(Enum):
    """The status of a fetch operation."""

    SUCCESS = auto()
    IN_PROGRESS = auto()
    FAIL = auto()
    NONE = auto()


class LearningBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)

    @property
    def local_state(self) -> SharedState:
        """Return the state."""
        return cast(SharedState, self.context.state)

    @property
    def current_subgraph(self) -> ApiSpecs:
        self.sg = Subgrounds()
        url = self.params.subgraph_endpoint.format(api_key=self.params.subgraph_api_key)
        current_subgraph = self.sg.load_subgraph(
            url=url
        )
        """Get a subgraph by prediction market's name."""
        return current_subgraph

class APICheckBehaviour(LearningBaseBehaviour):  # pylint: disable=too-many-ancestors
    """APICheckBehaviour"""

    matching_round: Type[AbstractRound] = APICheckRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            price = yield from self.get_price()
            payload = APICheckPayload(sender=sender, price=price)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_price(self):
        """Get token price from Coingecko"""

        url = self.params.coingecko_price_template.format(api_key=self.params.coingecko_api_key)


        response = yield from self.get_http_response(
                method="GET",
                url=url
            )

        if response.status_code != 200:
            self.context.logger.error(
                f"Could not retrieve data from CoinGecko API. "
                f"Received status code {response.status_code}."
            )
            return "{}"

        # Example response: body=b'{"autonolas":{"usd":1.31}}
        price = json.loads(response.body)["autonolas"]["usd"]

        print(price)
        self.context.logger.info(f"Price is {price}")
        return price

class LargeDataCheckBehaviour(LearningBaseBehaviour):  # pylint: disable=too-many-ancestors
    """LargeDataCheckBehaviour"""

    matching_round: Type[AbstractRound] = LargeDataCheckRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            data = yield from self.get_large_data()
            if data is None:
                return
            try:
                ipfs_hash = self.upload_to_ipfs(data)
                print("The IPFS Hash: ")
                #THIS IS DICT SHOULD BE STRING????
                print(ipfs_hash)
                payload = LargeDataCheckPayload(sender=sender, ipfs_hash=ipfs_hash)
            except Exception as e:
                self.context.logger.error(f"Error while uploading to IPFS: {e}")
                return

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


    def upload_to_ipfs(self, data: Dict[str, Any]) -> str:
        """Upload data to IPFS and return the hash."""
        try:
            # Convert data to JSON string
            json_data = json.dumps(data)

            # Save JSON string to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
                temp_file.write(json_data.encode('utf-8'))
                temp_file_path = temp_file.name

            # Upload the temporary file to IPFS
            # TODO: get correct IPFS hash
            ipfs_interact = IPFSInteract()
            ipfs_hash = ipfs_interact.store(filepath=temp_file_path, obj=data, multiple=False, filetype=SupportedFiletype.JSON)

            return ipfs_hash
        except Exception as e:
            self.context.logger.error(f"IPFS interaction failed: {e}")
            raise

    # TODO: get data from subgraph
    def get_large_data(self) -> Generator[None, None, Optional[Dict[str, Any]]]:
        self._fetch_status = FetchStatus.IN_PROGRESS

        query = large_data_query.substitute()
        res_raw = yield from self.get_http_response(
            content=to_content(query),
            method='POST',
            url=self.params.subgraph_endpoint.format(api_key=self.params.subgraph_api_key)
        )
        # Directly process the response without calling process_response
        res = json.loads(res_raw.body) if res_raw else None
        if res is None:
            self.context.logger.error("Failed to fetch data from subgraph.")
            return None
        return res



# TODO: read behavior from ipfs hash and make decision based on it
class DecisionMakingBehaviour(
    LearningBaseBehaviour
):  # pylint: disable=too-many-ancestors
    """DecisionMakingBehaviour"""

    matching_round: Type[AbstractRound] = DecisionMakingRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            event = self.get_event()
            payload = DecisionMakingPayload(sender=sender, event=event)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_event(self):
        """Get the next event"""
        # Using the token price from the previous round, decide whether we should make a transfer or not
        if self.synchronized_data.price < 2:
            event = Event.TRANSACT.value
        else:
            event = Event.DONE.value
        self.context.logger.info(f"Event is {event}")
        return event

# TODO: get safe tx hash from contract
class TxPreparationBehaviour(
    LearningBaseBehaviour
):  # pylint: disable=too-many-ancestors
    """TxPreparationBehaviour"""

    matching_round: Type[AbstractRound] = TxPreparationRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            safe_tx_hash = yield from self._build_safe_tx_hash()
            if safe_tx_hash is None:
                self.context.logger.error("Could not build the safe transaction's hash.")
                return None

            tx_hash = hash_payload_to_hex(
                safe_tx_hash,
                call_data[VALUE_KEY],
                SAFE_GAS,
                call_data[TO_ADDRESS_KEY],
                TX_DATA,
            )

            payload = TxPreparationPayload(
                sender=sender, tx_submitter=None, tx_hash=tx_hash
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


    def _build_safe_tx_hash(self) -> Generator[None, None, Optional[str]]:
        """Prepares and returns the safe tx hash for a multisend tx."""
        response_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.synchronized_data.safe_contract_address,
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            data=TX_DATA,
            safe_tx_gas=SAFE_GAS,
            chain_id=GNOSIS_CHAIN_ID,
            to_address=call_data[TO_ADDRESS_KEY],
            value=call_data[VALUE_KEY],
        )

        print(response_msg)

        if response_msg.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                "Couldn't get safe tx hash. Expected response performative "
                f"{ContractApiMessage.Performative.STATE.value!r}, "  # type: ignore
                f"received {response_msg.performative.value!r}: {response_msg}."
            )
            return None

        tx_hash = response_msg.state.body.get("tx_hash", None)
        if tx_hash is None or len(tx_hash) != TX_HASH_LENGTH:
            self.context.logger.error(
                "Something went wrong while trying to get the buy transaction's hash. "
                f"Invalid hash {tx_hash!r} was returned."
            )
            return None

        # strip "0x" from the response hash
        print("safe_tx_hash is: ")
        print(tx_hash[2:])
        return tx_hash[2:]


class LearningRoundBehaviour(AbstractRoundBehaviour):
    """LearningRoundBehaviour"""

    initial_behaviour_cls = APICheckBehaviour
    abci_app_cls = LearningAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [  # type: ignore
        APICheckBehaviour,
        LargeDataCheckBehaviour,
        DecisionMakingBehaviour,
        TxPreparationBehaviour,
    ]
