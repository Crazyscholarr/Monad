# Адреса контрактов
ROUTER_CONTRACT = "0xb6091233aAcACbA45225a2B2121BBaC807aF4255"
WMON_CONTRACT = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
USDC_CONTRACT = "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea"
USDT_CONTRACT = "0x88b8E2161DEDC77EF4ab7585569D2415a1C1055D"
TEST1_CONTRACT = "0xe42cFeCD310d9be03d3F80D605251d8D0Bc5cDF3"
TEST2_CONTRACT = "0x73c03bc8F8f094c61c668AE9833D7Ed6C04FDc21"
DAK_CONTRACT = "0x0F0BDEbF0F83cD1EE3974779Bcb7315f9808c714"

# ABI для контрактов
ABI = {
    "router": [
        {
            "type": "function",
            "name": "swapExactETHForTokens",
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "amountOutMin",
                    "type": "uint256",
                },
                {"internalType": "address[]", "name": "path", "type": "address[]"},
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            ],
            "outputs": [
                {
                    "internalType": "uint256[]",
                    "name": "amounts",
                    "type": "uint256[]",
                }
            ],
            "stateMutability": "payable",
        },
        {
            "type": "function",
            "name": "swapExactTokensForETH",
            "inputs": [
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "amountOutMin",
                    "type": "uint256",
                },
                {"internalType": "address[]", "name": "path", "type": "address[]"},
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            ],
            "outputs": [
                {
                    "internalType": "uint256[]",
                    "name": "amounts",
                    "type": "uint256[]",
                }
            ],
            "stateMutability": "nonpayable",
        },
        {
            "type": "function",
            "name": "swapExactTokensForTokens",
            "inputs": [
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "amountOutMin",
                    "type": "uint256",
                },
                {"internalType": "address[]", "name": "path", "type": "address[]"},
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            ],
            "outputs": [
                {
                    "internalType": "uint256[]",
                    "name": "amounts",
                    "type": "uint256[]",
                }
            ],
            "stateMutability": "nonpayable",
        },
        {
            "type": "function",
            "name": "getAmountsOut",
            "inputs": [
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"},
            ],
            "outputs": [
                {
                    "internalType": "uint256[]",
                    "name": "amounts",
                    "type": "uint256[]",
                }
            ],
            "stateMutability": "view",
        },
    ],
    "token": [
        {
            "type": "function",
            "name": "approve",
            "inputs": [
                {"name": "guy", "type": "address"},
                {"name": "wad", "type": "uint256"},
            ],
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
        },
        {
            "type": "function",
            "name": "balanceOf",
            "inputs": [{"name": "", "type": "address"}],
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
        },
        {
            "type": "function",
            "name": "decimals",
            "inputs": [],
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
        },
        {
            "type": "function",
            "name": "allowance",
            "inputs": [
                {"name": "", "type": "address"},
                {"name": "", "type": "address"},
            ],
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
        },
    ],
    "weth": [
        {
            "type": "function",
            "name": "deposit",
            "inputs": [],
            "outputs": [],
            "stateMutability": "payable",
        },
        {
            "type": "function",
            "name": "withdraw",
            "inputs": [{"name": "wad", "type": "uint256"}],
            "outputs": [],
            "stateMutability": "nonpayable",
        },
    ],
}

# Доступные токены
AVAILABLE_TOKENS = {
    "MON": {"name": "MON", "address": None, "decimals": 18, "native": True},
    "WMON": {
        "name": "WMON",
        "address": WMON_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "USDC": {
        "name": "USDC",
        "address": USDC_CONTRACT,
        "decimals": 6,
        "native": False,
    },
    "DAK": {
        "name": "DAK",
        "address": DAK_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "USDT": {
        "name": "USDT",
        "address": USDT_CONTRACT,
        "decimals": 6,
        "native": False,
    },
    "TEST1": {
        "name": "TEST1",
        "address": TEST1_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "TEST2": {
        "name": "TEST2",
        "address": TEST2_CONTRACT,
        "decimals": 18,
        "native": False,
    },
}
