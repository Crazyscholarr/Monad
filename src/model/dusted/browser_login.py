import os
from pathlib import Path
import shutil
from typing import Dict, List
import uuid
from loguru import logger
import asyncio
import random
from patchright.async_api import async_playwright

from src.utils.config import Config


def get_profiles_dir() -> str:
    """Get the path to profiles directory and ensure it exists."""
    # Get the path to the main.py directory (project root)
    root_dir = Path(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    )
    profiles_dir = root_dir / "data" / "profiles"

    # Create directories if they don't exist
    os.makedirs(profiles_dir, exist_ok=True)

    return str(profiles_dir)


def cleanup_profile(profile_dir: str) -> None:
    """Safely remove a Chrome profile directory."""
    try:
        if os.path.exists(profile_dir):
            shutil.rmtree(profile_dir, ignore_errors=True)
            logger.debug(f"Successfully cleaned up profile directory: {profile_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup profile directory {profile_dir}: {e}")


def get_random_user_agent():
    chrome_versions = [
        "123.0.0.0",
        "124.0.0.0",
        "125.0.0.0",
        "126.0.0.0",
        "127.0.0.0",
        "128.0.0.0",
        "129.0.0.0",
        "130.0.0.0",
        "131.0.0.0",
        "132.0.0.0",
        "133.0.0.0",
    ]

    platforms = [
        ("Windows NT 10.0; Win64; x64", "Windows"),
        ("Macintosh; Intel Mac OS X 10_15_7", "macOS"),
        ("X11; Linux x86_64", "Linux"),
    ]

    platform, os_name = random.choice(platforms)
    chrome_version = random.choice(chrome_versions)

    return (
        f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36",
        chrome_version,
    )


def get_random_viewport() -> Dict[str, int]:
    resolutions = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
    ]
    return random.choice(resolutions)


def get_random_timezone() -> str:
    timezones = [
        "America/New_York",
        "America/Chicago",
        "America/Los_Angeles",
        "America/Phoenix",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Asia/Tokyo",
        "Asia/Singapore",
        "Australia/Sydney",
    ]
    return random.choice(timezones)


def get_random_launch_args(metamask_path: str) -> List[str]:
    base_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--password-store=basic",
        # "--use-mock-keychain",
        # "--disable-software-rasterizer",
        # "--disable-gpu-sandbox",
        "--no-default-browser-check",
        # "--allow-running-insecure-content",
    ]

    optional_args = [
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process,OptimizationGuideModelDownloading,OptimizationHintsFetching,OptimizationTargetPrediction,OptimizationHints",
        "--disable-site-isolation-trials",
        "--disable-setuid-sandbox",
        "--ignore-certificate-errors",
        # "--disable-accelerated-2d-canvas",
        # "--disable-bundled-ppapi-flash",
        "--disable-logging",
        "--disable-notifications",
    ]

    # Randomly select 2-4 optional arguments
    selected_optional = random.sample(optional_args, random.randint(2, 4))

    # Add extension-specific arguments
    extension_args = [
        f"--disable-extensions-except={metamask_path}",
        f"--load-extension={metamask_path}",
        "--lang=en-US",
    ]

    viewport = get_random_viewport()
    window_size_arg = [f"--window-size={viewport['width']},{viewport['height']}"]

    return base_args + selected_optional + extension_args + window_size_arg


async def setup_metamask(page, private_key: str) -> None:
    # Wait for MetaMask popup to appear
    await asyncio.sleep(30)  # Wait for MetaMask to load

    # Get all pages and find MetaMask popup
    pages = page.context.pages
    metamask_page = pages[2]

    # MetaMask popup is typically the second or third page
    # for p in pages:
    #     if "chrome-extension://hjbclcphfbpaoebnggnpdgjpjidhbfpl" in p.url:
    #         metamask_page = p
    #         break

    # if not metamask_page:
    #     logger.error("MetaMask page not found")
    #     return

    await asyncio.sleep(1)
    # Click through import flow
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/ul/li[1]/div/input"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/ul/li[2]/button"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/button[2]"
    )
    await asyncio.sleep(1)

    # Fill in password fields
    await metamask_page.fill(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/form/div[1]/label/input",
        "999999999",
    )
    await metamask_page.fill(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/form/div[2]/label/input",
        "999999999",
    )

    # Click through import flow
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/form/div[3]/label/span[1]/input"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/form/button"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/button[1]"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[2]/div/div/section/div[1]/div/div/label/input"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[2]/div/div/section/div[2]/div/button[2]"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[3]/button"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/button"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[1]/div/div[2]/div/div/div/div[2]/button"
    )
    await asyncio.sleep(1)
    await metamask_page.click("xpath=/html/body/div[1]/div/div[2]/div/div[2]/button")
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[3]/div[3]/div/section/div[2]/button"
    )
    await asyncio.sleep(1)
    await metamask_page.click(
        "xpath=/html/body/div[3]/div[3]/div/section/div/div[2]/button"
    )
    await asyncio.sleep(1)

    # Import private key
    await metamask_page.fill(
        "xpath=/html/body/div[3]/div[3]/div/section/div/div/div[1]/div/input",
        private_key,
    )
    await asyncio.sleep(3)
    await metamask_page.click(
        "xpath=/html/body/div[3]/div[3]/div/section/div/div/div[2]/button[2]"
    )

    # Close MetaMask popup
    await metamask_page.close()
    await asyncio.sleep(1)


