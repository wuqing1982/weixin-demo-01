import unittest
from uuid import uuid4

from backend.app.commerce_store import CommerceStore
from backend.app.postgres import connect_postgres


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class CommerceStoreTests(unittest.TestCase):
    def setUp(self):
        self.schema_name = f'commerce_{uuid4().hex[:12]}'
        self.store = CommerceStore(DATABASE_URL, self.schema_name)

    def tearDown(self):
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')

    def test_products_and_skus_round_trip(self):
        self.store.upsert_product({
            'id': 'product_membership_test',
            'productCode': 'membership_test',
            'productType': 'membership',
            'name': '测试会员',
            'status': 'active',
            'sortOrder': 10,
        })
        self.store.upsert_sku({
            'id': 'sku_membership_test_monthly',
            'productId': 'product_membership_test',
            'skuCode': 'membership_test_monthly',
            'name': '测试月卡',
            'billingType': 'monthly',
            'durationDays': 30,
            'status': 'active',
            'listPrice': '39.00',
            'salePrice': '19.90',
        })
        self.store.replace_sku_benefits('sku_membership_test_monthly', [
            {
                'id': 'benefit_membership_test_monthly',
                'benefitType': 'membership',
                'benefitValue': 'basic_member',
                'benefitJson': {'durationDays': 30},
            },
        ])

        products = self.store.list_products('membership')
        skus = self.store.list_product_skus('product_membership_test')

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['productCode'], 'membership_test')
        self.assertEqual(len(skus), 1)
        self.assertEqual(skus[0]['benefits'][0]['benefitType'], 'membership')

    def test_membership_and_credit_summary(self):
        self.store.grant_entitlement({
            'id': 'entitlement_test_001',
            'userId': 'user_test_001',
            'sourceType': 'system_grant',
            'entitlementType': 'membership',
            'entitlementCode': 'basic_member',
            'status': 'active',
            'startsAt': '2026-01-01T00:00:00Z',
            'expiresAt': '2099-01-01T00:00:00Z',
        })
        self.store.set_credit_account({
            'id': 'credit_account_test_001',
            'userId': 'user_test_001',
            'creditType': 'scene_generation_credits',
            'balance': 12,
            'frozenBalance': 1,
        })

        membership = self.store.get_membership_summary('user_test_001')
        credits = self.store.get_credit_summary('user_test_001')

        self.assertTrue(membership['isActive'])
        self.assertEqual(membership['entitlementCode'], 'basic_member')
        self.assertEqual(credits['sceneGenerateBalance'], 12)


if __name__ == '__main__':
    unittest.main()
