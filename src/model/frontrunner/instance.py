import asyncio
import random
from eth_account import Account
from loguru import logger
from primp import AsyncClient
from web3 import AsyncWeb3
from src.model.frontrunner.constants import ABI, CONTRACT_ADDRESS
from src.utils.config import Config
from src.utils.constants import RPC_URL, EXPLORER_URL


class Frontrunner:
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
        self.contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=ABI
        )

    async def send_transaction(self):
        amount_of_transactions = random.randint(self.config.FRONT_RUNNER.MAX_AMOUNT_TRANSACTIONS_FOR_ONE_RUN[0], self.config.FRONT_RUNNER.MAX_AMOUNT_TRANSACTIONS_FOR_ONE_RUN[1])
        for i in range(amount_of_transactions):
            try:
                logger.info(f"[{self.account_index}] Transaction {i+1} of {amount_of_transactions}")                
                # Get current nonce
                nonce = await self.web3.eth.get_transaction_count(self.account.address)
                
                # Build the transaction properly
                frontrun_tx = await self.contract.functions.frontrun().build_transaction(
                    {
                        "from": self.account.address,
                        "nonce": nonce,
                        "maxFeePerGas": self.web3.to_wei(60, "gwei"),
                        "maxPriorityFeePerGas": self.web3.to_wei(2, "gwei"),
                    }
                )
                
                # Estimate gas and update the transaction
                gas = await self.web3.eth.estimate_gas(frontrun_tx)
                frontrun_tx['gas'] = gas
                
                signed_txn = self.web3.eth.account.sign_transaction(
                    frontrun_tx, self.account.key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
                logger.info(f"[{self.account_index}] Waiting for transaction confirmation...")
                receipt = await self.web3.eth.wait_for_transaction_receipt(
                    tx_hash, poll_latency=2
                )

                if receipt["status"] == 1:
                    logger.success(
                        f"Transaction successful! Explorer URL: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                else:
                    logger.error(
                        f"Transaction failed! Explorer URL: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                random_pause = random.uniform(  
                    self.config.FRONT_RUNNER.PAUSE_BETWEEN_TRANSACTIONS[0],
                    self.config.FRONT_RUNNER.PAUSE_BETWEEN_TRANSACTIONS[1],
                )
                await asyncio.sleep(random_pause)

            except Exception as e:
                random_pause = random.uniform(  
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in send_transaction Frontrunner: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                continue
        return False

