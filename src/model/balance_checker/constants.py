CONTRACT_ADDRESS = "0xe1bEECa48cA52f9475A27891844022d4C49FFde1"
CONTRACT_ABI = [{"constant":True,"inputs":[{"name":"user","type":"address"},{"name":"token","type":"address"}],"name":"tokenBalance","outputs":[{"name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"name":"users","type":"address[]"},{"name":"tokens","type":"address[]"}],"name":"balances","outputs":[{"name":"","type":"uint256[]"}],"payable":False,"stateMutability":"view","type":"function"},{"payable":True,"stateMutability":"payable","type":"fallback"}]

TOKENS = {
    "mon": {
        "address": "0x0000000000000000000000000000000000000000",
        "decimals": 18
    },
    "weth": {
        "address": "0xB5a30b0FDc5EA94A52fDc42e3E9760Cb8449Fb37",
        "decimals": 18
    },
    "wmon": {
        "address": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",
        "decimals": 18
    },
    "seth": {
        "address": "0x836047a99e11F376522B447bffb6e3495Dd0637c",
        "decimals": 18
    },
    "usdc": {
        "address": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",
        "decimals": 6
    },

}