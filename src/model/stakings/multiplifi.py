import asyncio
from decimal import Decimal
import random
import aiohttp
from eth_account import Account
from loguru import logger
from web3 import AsyncWeb3, Web3
from primp import AsyncClient
from typing import Dict, Optional, List, Union, Tuple
import time
from functools import wraps

from src.utils.config import Config
from src.utils.constants import EXPLORER_URL, RPC_URL


class Multiplifi:
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

        # Create a configured Web3 client with retry middleware
        self.web3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(
                RPC_URL,
                request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
            )
        )

    async def faucet(self):
        for retry in range(3):
            try:
                logger.info(f"[{self.account_index}] | Starting multiplifi faucet...")

                # Contract address for MultipliFi
                contract_address = "0x181579497d5c4EfEC2424A21095907ED7d91ac9A"

                # Payload for ClaimToken function (0x32f289cf)
                payload = "0x32f289cf000000000000000000000000924f1bf31b19a7f9695f3fc6c69c2ba668ea4a0a"

                # Create transaction for gas estimation
                transaction = {
                    "from": self.account.address,
                    "to": contract_address,
                    "value": 0,
                    "data": payload,
                    "chainId": 10143,
                    "type": 2,
                }

                # Estimate gas with safety buffer
                try:
                    estimated_gas = await self.web3.eth.estimate_gas(transaction)
                    # Add 10% buffer for safety
                    estimated_gas = int(estimated_gas * 1.1)
                except Exception as e:
                    raise Exception(
                        f"[{self.account_index}] Error estimating gas in multiplifi faucet: {e}"
                    )

                # Get gas parameters
                latest_block = await self.web3.eth.get_block("latest")
                base_fee = latest_block["baseFeePerGas"]
                max_priority_fee = await self.web3.eth.max_priority_fee
                max_fee = base_fee + max_priority_fee

                # Build complete transaction
                transaction = {
                    "from": self.account.address,
                    "to": contract_address,
                    "value": 0,
                    "data": payload,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address
                    ),
                    "gas": estimated_gas,
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": max_priority_fee,
                    "chainId": 10143,
                    "type": 2,
                }

                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                logger.info(
                    f"[{self.account_index}] | Claiming MultipliFi tokens | Tx: {EXPLORER_URL}{tx_hash.hex()}"
                )

                # Wait for transaction receipt
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] | Successfully claimed MultipliFi tokens | Tx: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    raise Exception(
                        f"[{self.account_index}] Failed to claim MultipliFi tokens"
                    )

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] | Error faucet multiplifi: {e}. Sleeping {random_pause} seconds..."
                )
                await asyncio.sleep(random_pause)

        return False

    async def _get_usdc_balance(self):
        """Get USDC balance for the account"""
        try:
            # USDC contract address
            usdc_contract_address = "0x924F1Bf31b19a7f9695F3FC6c69C2BA668Ea4a0a"

            # ERC20 standard ABI for balanceOf function
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                }
            ]

            # Create contract instance
            usdc_contract = self.web3.eth.contract(
                address=usdc_contract_address, abi=erc20_abi
            )

            # Get balance
            balance = await usdc_contract.functions.balanceOf(
                self.account.address
            ).call()

            # USDC has 6 decimals
            return balance, balance / 10**6
        except Exception as e:
            logger.error(f"[{self.account_index}] | Error getting USDC balance: {e}")
            return 0, 0

    async def stake(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                logger.info(
                    f"[{self.account_index}] | Starting multiplifi stake process..."
                )

                # USDC token contract address
                usdc_contract_address = "0x924F1Bf31b19a7f9695F3FC6c69C2BA668Ea4a0a"

                # Multiplifi staking contract address
                staking_contract_address = "0xBCF1415BD456eDb3a94c9d416F9298ECF9a2cDd0"

                # Get USDC balance
                usdc_balance, usdc_balance_formatted = await self._get_usdc_balance()

                if usdc_balance == 0:
                    logger.warning(f"[{self.account_index}] | No USDC balance to stake")
                    return False

                logger.info(
                    f"[{self.account_index}] | USDC balance: {usdc_balance_formatted:.6f} USDC"
                )

                # Step 1: Approve transaction
                # Payload for Approve function (from transaction example)
                approve_payload = "0x095ea7b3000000000000000000000000bcf1415bd456edb3a94c9d416f9298ecf9a2cdd0ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

                # Create transaction for gas estimation
                approve_transaction = {
                    "from": self.account.address,
                    "to": usdc_contract_address,
                    "value": 0,
                    "data": approve_payload,
                    "chainId": 10143,
                    "type": 2,
                }

                # Estimate gas with safety buffer
                try:
                    estimated_gas = await self.web3.eth.estimate_gas(
                        approve_transaction
                    )
                    # Add 10% buffer for safety
                    estimated_gas = int(estimated_gas * 1.1)
                except Exception as e:
                    raise Exception(
                        f"[{self.account_index}] Error estimating gas for approve: {e}"
                    )

                # Get gas parameters
                latest_block = await self.web3.eth.get_block("latest")
                base_fee = latest_block["baseFeePerGas"]
                max_priority_fee = await self.web3.eth.max_priority_fee
                max_fee = base_fee + max_priority_fee

                # Build complete transaction
                approve_transaction = {
                    "from": self.account.address,
                    "to": usdc_contract_address,
                    "value": 0,
                    "data": approve_payload,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address
                    ),
                    "gas": estimated_gas,
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": max_priority_fee,
                    "chainId": 10143,
                    "type": 2,
                }

                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(
                    approve_transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                logger.info(
                    f"[{self.account_index}] | Approving USDC for MultipliFi staking | Tx: {EXPLORER_URL}{tx_hash.hex()}"
                )

                # Wait for transaction receipt
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                if receipt["status"] != 1:
                    raise Exception(
                        f"[{self.account_index}] Failed to approve USDC for MultipliFi staking"
                    )

                logger.success(
                    f"[{self.account_index}] | Successfully approved USDC for MultipliFi staking | Tx: {EXPLORER_URL}{tx_hash.hex()}"
                )

                # Wait a random time before proceeding to deposit
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.info(
                    f"[{self.account_index}] | Waiting {random_pause} seconds before depositing..."
                )
                await asyncio.sleep(random_pause)

                # Step 2: Deposit transaction
                # Using the full USDC balance for staking
                amount = usdc_balance

                # Convert amount to hex string with padding to match the expected format
                # The format is 32 bytes (64 hex chars) with leading zeros
                amount_hex = hex(amount)[2:].zfill(64)

                # Create deposit payload with the token address and amount
                # Format: 0x47e7ef24 + token_address (32 bytes) + amount (32 bytes)
                deposit_payload = f"0x47e7ef24000000000000000000000000924f1bf31b19a7f9695f3fc6c69c2ba668ea4a0a{amount_hex}"

                # Create transaction for gas estimation
                deposit_transaction = {
                    "from": self.account.address,
                    "to": staking_contract_address,
                    "value": 0,
                    "data": deposit_payload,
                    "chainId": 10143,
                    "type": 2,
                }

                # Estimate gas with safety buffer
                try:
                    estimated_gas = await self.web3.eth.estimate_gas(
                        deposit_transaction
                    )
                    # Add 10% buffer for safety
                    estimated_gas = int(estimated_gas * 1.1)
                except Exception as e:
                    raise Exception(
                        f"[{self.account_index}] Error estimating gas for deposit: {e}"
                    )

                # Get fresh gas parameters
                latest_block = await self.web3.eth.get_block("latest")
                base_fee = latest_block["baseFeePerGas"]
                max_priority_fee = await self.web3.eth.max_priority_fee
                max_fee = base_fee + max_priority_fee

                # Build complete transaction
                deposit_transaction = {
                    "from": self.account.address,
                    "to": staking_contract_address,
                    "value": 0,
                    "data": deposit_payload,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address
                    ),
                    "gas": estimated_gas,
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": max_priority_fee,
                    "chainId": 10143,
                    "type": 2,
                }

                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(
                    deposit_transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                logger.info(
                    f"[{self.account_index}] | Depositing all available USDC ({usdc_balance_formatted:.6f}) to MultipliFi staking | Tx: {EXPLORER_URL}{tx_hash.hex()}"
                )

                # Wait for transaction receipt
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] | Successfully deposited {usdc_balance_formatted:.6f} USDC to MultipliFi staking | Tx: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    raise Exception(
                        f"[{self.account_index}] Failed to deposit USDC to MultipliFi staking"
                    )

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] | Error staking at multiplifi: {e}. Sleeping {random_pause} seconds..."
                )
                await asyncio.sleep(random_pause)

        return False
