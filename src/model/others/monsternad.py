import asyncio
from loguru import logger
import random
import primp
from src.model.help.captcha import Capsolver, Solvium
from src.utils.config import Config
from eth_account import Account
import json
import platform


async def monsternad_whitelist(
    session: primp.AsyncClient,
    account_index: int,
    config: Config,
    private_key: str,
) -> bool:
    for retry in range(config.SETTINGS.ATTEMPTS):
        try:
            wallet = Account.from_key(private_key)
            logger.info(
                f"[{account_index}] | Starting monsternad whitelist for account {wallet.address}..."
            )

            headers = {
                "accept": "application/json, text/plain, */*",
                "content-type": "application/json",
                "origin": "https://airdrop.monsternad.xyz",
                "referer": "https://airdrop.monsternad.xyz/",
            }

            json_data = {
                "address": wallet.address,
                "chainId": 10143,
            }

            response = await session.post(
                "https://api.monsternad.xyz/wallets",
                headers=headers,
                json=json_data,
            )

            if response.status_code >= 200 and response.status_code < 300:
                if response.json()["address"].lower() == wallet.address.lower():
                    logger.success(
                        f"[{account_index}] | Successfully added to monsternad whitelist"
                    )
                    return True

            if "Wallet address already exists" in response.text:
                logger.success(
                    f"[{account_index}] | Successfully added to monsternad whitelist"
                )
                return True

            if "Too Many Requests" in response.text:
                logger.warning(
                    f"[{account_index}] | Too Many Requests. Most likely you have already added to whitelist"
                )
                return True

            raise Exception(response.text)

        except Exception as e:
            random_pause = random.randint(
                config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
            )

            logger.error(
                f"[{account_index}] | Error monsternad whitelist ({retry + 1}/{config.SETTINGS.ATTEMPTS}): {e}. Next whitelist in {random_pause} seconds"
            )
            await asyncio.sleep(random_pause)
            continue
    return False
