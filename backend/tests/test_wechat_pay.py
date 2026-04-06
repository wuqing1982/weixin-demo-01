"""Tests for WeChat Pay v3 client utilities."""
import pytest
from decimal import Decimal

from app.wechat_pay import _to_fen, _normalize_json, WechatPayConfig


class TestToFen:
    def test_integer_amount(self):
        assert _to_fen(1) == 100

    def test_decimal_amount(self):
        assert _to_fen('0.01') == 1

    def test_float_amount(self):
        assert _to_fen(12.34) == 1234

    def test_zero(self):
        assert _to_fen(0) == 0
        assert _to_fen('0') == 0
        assert _to_fen(None) == 0

    def test_large_amount(self):
        assert _to_fen('999.99') == 99999

    def test_rounding(self):
        assert _to_fen('1.005') == 101
        assert _to_fen('1.999') == 200


class TestNormalizeJson:
    def test_empty_dict(self):
        assert _normalize_json({}) == '{}'
        assert _normalize_json(None) == '{}'

    def test_sorted_keys(self):
        result = _normalize_json({'b': 2, 'a': 1})
        assert '"a"' in result

    def test_no_spaces(self):
        result = _normalize_json({'key': 'value'})
        assert ' ' not in result

    def test_chinese_chars(self):
        result = _normalize_json({'name': '测试'})
        assert '测试' in result


class TestWechatPayConfig:
    def test_is_configured_missing_fields(self):
        config = WechatPayConfig(
            app_id='', mch_id='', api_v3_key='',
            mch_serial_no='', mch_private_key_path='',
            platform_cert_path='', platform_serial_no='',
            notify_url='', api_base='',
        )
        assert not config.is_configured()

    def test_is_configured_all_present(self):
        config = WechatPayConfig(
            app_id='wx123', mch_id='1234', api_v3_key='key',
            mch_serial_no='serial', mch_private_key_path='/path/key.pem',
            platform_cert_path='/path/cert.pem', platform_serial_no='pserial',
            notify_url='https://example.com/notify', api_base='https://api.mch.weixin.qq.com',
        )
        assert config.is_configured()

    def test_default_currency(self):
        config = WechatPayConfig(
            app_id='', mch_id='', api_v3_key='',
            mch_serial_no='', mch_private_key_path='',
            platform_cert_path='', platform_serial_no='',
            notify_url='', api_base='',
        )
        assert config.currency == 'CNY'

    def test_can_verify_callbacks_no_cert(self):
        config = WechatPayConfig(
            app_id='', mch_id='', api_v3_key='',
            mch_serial_no='', mch_private_key_path='',
            platform_cert_path='/nonexistent/cert.pem', platform_serial_no='',
            notify_url='', api_base='',
        )
        assert not config.can_verify_callbacks()
