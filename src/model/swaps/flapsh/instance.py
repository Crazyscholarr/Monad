import time
import json
import random
import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Union, Tuple
from web3 import AsyncWeb3, Web3
from web3.contract import Contract
from web3.types import TxParams, Wei, ChecksumAddress
from eth_account import Account
from loguru import logger
from primp import AsyncClient
import aiohttp

from src.utils.config import Config
from src.utils.constants import EXPLORER_URL, RPC_URL


class Flapsh:
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

        # Создаем аккаунт из приватного ключа
        self.account: Account = Account.from_key(private_key=private_key)

        # Создаем настроенный Web3 клиент с middleware для повторных попыток
        self.web3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(
                RPC_URL,
                request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
            )
        )

    async def execute(self):
        """
        Основной метод для выполнения операций покупки мемкоинов.
        Берет настройки из конфигурационного файла:
        - количество покупок
        - сумму для каждой покупки
        - адреса токенов для покупки
        Если адреса в конфиге не указаны, получает их через API.
        """
        try:
            # Получаем настройки из конфига
            amount_range = self.config.FLAPSH.AMOUNT_TO_PAY
            number_of_buys_range = self.config.FLAPSH.NUMBER_OF_MEMCOINS_TO_BUY
            token_addresses = self.config.FLAPSH.TOKEN_ADDRESS

            # Если адреса токенов не указаны в конфиге, получаем их через API
            if not token_addresses:
                logger.info(
                    "No token addresses specified in config, fetching from API..."
                )
                token_addresses = await self._parse_tokens()

                if not token_addresses:
                    logger.error("Failed to get token addresses from API")
                    return False

                logger.info(
                    f"Successfully fetched {len(token_addresses)} token addresses from API"
                )

            # Определяем случайное количество операций покупки
            number_of_buys = random.randint(
                number_of_buys_range[0], number_of_buys_range[1]
            )

            logger.info(
                f"[Account #{self.account_index}] Planning to perform {number_of_buys} memcoin purchases"
            )

            # Получаем начальный баланс кошелька
            initial_balance = await self.web3.eth.get_balance(self.account.address)
            initial_balance_eth = Web3.from_wei(initial_balance, "ether")

            logger.info(f"Initial wallet balance: {initial_balance_eth} MON")

            # Выполняем заданное количество покупок
            successful_buys = 0

            for i in range(number_of_buys):
                # Выбираем случайный токен из списка
                token_address = random.choice(token_addresses)

                # Генерируем случайную сумму для покупки
                amount_to_pay = random.uniform(amount_range[0], amount_range[1])
                amount_to_pay = round(
                    amount_to_pay, 6
                )  # Округляем до 6 знаков после запятой

                # Проверяем баланс перед покупкой
                current_balance = await self.web3.eth.get_balance(self.account.address)
                current_balance_eth = Web3.from_wei(current_balance, "ether")

                # Учитываем газ (примерно 0.01 MON)
                if current_balance_eth < amount_to_pay + 0.01:
                    logger.warning(
                        f"[Buy {i+1}/{number_of_buys}] Insufficient balance for purchase: {current_balance_eth} MON"
                    )
                    continue

                logger.info(
                    f"[Buy {i+1}/{number_of_buys}] Purchasing token: {token_address}"
                    f" for {amount_to_pay} MON"
                )

                try:
                    # Выполняем покупку токена
                    tx_hash = await self.buy(token_address, amount_to_pay)
                    successful_buys += 1

                    # Добавляем случайную паузу между покупками
                    if i < number_of_buys - 1:
                        pause_time = random.uniform(
                            self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[0],
                            self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[1],
                        )
                        logger.info(
                            f"Waiting {pause_time:.2f} seconds before next purchase"
                        )
                        await asyncio.sleep(pause_time)

                except Exception as e:
                    logger.error(
                        f"[Buy {i+1}/{number_of_buys}] Error during purchase: {str(e)}"
                    )
                    continue

            # Получаем конечный баланс
            final_balance = await self.web3.eth.get_balance(self.account.address)
            final_balance_eth = Web3.from_wei(final_balance, "ether")

            spent = initial_balance_eth - final_balance_eth

            logger.info(
                f"Completed {successful_buys}/{number_of_buys} planned purchases"
            )
            logger.info(f"Final wallet balance: {final_balance_eth} MON")
            logger.info(f"Total spent (including fees): {spent} MON")

            return successful_buys > 0

        except Exception as e:
            logger.error(f"Error during execution: {str(e)}")
            return False

    async def buy(self, token_address: str, amount_to_pay: float) -> str:
        """
        Отправляет транзакцию на покупку токена через swap-контракт.

        Args:
            token_address: Адрес контракта токена для покупки
            amount_to_pay: Количество нативной валюты (MON) для оплаты, в эфирах

        Returns:
            Хеш транзакции
        """
        # Адрес контракта свопа
        swap_contract_address = "0x4267F317adee7C6478a5EE92985c2BD5D855E274"

        # Преобразуем адрес токена в правильный формат
        if token_address.startswith("0x"):
            token_address = token_address[2:]
        token_address = "0x" + token_address.lower()

        # Преобразуем эфиры в wei
        value_in_wei = Web3.to_wei(amount_to_pay, "ether")

        # Формируем data для транзакции (функция buy)
        function_selector = "0x153e66e6"  # Селектор функции buy

        # Форматируем параметры: token_address, recipient_address, min_amount
        # Адрес токена - параметр 1
        token_param = token_address.replace("0x", "").zfill(64)

        # Адрес получателя (наш кошелек) - параметр 2
        recipient_param = self.account.address.replace("0x", "").zfill(64)

        # Минимальное количество токенов (0) - параметр 3
        min_amount_param = "0".zfill(64)

        # Составляем полный payload
        data = function_selector + token_param + recipient_param + min_amount_param

        # Получаем текущую цену газа
        gas_price = await self.web3.eth.gas_price

        # Составляем транзакцию
        tx = {
            "from": self.account.address,
            "to": Web3.to_checksum_address(swap_contract_address),
            "value": value_in_wei,
            "gas": await self._estimate_gas_or_default(
                {
                    "from": self.account.address,
                    "to": Web3.to_checksum_address(swap_contract_address),
                    "value": value_in_wei,
                    "data": data,
                }
            ),
            "gasPrice": gas_price,
            "nonce": await self.web3.eth.get_transaction_count(self.account.address),
            "data": data,
            "chainId": await self.web3.eth.chain_id,
        }

        try:
            # Подписываем транзакцию
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)

            # Отправляем транзакцию
            tx_hash = await self.web3.eth.send_raw_transaction(
                signed_tx.raw_transaction
            )
            tx_hash_hex = tx_hash.hex()

            # Ждем подтверждения транзакции
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] == 1:
                logger.success(
                    f"Transaction successful: {EXPLORER_URL}{tx_hash_hex}"
                )
            else:
                logger.error(f"Transaction failed: {EXPLORER_URL}/tx/{tx_hash_hex}")

            return tx_hash_hex

        except Exception as e:
            logger.error(f"Error sending transaction: {str(e)}")
            raise

    async def _estimate_gas_or_default(self, tx_params, multiplier=1.2):
        """
        Оценивает количество газа для транзакции.
        Если оценка не удалась, возвращает значение по умолчанию.

        Args:
            tx_params: Параметры транзакции для оценки
            default_gas: Значение газа по умолчанию, если оценка не удалась
            multiplier: Множитель для увеличения оценки (запас)

        Returns:
            Оценка газа с запасом или значение по умолчанию
        """
        try:
            # Пытаемся получить оценку газа
            estimated_gas = await self.web3.eth.estimate_gas(tx_params)
            gas_with_buffer = int(estimated_gas * multiplier)
            return gas_with_buffer

        except Exception as e:
            raise e

    async def _parse_tokens(self) -> List[str] | None:
        """
        Получает список адресов токенов с API Flapsh.
        Использует aiohttp и настроенный прокси.

        Returns:
            Список адресов контрактов или None в случае ошибки
        """
        # Преобразуем формат прокси из "user:pass@ip:port" в http://user:pass@ip:port
        proxy_url = f"http://{self.proxy}"

        for retry in range(3):
            try:
                headers = {
                    "accept": "*/*",
                    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5",
                    "content-type": "text/plain;charset=UTF-8",
                    "origin": "https://monad.flap.sh",
                    "referer": "https://monad.flap.sh/",
                    "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                }

                data = '{"query":"\\nquery Coins($options:CoinsOptions) {\\n  coins(options:$options) {\\n    name\\n    address\\n    symbol\\n    createdAt\\n    creator\\n    meta\\n    merged\\n    sequence\\n    messagesCount\\n    listed\\n    mode\\n    r(round: 3)\\n    version\\n    dexThreshSupply\\n    reserve(round: 18)\\n    marketcap(round: 18)\\n    supply(round: 18)\\n    author {\\n      name\\n      pfp\\n    }\\n    metadata {\\n      description\\n      image\\n      website\\n      twitter\\n      telegram\\n    }\\n  }\\n}\\n","variables":{"options":{"asc":false,"sort":1,"limit":50,"offset":0,"duel":false,"listed":false}}}'

                api_url = "https://v8xq3y0pc5.execute-api.eu-west-3.amazonaws.com/v1"

                # Используем контекстный менеджер для сессии aiohttp
                async with aiohttp.ClientSession() as session:
                    # Настраиваем прокси для запроса
                    async with session.post(
                        api_url,
                        headers=headers,
                        data=data,
                        proxy=proxy_url,
                        ssl=False,  # Отключаем проверку SSL
                    ) as response:
                        if response.status != 200:
                            logger.error(
                                f"API returned non-200 status: {response.status}"
                            )
                            continue

                        response_json = await response.json()

                        # Проверяем структуру ответа
                        if (
                            "data" not in response_json
                            or "coins" not in response_json["data"]
                        ):
                            logger.error("Invalid API response structure")
                            continue

                        # Извлекаем адреса контрактов
                        contracts = []
                        for coin in response_json["data"]["coins"]:
                            try:
                                if "address" in coin and coin["address"]:
                                    contracts.append(coin["address"])
                            except Exception as e:
                                logger.warning(
                                    f"Error extracting contract address: {str(e)}"
                                )
                                continue

                        if not contracts:
                            logger.warning(
                                "No contract addresses found in API response"
                            )
                            continue

                        logger.success(
                            f"Successfully retrieved {len(contracts)} contract addresses"
                        )
                        return contracts

            except Exception as e:
                random_sleep = random.uniform(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.error(
                    f"Error parsing tokens (attempt {retry+1}/3): {str(e)}. Retrying in {random_sleep:.2f} seconds."
                )
                await asyncio.sleep(random_sleep)

        logger.error("Failed to fetch token addresses after 3 attempts")
        return None
