from web3 import Web3

# Преобразуем все адреса в checksum
ROUTER_CONTRACT = Web3.to_checksum_address("0x64Aff7245EbdAAECAf266852139c67E4D8DBa4de")

# Token addresses
WMON_CONTRACT = Web3.to_checksum_address("0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701")
WETH_CONTRACT = Web3.to_checksum_address("0xB5a30b0FDc5EA94A52fDc42e3E9760Cb8449Fb37")
WSOL_CONTRACT = Web3.to_checksum_address("0x5387C85A4965769f6B0Df430638a1388493486F1")
USDT_CONTRACT = Web3.to_checksum_address("0x88b8E2161DEDC77EF4ab7585569D2415a1C1055D")
WBTC_CONTRACT = Web3.to_checksum_address("0xcf5a6076cfa32686c0Df13aBaDa2b40dec133F1d")
MAD_CONTRACT = Web3.to_checksum_address("0xC8527e96c3CB9522f6E35e95C0A28feAb8144f15")
USDC_CONTRACT = Web3.to_checksum_address("0xf817257fed379853cde0fa4f97ab987181b1e5ea")

# Available tokens for swaps
AVAILABLE_TOKENS = {
    "MON": {
        "name": "MON",
        "address": None,  # Native token doesn't have an address
        "decimals": 18,
        "native": True,
    },
    "WMON": {
        "name": "WMON",
        "address": WMON_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "WETH": {
        "name": "WETH",
        "address": WETH_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "WSOL": {
        "name": "WSOL",
        "address": WSOL_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "USDT": {
        "name": "USDT",
        "address": USDT_CONTRACT,
        "decimals": 6,
        "native": False,
    },
    "WBTC": {
        "name": "WBTC",
        "address": WBTC_CONTRACT,
        "decimals": 8,
        "native": False,
    },
    "MAD": {
        "name": "MAD",
        "address": MAD_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "USDC": {
        "name": "USDC",
        "address": USDC_CONTRACT,
        "decimals": 6,
        "native": False,
    },
}

# ABIs
ABI = {
    "router": [
        {
            "type": "constructor",
            "stateMutability": "nonpayable",
            "inputs": [
                {"type": "address", "name": "_factory", "internalType": "address"},
                {"type": "address", "name": "_WETH", "internalType": "address"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "view",
            "outputs": [{"type": "address", "name": "", "internalType": "address"}],
            "name": "WETH",
            "inputs": [],
        },
        {
            "type": "function",
            "stateMutability": "nonpayable",
            "outputs": [
                {"type": "uint256", "name": "amountA", "internalType": "uint256"},
                {"type": "uint256", "name": "amountB", "internalType": "uint256"},
                {"type": "uint256", "name": "liquidity", "internalType": "uint256"},
            ],
            "name": "addLiquidity",
            "inputs": [
                {"type": "address", "name": "tokenA", "internalType": "address"},
                {"type": "address", "name": "tokenB", "internalType": "address"},
                {
                    "type": "uint256",
                    "name": "amountADesired",
                    "internalType": "uint256",
                },
                {
                    "type": "uint256",
                    "name": "amountBDesired",
                    "internalType": "uint256",
                },
                {"type": "uint256", "name": "amountAMin", "internalType": "uint256"},
                {"type": "uint256", "name": "amountBMin", "internalType": "uint256"},
                {"type": "address", "name": "to", "internalType": "address"},
                {"type": "uint256", "name": "deadline", "internalType": "uint256"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "payable",
            "outputs": [
                {"type": "uint256", "name": "amountToken", "internalType": "uint256"},
                {"type": "uint256", "name": "amountETH", "internalType": "uint256"},
                {"type": "uint256", "name": "liquidity", "internalType": "uint256"},
            ],
            "name": "addLiquidityETH",
            "inputs": [
                {"type": "address", "name": "token", "internalType": "address"},
                {
                    "type": "uint256",
                    "name": "amountTokenDesired",
                    "internalType": "uint256",
                },
                {
                    "type": "uint256",
                    "name": "amountTokenMin",
                    "internalType": "uint256",
                },
                {"type": "uint256", "name": "amountETHMin", "internalType": "uint256"},
                {"type": "address", "name": "to", "internalType": "address"},
                {"type": "uint256", "name": "deadline", "internalType": "uint256"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "view",
            "outputs": [{"type": "address", "name": "", "internalType": "address"}],
            "name": "factory",
            "inputs": [],
        },
        {
            "type": "function",
            "stateMutability": "pure",
            "outputs": [
                {"type": "uint256", "name": "amountIn", "internalType": "uint256"}
            ],
            "name": "getAmountIn",
            "inputs": [
                {"type": "uint256", "name": "amountOut", "internalType": "uint256"},
                {"type": "uint256", "name": "reserveIn", "internalType": "uint256"},
                {"type": "uint256", "name": "reserveOut", "internalType": "uint256"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "pure",
            "outputs": [
                {"type": "uint256", "name": "amountOut", "internalType": "uint256"}
            ],
            "name": "getAmountOut",
            "inputs": [
                {"type": "uint256", "name": "amountIn", "internalType": "uint256"},
                {"type": "uint256", "name": "reserveIn", "internalType": "uint256"},
                {"type": "uint256", "name": "reserveOut", "internalType": "uint256"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "view",
            "outputs": [
                {"type": "uint256[]", "name": "amounts", "internalType": "uint256[]"}
            ],
            "name": "getAmountsIn",
            "inputs": [
                {"type": "uint256", "name": "amountOut", "internalType": "uint256"},
                {"type": "address[]", "name": "path", "internalType": "address[]"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "view",
            "outputs": [
                {"type": "uint256[]", "name": "amounts", "internalType": "uint256[]"}
            ],
            "name": "getAmountsOut",
            "inputs": [
                {"type": "uint256", "name": "amountIn", "internalType": "uint256"},
                {"type": "address[]", "name": "path", "internalType": "address[]"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "payable",
            "outputs": [
                {"type": "uint256[]", "name": "amounts", "internalType": "uint256[]"}
            ],
            "name": "swapExactETHForTokens",
            "inputs": [
                {"type": "uint256", "name": "amountOutMin", "internalType": "uint256"},
                {"type": "address[]", "name": "path", "internalType": "address[]"},
                {"type": "address", "name": "to", "internalType": "address"},
                {"type": "uint256", "name": "deadline", "internalType": "uint256"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "nonpayable",
            "outputs": [
                {"type": "uint256[]", "name": "amounts", "internalType": "uint256[]"}
            ],
            "name": "swapExactTokensForETH",
            "inputs": [
                {"type": "uint256", "name": "amountIn", "internalType": "uint256"},
                {"type": "uint256", "name": "amountOutMin", "internalType": "uint256"},
                {"type": "address[]", "name": "path", "internalType": "address[]"},
                {"type": "address", "name": "to", "internalType": "address"},
                {"type": "uint256", "name": "deadline", "internalType": "uint256"},
            ],
        },
        {
            "type": "function",
            "stateMutability": "nonpayable",
            "outputs": [
                {"type": "uint256[]", "name": "amounts", "internalType": "uint256[]"}
            ],
            "name": "swapExactTokensForTokens",
            "inputs": [
                {"type": "uint256", "name": "amountIn", "internalType": "uint256"},
                {"type": "uint256", "name": "amountOutMin", "internalType": "uint256"},
                {"type": "address[]", "name": "path", "internalType": "address[]"},
                {"type": "address", "name": "to", "internalType": "address"},
                {"type": "uint256", "name": "deadline", "internalType": "uint256"},
            ],
        },
    ],
    "token": [
        {
            "inputs": [],
            "name": "decimals",
            "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "account", "type": "address"}
            ],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "spender", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
            ],
            "name": "approve",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "owner", "type": "address"},
                {"internalType": "address", "name": "spender", "type": "address"},
            ],
            "name": "allowance",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ],
    "weth": [
        {
            "constant": True,
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"name": "guy", "type": "address"},
                {"name": "wad", "type": "uint256"},
            ],
            "name": "approve",
            "outputs": [{"name": "", "type": "bool"}],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"name": "src", "type": "address"},
                {"name": "dst", "type": "address"},
                {"name": "wad", "type": "uint256"},
            ],
            "name": "transferFrom",
            "outputs": [{"name": "", "type": "bool"}],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [{"name": "wad", "type": "uint256"}],
            "name": "withdraw",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [{"name": "", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"name": "dst", "type": "address"},
                {"name": "wad", "type": "uint256"},
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [],
            "name": "deposit",
            "outputs": [],
            "payable": True,
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [
                {"name": "", "type": "address"},
                {"name": "", "type": "address"},
            ],
            "name": "allowance",
            "outputs": [{"name": "", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {"payable": True, "stateMutability": "payable", "type": "fallback"},
    ],
}
