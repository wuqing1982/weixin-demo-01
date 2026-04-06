from __future__ import annotations

import base64
import json
import secrets
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _normalize_json(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(',', ':'))


def _to_fen(amount: str | Decimal | float | int) -> int:
    decimal_amount = Decimal(str(amount or '0'))
    return int((decimal_amount * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


@dataclass
class WechatPayConfig:
    app_id: str
    mch_id: str
    api_v3_key: str
    mch_serial_no: str
    mch_private_key_path: str
    platform_cert_path: str
    platform_serial_no: str
    notify_url: str
    api_base: str
    currency: str = 'CNY'
    timeout_seconds: float = 10.0

    def is_configured(self) -> bool:
        return all([
            self.app_id,
            self.mch_id,
            self.api_v3_key,
            self.mch_serial_no,
            self.mch_private_key_path,
            self.notify_url,
            self.api_base,
        ])

    def can_verify_callbacks(self) -> bool:
        return bool(self.platform_cert_path and Path(self.platform_cert_path).exists())


class WechatPayClient:
    def __init__(self, config: WechatPayConfig):
        self.config = config
        self._merchant_private_key = None
        self._platform_public_key = None

    def is_configured(self) -> bool:
        return self.config.is_configured()

    def _load_merchant_private_key(self):
        if self._merchant_private_key is None:
            path = Path(self.config.mch_private_key_path)
            if not path.exists():
                raise ValueError('wechat pay merchant private key file not found')
            self._merchant_private_key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        return self._merchant_private_key

    def _load_platform_public_key(self):
        if self._platform_public_key is None:
            path = Path(self.config.platform_cert_path)
            if not path.exists():
                raise ValueError('wechat pay platform certificate file not found')
            certificate = x509.load_pem_x509_certificate(path.read_bytes())
            self._platform_public_key = certificate.public_key()
        return self._platform_public_key

    def _sign_message(self, message: str) -> str:
        signature = self._load_merchant_private_key().sign(
            message.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode('utf-8')

    def _build_authorization(self, *, method: str, path: str, body: str = '') -> tuple[str, str, str]:
        timestamp = str(int(time.time()))
        nonce_str = secrets.token_hex(16)
        message = f'{method.upper()}\n{path}\n{timestamp}\n{nonce_str}\n{body}\n'
        signature = self._sign_message(message)
        token = (
            'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{self.config.mch_id}",'
            f'nonce_str="{nonce_str}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{self.config.mch_serial_no}"'
        )
        return token, timestamp, nonce_str

    def _request(self, *, method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.is_configured():
            raise ValueError('wechat pay config incomplete')
        body = _normalize_json(json_body) if json_body is not None else ''
        authorization, _, _ = self._build_authorization(method=method, path=path, body=body)
        response = requests.request(
            method=method.upper(),
            url=f'{self.config.api_base}{path}',
            headers={
                'Authorization': authorization,
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
            data=body.encode('utf-8') if body else None,
            timeout=self.config.timeout_seconds,
        )
        if response.status_code < 200 or response.status_code >= 300:
            try:
                payload = response.json()
            except Exception:
                payload = {}
            message = payload.get('message') or payload.get('code') or f'wechat pay http {response.status_code}'
            raise ValueError(f'wechat pay request failed: {message}')
        return response.json() if response.content else {}

    def create_jsapi_transaction(
        self,
        *,
        out_trade_no: str,
        description: str,
        total_fen: int,
        payer_openid: str,
    ) -> dict[str, Any]:
        payload = {
            'appid': self.config.app_id,
            'mchid': self.config.mch_id,
            'description': description[:127] or '订单支付',
            'out_trade_no': out_trade_no,
            'notify_url': self.config.notify_url,
            'amount': {
                'total': int(total_fen),
                'currency': self.config.currency,
            },
            'payer': {
                'openid': payer_openid,
            },
        }
        return self._request(method='POST', path='/v3/pay/transactions/jsapi', json_body=payload)

    def build_miniapp_request_payment(self, prepay_id: str) -> dict[str, Any]:
        timestamp = str(int(time.time()))
        nonce_str = secrets.token_hex(16)
        package_value = f'prepay_id={prepay_id}'
        message = f'{self.config.app_id}\n{timestamp}\n{nonce_str}\n{package_value}\n'
        pay_sign = self._sign_message(message)
        return {
            'timeStamp': timestamp,
            'nonceStr': nonce_str,
            'package': package_value,
            'signType': 'RSA',
            'paySign': pay_sign,
        }

    def query_order_by_out_trade_no(self, out_trade_no: str) -> dict[str, Any]:
        path = f'/v3/pay/transactions/out-trade-no/{quote(out_trade_no, safe="")}?mchid={quote(self.config.mch_id, safe="")}'
        return self._request(method='GET', path=path)

    def verify_and_decrypt_callback(self, *, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        if not self.config.can_verify_callbacks():
            raise ValueError('wechat pay platform certificate not configured')
        timestamp = headers.get('Wechatpay-Timestamp') or headers.get('wechatpay-timestamp') or ''
        nonce = headers.get('Wechatpay-Nonce') or headers.get('wechatpay-nonce') or ''
        signature = headers.get('Wechatpay-Signature') or headers.get('wechatpay-signature') or ''
        serial = headers.get('Wechatpay-Serial') or headers.get('wechatpay-serial') or ''
        if not timestamp or not nonce or not signature:
            raise ValueError('wechat pay callback signature headers missing')
        if self.config.platform_serial_no and serial and serial != self.config.platform_serial_no:
            raise ValueError('wechat pay callback serial mismatch')

        message = f'{timestamp}\n{nonce}\n{body.decode("utf-8")}\n'
        self._load_platform_public_key().verify(
            base64.b64decode(signature),
            message.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        payload = json.loads(body.decode('utf-8'))
        resource = payload.get('resource') or {}
        ciphertext = resource.get('ciphertext') or ''
        associated_data = resource.get('associated_data') or ''
        resource_nonce = resource.get('nonce') or ''
        if not ciphertext or not resource_nonce:
            raise ValueError('wechat pay callback resource missing')
        plaintext = AESGCM(self.config.api_v3_key.encode('utf-8')).decrypt(
            resource_nonce.encode('utf-8'),
            base64.b64decode(ciphertext),
            associated_data.encode('utf-8') if associated_data else None,
        )
        return json.loads(plaintext.decode('utf-8'))


def build_wechat_pay_config(
    *,
    app_id: str,
    mch_id: str,
    api_v3_key: str,
    mch_serial_no: str,
    mch_private_key_path: str,
    platform_cert_path: str,
    platform_serial_no: str,
    notify_url: str,
    api_base: str,
    currency: str,
    timeout_seconds: float,
) -> WechatPayConfig:
    return WechatPayConfig(
        app_id=app_id,
        mch_id=mch_id,
        api_v3_key=api_v3_key,
        mch_serial_no=mch_serial_no,
        mch_private_key_path=mch_private_key_path,
        platform_cert_path=platform_cert_path,
        platform_serial_no=platform_serial_no,
        notify_url=notify_url,
        api_base=api_base,
        currency=currency,
        timeout_seconds=timeout_seconds,
    )
