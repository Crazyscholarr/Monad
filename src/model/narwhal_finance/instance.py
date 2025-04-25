import asyncio
import random
from eth_account import Account
from loguru import logger
from primp import AsyncClient
from web3 import AsyncWeb3, Web3
from typing import Dict

from src.model.narwhal_finance.constants import SLOTS_ABI
from src.utils.config import Config
from src.utils.constants import RPC_URL, EXPLORER_URL


class NarwhalFinance:
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

    async def faucet(self):
        """
        Call the mint function on the USDT faucet contract to receive 1,000,000 USDT tokens.
        First checks if the account already has USDT balance.
        """
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # USDT token address
                usdt_address = "0x6593F49Ca8D3038cA002314C187b63dD348c2F94"

                # USDT faucet contract address
                faucet_contract_address = "0xFF85587E991E16bcB9a6A0C52ff919305944f011"

                # Check USDT balance first
                usdt_abi = [
                    {
                        "inputs": [
                            {
                                "internalType": "address",
                                "name": "account",
                                "type": "address",
                            }
                        ],
                        "name": "balanceOf",
                        "outputs": [
                            {"internalType": "uint256", "name": "", "type": "uint256"}
                        ],
                        "stateMutability": "view",
                        "type": "function",
                    },
                    {
                        "inputs": [],
                        "name": "decimals",
                        "outputs": [
                            {"internalType": "uint8", "name": "", "type": "uint8"}
                        ],
                        "stateMutability": "view",
                        "type": "function",
                    },
                ]

                usdt_contract = self.web3.eth.contract(
                    address=usdt_address, abi=usdt_abi
                )

                # Get current USDT balance
                balance = await usdt_contract.functions.balanceOf(
                    self.account.address
                ).call()

                # Try to get decimals, default to 18 if not available
                try:
                    decimals = await usdt_contract.functions.decimals().call()
                except Exception:
                    decimals = 18

                if balance > 0:
                    # Convert to human-readable format
                    human_balance = balance / (10**decimals)
                    logger.success(
                        f"[{self.account_index}] Account already has USDT balance: {human_balance:,.2f} USDT. Skipping faucet."
                    )
                    return True

                logger.info(f"[{self.account_index}] Calling USDT faucet...")

                # ABI for the mint function (using the first ABI from the options provided)
                mint_abi = [
                    {
                        "inputs": [],
                        "name": "mint",
                        "outputs": [],
                        "stateMutability": "nonpayable",
                        "type": "function",
                    }
                ]

                # Create contract instance
                contract = self.web3.eth.contract(
                    address=faucet_contract_address, abi=mint_abi
                )

                # Get gas parameters
                gas_params = await self.get_gas_params()

                # Используем build_transaction вместо encodeABI
                transaction = await contract.functions.mint().build_transaction(
                    {
                        "from": self.account.address,
                        "chainId": 10143,
                        "type": 2,
                        "value": 0,
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address,
                            "latest",
                        ),
                        **gas_params,
                    }
                )

                # Estimate gas
                estimated_gas = await self.estimate_gas(transaction)
                logger.info(
                    f"[{self.account_index}] Estimated gas for faucet: {estimated_gas}"
                )

                # Update transaction with gas estimate
                transaction.update({"gas": estimated_gas})

                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Wait for transaction confirmation
                logger.info(
                    f"[{self.account_index}] Waiting for faucet transaction confirmation..."
                )
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                # Get new balance after mint
                new_balance = await usdt_contract.functions.balanceOf(
                    self.account.address
                ).call()
                human_new_balance = new_balance / (10**decimals)

                logger.success(
                    f"[{self.account_index}] Successfully received USDT from faucet. New balance: {human_new_balance:,.2f} USDT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True

            except Exception as e:
                random_pause = random.uniform(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in faucet: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                continue
        return False

    async def gamble(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Get number of bets from config (random between min and max)
                num_bets = random.randint(
                    self.config.NARWHAL_FINANCE.NUMBER_OF_BETS_PER_START[0],
                    self.config.NARWHAL_FINANCE.NUMBER_OF_BETS_PER_START[1],
                )

                logger.info(
                    f"[{self.account_index}] Starting gambling session with {num_bets} bets"
                )

                # Collect enabled games from config
                enabled_games = []
                if self.config.NARWHAL_FINANCE.PLAY_SLOTS:
                    enabled_games.append(self.slots)
                if self.config.NARWHAL_FINANCE.PLAY_DICE:
                    enabled_games.append(self.dice)
                if self.config.NARWHAL_FINANCE.PLAY_COINFLIP:
                    enabled_games.append(self.coinflip)

                if not enabled_games:
                    logger.warning(
                        f"[{self.account_index}] No games enabled in config. Skipping gambling."
                    )
                    return True

                # Play the specified number of bets by selecting random games
                for i in range(num_bets):
                    game_func = random.choice(enabled_games)
                    game_name = game_func.__name__

                    logger.info(
                        f"[{self.account_index}] Playing game {i+1}/{num_bets}: {game_name}"
                    )
                    success = await game_func()

                    if not success:
                        logger.error(
                            f"[{self.account_index}] Failed to play {game_name}. Stopping gambling session."
                        )
                        return False

                    # Add a random pause between games if there are more games to play
                    if i < num_bets - 1:
                        random_pause = random.uniform(
                            self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                            self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                        )
                        logger.info(
                            f"[{self.account_index}] Pausing for {random_pause:.2f} seconds before next game"
                        )
                        await asyncio.sleep(random_pause)

                return True

            except Exception as e:
                logger.error(f"[{self.account_index}] Error in gamble: {e}")
                await asyncio.sleep(
                    random.uniform(
                        self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                        self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                    )
                )
                continue
        return False

    async def slots(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Get random USDT amount from config
                usdt_amount = round(
                    random.randint(
                        self.config.NARWHAL_FINANCE.AMOUNT_USDT_FOR_BET[0],
                        self.config.NARWHAL_FINANCE.AMOUNT_USDT_FOR_BET[1],
                    ),
                    2,
                ) * (
                    10**18
                )  # Convert to wei

                # USDT token address and spender address
                usdt_address = "0x6593F49Ca8D3038cA002314C187b63dD348c2F94"
                spender_address = "0x5939199FC366f741c5f4981BF343aC5A3ddf748d"

                # First approve USDT spending
                await self._approve_usdt(spender_address, usdt_amount, usdt_address)

                # Format amount to match the payload format (pad with zeros to 64 chars)
                amount_hex = hex(usdt_amount)[2:].zfill(64)

                # Construct the exact payload from successful transaction
                payload = (
                    "0xf26c05f2"  # Function signature
                    f"{amount_hex}"  # Amount (64 chars)
                    "000000000000000000000000"  # Padding
                    "6593f49ca8d3038ca002314c187b63dd348c2f94"  # USDT address
                    "0000000000000000000000000000000000000000000000000000000000000001"  # numBets
                    "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopGain
                    "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopLoss
                )

                # Get nonce and gas parameters
                nonce = await self.web3.eth.get_transaction_count(
                    self.account.address, "latest"
                )
                gas_params = await self.get_gas_params()

                # Create transaction
                transaction = {
                    "from": self.account.address,
                    "to": spender_address,
                    "value": 27000001350000001,  # Exact value in wei
                    "nonce": nonce,
                    "chainId": 10143,
                    "type": 2,
                    "data": payload,
                    **gas_params,
                }

                # Estimate gas
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({"gas": estimated_gas})

                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Wait for transaction confirmation
                logger.info(
                    f"[{self.account_index}] Waiting for Slots_Play transaction confirmation..."
                )
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                logger.success(
                    f"[{self.account_index}] Successfully played Slots with {usdt_amount / (10**18)} USDT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True

            except Exception as e:
                random_pause = random.uniform(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in slots: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                continue
        return False

    async def _approve_usdt(self, spender: str, amount: int, contract_address: str):
        """
        Approve a specified amount of USDT for a spender.
        """
        try:
            # ABI for the approve function
            approve_abi = [
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "spender",
                            "type": "address",
                        },
                        {
                            "internalType": "uint256",
                            "name": "amount",
                            "type": "uint256",
                        },
                    ],
                    "name": "approve",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                }
            ]
            logger.info(
                f"[{self.account_index}] Approving {amount / (10**18)} USDT for spender {spender}"
            )
            # Create contract instance
            usdt_contract = self.web3.eth.contract(
                address=contract_address, abi=approve_abi
            )

            # Get gas parameters
            gas_params = await self.get_gas_params()

            # Build the approval transaction
            transaction = await usdt_contract.functions.approve(
                spender, amount
            ).build_transaction(
                {
                    "from": self.account.address,
                    "chainId": 10143,
                    "nonce": await self.web3.eth.get_transaction_count(
                        self.account.address, "latest"
                    ),
                    **gas_params,
                }
            )

            # Estimate gas
            estimated_gas = await self.estimate_gas(transaction)
            transaction.update({"gas": estimated_gas})

            # Sign and send transaction
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, self.private_key
            )
            tx_hash = await self.web3.eth.send_raw_transaction(
                signed_txn.raw_transaction
            )

            # Wait for transaction confirmation
            logger.info(
                f"[{self.account_index}] Waiting for approval transaction confirmation..."
            )
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.success(
                f"[{self.account_index}] Successfully approved {amount / (10**18)} USDT for spender {spender}. TX: {EXPLORER_URL}{tx_hash.hex()}"
            )
            return True

        except Exception as e:
            logger.error(f"[{self.account_index}] Error in approval: {e}")
            return False

    async def coinflip(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Get random USDT amount from config
                usdt_amount = round(
                    random.randint(
                        self.config.NARWHAL_FINANCE.AMOUNT_USDT_FOR_BET[0],
                        self.config.NARWHAL_FINANCE.AMOUNT_USDT_FOR_BET[1],
                    ),
                    2,
                ) * (
                    10**18
                )  # Convert to wei

                # USDT token address and CoinFlip contract address
                usdt_address = "0x6593F49Ca8D3038cA002314C187b63dD348c2F94"
                coinflip_address = "0x5c1C68a709427Cfdb184399304251658f91d4ea8"

                # First approve USDT spending
                await self._approve_usdt(coinflip_address, usdt_amount, usdt_address)

                # Format amount to match the payload format (pad with zeros to 64 chars)
                amount_hex = hex(usdt_amount)[2:].zfill(64)

                # Construct the payload for CoinFlip_Play
                payload = (
                    "0x6d974773"  # Function signature for CoinFlip_Play
                    f"{amount_hex}"  # Amount (64 chars)
                    "000000000000000000000000"  # Padding
                    "6593f49ca8d3038ca002314c187b63dd348c2f94"  # USDT address
                    "0000000000000000000000000000000000000000000000000000000000000001"  # numBets
                    "0000000000000000000000000000000000000000000000000000000000000001"  # betSide
                    "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopGain
                    "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopLoss
                )

                # Get nonce and gas parameters
                nonce = await self.web3.eth.get_transaction_count(
                    self.account.address, "latest"
                )
                gas_params = await self.get_gas_params()

                # Create transaction
                transaction = {
                    "from": self.account.address,
                    "to": coinflip_address,
                    "value": 27000001350000001,  # Exact value in wei
                    "nonce": nonce,
                    "chainId": 10143,
                    "type": 2,
                    "data": payload,
                    **gas_params,
                }

                # Estimate gas
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({"gas": estimated_gas})

                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Wait for transaction confirmation
                logger.info(
                    f"[{self.account_index}] Waiting for CoinFlip_Play transaction confirmation..."
                )
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                logger.success(
                    f"[{self.account_index}] Successfully played CoinFlip with {usdt_amount / (10**18)} USDT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True

            except Exception as e:
                random_pause = random.uniform(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in coinflip: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                continue
        return False

    async def dice(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # Get random USDT amount from config
                usdt_amount = round(
                    random.randint(
                        self.config.NARWHAL_FINANCE.AMOUNT_USDT_FOR_BET[0],
                        self.config.NARWHAL_FINANCE.AMOUNT_USDT_FOR_BET[1],
                    ),
                    2,
                ) * (
                    10**18
                )  # Convert to wei

                # Generate random multiplier between 1.5 and 9.5 (with 0.01 precision)
                multiplier = round(random.uniform(1.1, 9), 2)

                # Convert multiplier to the format needed (multiply by 10000 and convert to hex)
                multiplier_int = int(multiplier * 10000)
                # Format to hex without '0x' prefix
                multiplier_hex = format(multiplier_int, "x")

                # Ensure the value is properly padded to 64 characters
                multiplier_hex_padded = (
                    "0000000000000000000000000000000000000000000000000000000000000000"
                )
                # Replace the last n characters with our multiplier hex
                multiplier_hex_padded = (
                    multiplier_hex_padded[: -len(multiplier_hex)] + multiplier_hex
                )

                # USDT token address and Dice contract address
                usdt_address = "0x6593F49Ca8D3038cA002314C187b63dD348c2F94"
                dice_address = "0xc552a88f2FAB0b7800F2F54141ACe8C4C06f50A2"

                # First approve USDT spending
                await self._approve_usdt(dice_address, usdt_amount, usdt_address)

                # Format amount to match the payload format (pad with zeros to 64 chars)
                amount_hex = hex(usdt_amount)[2:].zfill(64)

                # Construct the payload for Dice_Play with exact positioning
                payload = (
                    "0x74af2e59"  # Function signature for Dice_Play
                    f"{amount_hex}"  # Amount (64 chars)
                    f"{multiplier_hex_padded}"  # Prediction number (multiplier)
                    "0000000000000000000000006593f49ca8d3038ca002314c187b63dd348c2f94"  # USDT address
                    "0000000000000000000000000000000000000000000000000000000000000001"  # numBets
                    "0000000000000000000000000000000000000000000000000000000000000001"  # betType
                    "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopGain
                    "000000000000000000000000ffffffffffffffffffffffffffffffffffffffff"  # stopLoss
                )

                # Get nonce and gas parameters
                nonce = await self.web3.eth.get_transaction_count(
                    self.account.address, "latest"
                )
                gas_params = await self.get_gas_params()

                # Create transaction
                transaction = {
                    "from": self.account.address,
                    "to": dice_address,
                    "value": 27000001350000001,  # Exact value in wei
                    "nonce": nonce,
                    "chainId": 10143,
                    "type": 2,
                    "data": payload,
                    **gas_params,
                }

                # Estimate gas
                estimated_gas = await self.estimate_gas(transaction)
                transaction.update({"gas": estimated_gas})

                # Sign and send transaction
                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # Wait for transaction confirmation
                logger.info(
                    f"[{self.account_index}] Waiting for Dice_Play transaction confirmation with multiplier {multiplier}x and amount {usdt_amount / (10**18)} USDT..."
                )
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                logger.success(
                    f"[{self.account_index}] Successfully played Dice with {usdt_amount / (10**18)} USDT and multiplier {multiplier}x. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True

            except Exception as e:
                random_pause = random.uniform(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in dice: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                continue
        return False
