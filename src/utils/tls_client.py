import os
import json
import ctypes
import platform
from typing import Dict, List, Optional, Union, Any


class TLSClient:
    def __init__(self):
        """
        Инициализация TLS клиента, который напрямую использует DLL библиотеку
        """
        # Загрузка библиотеки TLS клиента
        self._load_tls_library()
        self.session_id = None

    def _load_tls_library(self):
        """Загрузка DLL библиотеки TLS клиента в зависимости от операционной системы"""
        system = platform.system().lower()
        arch = platform.architecture()[0]

        if system == "windows":
            dll_path = os.path.join(
                os.path.dirname(__file__), "tls-client-windows-64-1.8.0.dll"
            )

            try:
                # Загружаем библиотеку
                self.tls_lib = ctypes.cdll.LoadLibrary(dll_path)

                # Настраиваем функции библиотеки
                self._setup_functions()
            except Exception as e:
                raise Exception(f"Не удалось загрузить TLS библиотеку: {e}")
        else:
            raise NotImplementedError(
                f"Операционная система {system} не поддерживается"
            )

    def _setup_functions(self):
        """Настройка функций библиотеки"""
        # Настраиваем функцию запроса
        self.request = self.tls_lib.request
        self.request.argtypes = [ctypes.c_char_p]
        self.request.restype = ctypes.c_char_p

        # Настраиваем функцию получения cookies
        try:
            self.get_cookies_from_session = self.tls_lib.getCookiesFromSession
            self.get_cookies_from_session.argtypes = [ctypes.c_char_p]
            self.get_cookies_from_session.restype = ctypes.c_char_p
        except AttributeError:
            print("Функция getCookiesFromSession не найдена в библиотеке")
            self.get_cookies_from_session = None

        # Настраиваем функцию добавления cookies
        try:
            self.add_cookies_to_session = self.tls_lib.addCookiesToSession
            self.add_cookies_to_session.argtypes = [ctypes.c_char_p]
            self.add_cookies_to_session.restype = ctypes.c_char_p
        except AttributeError:
            print("Функция addCookiesToSession не найдена в библиотеке")
            self.add_cookies_to_session = None

        # Настраиваем функцию освобождения памяти
        try:
            self.free_memory = self.tls_lib.freeMemory
            self.free_memory.argtypes = [ctypes.c_char_p]
        except AttributeError:
            print("Функция freeMemory не найдена в библиотеке")
            self.free_memory = None

        # Настраиваем функцию уничтожения сессии
        try:
            self.destroy_session = self.tls_lib.destroySession
            self.destroy_session.argtypes = [ctypes.c_char_p]
            self.destroy_session.restype = ctypes.c_char_p
        except AttributeError:
            print("Функция destroySession не найдена в библиотеке")
            self.destroy_session = None

        # Настраиваем функцию уничтожения всех сессий
        try:
            self.destroy_all = self.tls_lib.destroyAll
            self.destroy_all.restype = ctypes.c_char_p
        except AttributeError:
            print("Функция destroyAll не найдена в библиотеке")
            self.destroy_all = None

    def make_request(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        proxy: Optional[str] = None,
        tls_client_identifier: str = "chrome_133",
        follow_redirects: bool = True,
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Выполнение запроса через TLS клиент

        Args:
            url: URL для запроса
            method: HTTP метод (GET, POST, и т.д.)
            headers: HTTP заголовки
            data: Данные для отправки в теле запроса
            proxy: Прокси в формате http://user:pass@ip:port
            tls_client_identifier: Идентификатор TLS клиента
            follow_redirects: Следовать ли за редиректами
            timeout_seconds: Таймаут в секундах

        Returns:
            Ответ от сервера в виде словаря
        """
        if headers is None:
            headers = {}

        # Формирование запроса
        request_payload = {
            "tlsClientIdentifier": tls_client_identifier,
            "followRedirects": follow_redirects,
            "insecureSkipVerify": False,
            "withoutCookieJar": False,
            "withDefaultCookieJar": True,
            "isByteRequest": False,
            "isByteResponse": False,
            "forceHttp1": False,
            "withDebug": False,
            "catchPanics": False,
            "withRandomTLSExtensionOrder": True,  # Для Chrome 107+
            "timeoutSeconds": timeout_seconds,
            "timeoutMilliseconds": 0,
            "certificatePinningHosts": {},
            "headers": headers,
            "headerOrder": list(headers.keys()),  # Порядок заголовков
            "requestUrl": url,
            "requestMethod": method,
            "requestBody": "",
            "requestCookies": [],
        }

        # Добавление тела запроса, если оно есть
        if data:
            if isinstance(data, dict):
                request_payload["requestBody"] = json.dumps(data)
            else:
                request_payload["requestBody"] = str(data)

        # Добавление прокси, если он указан
        if proxy:
            request_payload["proxyUrl"] = proxy
            request_payload["isRotatingProxy"] = False

        # Добавление session_id, если он есть
        if self.session_id:
            request_payload["sessionId"] = self.session_id

        # Преобразование запроса в JSON и отправка в библиотеку
        request_json = json.dumps(request_payload).encode("utf-8")

        try:
            # Выполнение запроса
            response_ptr = self.request(request_json)

            # Преобразование ответа из C-строки в Python словарь
            response_bytes = ctypes.string_at(response_ptr)
            response_string = response_bytes.decode("utf-8")
            response = json.loads(response_string)

            # Освобождение памяти, если есть соответствующая функция
            if self.free_memory:
                self.free_memory(response_ptr)

            # Сохранение session_id для последующих запросов
            if "sessionId" in response:
                self.session_id = response["sessionId"]

            return response
        except Exception as e:
            return {"status": 0, "body": f"Ошибка при выполнении запроса: {str(e)}"}

    def get_cookies(self, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение cookies из текущей сессии

        Args:
            url: URL для которого нужно получить cookies

        Returns:
            Словарь с cookies
        """
        if not self.session_id:
            return {"status": 0, "body": "Нет активной сессии"}

        if not self.get_cookies_from_session:
            return {
                "status": 0,
                "body": "Функция getCookiesFromSession не найдена в библиотеке",
            }

        # Формирование запроса для получения cookies
        cookie_payload = {"sessionId": self.session_id}

        if url:
            cookie_payload["url"] = url

        # Преобразование запроса в JSON и отправка в библиотеку
        cookie_json = json.dumps(cookie_payload).encode("utf-8")

        try:
            # Выполнение запроса
            cookie_response_ptr = self.get_cookies_from_session(cookie_json)

            # Преобразование ответа из C-строки в Python словарь
            cookie_response_bytes = ctypes.string_at(cookie_response_ptr)
            cookie_response_string = cookie_response_bytes.decode("utf-8")
            cookie_response = json.loads(cookie_response_string)

            # Освобождение памяти, если есть соответствующая функция
            if self.free_memory:
                self.free_memory(cookie_response_ptr)

            return cookie_response
        except Exception as e:
            return {"status": 0, "body": f"Ошибка при получении cookies: {str(e)}"}

    def free_session(self) -> Dict[str, Any]:
        """
        Освобождение текущей сессии

        Returns:
            Результат операции
        """
        if not self.session_id:
            return {"status": 0, "body": "Нет активной сессии"}

        if not self.destroy_session:
            return {
                "status": 0,
                "body": "Функция destroySession не найдена в библиотеке",
            }

        # Формирование запроса для освобождения сессии
        destroy_payload = {"sessionId": self.session_id}

        # Преобразование запроса в JSON и отправка в библиотеку
        destroy_json = json.dumps(destroy_payload).encode("utf-8")

        try:
            # Выполнение запроса
            destroy_response_ptr = self.destroy_session(destroy_json)

            # Преобразование ответа из C-строки в Python словарь
            destroy_response_bytes = ctypes.string_at(destroy_response_ptr)
            destroy_response_string = destroy_response_bytes.decode("utf-8")
            destroy_response = json.loads(destroy_response_string)

            # Освобождение памяти, если есть соответствующая функция
            if self.free_memory:
                self.free_memory(destroy_response_ptr)

            self.session_id = None
            return destroy_response
        except Exception as e:
            return {"status": 0, "body": f"Ошибка при освобождении сессии: {str(e)}"}
