TESTNET_BRIDGE_RPCS = {
    "Arbitrum": "https://arb1.lava.build",
    "Optimism": "https://optimism.lava.build",
    "Sepolia": "https://sepolia.drpc.org",
}

TESTNET_BRIDGE_EXPLORERS = {
    "Arbitrum": "https://arbiscan.io/tx/0x",
    "Optimism": "https://optimistic.etherscan.io/tx/0x",
}   

TESTNET_BRIDGE_ADDRESS = {
    "Arbitrum": "0xfcA99F4B5186D4bfBDbd2C542dcA2ecA4906BA45",
    "Optimism": "0x8352C746839699B1fc631fddc0C3a00d4AC71A17",
}

ESTIMATE_SEND_FEE_CONTRACT_ADDRESS = "0xE71bDfE1Df69284f00EE185cf0d95d0c7680c0d4"


TESTNET_BRIDGE_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "uint16", "name": "dstChainId", "type": "uint16"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "address payable", "name": "refundAddress", "type": "address"},
            {"internalType": "address", "name": "zroPaymentAddress", "type": "address"},
            {"internalType": "bytes", "name": "adapterParams", "type": "bytes"}
        ],
        "name": "swapAndBridge",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "_dstChainId", "type": "uint16"},
            {"internalType": "bytes", "name": "_toAddress", "type": "bytes"},
            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            {"internalType": "bool", "name": "_useZro", "type": "bool"},
            {"internalType": "bytes", "name": "_adapterParams", "type": "bytes"}
        ],
        "name": "estimateSendFee",
        "outputs": [
            {"internalType": "uint256", "name": "nativeFee", "type": "uint256"},
            {"internalType": "uint256", "name": "zroFee", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

