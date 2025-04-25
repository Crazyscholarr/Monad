import asyncio
import random
from eth_account import Account
from loguru import logger
from primp import AsyncClient
from web3 import AsyncWeb3, Web3
from typing import Dict

from src.utils.config import Config
from src.utils.constants import RPC_URL, EXPLORER_URL
from .constants import DEPLOY_CONTRACT_BYTECODE_1, DEPLOY_CONTRACT_BYTECODE_2


class EasyNode:
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

    async def get_gas_params(self) -> Dict[str, int]:
        """Get current gas parameters from the network."""
        latest_block = await self.web3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = await self.web3.eth.max_priority_fee

        # Calculate maxFeePerGas (base fee + priority fee)
        max_fee = base_fee + max_priority_fee

        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

    async def estimate_gas(self, transaction: dict) -> int:
        """Estimate gas for transaction and add some buffer."""
        try:
            estimated = await self.web3.eth.estimate_gas(transaction)
            # Добавляем 10% к estimated gas для безопасности
            return int(estimated * 1.1)
        except Exception as e:
            logger.warning(
                f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit"
            )
            raise e

    async def deploy_contract(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                logger.info(f"[{self.account_index}] Deploying EasyNode contract...")

                # Случайно выбираем один из двух вариантов байткода
                contract_bytecode = random.choice(
                    [DEPLOY_CONTRACT_BYTECODE_1, DEPLOY_CONTRACT_BYTECODE_2]
                )
                contract_type = (
                    "1" if contract_bytecode == DEPLOY_CONTRACT_BYTECODE_1 else "2"
                )
                logger.info(
                    f"[{self.account_index}] Using contract type: {contract_type}"
                )

                gas_params = await self.get_gas_params()

                # Создаем базовую транзакцию для оценки газа
                transaction = {
                    "from": self.account.address,
                    "data": contract_bytecode,  # используем выбранный байткод
                    "chainId": 10143,
                    "type": 2,
                    "value": Web3.to_wei(
                        0.1, "ether"
                    ),  # Отправляем 0.1 MON как в примере транзакции
                }

                # Оцениваем газ
                try:
                    estimated_gas = await self.estimate_gas(transaction)
                    logger.info(
                        f"[{self.account_index}] Estimated gas: {estimated_gas}"
                    )
                except Exception as e:
                    logger.warning(
                        f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit"
                    )
                    raise e  # Используем фиксированный лимит газа, если оценка не удалась

                # Добавляем остальные параметры транзакции
                transaction.update(
                    {
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address,
                            "latest",
                        ),
                        "gas": estimated_gas,
                        **gas_params,
                    }
                )

                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Ждем подтверждения транзакции
                logger.info(
                    f"[{self.account_index}] Waiting for contract deployment confirmation..."
                )
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                logger.success(
                    f"[{self.account_index}] Successfully deployed EasyNode contract (type {contract_type}) at {receipt['contractAddress']}. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True

            except Exception as e:
                random_pause = random.uniform(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in deploy_contract EasyNode: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                continue
        return False
