"""Integration tests for Virtual Payment (xpay) order flow.

Covers:
- Payment initialization (POST /orders/{id}/pay with PAYMENT_MODE=virtual_pay)
- Payment sync (POST /orders/{id}/payment-sync)
- Delivery notification callback (POST /payments/virtual/notify)
"""
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

os.environ['AUTH_STORE_BACKEND'] = 'json'
os.environ['COMMERCE_STORE_BACKEND'] = 'disabled'
os.environ['PAYMENT_MODE'] = 'mock'

from backend.app import main
from backend.app.auth_store import AuthStore
from backend.app.commerce_store import CommerceStore
from backend.app.postgres import connect_postgres
from backend.app.security import create_access_token, encrypt_wechat_session_key
from backend.app.schemas import OrderCreateRequest
from backend.app.virtual_pay import VirtualPayConfig
from backend.tests.test_auth_api import build_request


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class VirtualPayOrderFlowTests(unittest.TestCase):
    """Test the full virtual payment order lifecycle."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_auth_file = Path(self.temp_dir.name) / 'auth.json'
        self.schema_name = f'vpay_flow_{uuid4().hex[:12]}'
        self.original_auth_store = main.auth_store
        self.original_commerce_store = getattr(main, 'commerce_store', None)
        self.original_debug_header = main.AUTH_ENABLE_DEBUG_USER_HEADER
        self.original_payment_mode = main.PAYMENT_MODE
        self.original_virtual_pay_client = getattr(main, 'virtual_pay_client', None)

        main.auth_store = AuthStore(self.temp_auth_file)
        main.commerce_store = CommerceStore(DATABASE_URL, self.schema_name)
        main.AUTH_ENABLE_DEBUG_USER_HEADER = True

        # Setup virtual pay client with test config
        main.virtual_pay_client = type('FakeVirtualPayClient', (), {
            'config': VirtualPayConfig(
                app_id='wx_test_app',
                offer_id='offer_test_001',
                app_key='test_app_key_abc123',
                env=1,
            ),
            'is_configured': lambda self: True,
        })()

        # Create test product and SKU
        main.commerce_store.upsert_product({
            'id': 'product_vp_test',
            'productCode': 'vp_test',
            'productType': 'membership',
            'name': '虚拟支付测试会员',
            'status': 'active',
        })
        main.commerce_store.upsert_sku({
            'id': 'sku_vp_membership',
            'productId': 'product_vp_test',
            'skuCode': 'vp_membership_pro',
            'name': 'Pro年度会员',
            'billingType': 'yearly',
            'durationDays': 365,
            'status': 'active',
            'listPrice': '39.90',
            'salePrice': '39.90',
        })
        main.commerce_store.replace_sku_benefits('sku_vp_membership', [
            {
                'id': 'benefit_vp_member',
                'benefitType': 'membership',
                'benefitValue': 'pro',
                'benefitJson': {'durationDays': 365},
            },
            {
                'id': 'benefit_vp_credit',
                'benefitType': 'credits',
                'benefitValue': 'scene_generation_credits',
                'benefitJson': {'creditType': 'scene_generation_credits', 'amount': 30},
            },
        ])

        # Create a WeChat user with session_key for virtual payment
        self.vp_user = main.auth_store.get_or_create_wechat_user(
            provider_uid='openid_vp_test_001',
            union_id='union_vp_test_001',
            profile={'displayName': 'VP测试用户'},
            session_key_encrypted=encrypt_wechat_session_key('mock_session_key_vp'),
        )
        self.vp_access_token, _ = create_access_token(
            self.vp_user['id'], 'session_vp_test', role='user',
        )
        self.vp_headers = {'Authorization': f'Bearer {self.vp_access_token}'}

    def tearDown(self):
        main.auth_store = self.original_auth_store
        main.commerce_store = self.original_commerce_store
        main.AUTH_ENABLE_DEBUG_USER_HEADER = self.original_debug_header
        main.PAYMENT_MODE = self.original_payment_mode
        main.virtual_pay_client = self.original_virtual_pay_client
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')
        self.temp_dir.cleanup()

    def test_virtual_pay_init_returns_correct_params(self):
        """POST /orders/{id}/pay with virtual_pay mode returns wx.requestVirtualPayment params."""
        main.PAYMENT_MODE = 'virtual_pay'
        headers = self.vp_headers

        # Create order
        order = main.create_order(
            OrderCreateRequest(skuId='sku_vp_membership', quantity=1),
            build_request(method='POST', path='/api/orders', headers=headers),
        )['data']
        self.assertEqual(order['status'], 'pending')

        # Initiate virtual payment
        pay_result = main.create_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/pay", headers=headers),
        )['data']
        self.assertEqual(pay_result['paymentMode'], 'virtual_pay')
        self.assertTrue(pay_result['paymentId'])

        # Verify requestPayment contains wx.requestVirtualPayment params
        rp = pay_result['requestPayment']
        self.assertEqual(rp['mode'], 'short_series_goods')
        self.assertTrue(rp['paySig'])
        self.assertTrue(rp['signature'])
        self.assertTrue(rp['signData'])

        import json
        sign_data = json.loads(rp['signData'])
        self.assertEqual(sign_data['productId'], 'sku_vp_membership')
        self.assertTrue(sign_data['goodsPrice'] > 0)  # 3990 fen for 39.90 CNY
        self.assertEqual(sign_data['env'], 1)  # sandbox
        self.assertEqual(sign_data['currencyType'], 'CNY')

    def test_virtual_pay_sync_completes_order(self):
        """POST /orders/{id}/payment-sync with virtual_pay marks order as paid and grants benefits."""
        main.PAYMENT_MODE = 'virtual_pay'
        headers = self.vp_headers

        order = main.create_order(
            OrderCreateRequest(skuId='sku_vp_membership', quantity=1),
            build_request(method='POST', path='/api/orders', headers=headers),
        )['data']

        main.create_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/pay", headers=headers),
        )

        # Simulate payment sync (front-end calls after wx.requestVirtualPayment success)
        synced = main.sync_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/payment-sync", headers=headers),
        )['data']
        self.assertEqual(synced['tradeState'], 'SUCCESS')
        self.assertEqual(synced['order']['status'], 'paid')

        # Verify benefits granted
        me = main.get_me(build_request(path='/api/me', headers=headers))['data']
        self.assertTrue(me['memberSummary']['isActive'])
        self.assertEqual(me['creditSummary']['sceneGenerateBalance'], 30)

    def test_virtual_pay_notify_callback(self):
        """POST /payments/virtual/notify processes XML delivery notification."""
        main.PAYMENT_MODE = 'virtual_pay'
        headers = self.vp_headers

        order = main.create_order(
            OrderCreateRequest(skuId='sku_vp_membership', quantity=1),
            build_request(method='POST', path='/api/orders', headers=headers),
        )['data']
        order_no = order['orderNo']

        # Initiate payment first (creates payment record)
        main.create_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/pay", headers=headers),
        )

        # Simulate XML callback from WeChat
        xml_body = f'''<xml>
<ToUserName>gh_test</ToUserName>
<FromUserName>system</FromUserName>
<CreateTime>1710000000</CreateTime>
<MsgType>event</MsgType>
<Event>xpay_goods_deliver_notify</Event>
<OpenId>o_test_openid</OpenId>
<OutTradeNo>{order_no}</OutTradeNo>
<Env>1</Env>
<WeChatPayInfo>
<MchOrderNo>mch_order_test</MchOrderNo>
<TransactionId>wx_trans_test_001</TransactionId>
<PaidTime>1710000000</PaidTime>
</WeChatPayInfo>
<GoodsInfo>
<ProductId>sku_vp_membership</ProductId>
<Quantity>1</Quantity>
<OrigPrice>3990</OrigPrice>
<ActualPrice>3990</ActualPrice>
<Attach></Attach>
</GoodsInfo>
</xml>'''

        from fastapi import Request
        scope = {
            'type': 'http',
            'http_version': '1.1',
            'method': 'POST',
            'scheme': 'https',
            'path': '/api/payments/virtual/notify',
            'raw_path': b'/api/payments/virtual/notify',
            'query_string': b'',
            'headers': [],
            'client': ('127.0.0.1', 12345),
            'server': ('testserver', 443),
        }
        # We need to provide the body via receive
        async def receive():
            return {'type': 'http.request', 'body': xml_body.encode('utf-8')}

        notify_request = Request(scope, receive)

        import asyncio
        response = asyncio.get_event_loop().run_until_complete(
            main.handle_virtual_payment_notify(notify_request)
        )

        # Response should be XML with ErrCode=0
        self.assertIn('ErrCode>0', response.body.decode('utf-8'))

        # Verify order is now paid
        updated_order = main.get_order(
            order['orderId'],
            build_request(path=f"/api/orders/{order['orderId']}", headers=headers),
        )['data']
        self.assertEqual(updated_order['status'], 'paid')

    def test_virtual_pay_idempotent_sync(self):
        """Multiple payment-sync calls should be idempotent."""
        main.PAYMENT_MODE = 'virtual_pay'
        headers = self.vp_headers

        order = main.create_order(
            OrderCreateRequest(skuId='sku_vp_membership', quantity=1),
            build_request(method='POST', path='/api/orders', headers=headers),
        )['data']

        main.create_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/pay", headers=headers),
        )

        # Sync twice
        r1 = main.sync_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/payment-sync", headers=headers),
        )['data']
        self.assertEqual(r1['order']['status'], 'paid')

        r2 = main.sync_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/payment-sync", headers=headers),
        )['data']
        self.assertEqual(r2['order']['status'], 'paid')

        # Credits should only be granted once
        me = main.get_me(build_request(path='/api/me', headers=headers))['data']
        self.assertEqual(me['creditSummary']['sceneGenerateBalance'], 30)


if __name__ == '__main__':
    unittest.main()
