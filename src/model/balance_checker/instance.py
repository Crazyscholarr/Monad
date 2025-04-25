from eth_account import Account
from web3 import AsyncWeb3
from src.model.balance_checker.constants import CONTRACT_ABI, CONTRACT_ADDRESS, TOKENS
from src.utils.constants import RPC_URL
from tabulate import tabulate
from loguru import logger


class BalanceChecker:
    def __init__(self, private_keys, proxy):
        self.private_keys = private_keys
        self.addresses = self.convert_private_keys()
        self.proxy = proxy
        self.web3 = AsyncWeb3(
             AsyncWeb3.AsyncHTTPProvider(
                 RPC_URL,
                 request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
             )
        ) 
    def convert_private_keys(self):
        addresses = []
        for private_key in self.private_keys:
            account = Account.from_key(private_key)
            address = account.address
            addresses.append(address)
        return addresses

    async def run(self):
        logger.info('Checking balances...')
        contract = self.web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        tokens = [token_info["address"] for token_info in TOKENS.values()]
        token_symbols = list(TOKENS.keys())
        balances = await contract.functions.balances(self.addresses, tokens).call()

        # Prepare data for tabulation
        all_wallet_data = []

        for i, address in enumerate(self.addresses):
            wallet_data = []
            wallet_data.append(f"Wallet {i+1}")
            wallet_data.append(address)
            
            # Add balance for each token
            for j, token_symbol in enumerate(token_symbols):
                token_info = TOKENS[token_symbol]
                index = i * len(tokens) + j
                raw_balance = balances[index]
                formatted_balance = raw_balance / (10 ** token_info["decimals"])
                wallet_data.append(f"{round(formatted_balance, 4)}")
            
            all_wallet_data.append(wallet_data)

        # Create headers
        headers = ["Wallet #", "Address"] + [symbol.upper() for symbol in token_symbols]

        # Format and display the table
        table = tabulate(
            all_wallet_data,
            headers=headers,
            tablefmt="double_grid",
            stralign="center",
            numalign="center",
        )

        logger.info(f"\n{'='*50}\n"
                    f"         Wallet Token Balances ({len(self.addresses)} wallets)\n"
                    f"{'='*50}\n"
                    f"{table}\n"
                    f"{'='*50}")


        
