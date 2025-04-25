import asyncio
from loguru import logger
import random
import primp
from src.model.help.captcha import Capsolver, Solvium
from src.utils.config import Config
from eth_account import Account
import hashlib
from pynocaptcha import CloudFlareCracker, TlsV1Cracker
from curl_cffi.requests import AsyncSession
from src.utils.tls_client import TLSClient
import json
import platform
import os
import time
import traceback


async def faucet(
    session,
    account_index: int,
    config: Config,
    wallet: Account,
    proxy: str,
) -> bool:
    # Константы
    FAUCET_ENDPOINT = "https://faucet-claim.molandak.org/api/claim"
    CLOUDFLARE_SITE = "https://testnet.monad.xyz/"
    CLOUDFLARE_SITEKEY = "0x4AAAAAAA-3X4Nd7hf3mNGx"
    MAX_RETRIES_PER_ERROR = 3
    
    for retry in range(config.SETTINGS.ATTEMPTS):
        try:
            logger.info(
                f"[{account_index}] | Starting faucet for account {wallet.address}..."
            )
            
            
            fingerprints = [
                {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                    "sec_ch_ua_platform": '"Windows"',
                    "accept": "*/*",
                    "sec_ch_ua_mobile": "?0"
                },
                {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
                    "sec_ch_ua": '"Not A(Brand";v="99", "Microsoft Edge";v="132", "Chromium";v="132"',
                    "sec_ch_ua_platform": '"Windows"',
                    "accept": "*/*",
                    "sec_ch_ua_mobile": "?0"
                },
                {
                    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                    "sec_ch_ua_platform": '"macOS"',
                    "accept": "*/*",
                    "sec_ch_ua_mobile": "?0"
                },
                {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="131", "Chromium";v="131"',
                    "sec_ch_ua_platform": '"Windows"',
                    "accept": "*/*",
                    "sec_ch_ua_mobile": "?0"
                },
                {
                    "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                    "sec_ch_ua_platform": '"Linux"',
                    "accept": "*/*",
                    "sec_ch_ua_mobile": "?0"
                }
            ]

            
            selected_fingerprint = random.choice(fingerprints)
            user_agent = selected_fingerprint["user_agent"]

            cf_result = await solve_cloudflare(account_index, config, session, proxy, CLOUDFLARE_SITE, CLOUDFLARE_SITEKEY)
            
            if not cf_result:
                raise Exception("Failed to solve Cloudflare challenge")

            logger.success(f"[{account_index}] | Cloudflare challenge solved")

            
            visitor_id = hashlib.md5(str(random.random()).encode()).hexdigest()

            json_data = {
                "address": wallet.address,
                "visitorId": visitor_id,
                "cloudFlareResponseToken": cf_result,
            }

            
            await asyncio.sleep(random.uniform(2, 5))
            
            logger.info(f"[{account_index}] | Sending claim request...")


            
            headers = create_headers(selected_fingerprint, cf_result)
            
            
            response_text, status_code = await make_request(
                account_index, 
                headers, 
                json_data, 
                proxy, 
                FAUCET_ENDPOINT
            )

            logger.info(
                f"[{account_index}] | Received response with status code: {status_code}"
            )

            
            result = process_response(account_index, response_text, status_code)
            
            if result == "success":
                return True
            elif result == "retry":
                
                await asyncio.sleep(random.uniform(5, 10))
                continue
            elif result == "fail":
                return False
            else:  # "continue"
                await asyncio.sleep(3)
                continue

        except Exception as e:
            random_pause = random.randint(
                config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
            )
            
            if "403 Forbidden" in str(e) or "Cloudflare" in str(e):
                logger.warning(f"[{account_index}] | Cloudflare detection, trying again...")
                
                await asyncio.sleep(random.uniform(5, 10))
                continue
            
            if "429 Too Many Requests" in str(e):
                logger.warning(f"[{account_index}] | Rate limit detected, waiting...")
                
                await asyncio.sleep(random.uniform(10, 15))
                continue

            if "operation timed out" in str(e):
                logger.error(
                    f"[{account_index}] | Error faucet to monad.xyz ({retry + 1}/{config.SETTINGS.ATTEMPTS}): Connection timed out. Next faucet in {random_pause} seconds"
                )
            else:
                logger.error(
                    f"[{account_index}] | Error faucet to monad.xyz ({retry + 1}/{config.SETTINGS.ATTEMPTS}): {e}. Next faucet in {random_pause} seconds"
                )
                
                
                if config.SETTINGS.DEBUG:
                    logger.debug(f"[{account_index}] | Traceback: {traceback.format_exc()}")
                    
            await asyncio.sleep(random_pause)
            continue
    return False


