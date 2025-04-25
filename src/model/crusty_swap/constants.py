CRUSTY_SWAP_RPCS = {
    "Arbitrum": "https://arb1.lava.build",
    "Optimism": "https://optimism.lava.build",
    "Base": "https://base.lava.build",
    # "ZkSync": "https://mainnet.era.zksync.io",
}

CONTRACT_ADDRESSES = {
    "Arbitrum": "0x3f82E0e8c853d1C8B4deB68b09b379ec25C2B0ee",
    # "ZkSync": "0xcD5D7Ed8C081a60D7A1436937cE944F671204280",
    "Optimism": "0x3f82E0e8c853d1C8B4deB68b09b379ec25C2B0ee",
    "Base": "0x3f82E0e8c853d1C8B4deB68b09b379ec25C2B0ee"
}

REFUEL_FROM_ONE_TO_ALL_CONTRACT_ADDRESS = {
    "Arbitrum": "0x16c434A25A71DF00551BDD392a3d761ABf74BB51",
    # "ZkSync": "0x7b72A471A37f248c47FA1845AE62A21210C25155",
    "Optimism": "0x16c434A25A71DF00551BDD392a3d761ABf74BB51",
    "Base": "0x16c434A25A71DF00551BDD392a3d761ABf74BB51"
}


REFUEL_FROM_ONE_TO_ALL_CONTRACT_ABI = [
    {
      "inputs": [
          {
              "internalType": "address",
              "name": "referrer",
              "type": "address"
          },
          {
              "internalType": "address",
              "name": "recipient", 
              "type": "address"
          }
      ],
      "name": "deposit",
      "outputs": [],
      "stateMutability": "payable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "sellMonad",
      "outputs": [],
      "stateMutability": "payable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "pricePerMonad",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "minimumSell",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "getAvailableCapacity",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "minimumDeposit",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    }
] 

EXPLORER_URLS = {
    "Arbitrum": "https://arbiscan.io/tx/0x",
    # "ZkSync": "https://explorer.zksync.io/tx/0x",
    "Optimism": "https://optimistic.etherscan.io/tx/0x",
    "Base": "https://basescan.org/tx/0x"
}

DESTINATION_CONTRACT_ADDRESS = "0x3f82E0e8c853d1C8B4deB68b09b379ec25C2B0ee"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
CRUSTY_SWAP_ABI = [
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "referrer",
          "type": "address"
        }
      ],
      "name": "deposit",
      "outputs": [],
      "stateMutability": "payable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "sellMonad",
      "outputs": [],
      "stateMutability": "payable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "pricePerMonad",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "minimumSell",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "getAvailableCapacity",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "minimumDeposit",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    }
]

CHAINLINK_ETH_PRICE_CONTRACT_ADDRESS = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"
CHAINLINK_ETH_PRICE_ABI = [
    {
        "inputs":[],
        "name":"latestAnswer",
        "outputs":[{"internalType":"int256","name":"","type":"int256"}],
        "stateMutability":"view",
        "type":"function"}
]