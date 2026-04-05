import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.commerce_store import CommerceStore
from app.settings import DATABASE_SCHEMA, DATABASE_URL


def main() -> int:
    if not DATABASE_URL:
        raise SystemExit('DATABASE_URL is required')

    store = CommerceStore(DATABASE_URL, DATABASE_SCHEMA)
    store.upsert_product({
        'id': 'product_membership_basic',
        'productCode': 'membership_basic',
        'productType': 'membership',
        'name': '会员月卡',
        'subtitle': '解锁公开场景与基础会员权益',
        'description': '第一阶段的基础会员商品。',
        'status': 'active',
        'sortOrder': 10,
    })
    store.upsert_sku({
        'id': 'sku_membership_basic_monthly',
        'productId': 'product_membership_basic',
        'skuCode': 'membership_basic_monthly',
        'name': '月度会员',
        'billingType': 'monthly',
        'durationDays': 30,
        'status': 'active',
        'listPrice': '39.00',
        'salePrice': '19.90',
        'currency': 'CNY',
        'sortOrder': 10,
    })
    store.replace_sku_benefits('sku_membership_basic_monthly', [
        {
            'id': 'benefit_membership_basic_monthly',
            'benefitType': 'membership',
            'benefitValue': 'basic_member',
            'benefitJson': {'durationDays': 30, 'sceneAccess': 'public'},
        },
    ])

    store.upsert_product({
        'id': 'product_credit_scene',
        'productCode': 'credit_scene',
        'productType': 'credit_pack',
        'name': '场景生成点数包',
        'subtitle': '用于 AI 私有场景生成',
        'description': '第一阶段的 credits 商品。',
        'status': 'active',
        'sortOrder': 20,
    })
    store.upsert_sku({
        'id': 'sku_credit_scene_20',
        'productId': 'product_credit_scene',
        'skuCode': 'credit_scene_20',
        'name': '20 次生成点数',
        'billingType': 'one_time',
        'durationDays': None,
        'status': 'active',
        'listPrice': '29.90',
        'salePrice': '9.90',
        'currency': 'CNY',
        'sortOrder': 10,
    })
    store.replace_sku_benefits('sku_credit_scene_20', [
        {
            'id': 'benefit_credit_scene_20',
            'benefitType': 'credits',
            'benefitValue': 'scene_generation_credits',
            'benefitJson': {'creditType': 'scene_generation_credits', 'amount': 20},
        },
    ])
    print('seeded demo catalog products=2 skus=2')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
