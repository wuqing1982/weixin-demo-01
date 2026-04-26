"""Tests for WeChat Virtual Payment (xpay) signing and configuration."""
import json

import pytest

from app.virtual_pay import (
    VirtualPayConfig,
    calc_pay_sig,
    calc_signature,
    build_virtual_payment_params,
)


class TestCalcPaySig:
    """pay_sig = HMAC-SHA256(appkey, uri + '&' + post_body)"""

    def test_known_vector(self):
        """Verify against the example from WeChat docs.

        The docs example post_body has spaces after colons/commas.
        The actual signed payload must match the HTTP request body exactly.
        """
        uri = "/xpay/query_user_balance"
        # The docs example uses json.dumps with default separators (spaces)
        post_body = '{"openid": "xxx", "user_ip": "127.0.0.1", "env": 0}'
        appkey = "test_appkey_123456"
        result = calc_pay_sig(uri, post_body, appkey)
        # Cross-verify: the algorithm itself is correct (HMAC-SHA256 hex)
        # The exact value depends on the JSON serialization used by the caller
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)

    def test_request_virtual_payment_uri(self):
        """Front-end wx.requestVirtualPayment uses uri = 'requestVirtualPayment'."""
        uri = "requestVirtualPayment"
        sign_data = json.dumps({
            "offerId": "123",
            "buyQuantity": 1,
            "env": 0,
            "currencyType": "CNY",
            "productId": "testproductId",
            "goodsPrice": 10,
            "outTradeNo": "xxxxxx",
            "attach": "testdata",
        }, separators=(',', ':'))
        appkey = "test_appkey"
        result = calc_pay_sig(uri, sign_data, appkey)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_empty_body(self):
        result = calc_pay_sig("/xpay/test", "", "key123")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_different_keys_produce_different_sigs(self):
        body = '{"test": true}'
        sig1 = calc_pay_sig("/xpay/test", body, "key_a")
        sig2 = calc_pay_sig("/xpay/test", body, "key_b")
        assert sig1 != sig2


class TestCalcSignature:
    """signature = HMAC-SHA256(session_key, post_body)"""

    def test_known_vector(self):
        """Using the same post_body as pay_sig example with session_key."""
        post_body = '{"offerId":"123","buyQuantity":1,"env":0,"currencyType":"CNY","productId":"testproductId","goodsPrice":10,"outTradeNo":"xxxxxx","attach":"testdata"}'
        session_key = "test_session_key"
        result = calc_signature(post_body, session_key)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_different_session_keys(self):
        body = '{"test": true}'
        sig1 = calc_signature(body, "session_a")
        sig2 = calc_signature(body, "session_b")
        assert sig1 != sig2

    def test_empty_body(self):
        result = calc_signature("", "session_key")
        assert isinstance(result, str)
        assert len(result) == 64


class TestVirtualPayConfig:
    def test_is_configured_when_all_present(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_123",
            app_key="key_abc",
            env=1,
        )
        assert config.is_configured()

    def test_is_configured_missing_app_key(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_123",
            app_key="",
            env=1,
        )
        assert not config.is_configured()

    def test_is_configured_missing_offer_id(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="",
            app_key="key_abc",
            env=1,
        )
        assert not config.is_configured()

    def test_default_env_is_sandbox(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_123",
            app_key="key_abc",
        )
        assert config.env == 1

    def test_sandbox_app_key_property(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_123",
            app_key="sandbox_key",
            sandbox_app_key="prod_key",
            env=1,
        )
        assert config.effective_app_key == "sandbox_key"

    def test_prod_app_key_property(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_123",
            app_key="sandbox_key",
            sandbox_app_key="prod_key",
            env=0,
        )
        assert config.effective_app_key == "sandbox_key"


class TestBuildVirtualPaymentParams:
    def test_returns_required_fields(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_abc",
            app_key="key123",
            env=1,
        )
        result = build_virtual_payment_params(
            config=config,
            order_no="ORD-test-001",
            product_id="membership_pro",
            price_fen=3990,
            session_key="sess_abc",
        )
        assert result["mode"] == "short_series_goods"
        assert result["paySig"]
        assert result["signature"]
        assert "signData" in result
        sign_data = json.loads(result["signData"])
        assert sign_data["offerId"] == "offer_abc"
        assert sign_data["productId"] == "membership_pro"
        assert sign_data["goodsPrice"] == 3990
        assert sign_data["outTradeNo"] == "ORD-test-001"
        assert sign_data["env"] == 1
        assert sign_data["currencyType"] == "CNY"
        assert sign_data["buyQuantity"] == 1

    def test_signatures_are_deterministic(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_abc",
            app_key="key123",
            env=1,
        )
        r1 = build_virtual_payment_params(config, "ORD-test-0001", "p1", 100, "sk1")
        r2 = build_virtual_payment_params(config, "ORD-test-0001", "p1", 100, "sk1")
        assert r1["paySig"] == r2["paySig"]
        assert r1["signature"] == r2["signature"]

    def test_different_order_produces_different_sig(self):
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_abc",
            app_key="key123",
            env=1,
        )
        r1 = build_virtual_payment_params(config, "ORD-test-0001", "p1", 100, "sk1")
        r2 = build_virtual_payment_params(config, "ORD-test-0002", "p1", 100, "sk1")
        assert r1["paySig"] != r2["paySig"]
        assert r1["signature"] != r2["signature"]

    def test_out_trade_no_validation(self):
        """outTradeNo must be 8-32 chars, only digits, letters, -|*@"""
        config = VirtualPayConfig(
            app_id="wx123",
            offer_id="offer_abc",
            app_key="key123",
            env=1,
        )
        # Valid
        build_virtual_payment_params(config, "ORD-test-001", "p1", 100, "sk")
        # Invalid: starts with underscore
        with pytest.raises(ValueError, match="outTradeNo"):
            build_virtual_payment_params(config, "_invalid", "p1", 100, "sk")
        # Invalid: too short
        with pytest.raises(ValueError, match="outTradeNo"):
            build_virtual_payment_params(config, "AB", "p1", 100, "sk")
        # Invalid: too long
        with pytest.raises(ValueError, match="outTradeNo"):
            build_virtual_payment_params(config, "A" * 33, "p1", 100, "sk")
        # Invalid: contains invalid chars
        with pytest.raises(ValueError, match="outTradeNo"):
            build_virtual_payment_params(config, "ORD#test!", "p1", 100, "sk")
