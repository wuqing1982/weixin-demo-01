"""WeChat Virtual Payment (xpay) client for mini programs.

Handles HMAC-SHA256 signing (pay_sig and signature), payment parameter
construction, server-side order queries, and delivery notifications.

Docs: https://developers.weixin.qq.com/miniprogram/dev/platform-capabilities/business-capabilities/virtual-payment.html
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests


_OUT_TRADE_NO_RE = re.compile(r'^[0-9a-zA-Z\-|*@]{8,32}$')


def calc_pay_sig(uri: str, post_body: str, appkey: str) -> str:
    """Calculate pay_sig: HMAC-SHA256(appkey, uri + '&' + post_body).

    For front-end wx.requestVirtualPayment, uri = 'requestVirtualPayment'.
    For server APIs, uri is the API path (e.g. '/xpay/query_order').
    """
    message = uri + '&' + post_body
    return hmac.new(
        key=appkey.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256,
    ).hexdigest()


def calc_signature(post_body: str, session_key: str) -> str:
    """Calculate user-session signature: HMAC-SHA256(session_key, post_body)."""
    return hmac.new(
        key=session_key.encode('utf-8'),
        msg=post_body.encode('utf-8'),
        digestmod=hashlib.sha256,
    ).hexdigest()


@dataclass
class VirtualPayConfig:
    app_id: str
    offer_id: str
    app_key: str
    env: int = 1  # 0=production, 1=sandbox (default sandbox for safety)
    sandbox_app_key: str = ''
    api_base: str = 'https://api.weixin.qq.com'
    timeout_seconds: float = 10.0

    def is_configured(self) -> bool:
        return bool(self.app_id and self.offer_id and self.app_key)

    @property
    def effective_app_key(self) -> str:
        return self.app_key


def _validate_out_trade_no(order_no: str) -> None:
    if not _OUT_TRADE_NO_RE.match(order_no):
        raise ValueError(
            f'outTradeNo "{order_no}" is invalid: must be 8-32 chars, '
            'only digits/letters/-|*@, cannot start with underscore'
        )


def build_virtual_payment_params(
    config: VirtualPayConfig,
    order_no: str,
    product_id: str,
    price_fen: int,
    session_key: str,
    attach: str = '',
    currency_type: str = 'CNY',
    buy_quantity: int = 1,
) -> dict[str, Any]:
    """Build parameters for wx.requestVirtualPayment (mode=short_series_goods).

    Returns a dict with: mode, signData (JSON string), paySig, signature.
    """
    _validate_out_trade_no(order_no)

    sign_data_dict = {
        'offerId': config.offer_id,
        'buyQuantity': buy_quantity,
        'env': config.env,
        'currencyType': currency_type,
        'productId': product_id,
        'goodsPrice': price_fen,
        'outTradeNo': order_no,
        'attach': attach or order_no,
    }
    sign_data_str = json.dumps(sign_data_dict, separators=(',', ':'))

    pay_sig = calc_pay_sig('requestVirtualPayment', sign_data_str, config.effective_app_key)
    signature = calc_signature(sign_data_str, session_key)

    return {
        'mode': 'short_series_goods',
        'signData': sign_data_str,
        'paySig': pay_sig,
        'signature': signature,
    }


class VirtualPayClient:
    """Server-side client for WeChat Virtual Payment APIs (/xpay/*)."""

    def __init__(self, config: VirtualPayConfig):
        self.config = config

    def is_configured(self) -> bool:
        return self.config.is_configured()

    def _request(
        self,
        *,
        uri: str,
        access_token: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise ValueError('virtual pay config incomplete')
        if not access_token:
            raise ValueError('access_token is required for virtual pay API')

        post_body = json.dumps(body or {}, ensure_ascii=False, separators=(',', ':'))
        pay_sig = calc_pay_sig(uri, post_body, self.config.effective_app_key)

        params: dict[str, str] = {
            'access_token': access_token,
            'pay_sig': pay_sig,
        }

        # Some APIs also need user-session signature
        session_key = (body or {}).get('session_key', '') if body else ''
        if session_key:
            params['signature'] = calc_signature(post_body, session_key)

        response = requests.post(
            url=f'{self.config.api_base}{uri}',
            params=params,
            data=post_body.encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            timeout=self.config.timeout_seconds,
        )
        if response.status_code < 200 or response.status_code >= 300:
            try:
                payload = response.json()
            except Exception:
                payload = {}
            errcode = payload.get('errcode', '')
            errmsg = payload.get('errmsg', '')
            raise ValueError(f'virtual pay API error: {errcode} {errmsg}')
        return response.json() if response.content else {}

    def query_order(
        self,
        *,
        access_token: str,
        order_no: str,
        env: int | None = None,
    ) -> dict[str, Any]:
        """Query order status via POST /xpay/query_order."""
        return self._request(
            uri='/xpay/query_order',
            access_token=access_token,
            body={
                'out_trade_no': order_no,
                'env': env if env is not None else self.config.env,
            },
        )

    def notify_provide_goods(
        self,
        *,
        access_token: str,
        order_no: str,
        env: int | None = None,
    ) -> dict[str, Any]:
        """Notify that goods have been delivered via POST /xpay/notify_provide_goods."""
        return self._request(
            uri='/xpay/notify_provide_goods',
            access_token=access_token,
            body={
                'out_trade_no': order_no,
                'env': env if env is not None else self.config.env,
            },
        )


def build_virtual_pay_config(
    *,
    app_id: str,
    offer_id: str,
    app_key: str,
    env: int,
    sandbox_app_key: str = '',
    api_base: str,
    timeout_seconds: float,
) -> VirtualPayConfig:
    return VirtualPayConfig(
        app_id=app_id,
        offer_id=offer_id,
        app_key=app_key,
        env=env,
        sandbox_app_key=sandbox_app_key,
        api_base=api_base,
        timeout_seconds=timeout_seconds,
    )
