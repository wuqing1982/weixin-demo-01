import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

os.environ['AUTH_STORE_BACKEND'] = 'json'
os.environ['COMMERCE_STORE_BACKEND'] = 'disabled'
os.environ['PAYMENT_MODE'] = 'mock'

from fastapi import HTTPException

from backend.app import main
from backend.app.auth_store import AuthStore
from backend.app.commerce_store import CommerceStore
from backend.app.postgres import connect_postgres
from backend.app.scene_store import SceneStore
from backend.app.security import create_access_token
from backend.app.schemas import AdminLoginRequest, AdminProductRequest, AdminPublicSceneRequest, AdminSkuRequest
from backend.app.task_store import TaskStore
from backend.tests.test_auth_api import build_request


DATABASE_URL = 'postgresql://weixin_saas:hq425771@localhost:5432/weixin_saas'


class AdminApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_auth_file = Path(self.temp_dir.name) / 'auth.json'
        self.temp_tasks_file = Path(self.temp_dir.name) / 'tasks.json'
        self.temp_public_scenes_file = Path(self.temp_dir.name) / 'scenes.json'
        self.schema_name = f'admin_api_{uuid4().hex[:12]}'

        self.original_auth_store = main.auth_store
        self.original_commerce_store = getattr(main, 'commerce_store', None)
        self.original_task_store = main.task_store
        self.original_public_store = main.public_store
        self.original_admin_enabled = main.ADMIN_DASHBOARD_ENABLED
        self.original_admin_username = main.ADMIN_DASHBOARD_USERNAME
        self.original_admin_password = main.ADMIN_DASHBOARD_PASSWORD

        main.auth_store = AuthStore(self.temp_auth_file)
        main.commerce_store = CommerceStore(DATABASE_URL, self.schema_name)
        main.task_store = TaskStore(self.temp_tasks_file)
        main.public_store = SceneStore(self.temp_public_scenes_file)
        main.ADMIN_DASHBOARD_ENABLED = True
        main.ADMIN_DASHBOARD_USERNAME = 'admin_test'
        main.ADMIN_DASHBOARD_PASSWORD = 'pass_test'

        user = main.auth_store.get_or_create_debug_user('debug_user_admin_001')
        main.commerce_store.upsert_product({
            'id': 'product_admin_membership',
            'productCode': 'membership_annual',
            'productType': 'membership',
            'name': '包年会员',
            'status': 'active',
        })
        main.commerce_store.upsert_sku({
            'id': 'sku_admin_membership_annual',
            'productId': 'product_admin_membership',
            'skuCode': 'membership_annual',
            'name': '年度会员',
            'billingType': 'yearly',
            'durationDays': 365,
            'status': 'active',
            'listPrice': '299.00',
            'salePrice': '199.00',
        })
        main.commerce_store.replace_sku_benefits('sku_admin_membership_annual', [
            {
                'id': 'benefit_admin_member',
                'benefitType': 'membership',
                'benefitValue': 'basic_member',
                'benefitJson': {'durationDays': 365},
            },
        ])
        order = main.commerce_store.create_order(user_id=user['id'], sku_id='sku_admin_membership_annual', quantity=1)
        payment = main.commerce_store.create_payment_intent(order_id=order['orderId'], user_id=user['id'], payment_mode='mock')
        main.commerce_store.complete_mock_payment(
            order_id=order['orderId'],
            user_id=user['id'],
            payment_id=payment['paymentId'],
        )

        main.task_store.create_task(owner_id=user['id'], payload={'uploadId': 'upload_001', 'title': '厨房场景'})
        task = main.task_store.create_task(owner_id=user['id'], payload={'uploadId': 'upload_002', 'title': '客厅场景'})
        main.task_store.update_task(task['taskId'], status='done', step='finished', progress=100, sceneId='scene_done_001')

    def tearDown(self):
        main.auth_store = self.original_auth_store
        main.commerce_store = self.original_commerce_store
        main.task_store = self.original_task_store
        main.public_store = self.original_public_store
        main.ADMIN_DASHBOARD_ENABLED = self.original_admin_enabled
        main.ADMIN_DASHBOARD_USERNAME = self.original_admin_username
        main.ADMIN_DASHBOARD_PASSWORD = self.original_admin_password
        with connect_postgres(DATABASE_URL, 'public') as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'drop schema if exists {self.schema_name} cascade')
        self.temp_dir.cleanup()

    def _login_header(self):
        response = main.admin_auth_login(AdminLoginRequest(username='admin_test', password='pass_test'))['data']
        return {'Authorization': f"Bearer {response['accessToken']}"}

    def _user_access_token(self, user_id: str, *, role: str = 'user') -> str:
        token, _ = create_access_token(user_id, 'session_test_user_role', role=role)
        return token

    def test_admin_login_rejects_invalid_password(self):
        with self.assertRaises(HTTPException):
            main.admin_auth_login(AdminLoginRequest(username='admin_test', password='bad_password'))

    def test_admin_endpoints_return_dashboard_data(self):
        headers = self._login_header()

        overview = main.admin_overview(build_request(path='/api/admin/overview', headers=headers))['data']
        users = main.admin_list_users(build_request(path='/api/admin/users', headers=headers), limit=20)['data']['list']
        products = main.admin_list_products(build_request(path='/api/admin/products', headers=headers))['data']['list']
        orders = main.admin_list_orders(build_request(path='/api/admin/orders', headers=headers), limit=20)['data']['list']
        tasks = main.admin_list_tasks(build_request(path='/api/admin/tasks', headers=headers), limit=20)['data']['list']

        self.assertGreaterEqual(overview['userCount'], 1)
        self.assertGreaterEqual(overview['paidOrderCount'], 1)
        self.assertGreaterEqual(overview['activeMemberCount'], 1)
        self.assertEqual(users[0]['id'], 'debug_user_admin_001')
        self.assertEqual(products[0]['productCode'], 'membership_annual')
        self.assertEqual(products[0]['skus'][0]['skuCode'], 'membership_annual')
        self.assertEqual(orders[0]['status'], 'paid')
        self.assertIn('done', {task['status'] for task in tasks})

    def test_admin_mutations_and_details(self):
        headers = self._login_header()
        request = build_request(path='/api/admin/users', headers=headers)

        user_detail = main.admin_get_user_detail('debug_user_admin_001', request)['data']
        self.assertEqual(user_detail['id'], 'debug_user_admin_001')
        self.assertEqual(user_detail['orders'][0]['status'], 'paid')

        blocked = main.admin_block_user('debug_user_admin_001', request)['data']
        self.assertEqual(blocked['status'], 'blocked')
        unblocked = main.admin_unblock_user('debug_user_admin_001', request)['data']
        self.assertEqual(unblocked['status'], 'active')

        created_product = main.admin_create_product(
            AdminProductRequest(
                productCode='credit_pack_99',
                productType='credit_pack',
                name='99 点数包',
                subtitle='测试商品',
                description='测试商品描述',
                status='draft',
                sortOrder=1,
            ),
            build_request(method='POST', path='/api/admin/products', headers=headers),
        )['data']
        self.assertEqual(created_product['productCode'], 'credit_pack_99')

        published = main.admin_publish_product(
            created_product['productId'],
            build_request(method='POST', path='/api/admin/products/publish', headers=headers),
        )['data']
        self.assertEqual(published['status'], 'active')

        created_sku = main.admin_create_sku(
            AdminSkuRequest(
                productId=created_product['productId'],
                skuCode='credit_pack_99_once',
                name='99 点点包',
                billingType='one_time',
                durationDays=None,
                status='active',
                listPrice='99.00',
                salePrice='49.00',
                benefits=[{
                    'benefitType': 'credits',
                    'benefitValue': 'scene_generation_credits',
                    'benefitJson': {'amount': 99},
                }],
            ),
            build_request(method='POST', path='/api/admin/skus', headers=headers),
        )['data']
        self.assertEqual(created_sku['skuCode'], 'credit_pack_99_once')

        updated_sku = main.admin_update_sku(
            created_sku['skuId'],
            AdminSkuRequest(
                productId=created_product['productId'],
                skuCode='credit_pack_99_once',
                name='99 点点包升级',
                billingType='one_time',
                durationDays=None,
                status='active',
                listPrice='99.00',
                salePrice='39.00',
                benefits=[{
                    'benefitType': 'credits',
                    'benefitValue': 'scene_generation_credits',
                    'benefitJson': {'amount': 120},
                }],
            ),
            build_request(method='PUT', path='/api/admin/skus/update', headers=headers),
        )['data']
        self.assertEqual(updated_sku['name'], '99 点点包升级')

        order_detail = main.admin_get_order(
            main.admin_list_orders(build_request(path='/api/admin/orders', headers=headers), limit=20)['data']['list'][0]['orderId'],
            build_request(path='/api/admin/orders/detail', headers=headers),
        )['data']
        self.assertEqual(order_detail['status'], 'paid')

        task_id = main.admin_list_tasks(build_request(path='/api/admin/tasks', headers=headers), limit=20)['data']['list'][0]['taskId']
        retried = main.admin_retry_task(task_id, build_request(method='POST', path='/api/admin/tasks/retry', headers=headers))['data']
        self.assertEqual(retried['status'], 'queued')

        created_scene = main.admin_create_public_scene(
            AdminPublicSceneRequest(
                title='测试公共场景',
                category='test',
                visibility='public',
                sceneType='public',
                backgroundPath='/assets/test/background.jpg',
                coverPath='/assets/test/cover.jpg',
            ),
            build_request(method='POST', path='/api/admin/public-scenes', headers=headers),
        )['data']
        self.assertEqual(created_scene['title'], '测试公共场景')

        updated_scene = main.admin_update_public_scene(
            created_scene['sceneId'],
            AdminPublicSceneRequest(
                title='测试公共场景已更新',
                category='updated',
                visibility='member',
                sceneType='public',
                backgroundPath='/assets/test/background.jpg',
                coverPath='/assets/test/cover.jpg',
            ),
            build_request(method='PUT', path='/api/admin/public-scenes/update', headers=headers),
        )['data']
        self.assertEqual(updated_scene['visibility'], 'member')

    def test_admin_can_grant_and_revoke_user_admin_role(self):
        headers = self._login_header()
        request = build_request(path='/api/admin/users', headers=headers)

        promoted = main.admin_grant_user_admin(
            'debug_user_admin_001',
            build_request(method='POST', path='/api/admin/users/grant-admin', headers=headers),
        )['data']
        self.assertEqual(promoted['role'], 'admin')

        me = main.get_me(
            build_request(
                path='/api/me',
                headers={'Authorization': f"Bearer {self._user_access_token('debug_user_admin_001')}"},
            )
        )['data']
        self.assertEqual(me['role'], 'admin')

        admin_me = main.admin_auth_me(
            build_request(
                path='/api/admin/auth/me',
                headers={'Authorization': f"Bearer {self._user_access_token('debug_user_admin_001')}"},
            )
        )['data']
        self.assertEqual(admin_me['userId'], 'debug_user_admin_001')
        self.assertEqual(admin_me['role'], 'admin')

        revoked = main.admin_revoke_user_admin(
            'debug_user_admin_001',
            build_request(method='POST', path='/api/admin/users/revoke-admin', headers=headers),
        )['data']
        self.assertEqual(revoked['role'], 'user')

        with self.assertRaises(HTTPException):
            main.admin_auth_me(
                build_request(
                    path='/api/admin/auth/me',
                    headers={'Authorization': f"Bearer {self._user_access_token('debug_user_admin_001')}"},
                )
            )


if __name__ == '__main__':
    unittest.main()
