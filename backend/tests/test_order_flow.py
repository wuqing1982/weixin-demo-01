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
from backend.app.security import create_access_token
from backend.app.schemas import MockPaymentCompleteRequest, OrderCreateRequest
from backend.tests.test_auth_api import build_request


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class MockOrderFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_auth_file = Path(self.temp_dir.name) / 'auth.json'
        self.schema_name = f'order_flow_{uuid4().hex[:12]}'
        self.original_auth_store = main.auth_store
        self.original_commerce_store = getattr(main, 'commerce_store', None)
        self.original_debug_header = main.AUTH_ENABLE_DEBUG_USER_HEADER
        self.original_payment_mode = main.PAYMENT_MODE
        self.original_wechat_pay_client = getattr(main, 'wechat_pay_client', None)

        main.auth_store = AuthStore(self.temp_auth_file)
        main.commerce_store = CommerceStore(DATABASE_URL, self.schema_name)
        main.AUTH_ENABLE_DEBUG_USER_HEADER = True
        main.PAYMENT_MODE = 'mock'
        main.auth_store.get_or_create_debug_user('debug_user_order_001')

        main.commerce_store.upsert_product({
            'id': 'product_combo_test',
            'productCode': 'combo_test',
            'productType': 'membership',
            'name': '会员+点数组合包',
            'status': 'active',
        })
        main.commerce_store.upsert_sku({
            'id': 'sku_combo_test',
            'productId': 'product_combo_test',
            'skuCode': 'combo_test_monthly',
            'name': '月卡组合包',
            'billingType': 'monthly',
            'durationDays': 30,
            'status': 'active',
            'listPrice': '49.00',
            'salePrice': '29.90',
        })
        main.commerce_store.replace_sku_benefits('sku_combo_test', [
            {
                'id': 'benefit_combo_member',
                'benefitType': 'membership',
                'benefitValue': 'basic_member',
                'benefitJson': {'durationDays': 30},
            },
            {
                'id': 'benefit_combo_credit',
                'benefitType': 'credits',
                'benefitValue': 'scene_generation_credits',
                'benefitJson': {'creditType': 'scene_generation_credits', 'amount': 15},
            },
        ])

    def tearDown(self):
        main.auth_store = self.original_auth_store
        main.commerce_store = self.original_commerce_store
        main.AUTH_ENABLE_DEBUG_USER_HEADER = self.original_debug_header
        main.PAYMENT_MODE = self.original_payment_mode
        main.wechat_pay_client = self.original_wechat_pay_client
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')
        self.temp_dir.cleanup()

    def test_create_pay_and_grant(self):
        headers = {'X-Debug-User-Id': 'debug_user_order_001'}

        order = main.create_order(
            OrderCreateRequest(skuId='sku_combo_test', quantity=1),
            build_request(method='POST', path='/api/orders', headers=headers),
        )['data']
        self.assertEqual(order['status'], 'pending')
        self.assertEqual(order['paymentStatus'], 'pending')

        pay_result = main.create_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/pay", headers=headers),
        )['data']
        self.assertEqual(pay_result['paymentMode'], 'mock')
        self.assertTrue(pay_result['paymentId'])

        paid = main.complete_mock_order_payment(
            order['orderId'],
            MockPaymentCompleteRequest(paymentId=pay_result['paymentId']),
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/mock-pay-success", headers=headers),
        )['data']
        self.assertEqual(paid['order']['status'], 'paid')
        self.assertEqual(paid['order']['paymentStatus'], 'success')

        me = main.get_me(build_request(path='/api/me', headers=headers))['data']
        self.assertTrue(me['memberSummary']['isActive'])
        self.assertEqual(me['creditSummary']['sceneGenerateBalance'], 15)

        orders = main.list_orders(build_request(path='/api/orders', headers=headers))['data']['list']
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['status'], 'paid')

    def test_real_wechat_pay_create_and_sync(self):
        user = main.auth_store.get_or_create_wechat_user(
            provider_uid='openid_real_pay_001',
            union_id='union_real_pay_001',
            profile={'displayName': '真实支付用户'},
            session_key_encrypted='session_key_encrypted',
        )
        access_token, _ = create_access_token(user['id'], 'session_real_pay_001', role='user')
        headers = {'Authorization': f'Bearer {access_token}'}

        class FakeWechatPayClient:
            class _Config:
                def can_verify_callbacks(self):
                    return True

            def __init__(self):
                self.config = self._Config()
                self.created = []
                self.queried = []

            def is_configured(self):
                return True

            def create_jsapi_transaction(self, *, out_trade_no, description, total_fen, payer_openid):
                self.created.append({
                    'out_trade_no': out_trade_no,
                    'description': description,
                    'total_fen': total_fen,
                    'payer_openid': payer_openid,
                })
                return {'prepay_id': 'wx_prepay_test_001'}

            def build_miniapp_request_payment(self, prepay_id):
                return {
                    'timeStamp': '1710000000',
                    'nonceStr': 'nonce_test',
                    'package': f'prepay_id={prepay_id}',
                    'signType': 'RSA',
                    'paySign': 'sign_test',
                }

            def query_order_by_out_trade_no(self, out_trade_no):
                self.queried.append(out_trade_no)
                return {
                    'trade_state': 'SUCCESS',
                    'transaction_id': '4200000000000001',
                    'out_trade_no': out_trade_no,
                }

        main.PAYMENT_MODE = 'wechat_pay'
        main.wechat_pay_client = FakeWechatPayClient()

        order = main.create_order(
            OrderCreateRequest(skuId='sku_combo_test', quantity=1),
            build_request(method='POST', path='/api/orders', headers=headers),
        )['data']

        pay_result = main.create_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/pay", headers=headers),
        )['data']
        self.assertEqual(pay_result['paymentMode'], 'wechat_pay')
        self.assertEqual(pay_result['requestPayment']['package'], 'prepay_id=wx_prepay_test_001')
        self.assertEqual(main.wechat_pay_client.created[0]['payer_openid'], 'openid_real_pay_001')

        synced = main.sync_order_payment(
            order['orderId'],
            build_request(method='POST', path=f"/api/orders/{order['orderId']}/payment-sync", headers=headers),
        )['data']
        self.assertEqual(synced['tradeState'], 'SUCCESS')
        self.assertEqual(synced['order']['status'], 'paid')

        me = main.get_me(build_request(path='/api/me', headers=headers))['data']
        self.assertTrue(me['memberSummary']['isActive'])
        self.assertEqual(me['creditSummary']['sceneGenerateBalance'], 15)


if __name__ == '__main__':
    unittest.main()
