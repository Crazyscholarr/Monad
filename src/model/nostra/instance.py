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

from .constants import (
    WMON_CONTRACT, USDC_CONTRACT, USDT_CONTRACT, CDP_MANAGER,
    WMON_LENDING_MANAGER_ADDRESS, WMON_LENDING_MANAGER_ABI,
    WMON_BORROWER_ADDRESS, WMON_BORROWER_ABI,
    USDC_LENDING_MANAGER_ADDRESS, USDC_LENDING_MANAGER_ABI,
    USDC_BORROWER_ADDRESS, USDC_BORROWER_ABI,
    USDT_LENDING_MANAGER_ADDRESS, USDT_LENDING_MANAGER_ABI,
    USDT_BORROWER_ADDRESS, USDT_BORROWER_ABI,
    STANDARD_TOKEN_ABI, STANDARD_PROTOCOL_ABI,
)
from src.utils.constants import ERC20_ABI

class Nostra:
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
        
        # Define assets mapping
        self.assets = {
            "WMON": {
                "token_address": WMON_CONTRACT,
                "symbol": "WMON",
                "lending_manager_address": WMON_LENDING_MANAGER_ADDRESS,
                "lending_manager_abi": WMON_LENDING_MANAGER_ABI,
                "borrower_address": WMON_BORROWER_ADDRESS,
                "borrower_abi": WMON_BORROWER_ABI
            },
            "USDC": {
                "token_address": USDC_CONTRACT,
                "symbol": "USDC",
                "lending_manager_address": USDC_LENDING_MANAGER_ADDRESS,
                "lending_manager_abi": USDC_LENDING_MANAGER_ABI,
                "borrower_address": USDC_BORROWER_ADDRESS,
                "borrower_abi": USDC_BORROWER_ABI
            },
            "USDT": {
                "token_address": USDT_CONTRACT,
                "symbol": "USDT",
                "lending_manager_address": USDT_LENDING_MANAGER_ADDRESS,
                "lending_manager_abi": USDT_LENDING_MANAGER_ABI,
                "borrower_address": USDT_BORROWER_ADDRESS,
                "borrower_abi": USDT_BORROWER_ABI
            }
        }

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
    
    async def pick_asset(self) -> Tuple[Optional[str], Decimal]:
        """
        Check balances of tokens and randomly pick one among those that have at least 0.01 balance.
        Returns tuple of (token_symbol, token_balance_adjusted_to_decimals)
        """
        # Get balances for all tokens
        wmon_balance_wei = await self.get_token_balance(WMON_CONTRACT)
        usdt_balance_wei = await self.get_token_balance(USDT_CONTRACT)
        usdc_balance_wei = await self.get_token_balance(USDC_CONTRACT)
        
        # Define minimum balance threshold in wei for each token
        # 0.01 with appropriate decimal places
        wmon_min_balance = 10**16  # 0.01 * 10^18 (18 decimals)
        usdt_min_balance = 10**4   # 0.01 * 10^6 (6 decimals)
        usdc_min_balance = 10**4   # 0.01 * 10^6 (6 decimals)
        
        # Create list of tokens with sufficient balance
        tokens_with_balance = []
        
        if wmon_balance_wei >= wmon_min_balance:
            adjusted_balance = Decimal(wmon_balance_wei) / Decimal(10**18)
            tokens_with_balance.append(("WMON", wmon_balance_wei, adjusted_balance))
            
        if usdt_balance_wei >= usdt_min_balance:
            adjusted_balance = Decimal(usdt_balance_wei) / Decimal(10**6)
            tokens_with_balance.append(("USDT", usdt_balance_wei, adjusted_balance))
            
        if usdc_balance_wei >= usdc_min_balance:
            adjusted_balance = Decimal(usdc_balance_wei) / Decimal(10**6)
            tokens_with_balance.append(("USDC", usdc_balance_wei, adjusted_balance))
        
        # If no tokens have sufficient balance, return None
        if not tokens_with_balance:
            logger.warning(f"[{self.account_index}] No tokens with sufficient balance (min 0.01) found")
            return None, Decimal(0)
        
        # Log available tokens
        token_balances_display = []
        for symbol, _, adjusted_balance in tokens_with_balance:
            token_balances_display.append(f"{symbol}: {adjusted_balance}")
            
        logger.info(f"[{self.account_index}] Available tokens: {', '.join(token_balances_display)}")
        
        # Randomly select a token from the list
        selected_token = random.choice(tokens_with_balance)
        token_symbol, token_balance_wei, adjusted_balance = selected_token
        logger.info(f"[{self.account_index}] Selected token: {token_symbol} with balance: {adjusted_balance}")
        
        return token_symbol, adjusted_balance
    
    async def get_token_balance(self, token_address: str) -> int:
        """Get balance of token for self.address in wei"""
        max_retries = 15
        retries = 0
        last_exception = None
        
        while retries <= max_retries:
            try:
                token_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(token_address),
                    abi=ERC20_ABI
                )
                
                balance_wei = await token_contract.functions.balanceOf(self.account.address).call()
                return balance_wei
                
            except Exception as e:
                retries += 1
                last_exception = e

        logger.error(f"[{self.account_index}] All {max_retries} retry attempts failed when checking balance for {token_address}. Last error: {last_exception}")
        return None
    
    async def check_allowance(self, token_address: str, spender_address: str, amount_wei: int) -> bool:
        """Check if token allowance is sufficient."""
        token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
        current_allowance = await token_contract.functions.allowance(
            self.account.address, spender_address
        ).call()
        return current_allowance >= amount_wei
    
    async def approve_token(self, token_address: str, spender_address: str) -> bool:
        """Approve token for spending."""
        try:
            token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
            
            # Create transaction for approval
            gas_params = await self.get_gas_params()
            max_uint256 = (2**256) - 1  # Max uint256 value for unlimited approval
            
            transaction = {
                "from": self.account.address,
                "to": token_address,
                "data": token_contract.functions.approve(
                    spender_address, max_uint256
                )._encode_transaction_data(),
                "chainId": 10143,
                "type": 2,
                "nonce": await self.web3.eth.get_transaction_count(
                    self.account.address, "latest"
                ),
            }
            
            # Estimate gas
            estimated_gas = await self.estimate_gas(transaction)
            transaction.update({"gas": estimated_gas, **gas_params})
            
            # Sign and send transaction
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            # Wait for confirmation
            logger.info(f"[{self.account_index}] Waiting for approval transaction confirmation...")
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt["status"] == 1:
                logger.success(
                    f"[{self.account_index}] Successfully approved token. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True
            else:
                logger.error(f"[{self.account_index}] Approval transaction failed.")
                return False
                
        except Exception as e:
            logger.error(f"[{self.account_index}] Error in approve_token: {e}")
            return False
    
    async def deposit_asset(self, asset_symbol: str) -> Tuple[bool, int]:
        """Deposit asset to Nostra protocol
            asset_symbol: Symbol of the asset to deposit (WMON, USDC, USDT)
            
        Returns:
            Tuple of (success, amount_deposited_wei)
        """
        if asset_symbol not in self.assets:
            logger.error(f"[{self.account_index}] Unsupported asset symbol: {asset_symbol}")
            return False, 0
            
        asset_info = self.assets[asset_symbol]
        
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Generate random deposit percentage
                percentage = random.uniform(
                    self.config.NOSTRA.PERCENT_OF_BALANCE_TO_DEPOSIT[0],
                    self.config.NOSTRA.PERCENT_OF_BALANCE_TO_DEPOSIT[1]
                )
                
                # Get token balance
                token_balance_wei = await self.get_token_balance(asset_info["token_address"])
                
                # Calculate amount to deposit in wei (percentage of balance)
                amount_wei = int(token_balance_wei * percentage / 100)
                # Convert to ether for logging purposes
                decimals = 6 if asset_symbol in ["USDC", "USDT"] else 18
                amount = Decimal(amount_wei) / Decimal(10**decimals)
                
                logger.info(f"[{self.account_index}] Depositing {amount} {asset_symbol} to Nostra")
                
                # Check if we have enough balance
                if token_balance_wei < amount_wei:
                    token_balance = Decimal(token_balance_wei) / Decimal(10**decimals)
                    logger.warning(
                        f"[{self.account_index}] Insufficient {asset_symbol} balance. "
                        f"Have: {token_balance}, Need: {amount}"
                    )
                    return False, 0
                
                # Check allowance and approve if needed
                if not await self.check_allowance(
                    asset_info["token_address"], 
                    asset_info["lending_manager_address"], 
                    amount_wei
                ):
                    logger.info(f"[{self.account_index}] Approving {asset_symbol} for deposit")
                    approval_success = await self.approve_token(
                        asset_info["token_address"], 
                        asset_info["lending_manager_address"]
                    )
                    if not approval_success:
                        logger.error(f"[{self.account_index}] Failed to approve {asset_symbol}")
                        continue
                
                # Create lending manager contract
                lending_manager_contract = self.web3.eth.contract(
                    address=asset_info["lending_manager_address"],
                    abi=asset_info["lending_manager_abi"]
                )
                
                # Prepare deposit transaction
                gas_params = await self.get_gas_params()
                
                transaction = {
                    "from": self.account.address,
                    "to": asset_info["lending_manager_address"],
                    "data": lending_manager_contract.functions.deposit(
                        self.account.address, amount_wei
                    )._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address, "latest"
                    ),
                }
                
                # Estimate gas
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({"gas": estimated_gas, **gas_params})
                
                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
                
                # Wait for confirmation
                logger.info(f"[{self.account_index}] Waiting for deposit transaction confirmation...")
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully deposited {amount} {asset_symbol} to Nostra. "
                        f"TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True, amount_wei
                else:
                    logger.error(
                        f"[{self.account_index}] Deposit transaction failed."
                        f"TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    continue
                    
            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1]
                )
                logger.error(
                    f"[{self.account_index}] Error in deposit_asset: {e}. "
                    f"Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                
        return False, 0
    
    async def withdraw_asset(self, asset_symbol: str) -> bool:
        """
        Withdraw assets from Nostra protocol.
        
        Args:
            asset_symbol: Symbol of the asset to withdraw (WMON, USDC, USDT)
        """
        if asset_symbol not in self.assets:
            logger.error(f"[{self.account_index}] Unsupported asset symbol: {asset_symbol}")
            return False
            
        asset_info = self.assets[asset_symbol]
        
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                logger.info(f"[{self.account_index}] Withdrawing {asset_symbol} from Nostra")
                # Create lending manager contract
                lending_manager_contract = self.web3.eth.contract(
                    address=asset_info["lending_manager_address"],
                    abi=asset_info["lending_manager_abi"]
                )
                # If we couldn't find the withdraw amount, inform the user and return
                withdraw_amount = await lending_manager_contract.functions.balanceOf(self.account.address).call()
                withdraw_amount = int(withdraw_amount * random.uniform(0.97, 0.99))
                if withdraw_amount is None or withdraw_amount == 0:
                    logger.warning(f"[{self.account_index}] No {asset_symbol} deposits found to withdraw")
                    return False
                
                # Convert to human-readable format for logging
                decimals = 6 if asset_symbol in ["USDC", "USDT"] else 18
                withdraw_amount_human = Decimal(withdraw_amount) / Decimal(10**decimals)
                
                logger.info(f"[{self.account_index}] Found {asset_symbol} deposit amount: {withdraw_amount_human}")
                
                # Prepare withdraw transaction
                gas_params = await self.get_gas_params()
                
                transaction = {
                    "from": self.account.address,
                    "to": asset_info["lending_manager_address"],
                    "data": lending_manager_contract.functions.withdraw(
                        self.account.address, self.account.address, withdraw_amount
                    )._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address, "latest"
                    ),
                }
                
                # Estimate gas
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({"gas": estimated_gas, **gas_params})
                
                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
                
                # Wait for confirmation
                logger.info(f"[{self.account_index}] Waiting for withdraw transaction confirmation...")
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully withdrew {withdraw_amount_human} {asset_symbol} from Nostra. "
                        f"TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    logger.error(f"[{self.account_index}] Withdraw transaction failed.")
                    continue
                    
            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1]
                )
                logger.error(
                    f"[{self.account_index}] Error in withdraw_asset: {e}. "
                    f"Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                
        return False
    
    async def borrow_asset(self, asset_symbol: str, amount_deposited_wei: int) -> bool:
        """
        Borrow assets from Nostra protocol.
        
        Args:
            asset_symbol: Symbol of the asset to borrow (WMON, USDC, USDT)
            amount_deposited_wei: Amount deposited in wei, used to calculate borrow amount
        """
        if asset_symbol not in self.assets:
            logger.error(f"[{self.account_index}] Unsupported asset symbol: {asset_symbol}")
            return False
            
        asset_info = self.assets[asset_symbol]
        
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Generate random borrow amount (40-60% of deposited amount)
                amount_wei = int(amount_deposited_wei * random.uniform(0.35, 0.6))
                
                # Convert to human readable format for logging
                decimals = 6 if asset_symbol in ["USDC", "USDT"] else 18
                amount = Decimal(amount_wei) / Decimal(10**decimals)
                
                logger.info(f"[{self.account_index}] Borrowing {amount} {asset_symbol} from Nostra")
                
                # Create borrower contract
                borrower_contract = self.web3.eth.contract(
                    address=asset_info["borrower_address"],
                    abi=asset_info["borrower_abi"]
                )
                
                # Prepare borrow transaction
                gas_params = await self.get_gas_params()
                
                transaction = {
                    "from": self.account.address,
                    "to": asset_info["borrower_address"],
                    "data": borrower_contract.functions.borrow(
                        self.account.address, amount_wei
                    )._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address, "latest"
                    ),
                }
                
                # Estimate gas
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({"gas": estimated_gas, **gas_params})
                
                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
                
                # Wait for confirmation
                logger.info(f"[{self.account_index}] Waiting for borrow transaction confirmation...")
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully borrowed {amount} {asset_symbol} from Nostra. "
                        f"TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    logger.error(f"[{self.account_index}] Borrow transaction failed.")
                    continue
                    
            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1]
                )
                logger.error(
                    f"[{self.account_index}] Error in borrow_asset: {e}. "
                    f"Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                
        return False
    
    async def repay_asset(self, asset_symbol: str) -> bool:
        """
        Repay borrowed assets to Nostra protocol.
        
        Args:
            asset_symbol: Symbol of the asset to repay (WMON, USDC, USDT)
        """
        if asset_symbol not in self.assets:
            logger.error(f"[{self.account_index}] Unsupported asset symbol: {asset_symbol}")
            return False
            
        asset_info = self.assets[asset_symbol]
        
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                logger.info(f"[{self.account_index}] Repaying {asset_symbol} to Nostra")

                # Create borrower contract
                borrower_contract = self.web3.eth.contract(
                    address=asset_info["borrower_address"],
                    abi=asset_info["borrower_abi"]
                )
                
                # Get token-specific debt using balanceOf
                debt = await self.get_token_balance(asset_info["borrower_address"])
                decimals = 6 if asset_symbol in ["USDC", "USDT"] else 18
                debt_human = Decimal(debt) / Decimal(10**decimals)
                logger.info(f"[{self.account_index}] Found {asset_symbol} debt: {debt_human}")

                # Check if there's debt to repay
                if debt == 0:
                    logger.warning(f"[{self.account_index}] No {asset_symbol} debt to repay")
                    return False
                # Repay full debt
                amount_wei = debt
                # Convert to ether for logging purposes
                decimals = 6 if asset_symbol in ["USDC", "USDT"] else 18
                amount = Decimal(amount_wei) / Decimal(10**decimals)
                
                # Check token balance and approve if needed
                token_balance_wei = await self.get_token_balance(asset_info["token_address"])
                if token_balance_wei < amount_wei:
                    token_balance = Decimal(token_balance_wei) / Decimal(10**decimals)
                    logger.warning(
                        f"[{self.account_index}] Insufficient {asset_symbol} balance. "
                        f"Have: {token_balance}, Need: {amount}"
                    )
                    return False
                # Check allowance and approve if needed
                if not await self.check_allowance(
                    asset_info["token_address"], 
                    asset_info["borrower_address"], 
                    amount_wei
                ):
                    logger.info(f"[{self.account_index}] Approving {asset_symbol} for repayment")
                    approval_success = await self.approve_token(
                        asset_info["token_address"], 
                        asset_info["borrower_address"]
                    )
                    if not approval_success:
                        logger.error(f"[{self.account_index}] Failed to approve {asset_symbol}")
                        continue
                
                # Prepare repay transaction
                gas_params = await self.get_gas_params()
                transaction = {
                    "from": self.account.address,
                    "to": asset_info["borrower_address"],
                    "data": borrower_contract.functions.repay(
                        self.account.address, amount_wei
                    )._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address, "latest"
                    ),
                }
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({"gas": estimated_gas, **gas_params})
                
                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
                
                # Wait for confirmation
                logger.info(f"[{self.account_index}] Waiting for repay transaction confirmation...")
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully repaid {amount} {asset_symbol} to Nostra. "
                        f"TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    logger.error(f"[{self.account_index}] Repay transaction failed.")
                    continue
                    
            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1]
                )
                logger.error(
                    f"[{self.account_index}] Error in repay_asset: {e}. "
                    f"Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                
        return False
    
    async def execute(self):
        """
        Execute Nostra operations based on config settings.
        Will deposit, borrow, repay, or withdraw depending on config.
        """
        # Select an asset with sufficient balance
        asset_symbol, token_balance_adjusted = await self.pick_asset()

        
        # If no token with sufficient balance was found, exit
        if asset_symbol is None:
            logger.warning(f"[{self.account_index}] No suitable tokens found with sufficient balance. Skipping Nostra operations.")
            return
            
        logger.info(f"[{self.account_index}] Using token {asset_symbol} with balance {token_balance_adjusted}")
        
        if self.config.NOSTRA.DEPOSIT:
            deposit_success, amount_deposited_wei = await self.deposit_asset(asset_symbol)
            if not deposit_success:
                logger.warning(f"[{self.account_index}] Deposit failed, skipping further operations.")
                return
                
            await asyncio.sleep(random.randint(
                self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
            ))

        if self.config.NOSTRA.BORROW:
            await self.borrow_asset(asset_symbol, amount_deposited_wei)
            
            await asyncio.sleep(random.randint(
                self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
            ))
        
        if self.config.NOSTRA.REPAY:
            await self.repay_asset(asset_symbol)
            
            await asyncio.sleep(random.randint(
                self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
            ))
        
        if self.config.NOSTRA.WITHDRAW:
            await self.withdraw_asset(asset_symbol)


        

