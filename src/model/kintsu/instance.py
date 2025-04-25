import asyncio
from decimal import Decimal
import random
from eth_account import Account
from loguru import logger
from web3 import AsyncWeb3, Web3
from primp import AsyncClient
from typing import Dict, Optional

from src.utils.config import Config
from src.utils.constants import EXPLORER_URL, RPC_URL
from .constants import STAKE_ADDRESS, STAKE_ABI
from src.utils.constants import ERC20_ABI


class Kintsu:
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
            # Add 10% to estimated gas for safety
            return int(estimated * 1.1)
        except Exception as e:
            logger.warning(
                f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit"
            )
            raise e

    async def stake_mon(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Use a higher minimum amount to avoid "Minimum stake" error
                # Based on the transaction you shared (0.04072 MON)
                random_amount = round(
                    random.uniform(
                        max(
                            0.01, self.config.KINTSU.AMOUNT_TO_STAKE[0]
                        ),  # Ensure minimum of 0   .01
                        max(
                            0.015, self.config.KINTSU.AMOUNT_TO_STAKE[1]
                        ),  # Ensure minimum of 0.015
                    ),
                    random.randint(5, 10),
                )
                logger.info(
                    f"[{self.account_index}] Staking {random_amount} MON on Kintsu"
                )

                # Create synchronous contract version for encoding data
                contract = Web3().eth.contract(address=STAKE_ADDRESS, abi=STAKE_ABI)
                amount_wei = Web3.to_wei(random_amount, "ether")
                gas_params = await self.get_gas_params()

                # Create base transaction for gas estimation
                transaction = {
                    "from": self.account.address,
                    "to": STAKE_ADDRESS,
                    "value": amount_wei,
                    "data": contract.functions.stake()._encode_transaction_data(),
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
                logger.info(
                    f"[{self.account_index}] Waiting for transaction confirmation..."
                )
                await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                logger.success(
                    f"[{self.account_index}] Successfully staked {random_amount} MON on Kintsu. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True

            except Exception as e:
                error_message = str(e)
                if "Minimum stake" in error_message:
                    logger.error(
                        f"[{self.account_index}] Error: Minimum stake requirement not met. Trying with a higher amount."
                    )
                    # Update config values to use higher amounts
                    self.config.KINTSU.AMOUNT_TO_STAKE = (0.04, 0.05)
                    continue

                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.error(
                    f"[{self.account_index}] | Error in stake_mon on Kintsu: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
        return False

    async def get_token_balance(self, token_symbol: str) -> Decimal:
        """Get balance of specified token."""
        if token_symbol == "native":
            balance_wei = await self.web3.eth.get_balance(self.account.address)
            return Decimal(balance_wei) / Decimal(10**18)

    async def get_staked_token_balance(self) -> int:
        """
        Get the balance of the staked token for the current account.
        
        Returns:
            int: The balance in wei
        """
        try:
            # Create contract instance
            contract = self.web3.eth.contract(address=STAKE_ADDRESS, abi=ERC20_ABI)
            balance = await contract.functions.balanceOf(self.account.address).call()
            
            logger.info(f"[{self.account_index}] Staked token balance: {Web3.from_wei(balance, 'ether')} tokens")
            return balance
        except Exception as e:
            logger.error(f"[{self.account_index}] Error getting staked token balance: {e}")
            return None

    async def request_unstake(self):
        """
        Request to unstake MON tokens. If no amount is provided, 
        it will unstake the maximum available amount based on staked token balance.
        
        Args:
            amount (Optional[float]): Amount of shares to unstake (default: None, which means max amount)
            
        Returns:
            Dict with transaction status, hash, and request ID
        """
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                logger.info(f"[{self.account_index}] Requesting to unstake MON from Kintsu")
                
                # Create contract
                contract = self.web3.eth.contract(address=STAKE_ADDRESS, abi=STAKE_ABI)
                

                amount_wei = await self.get_staked_token_balance()
                amount_ether = Web3.from_wei(amount_wei, "ether")
                
                if amount_wei == 0:
                    logger.warning(f"[{self.account_index}] No staked tokens found to unstake")
                    return {
                        'status': 0,
                        'error': 'No staked tokens found to unstake'
                    }
 
                
                # Get gas parameters
                gas_params = await self.get_gas_params()
                
                # Create base transaction for requestUnlock
                transaction = {
                    "from": self.account.address,
                    "to": STAKE_ADDRESS,
                    "data": contract.functions.requestUnlock(
                        amount_wei
                    )._encode_transaction_data(),
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
                        f"[{self.account_index}] Successfully requested to unstake {amount_ether} MON from Kintsu. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return {
                        'status': 1,
                        'hash': tx_hash.hex(),
                        'amount': float(amount_ether)
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
                    f"[{self.account_index}] | Error in request_unstake on Kintsu: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
        
        return {
            'status': 0,
            'error': 'Max retries exceeded'
        }

    async def execute(self):
        """
        Execute Kintsu operations based on config settings.
        Will stake, unstake, or both depending on config.
        
        Returns:
            Dict with results of operations performed
        """

        if self.config.KINTSU.STAKE:
            await self.stake_mon()

        await asyncio.sleep(random.randint(
            self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
            self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
        ))
        
        if self.config.KINTSU.UNSTAKE:
            await self.request_unstake()

        return 
