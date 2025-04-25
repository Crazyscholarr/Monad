from loguru import logger
import urllib3
import sys
import asyncio
import platform
from datetime import datetime, timezone, timedelta  # Thêm để xử lý múi giờ

from process import start
import src


# SETTING POLICY FOR WINDOWS
# config = src.utils.get_config()
# using_playwright = 'faucet' in str(config.FLOW.TASKS) or 'dusted' in str(config.FLOW.TASKS)


# if not using_playwright:
# if platform.system() == "Windows":
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    configuration()
    await start()


# Định nghĩa múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

log_format = (
    "<light-blue>[</light-blue><yellow>{time:HH:mm:ss | YYYY-MM-DD}</yellow><light-blue>]</light-blue> "
    "<magenta>[Crazyscholar x Monad]</magenta> | "
    "<level>{level: <8}</level> | "
    "<cyan>{file}:{line}</cyan> | "
    "<level>{message}</level>"
)


def configuration():
    urllib3.disable_warnings()
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format=log_format,
        # Thêm múi giờ Việt Nam
        serialize=False,

    )
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="1 month",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}",
        level="INFO",
    )


if __name__ == "__main__":
    asyncio.run(main())