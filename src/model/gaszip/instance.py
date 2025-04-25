from web3 import AsyncWeb3
from eth_account import Account
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
import random
import asyncio
from loguru import logger
from src.utils.config import Config
from src.model.gaszip.constants import (
    GASZIP_RPCS, 
    REFUEL_ADDRESS, 
    REFUEL_CALLLDATA,
    GASZIP_EXPLORERS
)
from src.utils.constants import RPC_URL


class Gaszip:
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
            web3 = AsyncWeb3(
                AsyncWeb3.AsyncHTTPProvider(
                    GASZIP_RPCS[network], request_kwargs={"ssl": False}
                )
            )
            balance_wei = await web3.eth.get_balance(self.account.address)
            return float(web3.from_wei(balance_wei, "ether"))
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get balance for {network}: {str(e)}")
            return 0

    async def wait_for_balance_increase(self, initial_balance: float) -> bool:
        """Wait for MON balance to increase after refuel."""
        # Use the timeout from config
        timeout = self.config.GASZIP.MAX_WAIT_TIME
        
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

    async def get_balances(self) -> Optional[Tuple[str, float, Dict[str, int]]]:
        """
        Check balances across networks and return a network with sufficient balance.
        Returns tuple of (network_name, amount_to_refuel, gas_params) or None if no suitable network found.
        """
        try:
            # First check if current MON balance is already sufficient
            current_mon_balance = await self.get_monad_balance()
            logger.info(f"[{self.account_index}] Current MON balance: {current_mon_balance}")
            
            if current_mon_balance >= self.config.GASZIP.MINIMUM_BALANCE_TO_REFUEL:
                logger.info(
                    f"[{self.account_index}] Current balance ({current_mon_balance}) is above minimum "
                    f"({self.config.GASZIP.MINIMUM_BALANCE_TO_REFUEL}), skipping refuel"
                )
                return None
            
            eligible_networks = []
            
            # Determine amount to refuel based on configuration
            if not self.config.GASZIP.BRIDGE_ALL:
                # Use the configured range if not bridging all
                amount_to_refuel = random.uniform(
                    self.config.GASZIP.AMOUNT_TO_REFUEL[0],
                    self.config.GASZIP.AMOUNT_TO_REFUEL[1]
                )
                logger.info(f"[{self.account_index}] Using configured amount: {amount_to_refuel} ETH")
            else:
                # We'll determine the exact amount per network later
                amount_to_refuel = None
                logger.info(f"[{self.account_index}] Will bridge maximum amount based on balance")
            
            for network in self.config.GASZIP.NETWORKS_TO_REFUEL_FROM:
                balance = await self.get_native_balance(network)
                logger.info(f"[{self.account_index}] {network} balance: {balance}")
                
                if self.config.GASZIP.BRIDGE_ALL:
                    # Get a Web3 instance for this network
                    web3 = AsyncWeb3(
                        AsyncWeb3.AsyncHTTPProvider(
                            GASZIP_RPCS[network], request_kwargs={"ssl": False}
                        )
                    )

                    # Build the actual transaction to estimate its gas cost
                    try:
                        # Get the current gas parameters (EIP-1559 or legacy)
                        # Store these for reuse in the actual transaction
                        gas_params = await self.get_gas_params(web3)
                        
                        # Create transaction object that would be used for bridging
                        tx = {
                            'from': self.account.address,
                            'to': REFUEL_ADDRESS,
                            'data': REFUEL_CALLLDATA,
                            'value': web3.to_wei(0.0001, 'ether'),  # Dummy value for estimation
                            **gas_params
                        }
                        
                        # Estimate gas for this exact transaction
                        estimated_gas = await web3.eth.estimate_gas(tx)
                        
                        # Calculate total cost with a 10% buffer for safety
                        gas_price_wei = gas_params.get('maxFeePerGas', gas_params.get('gasPrice', 0))
                        total_gas_cost_wei = int(estimated_gas * gas_price_wei * 1.1)
                        
                        # Convert to ETH
                        gas_reserve = float(web3.from_wei(total_gas_cost_wei, 'ether')) + random.uniform(0.000005, 0.00001)    
                        logger.info(f"[{self.account_index}] Estimated gas for {network} transaction: {estimated_gas} units")
                        logger.info(f"[{self.account_index}] Calculated gas reserve: {gas_reserve} ETH")
                        
                    except Exception as e:
                        logger.error(f"[{self.account_index}] Failed to estimate transaction cost: {str(e)}")
                        continue  # Skip this network if we can't estimate gas
                    
                    # Only proceed if we have more than the gas cost
                    if balance > gas_reserve:
                        max_to_bridge = balance - gas_reserve
                        
                        # If balance exceeds max amount, apply the limit with randomization
                        if self.config.GASZIP.BRIDGE_ALL_MAX_AMOUNT and max_to_bridge > self.config.GASZIP.BRIDGE_ALL_MAX_AMOUNT:
                            # Apply 1-3% random reduction to avoid same amount transfers
                            random_reduction = random.uniform(0.01, 0.05)
                            network_amount = self.config.GASZIP.BRIDGE_ALL_MAX_AMOUNT * (1 - random_reduction)
                            logger.info(f"[{self.account_index}] Limiting bridge amount to {network_amount} ETH (max: {self.config.GASZIP.BRIDGE_ALL_MAX_AMOUNT} with {random_reduction*100:.1f}% reduction)")
                        else:
                            network_amount = max_to_bridge
                            logger.info(f"[{self.account_index}] Will bridge {network_amount} ETH (full available balance minus gas cost of {gas_reserve} ETH)")
                        
                        eligible_networks.append((network, network_amount, gas_params))
                else:
                    # For fixed amount refueling, we still need to get gas params
                    if balance > amount_to_refuel:
                        try:
                            web3 = AsyncWeb3(
                                AsyncWeb3.AsyncHTTPProvider(
                                    GASZIP_RPCS[network], request_kwargs={"ssl": False}
                                )
                            )
                            gas_params = await self.get_gas_params(web3)
                            eligible_networks.append((network, amount_to_refuel, gas_params))
                        except Exception as e:
                            logger.error(f"[{self.account_index}] Failed to get gas params for {network}: {str(e)}")
                            continue
            
            if not eligible_networks:
                logger.warning(f"[{self.account_index}] No networks with sufficient balance found")
                return None
            
            # Randomly select from eligible networks
            selected = random.choice(eligible_networks)
            selected_network, final_amount, selected_gas_params = selected
            logger.info(f"[{self.account_index}] Selected {selected_network} for refueling with {final_amount} ETH")
            
            return (selected_network, final_amount, selected_gas_params)
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error checking balances: {str(e)}")
            return None

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
    
    async def refuel(self) -> bool:
        """Refuel MON from one of the supported networks."""
        try:
            # Get current MON balance before refuel
            initial_balance = await self.get_monad_balance()
            logger.info(f"[{self.account_index}] Initial MON balance: {initial_balance}")
            
            # Check balances across networks and select one to refuel from
            balance_check = await self.get_balances()
            if not balance_check:
                logger.info(f"[{self.account_index}] No refueling needed or possible")
                return False
                
            network, amount, gas_params = balance_check
            logger.info(f"[{self.account_index}] Refueling from {network} with {amount} ETH")
            
            # Get web3 for the selected network
            web3 = AsyncWeb3(
                AsyncWeb3.AsyncHTTPProvider(
                    GASZIP_RPCS[network], request_kwargs={"ssl": False}
                )
            )
            
            # Convert amount to wei
            amount_wei = web3.to_wei(amount, "ether")
            
            # Get nonce
            nonce = await web3.eth.get_transaction_count(self.account.address)
            
            # Estimate gas using the same gas parameters from get_balances
            gas_estimate = await web3.eth.estimate_gas({
                'from': self.account.address,
                'to': REFUEL_ADDRESS,
                'value': amount_wei,
                'data': REFUEL_CALLLDATA,
            })
            
            tx = {
                'from': self.account.address,
                'to': REFUEL_ADDRESS,
                'value': amount_wei,
                'data': REFUEL_CALLLDATA,
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
            
            explorer_url = f"{GASZIP_EXPLORERS[network]}{tx_hash.hex()}"
            
            if receipt['status'] == 1:
                logger.success(f"[{self.account_index}] Refuel transaction successful! Explorer URL: {explorer_url}")
                
                # Wait for balance to increase if configured to do so
                if self.config.GASZIP.WAIT_FOR_FUNDS_TO_ARRIVE:
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
