import asyncio
import random
from eth_account import Account
from primp import AsyncClient
from web3 import AsyncWeb3, Web3
from loguru import logger
from typing import Dict

from src.utils.config import Config
from src.utils.constants import RPC_URL, EXPLORER_URL
from .constants import STAKE_ADDRESS, STAKE_ABI, STAKED_TOKEN
from src.utils.constants import ERC20_ABI


class Magma:
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
        
    async def get_staked_token_balance(self) -> int:
        """
        Get the balance of the staked token for the current account.
        
        Returns:
            int: The balance in wei
        """
        try:
            # Create contract instance
            contract = self.web3.eth.contract(address=STAKED_TOKEN, abi=ERC20_ABI)
            balance = await contract.functions.balanceOf(self.account.address).call()
            
            logger.info(f"[{self.account_index}] Staked token balance: {Web3.from_wei(balance, 'ether')} tokens")
            return balance
        except Exception as e:
            logger.error(f"[{self.account_index}] Error getting staked token balance: {e}")
            return None
        
    async def request_unstake(self,):
        """
        Request to unstake MON tokens from Magma using withdrawMon. 
        If no amount is provided, it will unstake a random amount.
        
        Args:
            amount (Optional[float]): Amount to unstake (default: None, which means random amount)
            
        Returns:
            Dict with transaction status, hash, and amount
        """
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # If amount is not specified, generate a random one or set a default
                amount_wei = await self.get_staked_token_balance()
                amount_ether = Web3.from_wei(amount_wei, "ether")
                logger.info(f"[{self.account_index}] Requesting to unstake {amount_ether} MON from Magma")
                
                # Create contract
                contract = self.web3.eth.contract(address=STAKE_ADDRESS, abi=STAKE_ABI)
                

                # Get gas parameters
                gas_params = await self.get_gas_params()
                
                # Create transaction for withdrawMon function
                transaction = {
                    "from": self.account.address,
                    "to": STAKE_ADDRESS,
                    "data": contract.functions.withdrawMon(amount_wei)._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                }
                
                # Estimate gas
                estimated_gas = await self.estimate_gas(transaction)
                logger.info(f"[{self.account_index}] Estimated gas: {estimated_gas}")
                
                # Add remaining transaction parameters
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
                
                # Wait for transaction confirmation
                logger.info(f"[{self.account_index}] Waiting for unstake request confirmation...")
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully requested to unstake {amount_ether} MON from Magma. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return {
                        'status': 1,
                        'hash': tx_hash.hex(),
                        'amount': amount_ether
                    }
                else:
                    logger.error(f"[{self.account_index}] Transaction failed. Status: {receipt['status']}")
                    return {
                        'status': 0,
                        'hash': tx_hash.hex(),
                        'error': 'Transaction failed'
                    }
                    
            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.error(
                    f"[{self.account_index}] | Error in request_unstake on Magma: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
        
        return {
            'status': 0,
            'error': 'Maximum retry attempts reached'
        }
        

    async def stake_mon(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                random_amount = round(
                    random.uniform(
                        self.config.MAGMA.AMOUNT_TO_STAKE[0],
                        self.config.MAGMA.AMOUNT_TO_STAKE[1],
                    ),
                    random.randint(6, 12),
                )
                logger.info(
                    f"[{self.account_index}] Staking {random_amount} MON on Magma"
                )

                amount_wei = Web3.to_wei(random_amount, "ether")
                gas_params = await self.get_gas_params()

                # Создаем базовую транзакцию для оценки газа
                transaction = {
                    "from": self.account.address,
                    "to": STAKE_ADDRESS,
                    "data": "0xd5575982",
                    "value": amount_wei,
                    "chainId": 10143,
                    "type": 2,
                }

                # Оцениваем газ
                estimated_gas = await self.estimate_gas(transaction)
                logger.info(f"[{self.account_index}] Estimated gas: {estimated_gas}")

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
                    f"[{self.account_index}] Waiting for transaction confirmation..."
                )
                await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                logger.success(
                    f"[{self.account_index}] Successfully staked {random_amount} MON on Magma. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in stake_mon on Magma: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                continue

        return False

    async def execute(self):
        """
        Execute Magma operations based on config settings.
        Will stake, unstake, or both depending on config.
        
        Returns:
            Dict with results of operations performed
        """

        # Check if staking is enabled in config
        if self.config.MAGMA.STAKE:
            await self.stake_mon()
            
        await asyncio.sleep(random.randint(
            self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
            self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
        ))
        
        # Check if unstaking is enabled in config
        if self.config.MAGMA.UNSTAKE:
            await self.request_unstake()

        return 