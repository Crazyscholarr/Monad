from typing import Optional, Dict, Any
import primp
from loguru import logger


async def make_wanda_request(
    session: primp.AsyncClient,
    user_token: str,
    url: str,
    method: str = "get",
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    proxy: Optional[str] = None,
    http2: bool = False,
    timeout: int = 30,
    developer_id: Optional[str] = None,
    debug: bool = False,
    internal_host: bool = False,
) -> Dict[str, Any]:
    """
    Асинхронная функция для выполнения Wanda TLS запросов
    """
    api_host = "api.nocaptcha.cn" if internal_host else "api.nocaptcha.io"

    # Подготовка параметров запроса
    wanda_args = {
        "url": url,
        "method": method.lower(),
        "internal": True,
        "is_auth": False,
        "timeout": timeout,
        "http2": http2,
    }

    if headers:
        wanda_args["headers"] = headers
    if json_data:
        wanda_args["json"] = json_data
    if proxy:
        wanda_args["proxy"] = proxy

    # Подготовка заголовков
    request_headers = {"User-Token": user_token}
    if developer_id:
        request_headers["Developer-Id"] = developer_id

    try:
        response = await session.post(
            f"http://{api_host}/api/wanda/tls/v1",
            headers=request_headers,
            json=wanda_args,
            timeout=timeout,
        )

        result = response.json()

        if debug:
            logger.info(result)

        if not result.get("data"):
            if debug:
                logger.error(result.get("msg"))
            return None

        return {"data": result.get("data"), "extra": result.get("extra")}

    except Exception as e:
        logger.error(f"Error making Wanda request: {e}")
        raise


async def make_tls_request(
    session: primp.AsyncClient,
    url: str,
    method: str = "get",
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    proxy: Optional[str] = None,
    http2: bool = False,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    Асинхронная функция для выполнения TLS запросов

    :param session: primp.AsyncClient сессия
    :param url: URL для запроса
    :param method: HTTP метод (get/post)
    :param headers: Заголовки запроса
    :param json_data: JSON данные для POST запроса
    :param proxy: Прокси в формате http://user:pass@ip:port
    :param http2: Использовать ли HTTP/2
    :param timeout: Таймаут в секундах
    :return: Ответ сервера в виде словаря
    """
    try:
        if method.lower() == "post":
            response = await session.post(
                url, headers=headers, json=json_data, timeout=timeout
            )
        else:
            response = await session.get(url, headers=headers, timeout=timeout)

        return response.json()

    except Exception as e:
        logger.error(f"Error making TLS request: {e}")
        raise
