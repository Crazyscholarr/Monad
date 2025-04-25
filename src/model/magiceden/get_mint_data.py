import random
import asyncio
from loguru import logger
from eth_account import Account
from eth_account.signers.local import LocalAccount
from curl_cffi import requests

# List of common user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


def get_random_headers():
    """Generate random headers for requests"""
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://magiceden.io",
        "referer": "https://magiceden.io/",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": random.choice(USER_AGENTS),
        "x-client-platform": "web",
    }


async def get_mint_data(
    proxy: str,
    nft_contract: str,
    wallet: Account,
    max_retries: int = 10,
    retry_delay: int = 2,
) -> dict:
    """
    Get mint data from MagicEden API with improved error handling and headers.
    """
    if proxy:
        curl_session = requests.AsyncSession(
            impersonate="chrome131",
            proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
            headers=get_random_headers(),
            verify=False,
            timeout=30,
        )
    else:
        curl_session = requests.AsyncSession(
            impersonate="chrome131",
            headers=get_random_headers(),
            verify=False,
            timeout=30,
        )

    error_log_frequency = 5
    error = ""

    for attempt in range(1, max_retries + 1):
        should_log = (
            attempt % error_log_frequency == 0 or attempt == 1 or attempt == max_retries
        )

        try:
            payload = {
                "chain": "monad-testnet",
                "collectionId": nft_contract,
                "kind": "public",
                "nftAmount": 1,
                "protocol": "ERC1155",
                "tokenId": 0,
                "wallet": {"address": wallet.address, "chain": "monad-testnet"},
                "address": wallet.address,
                "chain": "monad-testnet",
            }

            # Add random delay between attempts
            if attempt > 1:
                delay = retry_delay * (1 + random.random())
                await asyncio.sleep(delay)

            response = await curl_session.post(
                "https://api-mainnet.magiceden.io/v4/self_serve/nft/mint_token",
                json=payload,
            )

            # Check if we got an access denied response
            if "Access denied" in response.text:
                if should_log:
                    logger.warning(
                        f"Access denied (attempt {attempt}/{max_retries}). Retrying with new headers..."
                    )
                # Rotate headers and continue
                curl_session.headers = get_random_headers()
                continue

            if response.status_code == 200:
                return response.json()

            # Handle specific error cases
            if "Token has no eligible mints" in response.text:
                logger.warning(f"💀 Wait a bit, MagicEden API returned wrong data...")
                await asyncio.sleep(3)
                error = "all_nfts_minted"

            elif "max mints per wallet possibly exceeded" in response.text:
                return "already_minted"

            elif "no healthy upstream" in response.text:
                if should_log:
                    logger.error(f"❌ MagicEden API is down now. Trying again...")
                await asyncio.sleep(3)
                continue

            # Handle other status codes
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get("message", "")
                    if "max mints per wallet possibly exceeded" in error_message:
                        return "already_minted"
                except:
                    pass

                if should_log:
                    logger.error(
                        f"❌ Failed to get mint data: {response.status_code} - {response.text}"
                    )

            elif response.status_code >= 500:
                if attempt < max_retries:
                    wait_time = retry_delay * attempt
                    if should_log:
                        logger.warning(
                            f"⚠️ Server error {response.status_code}. "
                            f"Retrying in {wait_time}s (attempt {attempt}/{max_retries})"
                        )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Server error after {max_retries} attempts")

            else:
                if should_log:
                    logger.error(
                        f"❌ Unexpected status code: {response.status_code} - {response.text}"
                    )

        except Exception as e:
            if attempt < max_retries:
                wait_time = retry_delay * attempt
                if "connection" in str(e).lower():
                    if should_log:
                        logger.warning(
                            f"⚠️ Connection error (attempt {attempt}/{max_retries}). "
                            f"Retrying in {wait_time}s..."
                        )
                else:
                    if should_log:
                        logger.warning(
                            f"⚠️ Error: {str(e)}. "
                            f"Retrying in {wait_time}s (attempt {attempt}/{max_retries})"
                        )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ Failed after {max_retries} attempts: {str(e)}")
                return None

    await curl_session.close()
    return error if error else None
