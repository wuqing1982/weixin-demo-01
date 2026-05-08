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

    # --- Product 1: Pro ---
    store.upsert_product({
        'id': 'product_tier_pro',
        'productCode': 'tier_pro',
        'productType': 'membership',
        'name': 'Pro',
        'subtitle': '50 积分，开启英语场景创作之旅',
        'description': '解锁全部公开场景，获得 50 次场景生成积分，有效期 365 天。',
        'status': 'active',
        'sortOrder': 10,
    })
    store.upsert_sku({
        'id': 'sku_tier_pro',
        'productId': 'product_tier_pro',
        'skuCode': 'tier_pro_365',
        'name': 'Pro（年）',
        'billingType': 'one_time',
        'durationDays': 365,
        'status': 'active',
        'listPrice': '69.00',
        'salePrice': '39.90',
        'currency': 'CNY',
        'sortOrder': 10,
    })
    store.replace_sku_benefits('sku_tier_pro', [
        {
            'id': 'benefit_pro_membership',
            'benefitType': 'membership',
            'benefitValue': 'pro',
            'benefitJson': {'durationDays': 365, 'tier': 'pro', 'sceneAccess': 'all_public'},
        },
        {
            'id': 'benefit_pro_credits',
            'benefitType': 'credits',
            'benefitValue': 'scene_generation_credits',
            'benefitJson': {'creditType': 'scene_generation_credits', 'amount': 50},
        },
    ])

    # --- Product 2: Plus ---
    store.upsert_product({
        'id': 'product_tier_plus',
        'productCode': 'tier_plus',
        'productType': 'membership',
        'name': 'Plus',
        'subtitle': '150 积分 + 视频导出，记录你的学习成果',
        'description': '全部公开场景 + 150 次场景生成 + 视频导出（保留3小时），有效期 365 天。',
        'status': 'active',
        'sortOrder': 20,
    })
    store.upsert_sku({
        'id': 'sku_tier_plus',
        'productId': 'product_tier_plus',
        'skuCode': 'tier_plus_365',
        'name': 'Plus（年）',
        'billingType': 'one_time',
        'durationDays': 365,
        'status': 'active',
        'listPrice': '168.00',
        'salePrice': '99.00',
        'currency': 'CNY',
        'sortOrder': 10,
    })
    store.replace_sku_benefits('sku_tier_plus', [
        {
            'id': 'benefit_plus_membership',
            'benefitType': 'membership',
            'benefitValue': 'plus',
            'benefitJson': {'durationDays': 365, 'tier': 'plus', 'sceneAccess': 'all_public'},
        },
        {
            'id': 'benefit_plus_credits',
            'benefitType': 'credits',
            'benefitValue': 'scene_generation_credits',
            'benefitJson': {'creditType': 'scene_generation_credits', 'amount': 200},
        },
        {
            'id': 'benefit_plus_video_export',
            'benefitType': 'feature',
            'benefitValue': 'video_export',
            'benefitJson': {'retentionHours': 3},
        },
    ])

    # --- Product 3: Max ---
    store.upsert_product({
        'id': 'product_tier_max',
        'productCode': 'tier_max',
        'productType': 'membership',
        'name': 'Max',
        'subtitle': '500 积分 + 全功能解锁，无限创作',
        'description': '全部公开场景 + 500 次场景生成 + 视频导出 + 优先生成队列，有效期 365 天。',
        'status': 'active',
        'sortOrder': 30,
    })
    store.upsert_sku({
        'id': 'sku_tier_max',
        'productId': 'product_tier_max',
        'skuCode': 'tier_max_365',
        'name': 'Max（年）',
        'billingType': 'one_time',
        'durationDays': 365,
        'status': 'active',
        'listPrice': '328.00',
        'salePrice': '199.00',
        'currency': 'CNY',
        'sortOrder': 10,
    })
    store.replace_sku_benefits('sku_tier_max', [
        {
            'id': 'benefit_max_membership',
            'benefitType': 'membership',
            'benefitValue': 'max',
            'benefitJson': {'durationDays': 365, 'tier': 'max', 'sceneAccess': 'all_public', 'priorityQueue': True},
        },
        {
            'id': 'benefit_max_credits',
            'benefitType': 'credits',
            'benefitValue': 'scene_generation_credits',
            'benefitJson': {'creditType': 'scene_generation_credits', 'amount': 500},
        },
        {
            'id': 'benefit_max_video_export',
            'benefitType': 'feature',
            'benefitValue': 'video_export',
            'benefitJson': {'retentionHours': 3},
        },
        {
            'id': 'benefit_max_priority_queue',
            'benefitType': 'feature',
            'benefitValue': 'priority_queue',
            'benefitJson': {},
        },
    ])

    print('seeded catalog: products=3 skus=3 (Pro/Plus/Max)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
