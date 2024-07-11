## Learning Service

A service to learn about [Olas](https://olas.network/) agents and [Open Autonomy](https://github.com/valory-xyz/open-autonomy).


## System requirements

- Python `>=3.10`
- [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Pip](https://pip.pypa.io/en/stable/installation/)
- [Poetry](https://python-poetry.org/)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Set Docker permissions so you can run containers as non-root user](https://docs.docker.com/engine/install/linux-postinstall/)


## Run you own agent

### Get the code

1. Clone this repo:

    ```
    git clone git@github.com:valory-xyz/academy-learning-service-template.git
    ```

2. Create the virtual environment:

    ```
    cd academy-learning-service
    poetry shell
    poetry install
    ```

3. Sync packages:

    ```
    autonomy packages sync --update-packages
    ```

### Prepare the data

1. Prepare a `keys.json` file containing wallet address and the private key for each of the four agents.

    ```
    autonomy generate-key ethereum -n 4
    ```

2. Prepare a `ethereum_private_key.txt` file containing one of the private keys from `keys.json`. Ensure that there is no newline at the end.

3. Deploy a [Safe on Gnosis](https://app.safe.global/welcome) (it's free) and set your agent addresses as signers. Set the signature threshold to 3 out of 4.

4. Fund your agents and Safe with a small amount of xDAI, i.e. $0.02 each.

5. Make a copy of the env file:

    ```
    cp sample.env .env
    ```

6. Fill in the required environment variables in .env. These variables are: `ALL_PARTICIPANTS`, `GNOSIS_LEDGER_RPC`, `COINGECKO_API_KEY` and `SAFE_CONTRACT_ADDRESS`. You will need to get a [Coingecko](https://www.coingecko.com/) free API and a [Tenderly](https://tenderly.co/) fork RPC (or alternatively an actual mainnet RPC if you want to run against the real chain).


### Run the service

1. Check that Docker is running:

    ```
    docker
    ```

2. Run the service:

    ```
    bash run_service.sh
    ```

3. Look at the service logs (on another terminal):

    ```
    docker logs -f learningservice_abci_0
    ```


### Run a single agent

1. Run the agent:

    ```
    bash run_agent.sh
    ```