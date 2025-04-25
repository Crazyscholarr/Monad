import asyncio
import random
import json
from eth_account import Account
from loguru import logger
from primp import AsyncClient
from web3 import AsyncWeb3, Web3
from typing import Dict, Optional
from eth_account.messages import encode_defunct
import functools

from src.utils.config import Config
from src.utils.constants import RPC_URL, EXPLORER_URL


# Global database lock for thread safety
_db_lock = asyncio.Lock()

def with_retries(func):
    """Decorator to add retry functionality to async methods."""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        attempts = getattr(self.config.SETTINGS, 'ATTEMPTS', 5)  # Default to 5 if not set
        pause_range = getattr(self.config.SETTINGS, 'PAUSE_BETWEEN_ATTEMPTS', [5, 15])  # Default to [5, 15] if not set
        last_exception = None
        
        for attempt in range(attempts):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"[{self.account_index}] Attempt {attempt + 1}/{attempts} failed for {func.__name__}: {str(e)}")
                if attempt < attempts - 1:  # Don't sleep on the last attempt
                    pause_time = random.uniform(pause_range[0], pause_range[1])
                    logger.info(f"[{self.account_index}] Waiting {pause_time:.2f} seconds before next attempt...")
                    await asyncio.sleep(pause_time)
                
        logger.error(f"[{self.account_index}] All {attempts} attempts failed for {func.__name__}")
        raise last_exception

    return wrapper

async def read_database() -> Dict:
    """Thread-safe function to read the database file."""
    try:
        async with _db_lock:
            try:
                with open("src/model/aircraft/database.json", "r") as f:
                    return json.load(f)
            except FileNotFoundError:
                # Create new database file if it doesn't exist
                with open("src/model/aircraft/database.json", "w") as f:
                    json.dump({}, f)
                return {}
            except json.JSONDecodeError:
                # Reset database if JSON is invalid
                with open("src/model/aircraft/database.json", "w") as f:
                    json.dump({}, f)
                return {}
    except Exception as e:
        logger.error(f"Error reading database: {e}")
        return {}

async def write_database(data: Dict) -> None:
    """Thread-safe function to write to the database file."""
    async with _db_lock:
        try:
            with open("src/model/aircraft/database.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error writing to database: {e}")
            raise

