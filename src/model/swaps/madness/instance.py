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

from src.utils.config import Config
from src.utils.constants import EXPLORER_URL, RPC_URL
from .constants import (
    ROUTER_CONTRACT,
    WMON_CONTRACT,
    ABI,
    AVAILABLE_TOKENS,
    USDT_CONTRACT,
    USDC_CONTRACT,
)


class Madness:
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
        Execute Madness swap operations based on configuration settings.
        Performs several random swaps according to the settings.
        If SWAP_ALL_TO_MONAD option is enabled, exchanges all tokens to MON.
        """
        logger.info(f"[{self.account_index}] Starting Madness swap operations")

        # Check if we need to swap all tokens to MON
        if (
            hasattr(self.config.MADNESS, "SWAP_ALL_TO_MONAD")
            and self.config.MADNESS.SWAP_ALL_TO_MONAD
        ):
            logger.info(
                f"[{self.account_index}] SWAP_ALL_TO_MONAD is enabled, swapping all tokens to MON"
            )
            await self.swap_all_to_monad()
            return

        # Get balances of all available tokens
        token_balances = {}
        for symbol, token_info in AVAILABLE_TOKENS.items():
            balance = await self.get_token_balance(self.account.address, token_info)
            token_balances[symbol] = balance
            logger.info(f"[{self.account_index}] Balance of {symbol}: {balance}")

        # Check if we have any tokens other than MON
        non_mon_tokens = []
        for symbol, balance in token_balances.items():
            if symbol != "MON" and balance > 0.01:
                non_mon_tokens.append(symbol)

        # If no tokens other than MON, buy a random token
        if not non_mon_tokens and token_balances.get("MON", 0) > 0.01:
            await self._buy_random_token(token_balances["MON"])

        # Determine number of swaps to perform
        min_swaps, max_swaps = self.config.FLOW.NUMBER_OF_SWAPS
        num_swaps = random.randint(min_swaps, max_swaps)

        logger.info(f"[{self.account_index}] Will perform {num_swaps} swaps")

        # Perform the specified number of swaps
        for swap_num in range(1, num_swaps + 1):
            logger.info(f"[{self.account_index}] Executing swap {swap_num}/{num_swaps}")

            # Update token balances for accurate selection
            for symbol, token_info in AVAILABLE_TOKENS.items():
                balance = await self.get_token_balance(self.account.address, token_info)
                token_balances[symbol] = balance

            # Choose random token pair for swap
            token_from, token_to, amount = await self._select_random_token_pair(
                token_balances
            )

            if not token_from or not token_to:
                logger.warning(
                    f"[{self.account_index}] No suitable tokens found for swap {swap_num}. Skipping."
                )
                continue

            logger.info(
                f"[{self.account_index}] Swap {swap_num}: {token_from} -> {token_to}, "
                f"amount: {amount}"
            )

            # Check if amount is sufficient for swap
            if amount <= 0.01:
                logger.warning(
                    f"[{self.account_index}] Amount too small for swap {swap_num}. Skipping."
                )
                continue

            # Execute swap
            swap_result = await self.swap(token_from, token_to, amount)

            if swap_result["success"]:
                logger.success(
                    f"[{self.account_index}] Swap {swap_num} completed successfully: "
                    f"{swap_result['amount_in']} {swap_result['from_token']} -> "
                    f"{swap_result['expected_out']} {swap_result['to_token']}"
                )

                # If not the last swap, pause before next one
                if swap_num < num_swaps:
                    pause_time = random.randint(
                        self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                        self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                    )
                    logger.info(
                        f"[{self.account_index}] Pausing for {pause_time} seconds before next swap"
                    )
                    await asyncio.sleep(pause_time)
            else:
                logger.error(
                    f"[{self.account_index}] Swap {swap_num} failed: {swap_result.get('error', 'Unknown error')}"
                )

                # If swap failed, pause before next attempt
                if swap_num < num_swaps:
                    pause_time = random.randint(
                        self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                        self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                    )
                    logger.info(
                        f"[{self.account_index}] Pausing for {pause_time} seconds before next swap attempt"
                    )
                    await asyncio.sleep(pause_time)

        logger.success(
            f"[{self.account_index}] Completed all {num_swaps} Madness swap operations"
        )

    async def get_gas_params(self) -> Dict[str, int]:
        """Get current gas parameters from the network."""
        latest_block = await self.web3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = await self.web3.eth.max_priority_fee
        max_fee = base_fee + max_priority_fee
        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

    async def estimate_gas(self, transaction: dict) -> int:
        """Estimate gas for transaction and add a buffer."""
        try:
            estimated = await self.web3.eth.estimate_gas(transaction)
            return int(estimated * 1.1)
        except Exception as e:
            logger.warning(
                f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit"
            )
            raise e

    async def get_token_contract(
        self, token_address: str, abi: Dict = None
    ) -> Contract:
        """
        Get token contract instance

        Args:
            token_address: Token contract address
            abi: ABI to use (defaults to token ABI)

        Returns:
            Contract: Token contract instance
        """
        if abi is None:
            abi = ABI["token"]

        return self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=abi
        )

    async def get_token_balance(self, wallet_address: str, token: Dict) -> float:
        """
        Get token balance for a wallet

        Args:
            wallet_address: Wallet address
            token: Token information

        Returns:
            float: Token balance
        """
        max_retries = 15
        retries = 0
        last_exception = None

        while retries <= max_retries:
            try:
                wallet_address = Web3.to_checksum_address(wallet_address)

                if token["native"]:
                    balance_wei = await self.web3.eth.get_balance(wallet_address)
                    return float(Web3.from_wei(balance_wei, "ether"))
                else:
                    token_contract = await self.get_token_contract(token["address"])
                    balance_wei = await token_contract.functions.balanceOf(
                        wallet_address
                    ).call()
                    return float(balance_wei) / (10 ** token["decimals"])
            except Exception as e:
                retries += 1
                last_exception = e
                await asyncio.sleep(1)

        logger.error(
            f"[{self.account_index}] All {max_retries} retry attempts failed when checking balance. Last error: {last_exception}"
        )
        return 0

    async def check_allowance(
        self, token_address: str, spender_address: str, amount_wei: int
    ) -> bool:
        """Check if allowance is sufficient for token."""
        token_contract = await self.get_token_contract(token_address)
        current_allowance = await token_contract.functions.allowance(
            self.account.address, spender_address
        ).call()
        return current_allowance >= amount_wei

    async def approve_token(
        self, token: Dict, amount_wei: int, spender_address: str
    ) -> Optional[str]:
        """
        Check and if necessary approve token

        Args:
            token: Token information
            amount_wei: Amount in wei to approve
            spender_address: Address of contract to approve

        Returns:
            Optional[str]: Approval transaction hash or None if approval not needed
        """
        if token["native"]:
            return None

        # Check current allowance
        if await self.check_allowance(token["address"], spender_address, amount_wei):
            return None

        logger.info(
            f"[{self.account_index}] 🔑 [APPROVAL] Approving {token['name']}..."
        )

        # Maximum value for approve (uint256 max)
        max_uint256 = 2**256 - 1

        # Create token contract
        token_contract = await self.get_token_contract(token["address"])

        # Prepare approve function
        approve_func = token_contract.functions.approve(spender_address, max_uint256)

        # Get gas parameters
        gas_params = await self.get_gas_params()

        # Create transaction
        transaction = {
            "from": self.account.address,
            "to": token["address"],
            "data": approve_func._encode_transaction_data(),
            "chainId": 10143,
            "type": 2,
            "nonce": await self.web3.eth.get_transaction_count(
                self.account.address, "latest"
            ),
        }

        # Estimate gas
        try:
            estimated_gas = await self.estimate_gas(transaction)
            transaction.update({"gas": estimated_gas, **gas_params})
        except Exception as e:
            logger.error(
                f"[{self.account_index}] Failed to estimate gas for approval: {str(e)}"
            )
            raise ValueError(
                f"Gas estimation failed for {token['name']} approval: {str(e)}"
            )

        # Sign and send transaction
        signed_tx = self.web3.eth.account.sign_transaction(
            transaction, self.private_key
        )
        tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for transaction confirmation
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt["status"] == 1:
            logger.success(
                f"[{self.account_index}] ✅ [APPROVAL] {token['name']} approved. TX: {EXPLORER_URL}{tx_hash.hex()}"
            )
            return Web3.to_hex(tx_hash)
        else:
            logger.error(f"[{self.account_index}] Approval transaction failed.")
            return None

    async def _deposit_mon_to_wmon(self, amount_wei: int) -> Dict:
        """
        Convert MON to WMON via deposit function

        Args:
            amount_wei: Amount of MON in wei to convert

        Returns:
            Dict: Operation result
        """
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Create WMON contract
                wmon_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(WMON_CONTRACT),
                    abi=ABI["weth"],
                )

                # Prepare deposit function
                deposit_func = wmon_contract.functions.deposit()

                # Get gas parameters
                gas_params = await self.get_gas_params()

                # Create transaction
                transaction = {
                    "from": self.account.address,
                    "to": WMON_CONTRACT,
                    "value": amount_wei,
                    "data": deposit_func._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address, "latest"
                    ),
                }

                # Estimate gas
                try:
                    estimated_gas = await self.estimate_gas(transaction)
                    transaction.update({"gas": estimated_gas, **gas_params})
                except Exception as e:
                    logger.error(
                        f"[{self.account_index}] Failed to estimate gas for deposit: {str(e)}"
                    )
                    raise ValueError(f"Gas estimation failed for deposit: {str(e)}")

                logger.info(
                    f"[{self.account_index}] 💰 [DEPOSIT] Converting MON to WMON via deposit..."
                )

                # Sign and send transaction
                signed_tx = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_tx.raw_transaction
                )
                logger.info(
                    f"[{self.account_index}] 🚀 [TX SENT] Transaction hash: {EXPLORER_URL}{tx_hash.hex()}"
                )

                # Wait for transaction confirmation
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                block_number = receipt["blockNumber"]

                if receipt["status"] == 1:
                    return {
                        "success": True,
                        "tx_hash": Web3.to_hex(tx_hash),
                        "block_number": block_number,
                        "from_token": "MON",
                        "to_token": "WMON",
                        "amount_in": Web3.from_wei(amount_wei, "ether"),
                        "expected_out": Web3.from_wei(amount_wei, "ether"),
                        "gas_used": receipt["gasUsed"],
                    }
                else:
                    logger.error(f"[{self.account_index}] Deposit transaction failed.")
                    continue

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in deposit_mon_to_wmon: {e}. "
                    f"Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)

        return {"success": False, "error": "Max retry attempts reached"}

    async def _withdraw_wmon_to_mon(self, amount_wei: int) -> Dict:
        """
        Convert WMON to MON via withdraw function

        Args:
            amount_wei: Amount of WMON in wei to convert

        Returns:
            Dict: Operation result
        """
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Create WMON contract
                wmon_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(WMON_CONTRACT),
                    abi=ABI["weth"],
                )

                # Prepare withdraw function
                withdraw_func = wmon_contract.functions.withdraw(amount_wei)

                # Get gas parameters
                gas_params = await self.get_gas_params()

                # Create transaction
                transaction = {
                    "from": self.account.address,
                    "to": WMON_CONTRACT,
                    "data": withdraw_func._encode_transaction_data(),
                    "chainId": 10143,
                    "type": 2,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address, "latest"
                    ),
                }

                # Estimate gas
                try:
                    estimated_gas = await self.estimate_gas(transaction)
                    transaction.update({"gas": estimated_gas, **gas_params})
                except Exception as e:
                    logger.error(
                        f"[{self.account_index}] Failed to estimate gas for withdraw: {str(e)}"
                    )
                    raise ValueError(f"Gas estimation failed for withdraw: {str(e)}")

                logger.info(
                    f"[{self.account_index}] 💸 [WITHDRAW] Converting WMON to MON via withdraw..."
                )

                # Sign and send transaction
                signed_tx = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_tx.raw_transaction
                )
                logger.info(
                    f"[{self.account_index}] 🚀 [TX SENT] Transaction hash: {EXPLORER_URL}{tx_hash.hex()}"
                )

                # Wait for transaction confirmation
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                block_number = receipt["blockNumber"]

                if receipt["status"] == 1:
                    return {
                        "success": True,
                        "tx_hash": Web3.to_hex(tx_hash),
                        "block_number": block_number,
                        "from_token": "WMON",
                        "to_token": "MON",
                        "amount_in": Web3.from_wei(amount_wei, "ether"),
                        "expected_out": Web3.from_wei(amount_wei, "ether"),
                        "gas_used": receipt["gasUsed"],
                    }
                else:
                    logger.error(f"[{self.account_index}] Withdraw transaction failed.")
                    continue

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in withdraw_wmon_to_mon: {e}. "
                    f"Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)

        return {"success": False, "error": "Max retry attempts reached"}

    async def pick_random_tokens(self) -> Tuple[str, str, float]:
        """
        Pick a random token pair for swap and an amount

        Returns:
            Tuple[str, str, float]: (token_from, token_to, amount)
        """
        # Get balances of all tokens
        available_tokens = []

        for symbol, token_info in AVAILABLE_TOKENS.items():
            balance = await self.get_token_balance(self.account.address, token_info)
            if balance > 0.01:  # Minimum balance for swap
                available_tokens.append((symbol, balance))

        if not available_tokens:
            logger.warning(
                f"[{self.account_index}] No tokens with sufficient balance found"
            )
            return None, None, 0

        # Choose random token to swap
        token_from, balance = random.choice(available_tokens)

        # Choose random token to receive (not the same one)
        possible_tokens_to = [
            symbol for symbol in AVAILABLE_TOKENS.keys() if symbol != token_from
        ]
        token_to = random.choice(possible_tokens_to)

        # Determine random amount for swap (30-70% of balance)
        amount = balance * random.uniform(0.3, 0.7)

        logger.info(
            f"[{self.account_index}] Selected swap: {token_from} -> {token_to}, amount: {amount}"
        )

        return token_from, token_to, amount

    async def swap_all_to_monad(self):
        """
        Swaps all tokens to MON (native token).
        Handles different token thresholds based on value.
        """
        target_token = AVAILABLE_TOKENS["MON"]
        logger.info(f"[{self.account_index}] 🔄 Swapping all tokens to MON")

        # Define minimum thresholds for different tokens
        # These values are in token units, not MON value
        token_thresholds = {
            "WMON": 0.01,  # Стандартный порог для WMON
            "WETH": 0.0001,  # Меньший порог для WETH из-за высокой стоимости
            "WSOL": 0.001,  # Очень низкий порог для WSOL
            "USDT": 0.01,  # Стандартный порог для стейблкоинов
            "WBTC": 0.000001,  # Низкий порог для WBTC из-за высокой стоимости
            "MAD": 0.01,  # Стандартный порог
            "USDC": 0.01,  # Стандартный порог для стейблкоинов
        }

        # Default threshold for any token not in the list
        default_threshold = 0.0000001

        # Iterate through all available tokens
        for symbol, token in AVAILABLE_TOKENS.items():
            # Skip MON, as it's the target token
            if token["native"]:
                continue

            # Get token balance
            balance = await self.get_token_balance(self.account.address, token)

            # Get threshold for this token
            threshold = token_thresholds.get(symbol, default_threshold)

            # If balance is too small, skip
            if balance <= threshold:
                logger.info(
                    f"[{self.account_index}] Skipping {symbol} - balance too low: {balance} (threshold: {threshold})"
                )
                continue

            # Log balances before swap
            mon_balance_before = await self.get_token_balance(
                self.account.address, target_token
            )
            logger.info(
                f"[{self.account_index}] Balance {symbol} before swap: {balance}"
            )
            logger.info(
                f"[{self.account_index}] Balance MON before swap: {mon_balance_before}"
            )

            try:
                # Special case: WMON -> MON via withdraw
                if symbol == "WMON":
                    amount_wei = int(balance * (10 ** token["decimals"]))
                    result = await self._withdraw_wmon_to_mon(amount_wei)
                else:
                    # For other tokens use regular swap
                    result = await self.swap(symbol, "MON", balance)

                if result["success"]:
                    logger.success(
                        f"[{self.account_index}] Successfully swapped {balance} {symbol} to MON. "
                        f"TX: {EXPLORER_URL}{result['tx_hash']}"
                    )
                else:
                    logger.error(
                        f"[{self.account_index}] Failed to swap {symbol} to MON: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                logger.error(
                    f"[{self.account_index}] Error swapping {symbol} to MON: {str(e)}"
                )

            # Log balances after swap
            token_balance_after = await self.get_token_balance(
                self.account.address, token
            )
            mon_balance_after = await self.get_token_balance(
                self.account.address, target_token
            )
            logger.info(
                f"[{self.account_index}] Balance {symbol} after swap: {token_balance_after}"
            )
            logger.info(
                f"[{self.account_index}] Balance MON after swap: {mon_balance_after}"
            )

            # Pause between swaps
            await asyncio.sleep(random.randint(2, 5))

        logger.success(f"[{self.account_index}] 🎉 All tokens have been swapped to MON")
        return True

    async def swap(
        self,
        token_from: str,
        token_to: str,
        amount: float,
        slippage: float = 0.5,
        custom_path: List[str] = None,
    ) -> Dict:
        """
        Execute token swap

        Args:
            token_from: Symbol of token to swap from (e.g., 'MON')
            token_to: Symbol of token to swap to (e.g., 'USDC')
            amount: Amount of token_from to swap
            slippage: Allowed slippage in percent (default 0.5%)
            custom_path: Optional custom path of token addresses for the swap

        Returns:
            Dict: Swap result with transaction information
        """
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Get token information
                token_a = AVAILABLE_TOKENS.get(token_from)
                token_b = AVAILABLE_TOKENS.get(token_to)

                if not token_a or not token_b:
                    raise ValueError(
                        f"Invalid token symbols: {token_from} or {token_to}"
                    )

                # Check balance
                balance = await self.get_token_balance(self.account.address, token_a)
                if balance < amount:
                    raise ValueError(
                        f"Insufficient balance. Have {balance} {token_a['name']}, need {amount}"
                    )

                # Convert amount to wei
                if token_a["native"]:
                    amount_in_wei = Web3.to_wei(amount, "ether")
                else:
                    amount_in_wei = int(amount * (10 ** token_a["decimals"]))

                # Special cases: MON -> WMON and WMON -> MON
                if token_a["native"] and token_b["name"] == "WMON":
                    return await self._deposit_mon_to_wmon(amount_in_wei)

                if token_a["name"] == "WMON" and token_b["native"]:
                    return await self._withdraw_wmon_to_mon(amount_in_wei)

                # Define swap path
                if custom_path:
                    # Use custom path if provided
                    path = custom_path
                else:
                    # Default path through WMON if different tokens
                    if token_a["native"]:
                        # MON -> Token (через WMON)
                        path = [WMON_CONTRACT, token_b["address"]]
                    elif token_b["native"]:
                        # Token -> MON (через WMON)
                        path = [token_a["address"], WMON_CONTRACT]
                    else:
                        # Token -> Token (через WMON) для стейблкоинов и других токенов
                        path = [token_a["address"], WMON_CONTRACT, token_b["address"]]

                # Create router contract
                router_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(ROUTER_CONTRACT),
                    abi=ABI["router"],
                )

                # Get expected output amount
                amounts_out = await router_contract.functions.getAmountsOut(
                    amount_in_wei, path
                ).call()
                expected_out = amounts_out[-1]

                # Apply slippage
                min_amount_out = int(expected_out * (1 - slippage / 100))

                # Set deadline (current time + 1 hour)
                deadline = int(time.time()) + 3600

                # If token is not native, approve it
                if not token_a["native"]:
                    await self.approve_token(token_a, amount_in_wei, ROUTER_CONTRACT)

                # Get gas parameters
                gas_params = await self.get_gas_params()

                # Prepare transaction based on token types
                if token_a["native"]:  # MON -> Token
                    tx_func = router_contract.functions.swapExactETHForTokens(
                        min_amount_out, path, self.account.address, deadline
                    )

                    transaction = {
                        "from": self.account.address,
                        "to": ROUTER_CONTRACT,
                        "value": amount_in_wei,
                        "data": tx_func._encode_transaction_data(),
                        "chainId": 10143,
                        "type": 2,
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address, "latest"
                        ),
                    }
                elif token_b["native"]:  # Token -> MON
                    tx_func = router_contract.functions.swapExactTokensForETH(
                        amount_in_wei,
                        min_amount_out,
                        path,
                        self.account.address,
                        deadline,
                    )

                    transaction = {
                        "from": self.account.address,
                        "to": ROUTER_CONTRACT,
                        "data": tx_func._encode_transaction_data(),
                        "chainId": 10143,
                        "type": 2,
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address, "latest"
                        ),
                    }
                else:  # Token -> Token
                    tx_func = router_contract.functions.swapExactTokensForTokens(
                        amount_in_wei,
                        min_amount_out,
                        path,
                        self.account.address,
                        deadline,
                    )

                    transaction = {
                        "from": self.account.address,
                        "to": ROUTER_CONTRACT,
                        "data": tx_func._encode_transaction_data(),
                        "chainId": 10143,
                        "type": 2,
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address, "latest"
                        ),
                    }

                # Estimate gas
                try:
                    estimated_gas = await self.estimate_gas(transaction)
                    transaction.update({"gas": estimated_gas, **gas_params})
                except Exception as e:
                    logger.error(
                        f"[{self.account_index}] Failed to estimate gas for swap: {str(e)}"
                    )
                    raise ValueError(f"Gas estimation failed for swap: {str(e)}")

                # Build, sign and send transaction
                signed_tx = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_tx.raw_transaction
                )

                logger.info(
                    f"[{self.account_index}] 🔄 [SWAP] Executing swap [{token_a['name']} -> {token_b['name']}]..."
                )
                logger.info(
                    f"[{self.account_index}] 🚀 [TX SENT] Transaction hash: {EXPLORER_URL}{tx_hash.hex()}"
                )

                # Wait for transaction confirmation
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
                block_number = receipt["blockNumber"]

                if receipt["status"] == 1:
                    # Return transaction information
                    return {
                        "success": True,
                        "tx_hash": Web3.to_hex(tx_hash),
                        "block_number": block_number,
                        "from_token": token_a["name"],
                        "to_token": token_b["name"],
                        "amount_in": amount,
                        "expected_out": expected_out / (10 ** token_b["decimals"]),
                        "gas_used": receipt["gasUsed"],
                    }
                else:
                    logger.error(f"[{self.account_index}] Swap transaction failed.")
                    continue

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in swap: {e}. "
                    f"Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)

        return {"success": False, "error": "Max retry attempts reached"}

    async def swap_usdt_to_usdc(self, amount: float) -> Dict:
        """
        Swap USDT to USDC using a direct swap

        Args:
            amount: Amount of USDT to swap

        Returns:
            Dict: Swap result
        """
        # Определяем путь через WMON (USDT -> WMON -> USDC) с преобразованием в checksum addresses
        custom_path = [
            Web3.to_checksum_address(USDT_CONTRACT),  # USDT
            Web3.to_checksum_address(WMON_CONTRACT),  # WMON
            Web3.to_checksum_address(USDC_CONTRACT),  # USDC
        ]

        logger.info(
            f"[{self.account_index}] Swapping {amount} USDT to USDC via WMON..."
        )
        return await self.swap("USDT", "USDC", amount, custom_path=custom_path)

    async def _buy_random_token(self, mon_balance: float):
        """
        Buy a random token using a percentage of MON balance

        Args:
            mon_balance: Current MON balance
        """
        # Get percent of balance to use from config
        min_percent, max_percent = self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP
        percent = random.uniform(min_percent, max_percent)

        # Calculate amount to use (percent of MON balance)
        amount = mon_balance * (percent / 100)

        # Choose a random token to buy (excluding MON and WMON)
        possible_tokens = [
            symbol
            for symbol in AVAILABLE_TOKENS.keys()
            if symbol not in ["MON", "WMON"]
        ]

        if not possible_tokens:
            logger.warning(f"[{self.account_index}] No tokens available to buy")
            return

        token_to_buy = random.choice(possible_tokens)

        logger.info(
            f"[{self.account_index}] Buying {token_to_buy} with {amount} MON ({percent:.2f}% of balance)"
        )

        # Execute the swap
        result = await self.swap("MON", token_to_buy, amount)

        if result["success"]:
            logger.success(
                f"[{self.account_index}] Successfully bought {result['expected_out']} {token_to_buy} "
                f"with {amount} MON. TX: {EXPLORER_URL}{result['tx_hash']}"
            )
        else:
            logger.error(
                f"[{self.account_index}] Failed to buy {token_to_buy}: "
                f"{result.get('error', 'Unknown error')}"
            )

    async def _select_random_token_pair(
        self, token_balances: Dict[str, float]
    ) -> Tuple[str, str, float]:
        """
        Select a random token pair for swap based on current balances.
        For MON, uses a percentage specified in config.
        For other tokens, uses the full balance.

        Args:
            token_balances: Dictionary of token balances

        Returns:
            Tuple[str, str, float]: token_from, token_to, amount
        """
        # Find tokens with sufficient balance
        available_tokens = []
        for symbol, balance in token_balances.items():
            if balance > 0.01:  # Minimum balance for swap
                available_tokens.append((symbol, balance))

        if not available_tokens:
            logger.warning(
                f"[{self.account_index}] No tokens with sufficient balance found"
            )
            return None, None, 0

        # Choose random token to swap from
        token_from, balance = random.choice(available_tokens)

        # Choose random token to receive (not the same one)
        possible_tokens_to = [
            symbol for symbol in AVAILABLE_TOKENS.keys() if symbol != token_from
        ]

        if not possible_tokens_to:
            logger.warning(
                f"[{self.account_index}] No target tokens available for swap"
            )
            return None, None, 0

        token_to = random.choice(possible_tokens_to)

        # Determine amount to swap
        if token_from == "MON":
            # For MON, use percentage from config
            min_percent, max_percent = self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP
            percent = random.uniform(min_percent, max_percent)
            amount = balance * (percent / 100)
            logger.info(
                f"[{self.account_index}] Selected swap: {token_from} -> {token_to}, "
                f"amount: {amount} ({percent:.2f}% of MON balance)"
            )
        else:
            # For other tokens, use full balance
            amount = balance
            logger.info(
                f"[{self.account_index}] Selected swap: {token_from} -> {token_to}, "
                f"amount: {amount} (100% of token balance)"
            )

        return token_from, token_to, amount
