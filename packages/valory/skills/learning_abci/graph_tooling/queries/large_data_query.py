# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 Valory AG
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

"""Network queries."""

from string import Template


large_data_query = Template(
    """
{
  pairs(first: $first) {
    id
    token0 {
      id
      symbol
      name
    }
    token1 {
      id
      symbol
      name
    }
    reserve0
    reserve1
    totalSupply
    reserveETH
    reserveUSD
    trackedReserveETH
    trackedReserveUSD
    token0Price
    token1Price
    volumeToken0
    volumeToken1
    volumeUSD
    txCount
    createdAtTimestamp
    createdAtBlockNumber
  }
}
"""
)

