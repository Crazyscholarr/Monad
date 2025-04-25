import json
import yaml
from loguru import logger


def read_txt_file(file_name: str, file_path: str) -> list:
    with open(file_path, "r") as file:
        items = [line.strip() for line in file]

    logger.success(f"Successfully loaded {len(items)} {file_name}.")
    return items


def split_list(lst, chunk_size=90):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def read_abi(path) -> dict:
    with open(path, "r") as f:
        return json.load(f)
    
def check_proxy_format(proxies: list):
    formatted_proxies = []
    
    for proxy in proxies:
        
        # Step 1: Strip protocols if present (http://, https://, socks://, etc.)
        for protocol in ["http://", "https://", "socks://", "socks4://", "socks5://"]:
            if proxy.startswith(protocol):
                proxy = proxy[len(protocol):]
                break
        
        # Step 2: Convert format if needed
        if "@" in proxy:
            # Already in user:pass@ip:port format
            formatted_proxies.append(proxy)
        else:
            # Likely in ip:port:user:pass format
            parts = proxy.split(":")
            if len(parts) == 4:
                # Convert ip:port:user:pass to user:pass@ip:port
                ip, port, user, password = parts
                formatted_proxy = f"{user}:{password}@{ip}:{port}"
                formatted_proxies.append(formatted_proxy)
            else:
                logger.warning(f"Unable to parse proxy format: {proxy}")
                return False
    
    return formatted_proxies