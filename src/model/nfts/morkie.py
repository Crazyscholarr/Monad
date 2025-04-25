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


class Morkie:
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

        # Изменяем адрес контракта на MonAI Qingyi (Week2NFT)
        self.monhog_contract_address = Web3.to_checksum_address(
            "0x8fb9EeDC9ae174C22B87FC8Cb87B902373D2a284"
        )  # price 0.5 MON
        self.monarch_contract_address = Web3.to_checksum_address(
            "0x0442309dC7f467F380836de685b650A3F1C10CF7"
        )  # price 0.1 MON
        self.morkie_contract_address = Web3.to_checksum_address(
            "0xdC8eDF8e9cA33EDBBd81b42b303bFE12298E717E"
        )  # price 0

        # Создаем контракты для каждого NFT
        self.monhog_contract = self.web3.eth.contract(
            address=self.monhog_contract_address, abi=MONAI_YAKUZA_ABI
        )
        self.monarch_contract = self.web3.eth.contract(
            address=self.monarch_contract_address, abi=MONAI_YAKUZA_ABI
        )
        self.morkie_contract = self.web3.eth.contract(
            address=self.morkie_contract_address, abi=MONAI_QINGYI_ABI
        )

        # Адрес для реферала (используйте свой или нулевой адрес)
        self.refer_address = Web3.to_checksum_address(
            "0x0000000000000000000000000000000000000000"
        )

    async def get_nft_balance(self, contract: Contract) -> int:
        """
        Проверяет баланс NFT для текущего аккаунта
        Args:
            contract: контракт NFT
        Returns:
            int: количество NFT
        """
        try:
            balance = await contract.functions.balanceOf(self.account.address).call()

            return balance
        except Exception as e:
            logger.error(f"[{self.account_index}] Error checking NFT balance: {e}")
            return 0

    async def mint_monhog(self):
        """Минтит Monhog NFT с использованием специального payload"""
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                balance = await self.get_nft_balance(self.monhog_contract)

                if balance >= 1:
                    logger.success(f"[{self.account_index}] Monhog NFT already minted")
                    return True

                logger.info(f"[{self.account_index}] Minting Monhog NFT")

                # Создаем специальный payload для Monhog
                # Заменяем адрес в payload на адрес текущего кошелька (без 0x)
                wallet_address_without_0x = self.account.address[2:].lower()

                # Базовый payload с замененным адресом
                payload = f"0x84bb1e42000000000000000000000000{wallet_address_without_0x}0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee00000000000000000000000000000000000000000000000006f05b59d3b2000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000016000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

                # Создаем транзакцию для оценки газа
                tx_for_estimate = {
                    "from": self.account.address,
                    "to": self.monhog_contract_address,
                    "value": self.web3.to_wei(0.5, "ether"),  # 0.5 MON для минта
                    "data": payload,
                    "chainId": 10143,  # Добавляем Chain ID
                }

                # Получаем оценку газа
                try:
                    estimated_gas = await self.web3.eth.estimate_gas(tx_for_estimate)
                    # Добавляем запас газа (+30%)
                    estimated_gas = int(estimated_gas * 1.3)
                except Exception as e:
                    logger.error(f"[{self.account_index}] Failed to estimate gas: {e}")
                    raise

                # Создаем окончательную транзакцию с полученным gas
                tx = {
                    "from": self.account.address,
                    "to": self.monhog_contract_address,
                    "value": self.web3.to_wei(0.5, "ether"),  # 0.5 MON для минта
                    "data": payload,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address
                    ),
                    "chainId": 10143,  # Добавляем Chain ID
                    "maxFeePerGas": await self.web3.eth.gas_price,
                    "maxPriorityFeePerGas": await self.web3.eth.gas_price,
                    "gas": estimated_gas,
                }

                # Подписываем транзакцию
                signed_txn = self.web3.eth.account.sign_transaction(
                    tx, self.private_key
                )

                # Отправляем транзакцию
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Ждем подтверждения
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully minted Monhog NFT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    logger.error(
                        f"[{self.account_index}] Failed to mint Monhog NFT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return False

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in mint Monhog: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)

        return False

    async def mint_monarch(self):
        """Минтит Monarch NFT с использованием специального payload"""
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                balance = await self.get_nft_balance(self.monarch_contract)

                if balance >= 1:
                    logger.success(f"[{self.account_index}] Monarch NFT already minted")
                    return True

                logger.info(f"[{self.account_index}] Minting Monarch NFT")

                # Создаем специальный payload для Monarch
                # Заменяем адрес в payload на адрес текущего кошелька (без 0x)
                wallet_address_without_0x = self.account.address[2:].lower()

                # Базовый payload с замененным адресом
                payload = f"0x84bb1e42000000000000000000000000{wallet_address_without_0x}0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee000000000000000000000000000000000000000000000000016345785d8a000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000016000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

                # Создаем транзакцию для оценки газа
                tx_for_estimate = {
                    "from": self.account.address,
                    "to": self.monarch_contract_address,
                    "value": self.web3.to_wei(0.1, "ether"),  # 0.1 MON для минта
                    "data": payload,
                    "chainId": 10143,  # Добавляем Chain ID
                }

                # Получаем оценку газа
                try:
                    estimated_gas = await self.web3.eth.estimate_gas(tx_for_estimate)
                    # Добавляем запас газа (+30%)
                    estimated_gas = int(estimated_gas * 1.3)
                except Exception as e:
                    logger.error(f"[{self.account_index}] Failed to estimate gas: {e}")
                    raise

                # Создаем окончательную транзакцию с полученным gas
                tx = {
                    "from": self.account.address,
                    "to": self.monarch_contract_address,
                    "value": self.web3.to_wei(0.1, "ether"),  # 0.1 MON для минта
                    "data": payload,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address
                    ),
                    "chainId": 10143,  # Добавляем Chain ID
                    "maxFeePerGas": await self.web3.eth.gas_price,
                    "maxPriorityFeePerGas": await self.web3.eth.gas_price,
                    "gas": estimated_gas,
                }

                # Подписываем транзакцию
                signed_txn = self.web3.eth.account.sign_transaction(
                    tx, self.private_key
                )

                # Отправляем транзакцию
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Ждем подтверждения
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully minted Monarch NFT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    logger.error(
                        f"[{self.account_index}] Failed to mint Monarch NFT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return False

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in mint Monarch: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)

        return False

    async def mint_morkie(self):
        """Минтит Morkie NFT (бесплатный)"""
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                random_nft_amount = random.randint(
                    self.config.MORKIE.MAX_PER_ACCOUNT[0],
                    self.config.MORKIE.MAX_PER_ACCOUNT[1],
                )
                balance = await self.get_nft_balance(self.morkie_contract)

                if balance >= random_nft_amount:
                    logger.success(f"[{self.account_index}] Morkie NFT already minted")
                    return True

                logger.info(f"[{self.account_index}] Minting Morkie NFT")

                # Создаем объект транзакции для оценки газа
                tx_params = {
                    "from": self.account.address,
                    "value": 0,  # бесплатный минт
                    "chainId": 10143,  # Добавляем Chain ID
                }

                # Получаем оценку газа
                try:
                    estimated_gas = await self.morkie_contract.functions.mint(
                        1,  # quantity - минтим 1 NFT
                        self.refer_address,  # refer - адрес реферала
                    ).estimate_gas(tx_params)
                    # Добавляем запас газа (+30%)
                    estimated_gas = int(estimated_gas * 1.3)
                except Exception as e:
                    logger.error(f"[{self.account_index}] Failed to estimate gas: {e}")
                    raise

                # Подготавливаем транзакцию минта
                mint_txn = await self.morkie_contract.functions.mint(
                    1,  # quantity - минтим 1 NFT
                    self.refer_address,  # refer - адрес реферала
                ).build_transaction(
                    {
                        "from": self.account.address,
                        "value": 0,  # бесплатный минт
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address
                        ),
                        "chainId": 10143,  # Добавляем Chain ID
                        "maxFeePerGas": await self.web3.eth.gas_price,
                        "maxPriorityFeePerGas": await self.web3.eth.gas_price,
                        "gas": estimated_gas,
                    }
                )

                # Подписываем транзакцию
                signed_txn = self.web3.eth.account.sign_transaction(
                    mint_txn, self.private_key
                )

                # Отправляем транзакцию
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Ждем подтверждения
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully minted Morkie NFT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    logger.error(
                        f"[{self.account_index}] Failed to mint Morkie NFT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return False

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in mint Morkie: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)

        return False
