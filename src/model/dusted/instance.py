import asyncio
import base64
import hashlib
import os
import random
import secrets
from eth_account import Account
from loguru import logger
from primp import AsyncClient
from web3 import AsyncWeb3, Web3
from typing import Dict, Optional, List
from eth_account.messages import encode_defunct
import functools
import time

from src.model.dusted.browser_login import dusted_browser_login
from src.utils.config import Config
from src.utils.constants import RPC_URL, EXPLORER_URL


def with_retries(func):
    """Decorator to add retry functionality to async methods."""

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        attempts = getattr(
            self.config.SETTINGS, "ATTEMPTS", 5
        )  # Default to 5 if not set
        pause_range = getattr(
            self.config.SETTINGS, "PAUSE_BETWEEN_ATTEMPTS", [5, 15]
        )  # Default to [5, 15] if not set

        last_exception = None

        for attempt in range(1, attempts + 1):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < attempts:
                    pause_time = random.uniform(pause_range[0], pause_range[1])
                    logger.warning(
                        f"[{self.account_index}] Attempt {attempt}/{attempts} failed for {func.__name__}: {e}. Retrying in {pause_time:.2f}s"
                    )
                    await asyncio.sleep(pause_time)
                else:
                    logger.error(
                        f"[{self.account_index}] All {attempts} attempts for {func.__name__} failed: {e}"
                    )

        raise last_exception

    return wrapper


