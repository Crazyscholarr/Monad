from web3 import AsyncWeb3
from eth_account import Account
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
import random
import asyncio
from loguru import logger
from src.utils.config import Config
from src.model.crusty_swap.constants import (
    CONTRACT_ADDRESSES, 
    EXPLORER_URLS,
    DESTINATION_CONTRACT_ADDRESS,
    CRUSTY_SWAP_RPCS,
    CRUSTY_SWAP_ABI,
    CHAINLINK_ETH_PRICE_CONTRACT_ADDRESS,
    CHAINLINK_ETH_PRICE_ABI,
    ZERO_ADDRESS,
    REFUEL_FROM_ONE_TO_ALL_CONTRACT_ADDRESS,
    REFUEL_FROM_ONE_TO_ALL_CONTRACT_ABI
)
from src.utils.constants import RPC_URL, ETH_RPC_URL, EXPLORER_URL

class CrustySwap:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        private_key: str,
        config: Config,
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = private_key
        self.config = config
        self.account = Account.from_key(private_key)
        self.monad_web3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(
                RPC_URL,
                request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
            )
        )
        self.eth_web3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(
                ETH_RPC_URL,
                request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
            )
        )
        self.monad_contract = self.monad_web3.eth.contract(address=DESTINATION_CONTRACT_ADDRESS, abi=CRUSTY_SWAP_ABI)

    async def check_available_monad(self, eth_amount_wei, contract, max_retries=5, retry_delay=5) -> bool:
        """
        Check if there is enough MON in the Crusty Swap contract to fill a buy order.
        Includes retry mechanism for resilience against temporary failures.
        
        Args:
            eth_amount_wei: Amount of ETH in wei to be used for the purchase
            contract: The Crusty Swap contract
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            bool: True if there is enough MON, False otherwise
        """
        for attempt in range(1, max_retries + 1):
            try:
                # Get available MON in the contract
                available_mon_wei = await self.monad_web3.eth.get_balance(DESTINATION_CONTRACT_ADDRESS)
                
                # Get ETH price from Chainlink (in USD with 8 decimals)
                chainlink_eth_price_contract = self.eth_web3.eth.contract(
                    address=CHAINLINK_ETH_PRICE_CONTRACT_ADDRESS, 
                    abi=CHAINLINK_ETH_PRICE_ABI
                )
                eth_price_usd = await chainlink_eth_price_contract.functions.latestAnswer().call()
                
                # Get MON price from contract (in USD with 8 decimals)
                mon_price_usd = await contract.functions.pricePerMonad().call()
                
                # Calculate how many MON we should receive for our ETH
                # Convert ETH to USD value with proper decimal handling
                eth_amount_ether = eth_amount_wei / 10**18
                eth_price_usd_real = eth_price_usd / 10**8  # Convert to real USD value
                eth_value_usd = eth_amount_ether * eth_price_usd_real
                
                # Calculate MON amount from USD value
                mon_price_usd_real = mon_price_usd / 10**8  # Convert to real USD value
                expected_mon_amount = eth_value_usd / mon_price_usd_real
                expected_mon_amount_wei = int(expected_mon_amount * 10**18)
                
                logger.info(f"[{self.account_index}] ETH amount: {eth_amount_ether} ETH (${eth_value_usd:.2f})")
                logger.info(f"[{self.account_index}] ETH price: ${eth_price_usd_real:.2f}")
                logger.info(f"[{self.account_index}] MON price: ${mon_price_usd_real:.4f}")
                logger.info(f"[{self.account_index}] Available MON: {self.monad_web3.from_wei(available_mon_wei, 'ether')} MON")
                logger.info(f"[{self.account_index}] Expected to receive: {expected_mon_amount:.4f} MON")
                
                # Check if there's enough MON in the contract
                has_enough_mon = available_mon_wei >= expected_mon_amount_wei
                
                if has_enough_mon:
                    logger.success(f"[{self.account_index}] Contract has enough MON to fill the order")
                else:
                    logger.warning(f"[{self.account_index}] Contract doesn't have enough MON! " 
                                f"Available: {self.monad_web3.from_wei(available_mon_wei, 'ether')} MON, "
                                f"Needed: {expected_mon_amount:.4f} MON")
                    
                return has_enough_mon
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"[{self.account_index}] Attempt {attempt}/{max_retries} failed to check available MON: {str(e)}")
                    logger.info(f"[{self.account_index}] Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"[{self.account_index}] All {max_retries} attempts failed to check available MON: {str(e)}")
                    return False
        
        # We should never reach here, but just in case
        return False

    async def get_monad_balance(self) -> float:
        """Get native MON balance."""
        try:
            balance_wei = await self.monad_web3.eth.get_balance(self.account.address)
            return float(self.monad_web3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get MON balance: {str(e)}")
            return 0

    async def get_native_balance(self, network: str) -> float:
        """Get native token balance for a specific network."""
        try:
            web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(CRUSTY_SWAP_RPCS[network]))
            return await web3.eth.get_balance(self.account.address)
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get balance for {network}: {str(e)}")
            return None

    async def wait_for_balance_increase(self, initial_balance: float) -> bool:
        """Wait for MON balance to increase after refuel."""
        # Use the timeout from config
        timeout = self.config.CRUSTY_SWAP.MAX_WAIT_TIME
        
        logger.info(f"[{self.account_index}] Waiting for balance to increase (max wait time: {timeout} seconds)...")
        start_time = asyncio.get_event_loop().time()
        
        # Check balance every 5 seconds until timeout
        while asyncio.get_event_loop().time() - start_time < timeout:
            current_balance = await self.get_monad_balance()
            if current_balance > initial_balance:
                logger.success(
                    f"[{self.account_index}] Balance increased from {initial_balance} to {current_balance} MON"
                )
                return True
            
            # Log progress every 15 seconds
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if elapsed % 15 == 0:
                logger.info(f"[{self.account_index}] Still waiting for balance to increase... ({elapsed}/{timeout} seconds)")
            
            await asyncio.sleep(5)
        
        logger.error(f"[{self.account_index}] Balance didn't increase after {timeout} seconds")
        return False
    
    async def get_gas_params(self, web3: AsyncWeb3) -> Dict[str, int]:
        """Get gas parameters for transaction."""
        latest_block = await web3.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        max_priority_fee = await web3.eth.max_priority_fee
        max_fee = int((base_fee + max_priority_fee) * 1.5)
        
        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }
    
    async def get_minimum_deposit(self, network: str) -> int:
        """Get minimum deposit amount for a specific network."""
        try:
            web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(CRUSTY_SWAP_RPCS[network]))
            contract = web3.eth.contract(address=CONTRACT_ADDRESSES[network], abi=CRUSTY_SWAP_ABI)
            return await contract.functions.minimumDeposit().call()
        except Exception as e:
            logger.error(f"[{self.account_index}] Error getting minimum deposit: {str(e)}")
            return 0
        
    async def get_eligible_networks(self, max_retries=5, retry_delay=5):
        """
        Get eligible networks for refueling with retry mechanism.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 5)
            retry_delay: Delay between retries in seconds (default: 5)
            
        Returns:
            List of tuples (network, balance) or False if no eligible networks found
        """
        for attempt in range(1, max_retries + 1):
            try:
                eligible_networks = []
                
                networks_to_refuel_from = self.config.CRUSTY_SWAP.NETWORKS_TO_REFUEL_FROM
                for network in networks_to_refuel_from:
                    balance = await self.get_native_balance(network)
                    if balance > await self.get_minimum_deposit(network):
                        eligible_networks.append((network, balance))
                return eligible_networks
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"[{self.account_index}] Attempt {attempt}/{max_retries} failed to get eligible networks: {str(e)}")
                    logger.info(f"[{self.account_index}] Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"[{self.account_index}] All {max_retries} attempts failed to get eligible networks: {str(e)}")
                    return False
        
        # We should never reach here, but just in case
        return False

    async def pick_network_to_refuel_from(self):
        eligible_networks = await self.get_eligible_networks()
        if not eligible_networks:
            logger.info(f"[{self.account_index}] No eligible networks found")
            return False
        return random.choice(eligible_networks)

    
    async def refuel(self) -> bool:
        """Refuel MON from one of the supported networks."""
        try:
            # Get current MON balance before refuel
            initial_balance = await self.get_monad_balance()
            logger.info(f"[{self.account_index}] Initial MON balance: {initial_balance}")
            if initial_balance > self.config.CRUSTY_SWAP.MINIMUM_BALANCE_TO_REFUEL:
                logger.info(f"[{self.account_index}] Current balance ({initial_balance}) is above minimum "
                    f"({self.config.CRUSTY_SWAP.MINIMUM_BALANCE_TO_REFUEL}), skipping refuel"
                )
                return False
            network, balance = await self.pick_network_to_refuel_from()
            if not network:
                logger.error(f"[{self.account_index}] No network found")
                return False
            # Get web3 for the selected network
            web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(CRUSTY_SWAP_RPCS[network]))
            gas_params = await self.get_gas_params(web3)
            contract = web3.eth.contract(address=CONTRACT_ADDRESSES[network], abi=CRUSTY_SWAP_ABI)
            # Estimate gas using the same gas parameters from get_balances

            gas_estimate = await web3.eth.estimate_gas({
                'from': self.account.address,
                'to': CONTRACT_ADDRESSES[network],
                'value': await contract.functions.minimumDeposit().call(),
                'data': contract.functions.deposit(
                        ZERO_ADDRESS,
                    )._encode_transaction_data(),
            })

            if self.config.CRUSTY_SWAP.BRIDGE_ALL:

                # Calculate exact gas units needed (same as tx)
                gas_units = int(gas_estimate * 1.2)
                
                # Calculate maximum possible gas cost
                max_total_gas_cost = (gas_units * gas_params['maxFeePerGas']) * random.uniform(1.15, 1.2)
                max_total_gas_cost = int(max_total_gas_cost + web3.to_wei(random.uniform(0.00001, 0.00002), 'ether'))

                
                # Calculate amount we can send
                amount_wei = balance - max_total_gas_cost

                if web3.from_wei(amount_wei, 'ether') > self.config.CRUSTY_SWAP.BRIDGE_ALL_MAX_AMOUNT:
                    amount_wei = int(web3.to_wei(self.config.CRUSTY_SWAP.BRIDGE_ALL_MAX_AMOUNT * (random.uniform(0.95, 0.99)), 'ether'))
                # Double check our math
                total_needed = amount_wei + max_total_gas_cost

                # Verify we have enough for the transaction
                if total_needed > balance:
                    raise Exception(f"Insufficient funds. Have: {balance}, Need: {total_needed}, Difference: {total_needed - balance}")
            else:
                amount_ether = random.uniform(
                    self.config.CRUSTY_SWAP.AMOUNT_TO_REFUEL[0], 
                    self.config.CRUSTY_SWAP.AMOUNT_TO_REFUEL[1]
                    )
                
                amount_wei = int(round(web3.to_wei(amount_ether, 'ether'), random.randint(8, 12)))
            # Get nonce
            nonce = await web3.eth.get_transaction_count(self.account.address)
            has_enough_monad = await self.check_available_monad(amount_wei, contract)
            if not has_enough_monad:
                logger.error(f"[{self.account_index}] Not enough MON in the contract for your amount of ETH deposit, try again later")
                return False
            tx = {
                'from': self.account.address,
                'to': CONTRACT_ADDRESSES[network],
                'value': amount_wei,
                'data': contract.functions.deposit(
                        ZERO_ADDRESS,
                    )._encode_transaction_data(),
                'nonce': nonce,
                'gas': int(gas_estimate * 1.1),  # Add 10% buffer to gas estimate
                'chainId': await web3.eth.chain_id,
                **gas_params  # Use the same gas params that we calculated during get_balances
            }
            
            # Sign and send transaction
            signed_tx = web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"[{self.account_index}] Waiting for refuel transaction confirmation...")
            receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
            
            explorer_url = f"{EXPLORER_URLS[network]}{tx_hash.hex()}"
            
            if receipt['status'] == 1:
                logger.success(f"[{self.account_index}] Refuel transaction successful! Explorer URL: {explorer_url}")
                
                # Wait for balance to increase if configured to do so
                if self.config.CRUSTY_SWAP.WAIT_FOR_FUNDS_TO_ARRIVE:
                    logger.success(f"[{self.account_index}] Waiting for balance increase...")
                    if await self.wait_for_balance_increase(initial_balance):
                        logger.success(f"[{self.account_index}] Successfully refueled from {network}")
                        return True
                    logger.warning(f"[{self.account_index}] Balance didn't increase, but transaction was successful")
                    return True
                else:
                    logger.success(f"[{self.account_index}] Successfully refueled from {network} (not waiting for balance)")
                    return True
            else:
                logger.error(f"[{self.account_index}] Refuel transaction failed! Explorer URL: {explorer_url}")
                return False
                
        except Exception as e:
            logger.error(f"[{self.account_index}] Refuel failed: {str(e)}")
            return False

    async def check_minimal_sell(self, initial_balance, max_retries=5, retry_delay=5) -> bool:
        """
        Check if the balance is above the minimal sell amount.
        
        Args:
            initial_balance: Current balance to check against minimal sell amount
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Tuple[bool, float]: (is_above_minimum, minimal_sell_amount_in_ether)
        """
        for attempt in range(1, max_retries + 1):
            try:
                minimal_sell = await self.monad_contract.functions.minimumSell().call()
                minimal_sell_ether = self.monad_web3.from_wei(minimal_sell, 'ether')
                logger.info(f"[{self.account_index}] Minimal sell amount: {minimal_sell_ether} MON")
                
                if initial_balance > minimal_sell_ether:
                    logger.success(f"[{self.account_index}] Balance is above minimal sell amount")
                    return True, minimal_sell_ether
                else:
                    logger.warning(f"[{self.account_index}] Balance is below minimal sell amount")
                    return False, minimal_sell_ether
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"[{self.account_index}] Attempt {attempt}/{max_retries} failed to check minimal sell: {str(e)}")
                    logger.info(f"[{self.account_index}] Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"[{self.account_index}] All {max_retries} attempts failed to check minimal sell: {str(e)}")
                    return False, 0
        
        # We should never reach here, but just in case
        return False, 0

    
    async def check_pull_capacity(self, max_retries=5, retry_delay=5) -> float:
        """
        Check the available pull capacity from the contract.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            float: Available pull capacity in ether
        """
        for attempt in range(1, max_retries + 1):
            try:
                pull_capacity = await self.monad_contract.functions.getAvailableCapacity().call()
                pull_capacity_ether = self.monad_web3.from_wei(pull_capacity, 'ether')
                logger.info(f"[{self.account_index}] Current pull capacity: {pull_capacity_ether} MON")
                return pull_capacity_ether
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"[{self.account_index}] Attempt {attempt}/{max_retries} failed to check pull capacity: {str(e)}")
                    logger.info(f"[{self.account_index}] Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"[{self.account_index}] All {max_retries} attempts failed to check pull capacity: {str(e)}")
                    return 0
        
        # We should never reach here, but just in case
        return 0

    async def wait_for_eth_balance_increase(self, initial_balance: int) -> bool:
        """Wait for MON balance to increase after refuel."""
        # Use the timeout from config
        timeout = self.config.CRUSTY_SWAP.MAX_WAIT_TIME
        logger.info(f"[{self.account_index}] Waiting for balance to increase (max wait time: {timeout} seconds)...")
        start_time = asyncio.get_event_loop().time()
        
        # Check balance every 5 seconds until timeout
        while asyncio.get_event_loop().time() - start_time < timeout:
            current_balance = await self.get_native_balance("Arbitrum")
            if current_balance > initial_balance:
                logger.success(
                    f"[{self.account_index}] Balance increased from {self.monad_web3.from_wei(initial_balance, 'ether')} to {self.monad_web3.from_wei(current_balance, 'ether')} ETH"
                )
                return True
            
            # Log progress every 15 seconds
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if elapsed % 15 == 0:
                logger.info(f"[{self.account_index}] Still waiting for balance to increase... ({elapsed}/{timeout} seconds)")
            
            await asyncio.sleep(5)
        
        logger.error(f"[{self.account_index}] Balance didn't increase after {timeout} seconds")
        return False
    
    async def sell_monad(self) -> bool:
        """Sell MON from Crusty Swap."""
        try:
            # Get current MON balance before refuel
            initial_balance = await self.get_monad_balance()
            initial_balance_eth = await self.get_native_balance("Arbitrum")
            logger.info(f"[{self.account_index}] Initial MON balance: {initial_balance}")
            check_minimal_sell, minimal_sell_ether = await self.check_minimal_sell(initial_balance)
            if not check_minimal_sell:
                logger.error(f"[{self.account_index}] Your wallet doesn't have enough MON to sell. Balance: {initial_balance} MON, Minimal sell: {minimal_sell_ether} MON")
                return False
            
            pull_capacity_ether = await self.check_pull_capacity()
            if pull_capacity_ether < minimal_sell_ether:
                logger.error(f"[{self.account_index}] Not enough pull capacity to sell MINIMUM AMOUNT: {minimal_sell_ether} MON")
                return False

            percent_to_sell = random.uniform(
                self.config.CRUSTY_SWAP.SELL_PERCENT_OF_BALANCE[0], 
                self.config.CRUSTY_SWAP.SELL_PERCENT_OF_BALANCE[1]
                )
            
            amount_to_sell_ether = (initial_balance * percent_to_sell) / 100

            if amount_to_sell_ether > self.config.CRUSTY_SWAP.SELL_MAXIMUM_AMOUNT:
                amount_to_sell_ether = self.config.CRUSTY_SWAP.SELL_MAXIMUM_AMOUNT * random.uniform(0.95, 0.99)
            amount_to_sell_wei = int(round(self.monad_web3.to_wei(amount_to_sell_ether, 'ether'), random.randint(8, 12)))
            
            nonce = await self.monad_web3.eth.get_transaction_count(self.account.address)
            difference = amount_to_sell_ether - initial_balance
            if difference < 0.03:
                amount_to_sell_ether = amount_to_sell_ether - random.uniform(0.03, 0.04)
                amount_to_sell_wei = int(round(self.monad_web3.to_wei(amount_to_sell_ether, 'ether'), random.randint(8, 12)))
            
            if amount_to_sell_ether < minimal_sell_ether:
                amount_to_sell_wei = int(round(self.monad_web3.to_wei(minimal_sell_ether, 'ether') * random.uniform(1.01, 1.1), random.randint(8, 12)))
            
            logger.info(f"[{self.account_index}] Trying to sell: {self.monad_web3.from_wei(amount_to_sell_wei, 'ether')} MON")
            gas_params = await self.get_gas_params(self.monad_web3)
            gas_estimate = await self.monad_web3.eth.estimate_gas({
                'from': self.account.address,
                'to': self.monad_contract.address,
                'value': amount_to_sell_wei,
                'data': self.monad_contract.functions.sellMonad()._encode_transaction_data(),
            })

            tx = {
                'from': self.account.address,
                'to': self.monad_contract.address,
                'value': amount_to_sell_wei,
                'data': self.monad_contract.functions.sellMonad()._encode_transaction_data(),
                'nonce': nonce,
                'gas': int(gas_estimate * 1.1),  # Add 10% buffer to gas estimate
                'chainId': await self.monad_web3.eth.chain_id,
                **gas_params  # Use the same gas params that we calculated during get_balances
            }
        

            # Sign and send transaction
            signed_tx = self.monad_web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await self.monad_web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"[{self.account_index}] Waiting for sell transaction confirmation...")
            receipt = await self.monad_web3.eth.wait_for_transaction_receipt(tx_hash)
            
            explorer_url = f"{EXPLORER_URL}{tx_hash.hex()}"
            
            if receipt['status'] == 1:
                logger.success(f"[{self.account_index}] Sell transaction successful! Explorer URL: {explorer_url}")
                
                # Wait for balance to increase if configured to do so
                if self.config.CRUSTY_SWAP.WAIT_FOR_FUNDS_TO_ARRIVE:
                    logger.success(f"[{self.account_index}] Waiting for balance increase...")
                    if await self.wait_for_eth_balance_increase(initial_balance_eth):
                        logger.success(f"[{self.account_index}] Successfully sold monad")
                        return True
                    logger.warning(f"[{self.account_index}] Balance didn't increase, but transaction was successful")
                    return True
                else:
                    logger.success(f"[{self.account_index}] Successfully sold monad (not waiting for balance)")
                    return True
            else:
                logger.error(f"[{self.account_index}] Sell transaction failed! Explorer URL: {explorer_url}")
                return False
                
        except Exception as e:
            logger.error(f"[{self.account_index}] Sell failed: {str(e)}")
            
            return False
    
    def _convert_private_keys_to_addresses(self, private_keys_to_distribute):
        """Convert private keys to addresses."""
        addresses = []
        for private_key in private_keys_to_distribute:
            addresses.append(Account.from_key(private_key).address)
        return addresses
    
    async def _get_monad_balance(self, address) -> float:
        """Get native MON balance."""
        try:
            balance_wei = await self.monad_web3.eth.get_balance(address)
            return float(self.monad_web3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get MON balance: {str(e)}")
            return None
        
    async def _wait_for_balance_increase(self, initial_balance: float, address: str) -> bool:
        """Wait for MON balance to increase after refuel."""
        # Use the timeout from config
        timeout = self.config.CRUSTY_SWAP.MAX_WAIT_TIME
        
        logger.info(f"[{self.account_index}] Waiting for balance to increase (max wait time: {timeout} seconds)...")
        start_time = asyncio.get_event_loop().time()
        
        # Check balance every 5 seconds until timeout
        while asyncio.get_event_loop().time() - start_time < timeout:
            current_balance = await self._get_monad_balance(address)
            if current_balance > initial_balance:
                logger.success(
                    f"[{self.account_index}] Balance increased from {initial_balance} to {current_balance} MON"
                )
                return True
            
            # Log progress every 15 seconds
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if elapsed % 15 == 0:
                logger.info(f"[{self.account_index}] Still waiting for balance to increase... ({elapsed}/{timeout} seconds)")
            
            await asyncio.sleep(5)
        
        logger.error(f"[{self.account_index}] Balance didn't increase after {timeout} seconds")
        return False
    
    async def _handle_transaction_status(self, receipt, explorer_url, initial_balance, network, address) -> bool:
        if receipt['status'] == 1:
            logger.success(f"[{self.account_index}] Refuel transaction successful! Explorer URL: {explorer_url}")
            
            # Wait for balance to increase if configured to do so
            if self.config.CRUSTY_SWAP.WAIT_FOR_FUNDS_TO_ARRIVE:
                logger.success(f"[{self.account_index}] Waiting for balance increase...")
                if await self._wait_for_balance_increase(initial_balance, address):
                    logger.success(f"[{self.account_index}] Successfully refueled from {network}")
                    return True
                logger.warning(f"[{self.account_index}] Balance didn't increase, but transaction was successful")
                return True
            else:
                logger.success(f"[{self.account_index}] Successfully refueled from {network} (not waiting for balance)")
                return True
        else:
            logger.error(f"[{self.account_index}] Refuel transaction failed! Explorer URL: {explorer_url}")
            return False


    
    async def send_refuel_from_one_to_all(self, address) -> bool:
        """Send a refuel transaction from one of the supported networks."""
        try:
            initial_balance = await self._get_monad_balance(address)
            if initial_balance is None:
                logger.error(f"[{self.account_index}] Failed to get MON balance for address: {address}")
                return False
            logger.info(f"[{self.account_index}] Initial MON balance: {initial_balance}")
            if initial_balance > self.config.CRUSTY_SWAP.MINIMUM_BALANCE_TO_REFUEL:
                logger.info(f"[{self.account_index}] Current balance ({initial_balance}) is above minimum "
                    f"({self.config.CRUSTY_SWAP.MINIMUM_BALANCE_TO_REFUEL}), skipping refuel"
                )
                return False
            network, balance = await self.pick_network_to_refuel_from()
            if not network:
                logger.error(f"[{self.account_index}] No network found")
                return False
            # Get web3 for the selected network
            web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(CRUSTY_SWAP_RPCS[network]))
            gas_params = await self.get_gas_params(web3)
            contract = web3.eth.contract(address=REFUEL_FROM_ONE_TO_ALL_CONTRACT_ADDRESS[network], abi=REFUEL_FROM_ONE_TO_ALL_CONTRACT_ABI)
            # Estimate gas using the same gas parameters from get_balances

            gas_estimate = await web3.eth.estimate_gas({
                'from': self.account.address,
                'to': REFUEL_FROM_ONE_TO_ALL_CONTRACT_ADDRESS[network],
                'value': await contract.functions.minimumDeposit().call(),
                'data': contract.functions.deposit(
                        ZERO_ADDRESS,
                        address
                    )._encode_transaction_data(),
            })

            if self.config.CRUSTY_SWAP.BRIDGE_ALL:

                # Calculate exact gas units needed (same as tx)
                gas_units = int(gas_estimate * 1.2)
                
                # Calculate maximum possible gas cost
                max_total_gas_cost = (gas_units * gas_params['maxFeePerGas']) * random.uniform(1.15, 1.2)
                max_total_gas_cost = int(max_total_gas_cost + web3.to_wei(random.uniform(0.00001, 0.00002), 'ether'))

                
                # Calculate amount we can send
                amount_wei = balance - max_total_gas_cost

                if web3.from_wei(amount_wei, 'ether') > self.config.CRUSTY_SWAP.BRIDGE_ALL_MAX_AMOUNT:
                    amount_wei = int(web3.to_wei(self.config.CRUSTY_SWAP.BRIDGE_ALL_MAX_AMOUNT * (random.uniform(0.95, 0.99)), 'ether'))
                # Double check our math
                total_needed = amount_wei + max_total_gas_cost

                # Verify we have enough for the transaction
                if total_needed > balance:
                    raise Exception(f"Insufficient funds. Have: {balance}, Need: {total_needed}, Difference: {total_needed - balance}")
            else:
                amount_ether = random.uniform(
                    self.config.CRUSTY_SWAP.AMOUNT_TO_REFUEL[0], 
                    self.config.CRUSTY_SWAP.AMOUNT_TO_REFUEL[1]
                    )
                
                amount_wei = int(round(web3.to_wei(amount_ether, 'ether'), random.randint(8, 12)))
            # Get nonce
            nonce = await web3.eth.get_transaction_count(self.account.address)
            has_enough_monad = await self.check_available_monad(amount_wei, contract)
            if not has_enough_monad:
                logger.error(f"[{self.account_index}] Not enough MON in the contract for your amount of ETH deposit, try again later")
                return False
            tx = {
                'from': self.account.address,
                'to': REFUEL_FROM_ONE_TO_ALL_CONTRACT_ADDRESS[network],
                'value': amount_wei,
                'data': contract.functions.deposit(
                        ZERO_ADDRESS,
                        address
                    )._encode_transaction_data(),
                'nonce': nonce,
                'gas': int(gas_estimate * 1.1),  # Add 10% buffer to gas estimate
                'chainId': await web3.eth.chain_id,
                **gas_params  # Use the same gas params that we calculated during get_balances
            }
            
            # Sign and send transaction
            signed_tx = web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"[{self.account_index}] Waiting for refuel transaction confirmation...")
            receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
            
            explorer_url = f"{EXPLORER_URLS[network]}{tx_hash.hex()}"
            await self._handle_transaction_status(receipt, explorer_url, initial_balance, network, address)

        except Exception as e:
            logger.error(f"[{self.account_index}] Refuel failed: {str(e)}")
            return False

    async def refuel_from_one_to_all(self, private_keys_to_distribute) -> bool:
        """Refuel MON from one of the supported networks."""
        try:
            addresses = self._convert_private_keys_to_addresses(private_keys_to_distribute)
            for index, address in enumerate(addresses):
                logger.info(f"[{self.account_index}] - [{index}/{len(addresses)}] Refueling from MAIN: {self.account.address} to: {address} ")
                status = await self.send_refuel_from_one_to_all(address)
                pause = random.uniform(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACCOUNTS[0], 
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACCOUNTS[1]
                )
                await asyncio.sleep(pause)
            return True
        except Exception as e:
            logger.error(f"[{self.account_index}] Refuel failed: {str(e)}")
            return False