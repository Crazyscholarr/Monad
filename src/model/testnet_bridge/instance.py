from web3 import AsyncWeb3, Web3
from eth_account import Account
from typing import Dict, Optional, List, Tuple
import random
import asyncio
from loguru import logger
from src.utils.config import Config
from src.model.testnet_bridge.constants import (
    TESTNET_BRIDGE_RPCS, 
    TESTNET_BRIDGE_ADDRESS, 
    TESTNET_BRIDGE_ABI,
    TESTNET_BRIDGE_EXPLORERS,
    ESTIMATE_SEND_FEE_CONTRACT_ADDRESS
)


class TestnetBridge:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        private_key: str,
        config: Config,
        session,  # Add session parameter
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = private_key
        self.config = config
        self.session = session  # Store the session
        self.account = Account.from_key(private_key)
        
        # Initialize Web3 connections for each network
        self.web3_connections = {}
        for network, rpc in TESTNET_BRIDGE_RPCS.items():
            self.web3_connections[network] = AsyncWeb3(
                AsyncWeb3.AsyncHTTPProvider(rpc, request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False})
            )
            
        # Initialize contract objects for each network
        self.bridge_contracts = {}
        for network in TESTNET_BRIDGE_ADDRESS:
            if network in self.web3_connections:
                self.bridge_contracts[network] = self.web3_connections[network].eth.contract(
                    address=self.web3_connections[network].to_checksum_address(TESTNET_BRIDGE_ADDRESS[network]),
                    abi=TESTNET_BRIDGE_ABI
                )
        
    async def get_sepolia_balance(self) -> float:
        """Get native ETH balance on Sepolia."""
        try:
            sepolia_web3 = self.web3_connections.get("Sepolia")
            if not sepolia_web3:
                logger.error(f"[{self.account_index}] Sepolia web3 connection not initialized")
                raise ValueError("Sepolia web3 connection not initialized")
                
            balance_wei = await sepolia_web3.eth.get_balance(self.account.address)
            return float(sepolia_web3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get Sepolia balance: {str(e)}")
            raise e

    async def get_native_balance(self, network: str) -> float:
        """Get native token balance for a specific network."""
        try:
            if network not in self.web3_connections:
                logger.error(f"[{self.account_index}] No web3 connection for {network}")
                raise ValueError(f"No web3 connection for {network}")
                
            balance_wei = await self.web3_connections[network].eth.get_balance(self.account.address)
            return float(self.web3_connections[network].from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get balance for {network}: {str(e)}")
            raise e

    async def wait_for_balance_increase(self, initial_balance: float) -> bool:
        """Wait for Sepolia ETH balance to increase after bridge."""
        # Use the timeout from config
        timeout = self.config.TESTNET_BRIDGE.MAX_WAIT_TIME
        
        logger.info(f"[{self.account_index}] Waiting for Sepolia balance to increase (max wait time: {timeout} seconds)...")
        start_time = asyncio.get_event_loop().time()
        
        # Check balance every 5 seconds until timeout
        while asyncio.get_event_loop().time() - start_time < timeout:
            current_balance = await self.get_sepolia_balance()
            if current_balance > initial_balance:
                logger.success(
                    f"[{self.account_index}] Sepolia balance increased from {initial_balance} to {current_balance} ETH"
                )
                return True
            
            # Log progress every 15 seconds
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if elapsed % 15 == 0:
                logger.info(f"[{self.account_index}] Still waiting for Sepolia balance to increase... ({elapsed}/{timeout} seconds)")
            
            await asyncio.sleep(5)
        
        logger.error(f"[{self.account_index}] Sepolia balance didn't increase after {timeout} seconds")
        raise TimeoutError(f"Sepolia balance didn't increase after {timeout} seconds")

    async def get_suitable_network(self) -> Optional[Tuple[str, float]]:
        """
        Check balances across networks and return a network with sufficient balance.
        Returns tuple of (network_name, amount_to_bridge) or None if no suitable network found.
        """
        try:
            # First check if current Sepolia balance is already sufficient
            current_sepolia_balance = await self.get_sepolia_balance()
            logger.info(f"[{self.account_index}] Current Sepolia balance: {current_sepolia_balance}")
            
            if current_sepolia_balance >= self.config.TESTNET_BRIDGE.MINIMUM_BALANCE_TO_REFUEL:
                logger.info(
                    f"[{self.account_index}] Current Sepolia balance ({current_sepolia_balance}) is above minimum "
                    f"({self.config.TESTNET_BRIDGE.MINIMUM_BALANCE_TO_REFUEL}), skipping bridge"
                )
                return None  # This is a valid case, not an error
            
            eligible_networks = []
            if self.config.TESTNET_BRIDGE.BRIDGE_ALL:
                amount_to_bridge = 0.0001
                logger.info(f"[{self.account_index}] Checking balances for bridging ALL ETH to Sepolia")
            else:
                amount_to_bridge = random.uniform(
                    self.config.TESTNET_BRIDGE.AMOUNT_TO_REFUEL[0],
                    self.config.TESTNET_BRIDGE.AMOUNT_TO_REFUEL[1]
                )
                logger.info(f"[{self.account_index}] Checking balances for bridging {amount_to_bridge} ETH to Sepolia")
            
            
            for network in self.config.TESTNET_BRIDGE.NETWORKS_TO_REFUEL_FROM:
                balance = await self.get_native_balance(network)
                logger.info(f"[{self.account_index}] {network} balance: {balance}")
                
                # Adjust the check to ensure there's enough for the bridge plus gas
                if balance > amount_to_bridge:  # Add buffer for gas
                    eligible_networks.append(network)
            
            if not eligible_networks:
                logger.warning(f"[{self.account_index}] No networks with sufficient balance found")
                return None
            
            selected_network = random.choice(eligible_networks)
            logger.info(f"[{self.account_index}] Selected {selected_network} for bridging to Sepolia")
            
            return (selected_network, amount_to_bridge)
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error checking balances: {str(e)}")
            raise e

    async def get_gas_params(self, web3: AsyncWeb3) -> Dict[str, int]:
        """Get gas parameters for transaction."""
        try:
            latest_block = await web3.eth.get_block('latest')
            base_fee = latest_block['baseFeePerGas']
            max_priority_fee = await web3.eth.max_priority_fee
            max_fee = int((base_fee + max_priority_fee) * 2)
            
            return {
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": max_priority_fee,
            }
        except Exception as e:
            logger.error(f"[{self.account_index}] Failed to get gas parameters: {str(e)}")
            raise e
    
    async def estimate_bridge_fee(self, network: str, amount_in: int) -> int:
        """Estimate the bridge fee for a given amount."""
        try:
            contract = self.web3_connections[network].eth.contract(
                address=ESTIMATE_SEND_FEE_CONTRACT_ADDRESS,
                abi=TESTNET_BRIDGE_ABI
            )

            # Get the estimateSendFee function
            fee = await contract.functions.estimateSendFee(
                161,
                self.account.address,
                amount_in,
                False,
                b""
            ).call()
            adjusted_fee = int(fee[0] * 1.2)
            return adjusted_fee
        except Exception as e:
            logger.error(f"[{self.account_index}] Error estimating bridge fee: {str(e)}")
            raise e
            
    
    async def calculate_amount_out_min(self, network: str, amount_in: int) -> int:
        """
        Calculate the minimum amount out for the swap and bridge using eth_call.
        Uses the quoter contract to get an accurate estimate.
        Raises exceptions instead of using fallback calculations.
        """
        try:
            # Convert amount_in to hex format for the request
            amount_in_hex = Web3.to_hex(amount_in)[2:]  # Remove '0x' prefix
            
            # Format the amount_in_hex to ensure it's the right length (13 chars)
            if len(amount_in_hex) < 13:
                amount_in_hex = f"{'0' * (13 - len(amount_in_hex))}{amount_in_hex}"
            elif len(amount_in_hex) > 13:
                amount_in_hex = amount_in_hex[:13]
                
            # Common variables across networks
            fee = "0000000000000000000000000000000000000000000000000000000000000bb8"  # Fee tier (3000)
            quoter_address = "0xb27308f9f90d607463bb33ea1bebb41c27ce5ab6"  # Uniswap Quoter
            token_out = "e71bdfe1df69284f00ee185cf0d95d0c7680c0d4"  # Destination token
            
            # Define token addresses and RPC URL based on network
            if network == "Arbitrum":
                token_in = "82af49447d8a07e3bd95bd0d56f35241523fbab1"  # WETH on Arbitrum
                rpc_url = TESTNET_BRIDGE_RPCS[network]
                request_id = 82
                
            elif network == "Optimism":
                token_in = "4200000000000000000000000000000000000006"  # WETH on Optimism
                rpc_url = TESTNET_BRIDGE_RPCS[network]
                request_id = 50
                
            else:
                # For unsupported networks, raise an exception
                error_msg = f"Network {network} is not supported for quoter calculation"
                logger.error(f"[{self.account_index}] {error_msg}")
                raise ValueError(error_msg)
                
            # Construct the data payload for the eth_call
            data = f"0xf7729d43000000000000000000000000{token_in}000000000000000000000000{token_out}{fee}000000000000000000000000000000000000000000000000000{amount_in_hex}0000000000000000000000000000000000000000000000000000000000000000"
            
            # Prepare the JSON-RPC request
            json_data = [
                {
                    "method": "eth_call",
                    "params": [
                        {
                            "to": quoter_address,
                            "data": data,
                        },
                        "latest",
                    ],
                    "id": request_id,
                    "jsonrpc": "2.0",
                },
            ]
            
            logger.info(f"[{self.account_index}] Making eth_call to calculate amountOutMin for {network}")
            
            # Use the existing session instead of creating a new aiohttp session
            response = await self.session.post(rpc_url, json=json_data)
            result = response.json()
            # Get the result and convert to an integer
            if "result" in result:                
                amount_out_hex = int(result["result"], 16)
                # Apply a safety factor (95% of the quoted amount)
                amount_out = float(amount_out_hex) * 0.95

                amount_out = Web3.to_wei(amount_out, "ether")

                # Handle very large numbers
                if len(str(amount_out)) > 18:
                    amount_out = int(amount_out / 1e18)
                    
                logger.info(f"[{self.account_index}] Calculated amountOutMin for {network}: {Web3.from_wei(amount_out, 'ether')} ETH")
                return amount_out
            else:
                # Raise exception if the quote fails
                error_message = f"Failed to get quote for {network}: {result}"
                logger.error(f"[{self.account_index}] {error_message}")
                raise ValueError(error_message)
        except Exception as e:
            logger.error(f"[{self.account_index}] Error calculating amount_out_min: {str(e)}")
            raise e
    
    async def build_bridge_transaction(self, network: str, amount_to_bridge: float) -> Dict:
        """Build the bridge transaction."""
        try:
            web3 = self.web3_connections[network]
            contract = self.bridge_contracts[network]
            
            # Convert amount to wei
            amount_in = web3.to_wei(amount_to_bridge, 'ether')
            sepolia_chain_id = 161  # LayerZero chain ID for Sepolia
            
            # Get nonce and gas parameters
            nonce = await web3.eth.get_transaction_count(self.account.address)
            
            if not self.config.TESTNET_BRIDGE.BRIDGE_ALL:
                amount_out_min = await self.calculate_amount_out_min(network, amount_in)
                # Build the transaction using the contract function
                transaction = contract.functions.swapAndBridge(
                    amount_in,  # amountIn
                    amount_out_min,  # amountOutMin
                    sepolia_chain_id,  # dstChainId
                    self.account.address,  # to
                    self.account.address,  # refundAddress
                    web3.to_checksum_address("0x0000000000000000000000000000000000000000"),  # zroPaymentAddress
                    b""  # adapterParams
                )
                
                # Estimate bridge fee based on the example
                bridge_fee = await self.estimate_bridge_fee(network, amount_in)
                # Build the transaction without gas limit first
                gas_params = await self.get_gas_params(web3)
                

                built_transaction = await transaction.build_transaction({
                    "from": self.account.address,
                    "value": amount_in + bridge_fee,  # The amount plus a fee for bridging
                    "nonce": nonce,
                    "chainId": await web3.eth.chain_id,
                    "type": "0x2",  # EIP-1559 transaction
                    **gas_params
                })
                
                # Manually estimate gas for the transaction
                logger.info(f"[{self.account_index}] Estimating gas for bridge transaction...")
                estimated_gas = await web3.eth.estimate_gas({
                    "from": self.account.address,
                    "to": contract.address,
                    "value": amount_in + bridge_fee,
                    "data": built_transaction["data"],
                    "nonce": nonce,
                    "maxFeePerGas": gas_params["maxFeePerGas"],
                    "maxPriorityFeePerGas": gas_params["maxPriorityFeePerGas"],
                })
                
                # Multiply by 1.2 for safety buffer
                gas_limit = int(estimated_gas * 1.2)
                logger.info(f"[{self.account_index}] Estimated gas: {estimated_gas}, with buffer: {gas_limit}")
                
                # Add gas limit to the transaction
                built_transaction["gas"] = gas_limit
                
                return built_transaction
            
            else:
                balance = await web3.eth.get_balance(self.account.address)
                balance_ether = web3.from_wei(balance, "ether")
                if balance_ether > self.config.TESTNET_BRIDGE.BRIDGE_ALL_MAX_AMOUNT:
                    balance = int(web3.to_wei(self.config.TESTNET_BRIDGE.BRIDGE_ALL_MAX_AMOUNT, "ether") * random.uniform(0.95, 0.99))
                bridge_fee = await self.estimate_bridge_fee(network, balance)

                logger.info(f"[{self.account_index}] Attempting to bridge full balance from {network}")
                
                gas_params = await self.get_gas_params(web3)
                # Create a dummy transaction to estimate gas
                dummy_amount = web3.to_wei(0.0001, "ether")  # Small amount for estimation
                dummy_transaction = contract.functions.swapAndBridge(
                    dummy_amount,
                    1,  # minimal amount out
                    sepolia_chain_id,
                    self.account.address,
                    self.account.address,
                    web3.to_checksum_address("0x0000000000000000000000000000000000000000"),
                    b""
                )
                
                # Estimate gas for the transaction with the dummy amount
                dummy_tx = await dummy_transaction.build_transaction({
                    "from": self.account.address,
                    "value": dummy_amount + bridge_fee,
                    "nonce": nonce,
                    "chainId": await web3.eth.chain_id,
                    "type": "0x2",
                    **gas_params
                })
                # Estimate gas for the transaction
                estimated_gas = await web3.eth.estimate_gas(dummy_tx)
                gas_limit = int(estimated_gas * 1.2)  # Add 20% buffer
                
                # Calculate the gas cost in wei
                gas_cost = gas_limit * gas_params["maxFeePerGas"]
                
                # Calculate the maximum amount we can bridge
                # Full balance - (gas cost + bridge fee + small buffer)
                buffer = web3.to_wei(random.uniform(0.00001, 0.00002), "ether")  # Small buffer to prevent errors
                costs = ((gas_cost + bridge_fee) * random.uniform(1.15, 1.2)  + buffer)
                max_amount = balance - costs
                if max_amount <= 0:
                    logger.warning(f"[{self.account_index}] Not enough balance to cover fees in {network}")
                    return None
                
                logger.info(f"[{self.account_index}] Bridging {web3.from_wei(max_amount, 'ether')} ETH from {network} (max possible amount)")
                
                # Update the amount_in to be the maximum possible
                amount_in = int(max_amount)
                amount_out_min = await self.calculate_amount_out_min(network, amount_in)
                # Now build the actual transaction with the correct amount
                transaction = contract.functions.swapAndBridge(
                    amount_in,  # amountIn
                    amount_out_min,  # amountOutMin
                    sepolia_chain_id,  # dstChainId
                    self.account.address,  # to
                    self.account.address,  # refundAddress
                    web3.to_checksum_address("0x0000000000000000000000000000000000000000"),  # zroPaymentAddress
                    b""  # adapterParams
                )
                
                # Build the transaction without gas limit first
                gas_params = await self.get_gas_params(web3)
                
                built_transaction = await transaction.build_transaction({
                    "from": self.account.address,
                    "value": amount_in + bridge_fee,  # The amount plus a fee for bridging
                    "nonce": nonce,
                    "gas": gas_limit,
                    "chainId": await web3.eth.chain_id,
                    "type": "0x2",  # EIP-1559 transaction
                    **gas_params
                })
                
                return built_transaction

        except Exception as e:
            logger.error(f"[{self.account_index}] Error building bridge transaction: {str(e)}")
            raise e

    async def bridge(self) -> bool:
        """Execute the bridge transaction."""
        try:
            network_info = await self.get_suitable_network()
            if not network_info:
                logger.info(f"[{self.account_index}] No need to bridge, Sepolia balance is sufficient")
                return True  # This is a success case, not an error
                
            network, amount = network_info
            web3 = self.web3_connections[network]
            
            # Get initial Sepolia balance if we're going to wait for it to increase
            initial_balance = 0
            if self.config.TESTNET_BRIDGE.WAIT_FOR_FUNDS_TO_ARRIVE:
                initial_balance = await self.get_sepolia_balance()
                logger.info(f"[{self.account_index}] Initial Sepolia balance: {initial_balance}")
            
            # Build the transaction
            built_transaction = await self.build_bridge_transaction(network, amount)
            
            # Sign and send the transaction
            signed_tx = web3.eth.account.sign_transaction(built_transaction, self.private_key)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"[{self.account_index}] Waiting for bridge transaction confirmation...")
            receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
            
            explorer_url = f"{TESTNET_BRIDGE_EXPLORERS[network]}{tx_hash.hex()}"
            
            if receipt['status'] == 1:
                logger.success(f"[{self.account_index}] Bridge transaction successful! Explorer URL: {explorer_url}")
                
                # Wait for balance to increase if configured to do so
                if self.config.TESTNET_BRIDGE.WAIT_FOR_FUNDS_TO_ARRIVE:
                    logger.success(f"[{self.account_index}] Waiting for balance increase on Sepolia...")
                    await self.wait_for_balance_increase(initial_balance)
                    logger.success(f"[{self.account_index}] Successfully bridged from {network} to Sepolia")
                    return True
                else:
                    logger.success(f"[{self.account_index}] Successfully bridged from {network} (not waiting for balance)")
                    return True
            else:
                logger.error(f"[{self.account_index}] Bridge transaction failed! Explorer URL: {explorer_url}")
                raise ValueError(f"Bridge transaction failed! Status: {receipt['status']}")
                
        except Exception as e:
            logger.error(f"[{self.account_index}] Bridge failed: {str(e)}")
            raise e
            
    async def execute(self) -> bool:
        """Main execution method with retry mechanism."""
        # Get retry settings from config
        attempts = getattr(self.config.SETTINGS, 'ATTEMPTS', 5)  # Default to 5 if not set
        pause_range = getattr(self.config.SETTINGS, 'PAUSE_BETWEEN_ATTEMPTS', [5, 15])  # Default to [5, 15] if not set
        last_exception = None
        
        logger.info(f"[{self.account_index}] Starting TestnetBridge operation with up to {attempts} attempts")
        
        for attempt in range(attempts):
            try:
                logger.info(f"[{self.account_index}] TestnetBridge attempt {attempt + 1}/{attempts}")
                result = await self.bridge()
                return result
            except Exception as e:
                last_exception = e
                logger.warning(f"[{self.account_index}] Attempt {attempt + 1}/{attempts} failed: {str(e)}")
                
                if attempt < attempts - 1:  # Don't sleep on the last attempt
                    pause_time = random.uniform(pause_range[0], pause_range[1])
                    logger.info(f"[{self.account_index}] Waiting {pause_time:.2f} seconds before next attempt...")
                    await asyncio.sleep(pause_time)
        
        logger.error(f"[{self.account_index}] All {attempts} attempts failed for TestnetBridge")
        if last_exception:
            logger.error(f"[{self.account_index}] Last error: {str(last_exception)}")
        return False

