import asyncio
import random
from eth_account import Account
from primp import AsyncClient
from web3 import AsyncWeb3, Web3
from web3.contract import Contract

from src.utils.constants import EXPLORER_URL, RPC_URL
from src.utils.config import Config
from loguru import logger

# Обновляем ABI для ERC1155
# Обновляем ABI для MonAI Yakuza NFT
MONAI_YAKUZA_ABI = [
    {
        "type": "function",
        "name": "mint",
        "inputs": [
            {"name": "quantity", "type": "uint256", "internalType": "uint256"},
            {"name": "refer", "type": "address", "internalType": "address"},
        ],
        "outputs": [],
        "stateMutability": "payable",
    },
    {
        "type": "function",
        "name": "balanceOf",
        "inputs": [{"name": "owner", "type": "address", "internalType": "address"}],
        "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
        "stateMutability": "view",
    },
]

# Обновляем ABI для MonAI Qingyi NFT
MONAI_QINGYI_ABI = [
    {
        "type": "function",
        "name": "mint",
        "inputs": [
            {"name": "quantity", "type": "uint256", "internalType": "uint256"},
            {"name": "refer", "type": "address", "internalType": "address"},
        ],
        "outputs": [],
        "stateMutability": "payable",
    },
    {
        "type": "function",
        "name": "balanceOf",
        "inputs": [{"name": "owner", "type": "address", "internalType": "address"}],
        "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
        "stateMutability": "view",
    },
]


class Nerzo:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        private_key: str,
        config: Config,
        session: AsyncClient,
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = private_key
        self.config = config
        self.session = session

        self.account: Account = Account.from_key(private_key=private_key)
        self.web3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(
                RPC_URL,
                request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
            )
        )

        # Изменяем адрес контракта на новый
        self.nft_contract_address = Web3.to_checksum_address(
            "0xe7D728CdBfa400EFDdB26ACc532B5006A3cdec68"
        )
        # Используем MONAI_QINGYI_ABI вместо MONAI_YAKUZA_ABI
        self.nft_contract: Contract = self.web3.eth.contract(
            address=self.nft_contract_address, abi=MONAI_QINGYI_ABI
        )
        # Адрес для реферала
        self.refer_address = Web3.to_checksum_address(
            "0xf8dd242cf234ecfcbfaba05e35fef5ff57cb9c0b"
        )

    async def get_nft_balance(self) -> int:
        """
        Проверяет баланс NFT для текущего аккаунта
        Returns:
            int: количество NFT
        """
        try:
            balance = await self.nft_contract.functions.balanceOf(
                self.account.address
            ).call()

            return balance
        except Exception as e:
            logger.error(f"[{self.account_index}] Error checking NFT balance: {e}")
            return 0

    async def mint(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                logger.info(f"[{self.account_index}] Minting Nerzo Soulbound")

                # Адрес контракта
                contract_address = Web3.to_checksum_address(
                    "0xe7D728CdBfa400EFDdB26ACc532B5006A3cdec68"
                )

                # Получаем адрес кошелька без 0x для пейлоада
                wallet_address_without_0x = self.account.address[2:].lower()

                # Формируем данные для пейлоада - метод claim с адресом кошелька
                data = f"0x84bb1e42000000000000000000000000{wallet_address_without_0x}0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000016000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

                # Формируем предварительную транзакцию для расчета газа
                transaction = {
                    "from": self.account.address,
                    "to": contract_address,
                    "value": 0,
                    "data": data,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address
                    ),
                    "maxFeePerGas": await self.web3.eth.gas_price,
                    "maxPriorityFeePerGas": await self.web3.eth.gas_price,
                    "chainId": 10143,
                }

                # Получаем оценку газа
                try:
                    estimated_gas = await self.web3.eth.estimate_gas(transaction)
                    # Добавляем небольшой запас для надежности (10%)
                    gas_limit = int(estimated_gas * 1.1)
                except Exception as gas_error:
                    raise gas_error

                # Добавляем gas_limit в транзакцию
                transaction["gas"] = gas_limit

                # Подписываем транзакцию
                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )

                # Отправляем транзакцию
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Ждем подтверждения
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully minted Nerzo Soulbound. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    logger.error(
                        f"[{self.account_index}] Transaction failed. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return False

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error sending transaction: {e}. Pause {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)

        return False