async def dusted_browser_login(config: Config, private_key: str, proxy: str) -> bool:
    profile_dir = None
    for retry in range(config.SETTINGS.ATTEMPTS):
        try:
            metamask_path = os.path.join(os.path.dirname(__file__), "metamask")

            proxy_parts = proxy.split("@")
            auth = proxy_parts[0].split(":")
            proxy_options = {
                "server": f"http://{proxy_parts[1]}",
                "username": auth[0],
                "password": auth[1],
            }

            # Get random browser settings
            user_agent, chrome_version = get_random_user_agent()
            viewport = get_random_viewport()
            launch_args = get_random_launch_args(metamask_path)

            async with async_playwright() as p:
                # Create a unique profile directory in data/profiles
                profile_dir = os.path.join(
                    get_profiles_dir(), f"chrome_profile_{str(uuid.uuid4())}"
                )

                # Launch browser with enhanced settings
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    channel="chrome",
                    proxy=proxy_options,
                    viewport=viewport,
                    user_agent=user_agent,
                    headless=False,
                    args=launch_args,
                    ignore_https_errors=True,
                    locale="en-US",
                    timezone_id="UTC",
                    bypass_csp=True,
                    accept_downloads=True,
                    timeout=int(30000 * config.SETTINGS.BROWSER_PAUSE_MULTIPLIER),
                )

                # Create new page and navigate
                page = await browser.new_page()

                # Set custom headers
                await page.set_extra_http_headers(
                    {
                        "accept": "*/*",
                        "accept-language": "en-US,en;q=0.9",
                        "sec-ch-ua": f'"Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": '"Windows"',
                        "sec-fetch-dest": "empty",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-site": "cross-site",
                    }
                )

                # Setup MetaMask
                await setup_metamask(page, private_key)

                await page.goto("https://www.dusted.app/")
                await asyncio.sleep(2)  # Wait for page to load

                # Click Enter App button
                await page.click('button:has-text("Enter App")')
                await asyncio.sleep(2)

                # Click MetaMask button
                await page.click('button:has-text("MetaMask")')
                await asyncio.sleep(10)

                # Find MetaMask popup and click Connect
                pages = page.context.pages
                metamask_page = pages[2]

                if metamask_page:
                    # Click Connect button in MetaMask
                    await metamask_page.click('button[data-testid="confirm-btn"]')
                    await asyncio.sleep(2)

                    # Click Confirm button in MetaMask
                    await metamask_page.click(
                        'button[data-testid="confirm-footer-button"]'
                    )
                    await asyncio.sleep(2)

                    # Close MetaMask popup
                    await metamask_page.close()
                    await asyncio.sleep(1)
                else:
                    raise Exception("MetaMask popup not found")

                logger.info("Logged in to dusted.app")
                await asyncio.sleep(20)

                await browser.close()
                cleanup_profile(
                    profile_dir
                )  # Clean up profile after successful completion
                return True

        except Exception as e:
            try:
                await browser.close()
            except:
                pass

            if profile_dir:  # Clean up profile on error
                cleanup_profile(profile_dir)

            random_pause = random.uniform(
                config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
            )
            logger.error(
                f"[{retry}] Error during dusted browser login: {e}. Waiting {random_pause} seconds before retrying..."
            )
            await asyncio.sleep(random_pause)
            continue

    if profile_dir:  # Final cleanup if all attempts failed
        cleanup_profile(profile_dir)
    return False
