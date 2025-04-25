from web3 import AsyncWeb3
from eth_account import Account
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
import random
import asyncio
from loguru import logger
from src.utils.config import Config
from src.model.memebridge.constansts import (
    MEMEBRIDGE_RPCS, 
    MEMEBRIDGE_ADDRESS, 
    MEMEBRIDGE_CALLLDATA,
    MEMEBRIDGE_EXPLORERS
)
from src.utils.constants import RPC_URL


class Memebridge:
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
            web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(MEMEBRIDGE_RPCS[network]))
            return await web3.eth.get_balance(self.account.address)
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get balance for {network}: {str(e)}")
            return None

    async def wait_for_balance_increase(self, initial_balance: float) -> bool:
        """Wait for MON balance to increase after refuel."""
        # Use the timeout from config
        timeout = self.config.MEMEBRIDGE.MAX_WAIT_TIME
        
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
    

    async def get_eligible_networks(self):
        try:
            eligible_networks = []
            networks_to_refuel_from = self.config.MEMEBRIDGE.NETWORKS_TO_REFUEL_FROM
            for network in networks_to_refuel_from:
                balance = await self.get_native_balance(network)
                if self.monad_web3.from_wei(balance, 'ether') > 0.0001:
                    eligible_networks.append((network, balance))
            return eligible_networks
        except Exception as e:
            logger.error(f"[{self.account_index}] Error getting eligible networks: {str(e)}")
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
            if initial_balance > self.config.MEMEBRIDGE.MINIMUM_BALANCE_TO_REFUEL:
                logger.info(f"[{self.account_index}] Current balance ({initial_balance}) is above minimum "
                    f"({self.config.MEMEBRIDGE.MINIMUM_BALANCE_TO_REFUEL}), skipping refuel"
                )
                return False
            logger.info(f"[{self.account_index}] Initial MON balance: {initial_balance}")
            network, balance = await self.pick_network_to_refuel_from()
            if not network:
                logger.error(f"[{self.account_index}] No network found")
                return False
            # Get web3 for the selected network
            web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(MEMEBRIDGE_RPCS[network]))
            gas_params = await self.get_gas_params(web3)
            # Estimate gas using the same gas parameters from get_balances
            gas_estimate = await web3.eth.estimate_gas({
                'from': self.account.address,
                'to': MEMEBRIDGE_ADDRESS,
                'value': balance,
                'data': MEMEBRIDGE_CALLLDATA,
            })
            if self.config.MEMEBRIDGE.BRIDGE_ALL:
                # Calculate exact gas units needed (same as tx)
                gas_units = int(gas_estimate * 1.2)
                
                # Calculate maximum possible gas cost
                max_total_gas_cost = (gas_units * gas_params['maxFeePerGas']) * random.uniform(1.15, 1.2)
                max_total_gas_cost = int(max_total_gas_cost + web3.to_wei(random.uniform(0.00001, 0.00002), 'ether'))

                
                # Calculate amount we can send
                amount_wei = balance - max_total_gas_cost
                if web3.to_wei(amount_wei, 'ether') > self.config.MEMEBRIDGE.BRIDGE_ALL_MAX_AMOUNT:
                    amount_wei = int(web3.to_wei(self.config.MEMEBRIDGE.BRIDGE_ALL_MAX_AMOUNT * (random.uniform(0.95, 0.99)), 'ether'))
                # Double check our math
                total_needed = amount_wei + max_total_gas_cost

                # Verify we have enough for the transaction
                if total_needed > balance:
                    raise Exception(f"Insufficient funds. Have: {balance}, Need: {total_needed}, Difference: {total_needed - balance}")
            else:
                amount_ether = random.uniform(
                    self.config.MEMEBRIDGE.AMOUNT_TO_REFUEL[0], 
                    self.config.MEMEBRIDGE.AMOUNT_TO_REFUEL[1]
                    )
                
                amount_wei = int(round(web3.to_wei(amount_ether, 'ether'), random.randint(8, 12)))
            # Get nonce
            nonce = await web3.eth.get_transaction_count(self.account.address)
            
            tx = {
                'from': self.account.address,
                'to': MEMEBRIDGE_ADDRESS,
                'value': amount_wei,
                'data': MEMEBRIDGE_CALLLDATA,
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
            
            explorer_url = f"{MEMEBRIDGE_EXPLORERS[network]}{tx_hash.hex()}"
            
            if receipt['status'] == 1:
                logger.success(f"[{self.account_index}] Refuel transaction successful! Explorer URL: {explorer_url}")
                
                # Wait for balance to increase if configured to do so
                if self.config.MEMEBRIDGE.WAIT_FOR_FUNDS_TO_ARRIVE:
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
