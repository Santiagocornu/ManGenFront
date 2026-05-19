from __future__ import annotations

import requests
from requests import RequestException
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class PaymentRequiredError(ApiError):
    def __init__(self, message: str = "Falta de pago."):
        super().__init__(message, status_code=402)


class ApiClient:
    # Developer-only: keep the API base URL in code/config, but do NOT display
    # it in the UI shown to end users. The frontend may log or use this value
    # internally, but it should remain hidden from ordinary users.
    DEFAULT_BASE_URL = "https://api.mangenapp.com"

    def __init__(self):
        self.base_url = self.DEFAULT_BASE_URL
        self.token = None
        self.session = requests.Session()

    def set_token(self, token: str):
        self.token = token

    def clear_token(self):
        self.token = None

    def login(self, email: str, password: str):
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password},
                timeout=20,
            )
        except RequestException as exc:
            raise self._handle_request_exception(exc) from exc
        data = self._parse_response(response)
        token = data.get("token")
        if not token:
            raise ApiError("La API no devolvi\u00f3 un token.")
        self.set_token(token)
        return data

    def register_sucursal_admin(
        self,
        nombre_sucursal: str,
        nombre_admin: str,
        email_admin: str,
        password_admin: str,
    ):
        try:
            response = self.session.post(
                f"{self.base_url}/auth/register-sucursal-admin",
                json={
                    "nombreSucursal": nombre_sucursal,
                    "nombreAdmin": nombre_admin,
                    "emailAdmin": email_admin,
                    "passwordAdmin": password_admin,
                },
                timeout=20,
            )
        except RequestException as exc:
            raise self._handle_request_exception(exc) from exc
        data = self._parse_response(response)
        token = data.get("token")
        if not token:
            raise ApiError("La API no devolvi\u00f3 un token al registrar la sucursal.")
        self.set_token(token)
        return data

    def change_password(self, email: str, password: str, new_password: str):
        try:
            response = self.session.post(
                f"{self.base_url}/auth/change-password",
                params={
                    "email": email,
                    "password": password,
                    "newPassword": new_password,
                },
                timeout=20,
            )
        except RequestException as exc:
            raise self._handle_request_exception(exc) from exc
        return self._parse_response(response)

    def get(self, path: str):
        return self._request("GET", path)

    def post(self, path: str, payload=None):
        return self._request("POST", path, json=payload)

    def put(self, path: str, payload=None):
        return self._request("PUT", path, json=payload)

    def patch(self, path: str, payload=None):
        return self._request("PATCH", path, json=payload)

    def delete(self, path: str):
        return self._request("DELETE", path)

    def _request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                timeout=20,
                **kwargs,
            )
        except RequestException as exc:
            raise self._handle_request_exception(exc) from exc
        return self._parse_response(response)

    def _handle_request_exception(self, exc: RequestException):
        if isinstance(exc, Timeout):
            return ApiError("La solicitud tard\u00f3 demasiado. Intenta nuevamente.")
        if isinstance(exc, RequestsConnectionError):
            return ApiError("Error al conectarse con el servidor. Verifica que la API y la base de datos est\u00e9n encendidas.")
        return ApiError("Ocurri\u00f3 un error de conexi\u00f3n con el servidor. Intenta nuevamente.")

    @staticmethod
    def _parse_response(response: requests.Response):
        if response.status_code == 204:
            return None

        try:
            data = response.json()
        except ValueError:
            data = response.text

        if not response.ok:
            if response.status_code == 402:
                raise PaymentRequiredError("Falta de pago.")
            raise ApiError(ApiClient._normalize_error_message(response.status_code, data))

        return data

    @staticmethod
    def _normalize_error_message(status_code: int, data):
        if status_code == 401:
            return "Email o contrase\u00f1a incorrectos."
        if status_code == 402:
            return "Falta de pago."
        if status_code == 403:
            return "No tienes permisos para realizar esta acci\u00f3n."
        if status_code == 404:
            return "No se encontr\u00f3 el recurso solicitado."
        if status_code >= 500:
            return "El servidor tuvo un problema al procesar la solicitud. Intenta nuevamente."

        if isinstance(data, dict):
            message = data.get("message") or data.get("error") or ""
        else:
            message = data or ""

        message = str(message).strip()
        if not message:
            return f"Ocurri\u00f3 un error inesperado (HTTP {status_code})."

        return (
            message.replace("password", "contrase\u00f1a")
            .replace("Password", "Contrase\u00f1a")
            .replace("contrasena", "contrase\u00f1a")
        )