class Aircraft:
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
        self.auth_token = None

        self.account: Account = Account.from_key(private_key=private_key)
        self.web3 = AsyncWeb3(
             AsyncWeb3.AsyncHTTPProvider(
                 RPC_URL,
                 request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
             )
        ) 
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authorization if token is available."""
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers

    @with_retries
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

    @with_retries
    async def estimate_gas(self, transaction: dict) -> int:
        """Estimate gas for transaction and add some buffer."""
        try:
            estimated = await self.web3.eth.estimate_gas(transaction)
            # Add 10% to estimated gas for safety
            return int(estimated * 1.1)
        except Exception as e:
            logger.warning(
                f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit"
            )
            raise e

    @with_retries
    async def login(self, referral_code: Optional[str] = None) -> Dict:
        """Login to the service and sign the message with wallet."""
        try:
            logger.info(f"[{self.account_index}] Starting login process")
            
            # Prepare request parameters
            params = {
                'address': self.account.address,
                'type': 'ETHEREUM_BASED'
            }
            
            # Add referral code if provided
            if referral_code:
                params['referralCode'] = referral_code
                
            # logger.debug(f"[{self.account_index}] Login request params: {params}")
                
            # Get the sign-in message
            logger.info(f"[{self.account_index}] Requesting sign-in message")
            response = await self.session.get(
                'https://api.aicraft.fun/auths/wallets/sign-in/message', 
                params=params
            )
            
            response_data = response.json()
            # logger.debug(f"[{self.account_index}] Sign-in message response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get('statusCode') != 200:
                raise Exception(f"Failed to get sign-in message: {response_data}")
                
            # Extract the encrypted message that needs to be signed
            encrypted_message = response_data['data']['message']
            logger.info(f"[{self.account_index}] Successfully received message to sign")
            # logger.debug(f"[{self.account_index}] Message to sign: {encrypted_message}")
            
            # Sign the message with the wallet
            message_hash = encode_defunct(text=encrypted_message)
            signature = self.account.sign_message(message_hash)
            signature_hex = "0x" + signature.signature.hex()
            # logger.debug(f"[{self.account_index}] Generated signature: {signature_hex}")
            
            # Prepare the sign-in payload
            sign_in_payload = {
                'address': self.account.address,
                'type': 'ETHEREUM_BASED',
                'signature': signature_hex,
                'message': encrypted_message
            }
            
            # Add referral code if provided
            if referral_code:
                sign_in_payload['referralCode'] = referral_code
                
            # logger.debug(f"[{self.account_index}] Sign-in payload: {json.dumps(sign_in_payload, indent=2)}")
                
            # Send the signed message for verification
            logger.info(f"[{self.account_index}] Sending sign-in request")
            sign_in_response = await self.session.post(
                'https://api.aicraft.fun/auths/wallets/sign-in',
                json=sign_in_payload
            )
            
            sign_in_data = sign_in_response.json()
            # logger.debug(f"[{self.account_index}] Sign-in response: {json.dumps(sign_in_data, indent=2)}")
            
            if sign_in_data.get('statusCode') not in [200, 201]:
                raise Exception(f"Failed to sign in: {sign_in_data}")
            
            # Store the auth token
            self.auth_token = sign_in_data['data']['token']
            logger.success(f"[{self.account_index}] Login successful")
            return sign_in_data
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error in login: {e}")
            raise e

    async def check_database(self, address: str) -> Optional[Dict]:
        """Thread-safe check if address has user info in database."""
        try:
            data = await read_database()
            # logger.debug(f"[{self.account_index}] Database content: {json.dumps(data, indent=2)}")
            return data.get(address)
        except Exception as e:
            logger.error(f"[{self.account_index}] Error checking database: {e}")
            return None

    async def save_to_database(self, address: str, user_info: Dict) -> None:
        """Thread-safe save user info to database."""
        try:
            # Read current database
            data = await read_database()
            
            # Update data with user info
            data[address] = user_info
            
            # Save back to file
            await write_database(data)
            logger.info(f"[{self.account_index}] Saved user info to database")
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error saving to database: {e}")
            raise

    @with_retries
    async def get_random_wallet_ref_code(self) -> Dict:
        """Get user info from a randomly generated wallet."""
        try:
            # Generate random wallet
            random_account = Account.create()
            logger.info(f"[{self.account_index}] Generated random wallet for ref code")
            
            # Login with random wallet to get its ref code
            params = {
                'address': random_account.address,
                'type': 'ETHEREUM_BASED'
            }
            
            # Get sign-in message
            response = await self.session.get(
                'https://api.aicraft.fun/auths/wallets/sign-in/message',
                params=params
            )
            
            response_data = response.json()
            if response_data.get('statusCode') != 200:
                raise Exception(f"Failed to get sign-in message for random wallet: {response_data}")
            
            # Sign the message with random wallet
            message = response_data['data']['message']
            message_hash = encode_defunct(text=message)
            signature = random_account.sign_message(message_hash)
            signature_hex = "0x" + signature.signature.hex()
            
            # Login with random wallet
            sign_in_payload = {
                'address': random_account.address,
                'type': 'ETHEREUM_BASED',
                'signature': signature_hex,
                'message': message
            }
            
            sign_in_response = await self.session.post(
                'https://api.aicraft.fun/auths/wallets/sign-in',
                json=sign_in_payload
            )
            
            sign_in_data = sign_in_response.json()
            if sign_in_data.get('statusCode') not in [200, 201]:
                raise Exception(f"Failed to sign in with random wallet: {sign_in_data}")
            
            # Get user info to extract ref code and wallet id
            temp_token = sign_in_data['data']['token']
            temp_headers = {'Authorization': f'Bearer {temp_token}'}
            
            user_response = await self.session.get(
                'https://api.aicraft.fun/users/me',
                params={'includeTodayFeedCount': 'true'},
                headers=temp_headers
            )
            
            user_data = user_response.json()
            if user_data.get('statusCode') != 200:
                raise Exception(f"Failed to get random wallet info: {user_data}")
            
            user_info = {
                'refCode': user_data['data']['refCode'],
                'walletId': user_data['data']['wallets'][0]['_id']
            }
            # logger.info(f"[{self.account_index}] Got user info from random wallet: {json.dumps(user_info, indent=2)}")
            return user_info
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error getting user info from random wallet: {e}")
            raise e

    @with_retries
    async def vote(self):
        """Cast a vote on the platform."""
        try:
            logger.info(f"[{self.account_index}] Casting vote")
            
            # Get available voting options
            options_response = await self.session.get(
                'https://api.aicraft.fun/voting/options',
                headers=self.get_auth_headers()
            )
            options_data = options_response.json()
            # logger.debug(f"[{self.account_index}] Voting options response: {json.dumps(options_data, indent=2)}")
            
            if options_data.get('statusCode') != 200:
                raise Exception(f"Failed to get voting options: {options_data}")
                
            voting_options = options_data['data']
            if not voting_options:
                logger.warning(f"[{self.account_index}] No voting options available")
                return
                
            # Select a random option
            selected_option = random.choice(voting_options)
            option_id = selected_option['id']
            # logger.debug(f"[{self.account_index}] Selected voting option: {json.dumps(selected_option, indent=2)}")
            
            # Cast vote
            vote_payload = {
                'optionId': option_id
            }
            # logger.debug(f"[{self.account_index}] Vote payload: {json.dumps(vote_payload, indent=2)}")
            
            vote_response = await self.session.post(
                'https://api.aicraft.fun/voting/cast',
                json=vote_payload,
                headers=self.get_auth_headers()
            )
            
            vote_data = vote_response.json()
            # logger.debug(f"[{self.account_index}] Vote response: {json.dumps(vote_data, indent=2)}")
            
            if vote_data.get('statusCode') != 200:
                raise Exception(f"Failed to cast vote: {vote_data}")
                
            logger.success(f"[{self.account_index}] Successfully cast vote for option {option_id}")
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error in vote: {e}")
            raise e

    @with_retries
    async def get_candidates(self) -> Dict:
        """Get available candidates from the platform."""
        try:
            logger.info(f"[{self.account_index}] Getting candidates")
            
            params = {
                'projectID': '678376133438e102d6ff5c6e',
            }
            
            response = await self.session.get(
                'https://api.aicraft.fun/candidates',
                params=params,
                headers=self.get_auth_headers()
            )
            
            response_data = response.json()
            # logger.debug(f"[{self.account_index}] Candidates response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get('statusCode') != 200:
                raise Exception(f"Failed to get candidates: {response_data}")
            
            candidates = response_data['data']
            if not candidates:
                logger.warning(f"[{self.account_index}] No candidates available")
                return None
            
            # Select a random candidate
            selected_candidate = random.choice(candidates)
            logger.info(f"[{self.account_index}] Selected candidate: {selected_candidate['name']}")
            
            return selected_candidate
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error getting candidates: {e}")
            raise e

    @with_retries
    async def create_feed_order_request(self, candidate_id: str, user_info: Dict) -> Dict:
        """Create initial feed order request."""
        json_data = {
            'candidateID': candidate_id,
            'walletID': user_info['walletId'],
            'feedAmount': 1,
            'chainID': '10143',
            'refCode': user_info['inviteRefCode'],
        }
        
        # logger.debug(f"[{self.account_index}] Feed order payload: {json.dumps(json_data, indent=2)}")
        
        response = await self.session.post(
            'https://api.aicraft.fun/feeds/orders',
            headers=self.get_auth_headers(),
            json=json_data
        )
        
        response_data = response.json()
        if response_data.get('statusCode') != 201:
            raise Exception(f"Failed to create feed order: {response_data}")
            
        return response_data['data']

    async def prepare_and_sign_transaction(self, payment_data: Dict) -> tuple:
        """Prepare and sign the transaction."""
        # Sign the user hashed message
        message_hash = payment_data['params']['userHashedMessage']
        message = encode_defunct(hexstr=message_hash)
        signature = self.account.sign_message(message)
        user_signature = signature.signature.hex()
        
        # logger.debug(f"[{self.account_index}] Signed user message: 0x{user_signature}")
        
        # Prepare transaction data
        contract_address = Web3.to_checksum_address(payment_data['contractAddress'])
        contract = self.web3.eth.contract(
            address=contract_address,
            abi=payment_data['abi']
        )
        
        # Get function parameters
        params = payment_data['params']
        
        # Prepare transaction
        transaction = contract.functions.feed(
            params['candidateID'],
            params['feedAmount'],
            params['requestID'],
            params['requestData'],
            bytes.fromhex(user_signature),
            bytes.fromhex(params['integritySignature'][2:])
        )
        
        # Get nonce and gas parameters
        nonce = await self.web3.eth.get_transaction_count(self.account.address)
        gas_params = await self.get_gas_params()
        
        # Build transaction
        tx = await transaction.build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            **gas_params
        })
        
        # Estimate gas
        try:
            gas_limit = await self.estimate_gas(tx)
            tx['gas'] = gas_limit
        except Exception as e:
            logger.error(f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit")
            raise
        
        # Sign transaction
        signed_tx = self.account.sign_transaction(tx)
        return signed_tx, user_signature

    @with_retries
    async def create_feed_order(self, candidate_id: str) -> Dict:
        """Create a feed order for a candidate."""
        try:
            logger.info(f"[{self.account_index}] Creating feed order for candidate {candidate_id}")
            
            # Get user info from database
            user_info = await self.check_database(self.account.address)
            if not user_info:
                raise Exception("No user info found in database")
            
            # Create initial feed order
            order_data = await self.create_feed_order_request(candidate_id, user_info)
            
            # Prepare and sign transaction
            signed_tx, _ = await self.prepare_and_sign_transaction(order_data['payment'])
            
            # Send transaction and wait for confirmation
            tx_hash, _ = await self.send_and_wait_transaction(signed_tx)
            
            # Add delay after transaction confirmation
            await asyncio.sleep(5)
            
            # Confirm the feed order
            await self.confirm_feed_order(
                order_data['order']['_id'],
                tx_hash.hex(),
                user_info['inviteRefCode']
            )
            
            return order_data
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error creating feed order: {e}")
            raise e

    @with_retries
    async def get_user_info(self) -> Dict:
        """Get current user info from the API."""
        user_response = await self.session.get(
            'https://api.aicraft.fun/users/me',
            params={'includeTodayFeedCount': 'true'},
            headers=self.get_auth_headers()
        )
        
        user_data = user_response.json()
        if user_data.get('statusCode') != 200:
            raise Exception(f"Failed to get user info: {user_data}")
            
        return user_data['data']

    @with_retries
    async def connect_referral(self, ref_code: str) -> Dict:
        """Connect wallet to a referral code."""
        connect_ref_payload = {
            'refCode': ref_code
        }
        
        logger.info(f"[{self.account_index}] Connecting wallet to referral code: {ref_code}")
        connect_response = await self.session.post(
            'https://api.aicraft.fun/users/referral',
            headers=self.get_auth_headers(),
            json=connect_ref_payload
        )
        
        connect_data = connect_response.json()
        if connect_data.get('statusCode') not in [200, 201]:
            raise Exception(f"Failed to connect to referral: {connect_data}")
            
        return connect_data

    @with_retries
    async def send_and_wait_transaction(self, signed_tx) -> tuple:
        """Send transaction and wait for receipt."""
        tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.info(f"[{self.account_index}] Waiting for transaction confirmation...")
        
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            logger.success(f"[{self.account_index}] Transaction successful! Explorer URL: {EXPLORER_URL}{tx_hash.hex()}")
        else:
            logger.error(f"[{self.account_index}] Transaction failed! Explorer URL: {EXPLORER_URL}{tx_hash.hex()}")
            raise Exception("Transaction failed")
            
        return tx_hash, receipt

    @with_retries
    async def confirm_feed_order(self, order_id: str, tx_hash: str, ref_code: str) -> Dict:
        """Confirm the feed order after transaction."""
        confirm_json_data = {
            'transactionHash': f"0x{tx_hash}",
            'refCode': ref_code,
        }
        
        # logger.debug(f"[{self.account_index}] Feed order confirmation payload: {json.dumps(confirm_json_data, indent=2)}")
        
        confirm_response = await self.session.post(
            f'https://api.aicraft.fun/feeds/orders/{order_id}/confirm',
            headers=self.get_auth_headers(),
            json=confirm_json_data
        )
        
        confirm_data = confirm_response.json()
        if confirm_data.get('statusCode') not in [200, 201]:
            raise Exception(f"Failed to confirm feed order: {confirm_data}")
            
        return confirm_data

    async def process_new_wallet(self) -> bool:
        """Process a new wallet without existing user info."""
        try:
            # First try to login with the wallet
            login_data = await self.login()
            if login_data.get('statusCode') not in [200, 201]:
                raise Exception("Failed to login with main wallet")

            # Get user info to check if already registered
            user_data = await self.get_user_info()
            
            # If user has invitedBy info, they're already registered
            if 'invitedBy' in user_data:
                logger.info(f"[{self.account_index}] Wallet already registered, using existing referral")
                
                # Save user info to database with existing referral
                current_user_info = {
                    'refCode': user_data['refCode'],
                    'walletId': user_data['wallets'][0]['_id'],
                    'inviteRefCode': user_data['invitedBy']['refCode']
                }
                await self.save_to_database(self.account.address, current_user_info)
                
                # Check if todayFeedCount is 0
                if user_data.get('todayFeedCount', 1) == 0:
                    logger.warning(f"[{self.account_index}] No more votes available today for this wallet, skipping")
                    return False
                    
                return await self.process_feed_order()
            
            # If not already registered, proceed with new wallet registration
            logger.info(f"[{self.account_index}] Wallet not registered, proceeding with new registration")
            
            # Get user info from random wallet
            random_user_info = await self.get_random_wallet_ref_code()
            
            # Connect to referral
            await self.connect_referral(random_user_info['refCode'])
            logger.success(f"[{self.account_index}] Successfully connected to referral")
            
            # Get updated user info after referral connection
            user_data = await self.get_user_info()
            
            # Check if todayFeedCount is 0
            if user_data.get('todayFeedCount', 1) == 0:
                logger.warning(f"[{self.account_index}] No more votes available today for this wallet, skipping")
                return False
            
            # Save user info to database
            current_user_info = {
                'refCode': user_data['refCode'],
                'walletId': user_data['wallets'][0]['_id'],
                'inviteRefCode': random_user_info['refCode']
            }
            await self.save_to_database(self.account.address, current_user_info)
            
            return await self.process_feed_order()
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error in process_new_wallet: {e}")
            raise e

    async def process_existing_wallet(self, user_info: Dict) -> bool:
        """Process an existing wallet with user info."""
        # Login with existing wallet
        login_data = await self.login()
        if login_data.get('statusCode') not in [200, 201]:
            raise Exception("Failed to login with main wallet")
        
        # Check user info and feed count
        user_data = await self.get_user_info()
        
        if user_data.get('todayFeedCount', 1) == 0:
            logger.warning(f"[{self.account_index}] No more votes available today for this wallet, skipping")
            return False
            
        return await self.process_feed_order()

    async def process_feed_order(self) -> bool:
        """Process getting candidate and creating feed order."""
        try:
            candidate = await self.get_candidates()
            if not candidate:
                return False
                
            order_data = await self.create_feed_order(candidate['_id'])
            if order_data:
                logger.info(f"[{self.account_index}] Feed order created successfully")
                return True
                
            return False
        except Exception as e:
            logger.error(f"[{self.account_index}] Error in process_feed_order: {e}")
            return False

    async def execute(self):
        """Main execution function."""
        try:
            logger.info(f"[{self.account_index}] Starting Aircraft execution")
            
            # Check if we already have user info
            user_info = await self.check_database(self.account.address)
            
            if not user_info:
                logger.info(f"[{self.account_index}] No user info found, generating random wallet")
                success = await self.process_new_wallet()
            else:
                # logger.info(f"[{self.account_index}] Found existing user info: {json.dumps(user_info, indent=2)}")
                success = await self.process_existing_wallet(user_info)
            
            if success:
                logger.success(f"[{self.account_index}] Aircraft execution completed successfully")
            
            return success

        except Exception as e:
            logger.error(f"[{self.account_index}] Error in execute: {e}")
            return False
    