class Dusted:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        private_key: str,
        twitter_token: str,
        config: Config,
        session: AsyncClient,
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = private_key
        self.config = config
        self.twitter_token = twitter_token
        self.session = session
        self.auth_token = None
        self.wallet_id = None
        self.user_id = None
        self.twitter_connected = False
        self.account: Account = Account.from_key(private_key=private_key)
        self.web3 = AsyncWeb3(
             AsyncWeb3.AsyncHTTPProvider(
                 RPC_URL,
                 request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
             )
        ) 
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authorization if token is available."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    @classmethod
    def _b64safe(cls, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")

    @classmethod
    def _random_string(cls) -> str:
        random_bytes = os.urandom(36)
        return cls._b64safe(random_bytes)

    @classmethod
    def _sha256(cls, value: str) -> str:
        h = hashlib.sha256(value.encode("utf-8")).digest()
        return cls._b64safe(h)

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
            return int(estimated * 1.2)
        except Exception as e:
            logger.warning(
                f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit"
            )
            raise e

    @with_retries
    async def login(self) -> Dict:
        """Login to Dusted service using the signature method."""
        try:
            logger.info(f"[{self.account_index}] Starting Dusted login process")

            # Generate current timestamp in ISO format
            current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            # logger.debug(f"[{self.account_index}] Generated timestamp: {current_time}")

            # Generate a random nonce
            nonce = f"{random.randint(100000, 999999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(100000000000, 999999999999)}"
            # logger.debug(f"[{self.account_index}] Generated nonce: {nonce}")

            # Create the message to sign
            message = f"www.dusted.app wants you to sign in with your Ethereum account:\n{self.account.address}\n\nI am proving ownership of the Ethereum account {self.account.address}.\n\nURI: https://www.dusted.app\nVersion: 1\nChain ID: 1\nNonce: {nonce}\nIssued At: {current_time}"
            # logger.debug(f"[{self.account_index}] Message to sign: {message}")

            # Sign the message
            message_hash = encode_defunct(text=message)
            signature = self.account.sign_message(message_hash)
            signature_hex = signature.signature.hex()
            # logger.debug(f"[{self.account_index}] Generated signature: 0x{signature_hex}")

            # Prepare the login payload
            json_data = {
                "message": message,
                "signature": f"0x{signature_hex}",
                "provider": "metamask",
                "chainId": "0x279f",  # Chain ID in hex (10143 in decimal)
            }
            # logger.debug(f"[{self.account_index}] Login payload: {json.dumps(json_data, indent=2)}")

            logger.info(f"[{self.account_index}] Sending sign-in request to Dusted")
            sign_in_response = await self.session.post(
                f"https://api.xyz.land/signature/evm/{self.account.address}/sign",
                json=json_data,
            )

            sign_in_data = sign_in_response.json()
            # logger.debug(f"[{self.account_index}] Login response: {json.dumps(sign_in_data, indent=2)}")

            if "token" not in sign_in_data:
                raise Exception(f"Failed to sign in: {sign_in_data}")

            # Store the auth token
            self.auth_token = sign_in_data["token"]
            # logger.debug(f"[{self.account_index}] Auth token received: {self.auth_token[:10]}...")
            logger.success(f"[{self.account_index}] Dusted login successful")
            return sign_in_data

        except Exception as e:
            logger.error(f"[{self.account_index}] Error in Dusted login: {e}")
            raise e

    @with_retries
    async def get_balance(self) -> Dict:
        """Get user balance and extract user_id and wallet_id."""
        try:
            logger.info(f"[{self.account_index}] Fetching user balance")

            balance_response = await self.session.get(
                "https://api.xyz.land/balances", headers=self.get_auth_headers()
            )

            balance_data = balance_response.json()
            # logger.debug(f"[{self.account_index}] Balance response: {json.dumps(balance_data, indent=2)}")

            if "user_id" not in balance_data or "wallet_address" not in balance_data:
                raise Exception(f"Invalid balance response: {balance_data}")

            # Store user_id for later use
            self.user_id = balance_data["user_id"]

            # Try to find wallet_id in tokens array if it exists
            self.wallet_id = self.user_id  # Default to user_id as fallback

            logger.info(f"[{self.account_index}] User ID: {self.user_id}")
            logger.info(
                f"[{self.account_index}] Wallet address: {balance_data['wallet_address']}"
            )

            return balance_data

        except Exception as e:
            logger.error(f"[{self.account_index}] Error fetching balance: {e}")
            raise e

    @with_retries
    async def join_room(self) -> Dict:
        """Join the Monad native token room."""
        try:
            logger.info(f"[{self.account_index}] Joining Monad native token room")

            json_data = {
                "wallet_id": self.user_id,  # Use user_id as wallet_id
            }

            room_response = await self.session.post(
                "https://api.xyz.land/rooms/monad-testnet/native/subscribe",
                headers=self.get_auth_headers(),
                json=json_data,
            )

            room_data = room_response.json()
            # logger.debug(f"[{self.account_index}] Room join response: {json.dumps(room_data, indent=2)}")

            if (
                "message" not in room_data
                or room_data.get("message") != "Successfully joined room"
            ):
                logger.warning(
                    f"[{self.account_index}] Room join may have failed: {room_data}"
                )
            else:
                logger.success(
                    f"[{self.account_index}] Successfully joined Monad native token room"
                )

                # Update wallet_id if it's available in the response
                if (
                    "user" in room_data
                    and "wallet" in room_data["user"]
                    and "wallet_id" in room_data["user"]["wallet"]
                ):
                    self.wallet_id = room_data["user"]["wallet"]["wallet_id"]
                    logger.info(f"[{self.account_index}] Wallet ID: {self.wallet_id}")

            return room_data

        except Exception as e:
            logger.error(f"[{self.account_index}] Error joining room: {e}")
            raise e

    @with_retries
    async def agree_to_tos(self) -> Dict:
        """Agree to the terms of service."""
        try:
            logger.info(f"[{self.account_index}] Agreeing to terms of service")

            json_data = {
                "agreed_tos": True,
            }

            tos_response = await self.session.patch(
                "https://api.xyz.land/users/@me",
                headers=self.get_auth_headers(),
                json=json_data,
            )

            tos_data = tos_response.json()
            # logger.debug(f"[{self.account_index}] TOS agreement response: {json.dumps(tos_data, indent=2)}")

            if (
                "message" not in tos_data
                or tos_data.get("message") != "updated successfully"
            ):
                logger.warning(
                    f"[{self.account_index}] TOS agreement may have failed: {tos_data}"
                )
            else:
                logger.success(
                    f"[{self.account_index}] Successfully agreed to terms of service"
                )

            return tos_data

        except Exception as e:
            logger.error(f"[{self.account_index}] Error agreeing to TOS: {e}")
            raise e

    @with_retries
    async def _get_twitter_connect_link(self) -> str:
        try:
            logger.info(f"[{self.account_index}] Getting Twitter connect link")
            params = {
                "return_url": "https://www.dusted.app/rewards",
                "jwt": self.auth_token,
            }
            response = await self.session.get(
                "https://api.xyz.land/auth/twitter",
                params=params,
            )
            if response.status_code == 200:
                return response.url
            else:
                raise Exception(f"[{self.account_index}] {response.status_code}")

        except Exception as e:
            logger.error(
                f"[{self.account_index}] Error getting Twitter connect link: {e}"
            )
            raise e

    @with_retries
    async def authorize_twitter(
        self,
        state: str,
        code_challenge: str,
        client_id: str,
        code_challenge_method: str,
        headers: dict,
    ) -> str:
        try:
            url = "https://x.com/i/api/2/oauth2/authorize"
            params = {
                "client_id": client_id,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "state": state,
                "scope": "users.read tweet.read offline.access",
                "response_type": "code",
                "redirect_uri": "https://api.xyz.land/auth/twitter/callback",
            }
            response = await self.session.get(
                url,
                params=params,
                headers=headers,
            )
            
            auth_code = response.json()['auth_code']
            
            data = {
                'approval': 'true',
                'code': auth_code,
            }

            response = await self.session.post('https://x.com/i/api/2/oauth2/authorize', headers=headers, data=data)

            redirect_url = response.json()['redirect_uri']

            headers = {
                'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'sec-fetch-site': 'cross-site',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-user': '?1',
                'sec-fetch-dest': 'document',
                'referer': 'https://x.com/',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5',
                'priority': 'u=0, i',
            }

            response = await self.session.get(redirect_url, params=params, headers=headers)

            headers = {
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'sec-fetch-site': 'cross-site',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-user': '?1',
                'sec-fetch-dest': 'document',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'referer': 'https://x.com/',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5',
                'priority': 'u=0, i',
            }

            params = {
                'x_link_success': 'true',
            }

            response = await self.session.get('https://www.dusted.app/rewards', params=params, headers=headers)

            if response.status_code == 200:
                logger.success(f"[{self.account_index}] Twitter connected successfully")
                return True
            else:
                raise Exception(f"[{self.account_index}] finish code {response.status_code}")
            
        except Exception as e:
            logger.error(f"[{self.account_index}] Error authorizing Twitter: {e}")
            raise e

    @with_retries
    async def connect_twitter(self) -> str:
        """Connect Twitter account."""
        try:
            logger.info(f"[{self.account_index}] Connecting Twitter account")

            generated_csrf_token = secrets.token_hex(16)

            cookies = {"ct0": generated_csrf_token, "auth_token": self.twitter_token}
            cookies_headers = "; ".join(f"{k}={v}" for k, v in cookies.items())

            headers = {
                "cookie": cookies_headers,
                "x-csrf-token": generated_csrf_token,
                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "referer": "https://x.com/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "x-twitter-auth-type": (
                    "OAuth2Session" if cookies.get("auth_token") else ""
                ),
            }

            connect_link = await self._get_twitter_connect_link()
            client_id = connect_link.split("client_id=")[1].split("&")[0]
            state = connect_link.split("state=")[1].split("&")[0]
            code_challenge = connect_link.split("code_challenge=")[1].split("&")[0]
            code_challenge_method = connect_link.split("code_challenge_method=")[
                1
            ].strip()

            logger.info(f"[{self.account_index}] Authorizing Twitter. State: {state}")

            return await self.authorize_twitter(
                state, code_challenge, client_id, code_challenge_method, headers
            )

        except Exception as e:
            logger.error(f"[{self.account_index}] Error connecting Twitter: {e}")
            raise e

    @with_retries
    async def claim(self) -> int:
        """Play the lasso game until no plays remain. Returns the total score."""
        try:
            logger.info(f"[{self.account_index}] Starting lasso game")

            params = {
                "network": "monad",
                "chain_id": "10143",
            }

            total_plays = 0
            total_score = 0

            # Try to play until no more plays remain
            try:
                while True:
                    logger.info(f"[{self.account_index}] Sending lasso play request")

                    response = await self.session.post(
                        "https://api.xyz.land/lasso/play",
                        params=params,
                        headers=self.get_auth_headers(),
                    )

                    play_data = response.json()
                    # logger.debug(f"[{self.account_index}] Lasso play response: {json.dumps(play_data, indent=2)}")

                    # Check for error response indicating no more plays
                    if "error" in play_data:
                        error_msg = play_data.get("error")
                        logger.warning(
                            f"[{self.account_index}] Lasso play error: {error_msg}"
                        )
                        logger.info(
                            f"[{self.account_index}] Already played all games or other error. Will still try to claim rewards."
                        )
                        break

                    if "score" not in play_data or "remainingPlays" not in play_data:
                        logger.warning(
                            f"[{self.account_index}] Invalid lasso play response: {play_data}"
                        )
                        break

                    score = play_data["score"]
                    remaining_plays = play_data["remainingPlays"]

                    total_plays += 1
                    total_score += score

                    logger.success(
                        f"[{self.account_index}] Lasso play #{total_plays} - Score: {score}, Remaining plays: {remaining_plays}"
                    )

                    if remaining_plays <= 0:
                        logger.info(
                            f"[{self.account_index}] No more plays remaining. Total plays: {total_plays}, Total score: {total_score}"
                        )
                        break

                    # Add a small delay between requests
                    await asyncio.sleep(random.uniform(1, 3))
            except Exception as e:
                logger.warning(
                    f"[{self.account_index}] Error during lasso gameplay: {e}. Will still try to claim rewards."
                )

            if total_plays > 0:
                logger.success(
                    f"[{self.account_index}] Completed all lasso plays with total score: {total_score}"
                )
            else:
                logger.info(f"[{self.account_index}] No lasso plays were completed.")

            return total_score

        except Exception as e:
            logger.error(f"[{self.account_index}] Error in claim method: {e}")
            # Don't raise the exception, return 0 score but still allow claiming
            return 0

    @with_retries
    async def get_lasso_score(self) -> Dict:
        """Get the current lasso score, remaining plays and rank information."""
        try:
            logger.info(f"[{self.account_index}] Fetching lasso score information")

            score_response = await self.session.get(
                "https://api.xyz.land/lasso/score", headers=self.get_auth_headers()
            )

            score_data = score_response.json()
            # logger.debug(f"[{self.account_index}] Lasso score response: {json.dumps(score_data, indent=2)}")

            if (
                "remainingPlays" in score_data
                and "score" in score_data
                and "rank" in score_data
            ):
                logger.info(
                    f"[{self.account_index}] Lasso stats - Score: {score_data['score']}, Rank: {score_data['rank']}, Remaining plays: {score_data['remainingPlays']}"
                )
            else:
                logger.warning(
                    f"[{self.account_index}] Invalid lasso score response format: {score_data}"
                )

            return score_data

        except Exception as e:
            logger.error(f"[{self.account_index}] Error fetching lasso score: {e}")
            raise e

    @with_retries
    async def get_lasso_leaderboard(self) -> Dict:
        """Get the top scores from the lasso game leaderboard."""
        try:
            logger.info(f"[{self.account_index}] Fetching lasso leaderboard")

            params = {
                "network": "monad",
                "chain_id": "10143",
            }

            leaderboard_response = await self.session.get(
                "https://api.xyz.land/lasso/scores",
                params=params,
                headers=self.get_auth_headers(),
            )

            leaderboard_data = leaderboard_response.json()
            # logger.debug(f"[{self.account_index}] Lasso leaderboard response: {json.dumps(leaderboard_data, indent=2)}")

            if "scores" in leaderboard_data and len(leaderboard_data["scores"]) > 0:
                top_score = leaderboard_data["scores"][0]
                logger.info(
                    f"[{self.account_index}] Lasso leaderboard - Top score: {top_score['score']} by {top_score['wallet_address']}"
                )
                logger.info(
                    f"[{self.account_index}] Leaderboard contains {len(leaderboard_data['scores'])} players"
                )
            else:
                logger.warning(
                    f"[{self.account_index}] Invalid leaderboard response format or empty leaderboard"
                )

            return leaderboard_data

        except Exception as e:
            logger.error(
                f"[{self.account_index}] Error fetching lasso leaderboard: {e}"
            )
            raise e

    @with_retries
    async def check_email_claim(self) -> Dict:
        """Check email claim status before claiming rewards."""
        try:
            logger.info(f"[{self.account_index}] Checking email claim status")

            email_claim_response = await self.session.get(
                "https://api.xyz.land/email/claim", headers=self.get_auth_headers()
            )

            email_claim_data = email_claim_response.json()
            # logger.debug(f"[{self.account_index}] Email claim response: {json.dumps(email_claim_data, indent=2)}")

            logger.info(f"[{self.account_index}] Email claim check completed")
            return email_claim_data

        except Exception as e:
            logger.error(f"[{self.account_index}] Error checking email claim: {e}")
            raise e

    @with_retries
    async def get_user(self) -> Dict:
        """Get user information before claiming rewards."""
        try:
            logger.info(f"[{self.account_index}] Fetching user information")

            user_response = await self.session.get(
                "https://api.xyz.land/users/@me", headers=self.get_auth_headers()
            )

            user_data = user_response.json()
            # logger.debug(f"[{self.account_index}] User information response: {json.dumps(user_data, indent=2)}")

            if "wallet" in user_data and "wallet_id" in user_data["wallet"]:
                logger.info(
                    f"[{self.account_index}] User wallet ID: {user_data['wallet']['wallet_id']}"
                )

                # Update wallet_id if it's available in the response
                self.wallet_id = user_data["wallet"]["wallet_id"]

            if "profile" in user_data and "user_id" in user_data["profile"]:
                logger.info(
                    f"[{self.account_index}] User ID: {user_data['profile']['user_id']}"
                )

                # Update user_id if it's available in the response
                self.user_id = user_data["profile"]["user_id"]
                
                # Check if Twitter is connected by looking for x_id
                if "x_id" in user_data["profile"] and user_data["profile"]["x_id"] is not None:
                    self.twitter_connected = True
                    logger.info(f"[{self.account_index}] Twitter already connected (ID: {user_data['profile']['x_id']})")
                else:
                    self.twitter_connected = False
                    logger.info(f"[{self.account_index}] Twitter not connected yet")

            logger.info(f"[{self.account_index}] User information check completed")
            return user_data

        except Exception as e:
            logger.error(f"[{self.account_index}] Error fetching user information: {e}")
            raise e

    @with_retries
    async def claim_rewards(self) -> bool:
        """Claim rewards after playing all games."""
        try:
            logger.info(f"[{self.account_index}] Requesting claim signature")

            # Get claim signature
            claim_response = await self.session.get(
                "https://api.xyz.land/lasso/claim", headers=self.get_auth_headers()
            )

            claim_data = claim_response.json()
            # logger.debug(f"[{self.account_index}] Claim response: {json.dumps(claim_data, indent=2)}")

            # Check for error in claim response
            if "error" in claim_data:
                error_msg = claim_data.get("error")
                logger.warning(f"[{self.account_index}] Claim error: {error_msg}")
                # If error indicates no rewards to claim, return gracefully
                if (
                    "already claimed" in error_msg.lower()
                    or "no rewards" in error_msg.lower()
                ):
                    logger.info(
                        f"[{self.account_index}] No rewards to claim or already claimed"
                    )
                    return False
                raise Exception(f"Claim error: {error_msg}")

            # Handle "Claim not available" message
            if (
                "message" in claim_data
                and claim_data.get("message") == "Claim not available"
            ):
                logger.warning(
                    f"[{self.account_index}] Claim not available yet, retrying..."
                )
                raise Exception("Claim not available yet, will retry")

            if "signature" not in claim_data or "score" not in claim_data:
                logger.warning(
                    f"[{self.account_index}] Invalid claim response: {claim_data}"
                )
                return False

            signature = claim_data["signature"]
            score = claim_data["score"]

            logger.info(f"[{self.account_index}] Received signature for score: {score}")

            # Create contract instance
            contract_address = Web3.to_checksum_address(
                "0x18C9534dfe16a0314B66395F48549716FfF9AA66"
            )

            # ABI for the claim function
            abi = [
                {
                    "inputs": [
                        {
                            "internalType": "uint256",
                            "name": "totalPoints",
                            "type": "uint256",
                        },
                        {"internalType": "bytes", "name": "signature", "type": "bytes"},
                    ],
                    "name": "claim",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                }
            ]

            contract = self.web3.eth.contract(address=contract_address, abi=abi)

            # Prepare transaction
            nonce = await self.web3.eth.get_transaction_count(self.account.address)
            gas_params = await self.get_gas_params()

            # Convert signature to bytes if it's a string
            if isinstance(signature, str) and signature.startswith("0x"):
                signature_bytes = bytes.fromhex(signature[2:])
            else:
                signature_bytes = bytes.fromhex(signature)

            # Build transaction
            tx = await contract.functions.claim(
                score, signature_bytes  # Using the score from the claim response
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": nonce,
                    "chainId": 10143,
                    **gas_params,
                }
            )

            # Estimate gas
            try:
                gas_limit = await self.estimate_gas(tx)
                tx["gas"] = gas_limit
            except Exception as e:
                raise e
            # Sign and send transaction
            signed_tx = self.account.sign_transaction(tx)
            tx_hash, receipt = await self.send_and_wait_transaction(signed_tx)

            logger.success(
                f"[{self.account_index}] Successfully claimed rewards for score: {score}"
            )
            return True

        except Exception as e:
            logger.error(f"[{self.account_index}] Error claiming rewards: {e}")
            raise e

    @with_retries
    async def send_and_wait_transaction(self, signed_tx) -> tuple:
        """Send transaction and wait for receipt."""
        tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.info(f"[{self.account_index}] Waiting for transaction confirmation...")

        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt["status"] == 1:
            logger.success(
                f"[{self.account_index}] Transaction successful! Explorer URL: {EXPLORER_URL}{tx_hash.hex()}"
            )
        else:
            logger.error(
                f"[{self.account_index}] Transaction failed! Explorer URL: {EXPLORER_URL}{tx_hash.hex()}"
            )
            raise Exception("Transaction failed")

        return tx_hash, receipt

    async def execute(self):
        """Main execution function for Dusted platform."""
        try:
            logger.info(f"[{self.account_index}] Starting Dusted execution")

            # Initialize user_id and wallet_id
            self.user_id = None
            self.wallet_id = None

            # result = await dusted_browser_login(self.config, self.private_key, self.proxy)
            # if not result:
            #     logger.error(f"[{self.account_index}] Failed to login to the platform")
            #     return False
            # Login to the platform
            await self.login()
            logger.info(f"[{self.account_index}] Login successful")

            # Get user balance to fetch user_id
            await self.get_balance()

            # Join Monad native token room
            await self.join_room()

            # Agree to terms of service
            await self.agree_to_tos()
            
            # Get user info and check Twitter connection status
            await self.get_user()
            
            # Connect Twitter only if not already connected and Twitter token is available
            if not self.config.DUSTED.SKIP_TWITTER_VERIFICATION:
                if not self.twitter_connected and self.twitter_token and self.twitter_token.strip():
                    logger.info(f"[{self.account_index}] Twitter not connected. Attempting to connect...")
                    await self.connect_twitter()
                elif not self.twitter_token or not self.twitter_token.strip():
                    logger.warning(f"[{self.account_index}] No valid Twitter token provided. Skipping Twitter connection.")
                else:
                    logger.info(f"[{self.account_index}] Twitter already connected. Skipping connection step.")
            else:
                logger.info(f"[{self.account_index}] Twitter verification is disabled. Skipping Twitter connection.")

            # Play the lasso game (will handle errors gracefully)
            random_pause = random.randint(5,10)
            await asyncio.sleep(random_pause)
            total_score = await self.claim()
            # Check if wallet has enough native balance before proceeding
            native_balance = await self.web3.eth.get_balance(self.account.address)
            native_balance_eth = self.web3.from_wei(native_balance, "ether")
            if native_balance_eth < 0.001:
                logger.warning(
                    f"[{self.account_index}] Insufficient MONAD balance: {native_balance_eth} MONAD. Minimum required: 0.01 MONAD. Skipping."
                )
                return False

            # Only claim rewards if the CLAIM option is enabled in config
            if self.config.DUSTED.CLAIM:
                claim_result = await self.claim_rewards()
            else:
                logger.info(
                    f"[{self.account_index}] CLAIM option is disabled, skipping reward claiming"
                )

            logger.success(
                f"[{self.account_index}] Dusted execution completed successfully"
            )
            return True

        except Exception as e:
            logger.error(f"[{self.account_index}] Error in Dusted execute: {e}")

            return False
