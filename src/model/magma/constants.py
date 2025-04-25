STAKE_ADDRESS = "0x2c9C959516e9AAEdB2C748224a41249202ca8BE7"
STAKED_TOKEN = "0xaEef2f6B429Cb59C9B2D7bB2141ADa993E8571c3"

STAKE_ABI = [
    {
        "type": "function",
        "name": "stake",  # используем произвольное имя функции
        "inputs": [],
        "outputs": [],
        "stateMutability": "payable",
        "signature": "0xd5575982"  # важно: используем точную сигнатуру из успешной транзакции
    },
    {
        "type": "function",
        "name": "withdrawMon",
        "inputs": [{"name": "amount", "type": "uint256", "internalType": "uint256"}],
        "outputs": [],
        "stateMutability": "nonpayable"
    }
]