async def solve_cloudflare(account_index, config, session, proxy, cloudflare_site, cloudflare_sitekey):
    
    if config.FAUCET.USE_SOLVIUM_FOR_CLOUDFLARE:
        logger.info(
            f"[{account_index}] | Solving Cloudflare challenge with Solvium..."
        )
        solvium = Solvium(
            api_key=config.FAUCET.SOLVIUM_API_KEY,
            session=session,
            proxy=proxy,
        )

        result = await solvium.solve_captcha(
            sitekey=cloudflare_sitekey,
            pageurl=cloudflare_site,
        )
        return result

    elif config.FAUCET.USE_CAPSOLVER_FOR_CLOUDFLARE:
        logger.info(
            f"[{account_index}] | Solving Cloudflare challenge with Capsolver..."
        )
        capsolver = Capsolver(
            api_key=config.FAUCET.CAPSOLVER_API_KEY,
            proxy=proxy,
            session=session,
        )
        return await capsolver.solve_turnstile(
            cloudflare_sitekey,
            cloudflare_site,
        )

    else:
        
        logger.info(
            f"[{account_index}] | Solving Cloudflare challenge with Nocaptcha..."
        )
        cracker = CloudFlareCracker(
            internal_host=True,
            user_token=config.FAUCET.NOCAPTCHA_API_KEY,
            href=cloudflare_site,
            sitekey=cloudflare_sitekey,
            proxy=proxy,
            debug=False,
            show_ad=False,
            timeout=60,
        )
        cf_result = cracker.crack()
        return cf_result["token"]


def create_headers(fingerprint, cf_result):
    """Создает заголовки для запроса"""
    headers = {
        "sec-ch-ua-platform": fingerprint["sec_ch_ua_platform"],
        "user-agent": fingerprint["user_agent"],
        "sec-ch-ua": fingerprint["sec_ch_ua"],
        "content-type": "application/json",
        "sec-ch-ua-mobile": fingerprint["sec_ch_ua_mobile"],
        "accept": fingerprint["accept"],
        "origin": "https://testnet.monad.xyz",
        "sec-fetch-site": "cross-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://testnet.monad.xyz/",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=1, i",
    }
    
    
    if random.random() > 0.5:
        headers["accept-encoding"] = "gzip, deflate, br"
    if random.random() > 0.5:
        headers["cache-control"] = "no-cache"
    if random.random() > 0.5:
        headers["pragma"] = "no-cache"
    
    
    headers["cookie"] = f"cf_clearance={cf_result}"
    
    return headers


async def make_request(account_index, headers, json_data, proxy, endpoint):
    """Выполняет запрос в зависимости от платформы"""
    if platform.system().lower() != "windows":

        curl_session = AsyncSession(
            impersonate="chrome131",
            proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
            verify=False,
        )

        claim_result = await curl_session.post(
            endpoint,
            headers=headers,
            json=json_data,
        )
        return claim_result.text, claim_result.status_code
    else:
        
        logger.info(f"[{account_index}] | Initializing TLS client...")
        tls_client = TLSClient()
        
       
        proxy_parts = proxy.split("@")
        if len(proxy_parts) == 2:
            proxy_url = f"http://{proxy}"
        else:
            proxy_url = f"http://{proxy}"

        
        logger.info(f"[{account_index}] | Sending claim request via TLS client...")
        
        
        tls_fingerprints = ["chrome_133", "chrome_120", "chrome_116", "firefox_110"]
        tls_fingerprint = random.choice(tls_fingerprints)
        
        response = tls_client.make_request(
            url=endpoint,
            method="POST",
            headers=headers,
            data=json_data,
            proxy=proxy_url,
            tls_client_identifier=tls_fingerprint
        )

        
        response_text = response.get("body", "")
        status_code = response.get("status", 0)
        
        return response_text, status_code


def process_response(account_index, response_text, status_code):
    """Обрабатывает ответ от сервера"""
    if "Faucet is currently closed" in response_text:
        logger.error(f"[{account_index}] | Faucet is currently closed")
        return "fail"

    if status_code == 429:
        logger.error(f"[{account_index}] | Cloudflare solved wrong...")
        return "retry"

    if status_code == 403 and "Cloudflare" in response_text:
        logger.error(f"[{account_index}] | Cloudflare solved wrong...")
        return "retry"

    if not response_text:
        raise Exception("Failed to send claim request")

    if '"Success"' in response_text:
        logger.success(
            f"[{account_index}] | Successfully got tokens from faucet"
        )
        return "success"

    if "Claimed already" in response_text:
        logger.success(
            f"[{account_index}] | Already claimed tokens from faucet"
        )
        return "success"


    if '"message":"Success"' in response_text:
        logger.success(
            f"[{account_index}] | Successfully got tokens from faucet"
        )
        return "success"
    else:
        if "FUNCTION_INVOCATION_TIMEOUT" in response_text:
            logger.error(
                f"[{account_index}] | Failed to get tokens from faucet: server is not responding, wait..."
            )
        elif "Vercel Security Checkpoint" in response_text:
            logger.error(
                f"[{account_index}] | Failed to solve Vercel challenge, trying again..."
            )
            return "retry"
        elif "Server error on QuickNode API" in response_text:
            logger.error(
                f"[{account_index}] | FAUCET DOES NOT WORK, QUICKNODE IS DOWN"
            )
        elif "Over Enterprise free quota" in response_text:
            logger.error(
                f"[{account_index}] | MONAD IS SHIT, FAUCET DOES NOT WORK, TRY LATER"
            )
            return "fail"
        elif "invalid-keys" in response_text:
            logger.error(
                f"[{account_index}] | PLEASE UPDATE THE BOT USING GITHUB"
            )
            return "fail"
        else:
            logger.error(
                f"[{account_index}] | Failed to get tokens from faucet: {response_text}"
            )
        return "continue"
