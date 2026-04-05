import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

os.environ['AUTH_STORE_BACKEND'] = 'json'
os.environ['COMMERCE_STORE_BACKEND'] = 'disabled'

from backend.app import main
from backend.app.auth_store import AuthStore
from backend.app.commerce_store import CommerceStore
from backend.app.postgres import connect_postgres
from backend.tests.test_auth_api import build_request


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class CommerceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_auth_file = Path(self.temp_dir.name) / 'auth.json'
        self.schema_name = f'commerce_api_{uuid4().hex[:12]}'
        self.original_auth_store = main.auth_store
        self.original_commerce_store = getattr(main, 'commerce_store', None)
        self.original_debug_header = main.AUTH_ENABLE_DEBUG_USER_HEADER

        main.auth_store = AuthStore(self.temp_auth_file)
        main.commerce_store = CommerceStore(DATABASE_URL, self.schema_name)
        main.AUTH_ENABLE_DEBUG_USER_HEADER = True
        main.auth_store.get_or_create_debug_user('debug_user_api_001')

        main.commerce_store.upsert_product({
            'id': 'product_credit_test',
            'productCode': 'credit_test',
            'productType': 'credit_pack',
            'name': '测试点数包',
            'status': 'active',
        })
        main.commerce_store.upsert_sku({
            'id': 'sku_credit_test_10',
            'productId': 'product_credit_test',
            'skuCode': 'credit_test_10',
            'name': '10 次点数',
            'billingType': 'one_time',
            'status': 'active',
            'listPrice': '19.90',
            'salePrice': '9.90',
        })
        main.commerce_store.replace_sku_benefits('sku_credit_test_10', [
            {
                'id': 'benefit_credit_test_10',
                'benefitType': 'credits',
                'benefitValue': 'scene_generation_credits',
                'benefitJson': {'amount': 10},
            },
        ])
        main.commerce_store.grant_entitlement({
            'id': 'entitlement_api_001',
            'userId': 'debug_user_api_001',
            'sourceType': 'system_grant',
            'entitlementType': 'membership',
            'entitlementCode': 'basic_member',
            'status': 'active',
            'startsAt': '2026-01-01T00:00:00Z',
            'expiresAt': '2099-01-01T00:00:00Z',
        })
        main.commerce_store.set_credit_account({
            'id': 'credit_api_001',
            'userId': 'debug_user_api_001',
            'creditType': 'scene_generation_credits',
            'balance': 18,
            'frozenBalance': 0,
        })

    def tearDown(self):
        main.auth_store = self.original_auth_store
        main.commerce_store = self.original_commerce_store
        main.AUTH_ENABLE_DEBUG_USER_HEADER = self.original_debug_header
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')
        self.temp_dir.cleanup()

    def test_products_and_me_endpoints(self):
        products = main.list_products(build_request(path='/api/products'), '')['data']['list']
        product_detail = main.get_product('product_credit_test', build_request(path='/api/products/product_credit_test'))['data']
        skus = main.list_product_skus('product_credit_test')['data']['list']
        me = main.get_me(build_request(path='/api/me', headers={'X-Debug-User-Id': 'debug_user_api_001'}))['data']
        membership = main.get_my_membership(build_request(path='/api/me/membership', headers={'X-Debug-User-Id': 'debug_user_api_001'}))['data']
        credits = main.get_my_credits(build_request(path='/api/me/credits', headers={'X-Debug-User-Id': 'debug_user_api_001'}))['data']
        entitlements = main.get_my_entitlements(build_request(path='/api/me/entitlements', headers={'X-Debug-User-Id': 'debug_user_api_001'}))['data']['list']

        self.assertEqual(len(products), 1)
        self.assertEqual(product_detail['productCode'], 'credit_test')
        self.assertEqual(skus[0]['benefits'][0]['benefitType'], 'credits')
        self.assertTrue(me['memberSummary']['isActive'])
        self.assertEqual(me['creditSummary']['sceneGenerateBalance'], 18)
        self.assertTrue(membership['isActive'])
        self.assertEqual(credits['sceneGenerateBalance'], 18)
        self.assertEqual(entitlements[0]['entitlementCode'], 'basic_member')


if __name__ == '__main__':
    unittest.main()
