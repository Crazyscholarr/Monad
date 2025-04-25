import random
import asyncio
from eth_account import Account
from loguru import logger
from web3 import AsyncWeb3

from src.utils.config import Config
from src.model.magiceden.get_mint_data import get_mint_data
from src.utils.constants import EXPLORER_URL, RPC_URL


class MagicEden:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        config: Config,
        private_key: str,
        session=None,  # Made optional since we're using curl_cffi now
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = private_key
        self.config = config
        self.account = Account.from_key(private_key)

        # Initialize web3 with proxy if provided
        proxy_settings = {"proxy": f"http://{proxy}", "ssl": False} if proxy else {}
        self.web3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(RPC_URL, request_kwargs=proxy_settings)
        )

    def get_random_gas_limit(self, min_gas: int = 180000, max_gas: int = 280000) -> int:
        """Generate random gas limit within range"""
        return random.randint(min_gas, max_gas)

    async def mint(self) -> bool:
        """
        Mint an NFT from the specified contract on MagicEden
        Returns:
            bool: True if minting was successful, False otherwise
        """
        try:
            # Randomly select NFT contract from config
            nft_contract_raw = random.choice(self.config.MAGICEDEN.NFT_CONTRACTS)
            nft_contract = self.web3.to_checksum_address(nft_contract_raw)

            logger.info(
                f"[{self.account_index}] | 🚀 Starting MagicEden mint for contract: {nft_contract}"
            )

            # Get mint data from MagicEden API
            mint_data = await get_mint_data(self.proxy, nft_contract, self.account)

            # Handle error cases
            if mint_data == "already_minted":
                logger.success(
                    f"[{self.account_index}] | ✅ NFT already minted from MagicEden (max mints per wallet reached)"
                )
                return True
            elif mint_data == "all_nfts_minted":
                logger.warning(f"[{self.account_index}] | 💀 All NFTs have been minted")
                return False
            elif not mint_data:
                logger.error(
                    f"[{self.account_index}] | ❌ Failed to get MagicEden mint data"
                )
                return False

            # Get current gas prices
            base_fee = await self.web3.eth.gas_price
            priority_fee = int(base_fee * 0.1)  # 10% priority fee
            max_fee = base_fee + priority_fee

            # Generate random gas limit
            gas_limit = self.get_random_gas_limit()

            # Extract transaction data
            if "steps" in mint_data and len(mint_data["steps"]) > 0:
                mint_step = mint_data["steps"][0]
                if mint_step.get("method") == "eth_sendTransaction":
                    tx_params = mint_step["params"]

                    # Build transaction
                    tx = {
                        "from": self.account.address,
                        "to": self.web3.to_checksum_address(tx_params["to"]),
                        "value": (
                            int(tx_params["value"], 16)
                            if tx_params["value"].startswith("0x")
                            else int(tx_params["value"])
                        ),
                        "data": tx_params["data"],
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address
                        ),
                        "maxFeePerGas": max_fee,
                        "maxPriorityFeePerGas": priority_fee,
                        "gas": gas_limit,
                        "chainId": 10143,
                    }

                    # Check balance
                    balance = await self.web3.eth.get_balance(self.account.address)
                    if balance < tx["value"]:
                        logger.error(
                            f"[{self.account_index}] | ❌ Insufficient balance for mint"
                        )
                        return False

                    # Sign and send transaction
                    signed_tx = self.web3.eth.account.sign_transaction(
                        tx, self.private_key
                    )
                    tx_hash = await self.web3.eth.send_raw_transaction(
                        signed_tx.raw_transaction
                    )

                    logger.info(
                        f"[{self.account_index}] | 📤 Transaction sent: {EXPLORER_URL}{tx_hash.hex()}"
                    )

                    # Wait for receipt
                    receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                    if receipt["status"] == 1:
                        logger.success(
                            f"[{self.account_index}] | ✅ Successfully minted NFT: {EXPLORER_URL}{tx_hash.hex()}"
                        )
                        return True
                    else:
                        logger.error(
                            f"[{self.account_index}] | ❌ Transaction failed: {EXPLORER_URL}{tx_hash.hex()}"
                        )
                        return False

            logger.error(f"[{self.account_index}] | ❌ Invalid mint data format")
            return False

        except Exception as e:
            if "Signer had insufficient balance" in str(e):
                logger.error(
                    f"[{self.account_index}] | ❌ Insufficient balance for mint"
                )
                return False
            logger.error(f"[{self.account_index}] | ❌ Error minting NFT: {str(e)}")
            return False
