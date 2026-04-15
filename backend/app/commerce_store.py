import json
import random
import secrets
import string
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from .commerce_postgres_schema import ensure_commerce_postgres_schema
from .postgres import connect_postgres
from .store_utils import build_object_id, utcnow_iso


TIER_RANK = {'pro': 1, 'plus': 2, 'max': 3}
TIER_PRICE = {'pro': Decimal('39.90'), 'plus': Decimal('99.00'), 'max': Decimal('199.00')}
TIER_DAYS = 365


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _to_amount(value: Decimal | None) -> str:
    return format(value or Decimal('0'), '.2f')


def _serialize_product(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        'productId': row.get('id', ''),
        'productCode': row.get('product_code', ''),
        'productType': row.get('product_type', ''),
        'name': row.get('name', ''),
        'subtitle': row.get('subtitle', ''),
        'description': row.get('description', ''),
        'status': row.get('status', ''),
        'coverUrl': row.get('cover_url', ''),
        'sortOrder': int(row.get('sort_order') or 0),
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
    }


def _serialize_sku(row: dict[str, Any], benefits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'skuId': row.get('id', ''),
        'productId': row.get('product_id', ''),
        'skuCode': row.get('sku_code', ''),
        'name': row.get('name', ''),
        'billingType': row.get('billing_type', ''),
        'durationDays': row.get('duration_days'),
        'status': row.get('status', ''),
        'listPrice': _to_amount(row.get('list_price')),
        'salePrice': _to_amount(row.get('sale_price')),
        'currency': row.get('currency', 'CNY'),
        'stockType': row.get('stock_type', 'unlimited'),
        'stockCount': row.get('stock_count'),
        'sortOrder': int(row.get('sort_order') or 0),
        'benefits': benefits,
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
    }


def _serialize_order_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'orderItemId': row.get('id', ''),
        'orderId': row.get('order_id', ''),
        'productId': row.get('product_id', ''),
        'skuId': row.get('sku_id', ''),
        'productName': row.get('product_name', ''),
        'skuName': row.get('sku_name', ''),
        'quantity': int(row.get('quantity') or 0),
        'unitPrice': _to_amount(row.get('unit_price')),
        'totalPrice': _to_amount(row.get('total_price')),
        'benefitSnapshot': row.get('benefit_snapshot') or [],
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
    }


def _serialize_payment(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'paymentId': row.get('id', ''),
        'paymentNo': row.get('payment_no', ''),
        'orderId': row.get('order_id', ''),
        'userId': row.get('user_id', ''),
        'channel': row.get('channel', ''),
        'status': row.get('status', ''),
        'amount': _to_amount(row.get('amount')),
        'channelTradeNo': row.get('channel_trade_no'),
        'channelPayload': row.get('channel_payload') or {},
        'paidAt': _to_iso(row.get('paid_at')),
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
    }


def _serialize_scene_category(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        'categoryId': row.get('id', ''),
        'categoryCode': row.get('category_code', ''),
        'name': row.get('name', ''),
        'description': row.get('description', ''),
        'status': row.get('status', 'active'),
        'sortOrder': int(row.get('sort_order') or 0),
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
    }


def _serialize_scene_collection(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        'collectionId': row.get('id', ''),
        'collectionCode': row.get('collection_code', ''),
        'name': row.get('name', ''),
        'description': row.get('description', ''),
        'status': row.get('status', 'active'),
        'coverUrl': row.get('cover_url', ''),
        'sortOrder': int(row.get('sort_order') or 0),
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
    }


def _serialize_scene_publication(row: dict[str, Any] | None, collection_ids: list[str]) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        'sourceGeneratedSceneId': row.get('source_generated_scene_id', ''),
        'publicSceneId': row.get('public_scene_id', ''),
        'categoryId': row.get('category_id') or '',
        'categoryName': row.get('category_name') or '',
        'visibility': row.get('visibility', 'public'),
        'publishedBy': row.get('published_by', ''),
        'publishedAt': _to_iso(row.get('published_at')),
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
        'collectionIds': collection_ids,
    }


def _serialize_order(row: dict[str, Any], items: list[dict[str, Any]], payments: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'orderId': row.get('id', ''),
        'orderNo': row.get('order_no', ''),
        'userId': row.get('user_id', ''),
        'status': row.get('status', ''),
        'totalAmount': _to_amount(row.get('total_amount')),
        'payableAmount': _to_amount(row.get('payable_amount')),
        'paidAmount': _to_amount(row.get('paid_amount')),
        'currency': row.get('currency', 'CNY'),
        'paymentStatus': row.get('payment_status', ''),
        'paidAt': _to_iso(row.get('paid_at')),
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
        'items': items,
        'payments': payments,
    }


def _build_business_no(prefix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    return f'{prefix}{timestamp}{secrets.token_hex(3)}'


def _serialize_cdk(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'cdkId': row.get('id', ''),
        'code': row.get('code', ''),
        'skuId': row.get('sku_id', ''),
        'skuName': row.get('sku_name') or row.get('sku_id', ''),
        'status': row.get('status', 'unused'),
        'batchId': row.get('batch_id') or '',
        'redeemedBy': row.get('redeemed_by') or '',
        'redeemedAt': _to_iso(row.get('redeemed_at')),
        'note': row.get('note') or '',
        'createdAt': _to_iso(row.get('created_at')),
        'updatedAt': _to_iso(row.get('updated_at')),
    }


class CommerceStore:
    def __init__(self, database_url: str, schema_name: str = 'public'):
        self.database_url = database_url
        self.schema_name = schema_name
        self._ensure_ready()

    def _connect(self):
        return connect_postgres(self.database_url, self.schema_name)

    def _ensure_ready(self) -> None:
        with self._connect() as connection:
            ensure_commerce_postgres_schema(connection)

    def list_products(self, product_type: str = '', *, status: str = 'active') -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append('status = %s')
            params.append(status)
        if product_type:
            clauses.append('product_type = %s')
            params.append(product_type)

        sql = 'select * from products'
        if clauses:
            sql += ' where ' + ' and '.join(clauses)
        sql += ' order by sort_order asc, created_at asc'

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return [_serialize_product(row) for row in cursor.fetchall()]

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('select * from products where id = %s limit 1', (product_id,))
                return _serialize_product(cursor.fetchone())

    def list_product_skus(self, product_id: str, *, status: str = 'active') -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if status:
                    cursor.execute(
                        'select * from product_skus where product_id = %s and status = %s order by sort_order asc, created_at asc',
                        (product_id, status),
                    )
                else:
                    cursor.execute(
                        'select * from product_skus where product_id = %s order by sort_order asc, created_at asc',
                        (product_id,),
                    )
                sku_rows = cursor.fetchall()
                sku_ids = [row.get('id') for row in sku_rows]
                benefits_by_sku: dict[str, list[dict[str, Any]]] = {sku_id: [] for sku_id in sku_ids}
                if sku_ids:
                    cursor.execute(
                        '''
                        select *
                        from sku_benefits
                        where sku_id = any(%s)
                        order by created_at asc
                        ''',
                        (sku_ids,),
                    )
                    for row in cursor.fetchall():
                        benefits_by_sku.setdefault(row.get('sku_id', ''), []).append({
                            'benefitId': row.get('id', ''),
                            'benefitType': row.get('benefit_type', ''),
                            'benefitValue': row.get('benefit_value', ''),
                            'benefitJson': row.get('benefit_json') or {},
                            'createdAt': _to_iso(row.get('created_at')),
                            'updatedAt': _to_iso(row.get('updated_at')),
                        })
                return [_serialize_sku(row, benefits_by_sku.get(row.get('id', ''), [])) for row in sku_rows]

    def list_skus(self, *, status: str = '') -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append('s.status = %s')
            params.append(status)

        sql = '''
            select
              s.*,
              p.name as product_name,
              p.product_code,
              p.product_type
            from product_skus s
            join products p on p.id = s.product_id
        '''
        if clauses:
            sql += ' where ' + ' and '.join(clauses)
        sql += ' order by s.sort_order asc, s.created_at asc'

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                sku_rows = cursor.fetchall()
                sku_ids = [row.get('id') for row in sku_rows]
                benefits_by_sku: dict[str, list[dict[str, Any]]] = {sku_id: [] for sku_id in sku_ids}
                if sku_ids:
                    cursor.execute(
                        '''
                        select *
                        from sku_benefits
                        where sku_id = any(%s)
                        order by created_at asc
                        ''',
                        (sku_ids,),
                    )
                    for row in cursor.fetchall():
                        benefits_by_sku.setdefault(row.get('sku_id', ''), []).append({
                            'benefitId': row.get('id', ''),
                            'benefitType': row.get('benefit_type', ''),
                            'benefitValue': row.get('benefit_value', ''),
                            'benefitJson': row.get('benefit_json') or {},
                            'createdAt': _to_iso(row.get('created_at')),
                            'updatedAt': _to_iso(row.get('updated_at')),
                        })
                return [
                    {
                        **_serialize_sku(row, benefits_by_sku.get(row.get('id', ''), [])),
                        'productName': row.get('product_name', ''),
                        'productCode': row.get('product_code', ''),
                        'productType': row.get('product_type', ''),
                    }
                    for row in sku_rows
                ]

    def list_scene_categories(self, *, status: str = '') -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append('status = %s')
            params.append(status)

        sql = 'select * from scene_categories'
        if clauses:
            sql += ' where ' + ' and '.join(clauses)
        sql += ' order by sort_order asc, created_at asc'

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return [_serialize_scene_category(row) for row in cursor.fetchall()]

    def get_scene_category(self, category_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('select * from scene_categories where id = %s limit 1', (category_id,))
                return _serialize_scene_category(cursor.fetchone())

    def upsert_scene_category(self, category: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into scene_categories (
                      id, category_code, name, description, status, sort_order, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      category_code = excluded.category_code,
                      name = excluded.name,
                      description = excluded.description,
                      status = excluded.status,
                      sort_order = excluded.sort_order,
                      created_at = excluded.created_at,
                      updated_at = excluded.updated_at
                    ''',
                    (
                        category.get('id') or category.get('categoryId') or '',
                        category.get('categoryCode') or '',
                        category.get('name') or '',
                        category.get('description') or '',
                        category.get('status') or 'active',
                        int(category.get('sortOrder') or 0),
                        _parse_iso(category.get('createdAt')) or _parse_iso(utcnow_iso()),
                        _parse_iso(category.get('updatedAt')) or _parse_iso(utcnow_iso()),
                    ),
                )

    def delete_scene_category(self, category_id: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'select count(*) as count from scene_publications where category_id = %s',
                    (category_id,),
                )
                if int((cursor.fetchone() or {}).get('count') or 0) > 0:
                    raise ValueError('scene category is still used by published scenes')
                cursor.execute('delete from scene_categories where id = %s', (category_id,))
                return cursor.rowcount > 0

    def list_scene_collections(self, *, status: str = '') -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append('status = %s')
            params.append(status)

        sql = 'select * from scene_collections'
        if clauses:
            sql += ' where ' + ' and '.join(clauses)
        sql += ' order by sort_order asc, created_at asc'

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return [_serialize_scene_collection(row) for row in cursor.fetchall()]

    def get_scene_collection(self, collection_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('select * from scene_collections where id = %s limit 1', (collection_id,))
                return _serialize_scene_collection(cursor.fetchone())

    def upsert_scene_collection(self, collection: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into scene_collections (
                      id, collection_code, name, description, status, cover_url, sort_order, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      collection_code = excluded.collection_code,
                      name = excluded.name,
                      description = excluded.description,
                      status = excluded.status,
                      cover_url = excluded.cover_url,
                      sort_order = excluded.sort_order,
                      created_at = excluded.created_at,
                      updated_at = excluded.updated_at
                    ''',
                    (
                        collection.get('id') or collection.get('collectionId') or '',
                        collection.get('collectionCode') or '',
                        collection.get('name') or '',
                        collection.get('description') or '',
                        collection.get('status') or 'active',
                        collection.get('coverUrl') or '',
                        int(collection.get('sortOrder') or 0),
                        _parse_iso(collection.get('createdAt')) or _parse_iso(utcnow_iso()),
                        _parse_iso(collection.get('updatedAt')) or _parse_iso(utcnow_iso()),
                    ),
                )

    def delete_scene_collection(self, collection_id: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'select count(*) as count from scene_publication_collections where collection_id = %s',
                    (collection_id,),
                )
                if int((cursor.fetchone() or {}).get('count') or 0) > 0:
                    raise ValueError('scene collection is still used by published scenes')
                cursor.execute('delete from scene_collections where id = %s', (collection_id,))
                return cursor.rowcount > 0

    def _load_publication_collection_ids(
        self,
        cursor,
        *,
        public_scene_ids: list[str] | None = None,
        source_generated_scene_ids: list[str] | None = None,
    ) -> dict[str, list[str]]:
        clauses = []
        params: list[Any] = []
        if public_scene_ids:
            clauses.append('spc.public_scene_id = any(%s)')
            params.append(public_scene_ids)
        if source_generated_scene_ids:
            clauses.append('sp.source_generated_scene_id = any(%s)')
            params.append(source_generated_scene_ids)
        if not clauses:
            return {}

        cursor.execute(
            f'''
            select sp.source_generated_scene_id, sp.public_scene_id, spc.collection_id
            from scene_publication_collections spc
            join scene_publications sp on sp.public_scene_id = spc.public_scene_id
            where {' and '.join(clauses)}
            order by spc.sort_order asc, spc.created_at asc
            ''',
            params,
        )
        by_public_scene: dict[str, list[str]] = {}
        by_source: dict[str, list[str]] = {}
        for row in cursor.fetchall():
            public_scene_id = row.get('public_scene_id', '')
            source_generated_scene_id = row.get('source_generated_scene_id', '')
            collection_id = row.get('collection_id', '')
            if public_scene_id:
                by_public_scene.setdefault(public_scene_id, []).append(collection_id)
            if source_generated_scene_id:
                by_source.setdefault(source_generated_scene_id, []).append(collection_id)
        return {
            **{f'public:{key}': value for key, value in by_public_scene.items()},
            **{f'source:{key}': value for key, value in by_source.items()},
        }

    def list_scene_publications_by_source_ids(self, source_generated_scene_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not source_generated_scene_ids:
            return {}
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select
                      sp.*,
                      sc.name as category_name
                    from scene_publications sp
                    left join scene_categories sc on sc.id = sp.category_id
                    where sp.source_generated_scene_id = any(%s)
                    ''',
                    (source_generated_scene_ids,),
                )
                rows = cursor.fetchall()
                collection_map = self._load_publication_collection_ids(
                    cursor,
                    source_generated_scene_ids=source_generated_scene_ids,
                )
                return {
                    row.get('source_generated_scene_id', ''): _serialize_scene_publication(
                        row,
                        collection_map.get(f"source:{row.get('source_generated_scene_id', '')}", []),
                    )
                    for row in rows
                }

    def list_scene_publications_by_public_scene_ids(self, public_scene_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not public_scene_ids:
            return {}
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select
                      sp.*,
                      sc.name as category_name
                    from scene_publications sp
                    left join scene_categories sc on sc.id = sp.category_id
                    where sp.public_scene_id = any(%s)
                    ''',
                    (public_scene_ids,),
                )
                rows = cursor.fetchall()
                collection_map = self._load_publication_collection_ids(
                    cursor,
                    public_scene_ids=public_scene_ids,
                )
                return {
                    row.get('public_scene_id', ''): _serialize_scene_publication(
                        row,
                        collection_map.get(f"public:{row.get('public_scene_id', '')}", []),
                    )
                    for row in rows
                }

    def get_scene_publication_by_source(self, source_generated_scene_id: str) -> dict[str, Any] | None:
        return self.list_scene_publications_by_source_ids([source_generated_scene_id]).get(source_generated_scene_id)

    def get_scene_publication_by_public_scene(self, public_scene_id: str) -> dict[str, Any] | None:
        return self.list_scene_publications_by_public_scene_ids([public_scene_id]).get(public_scene_id)

    def upsert_scene_publication(
        self,
        *,
        source_generated_scene_id: str,
        public_scene_id: str,
        category_id: str,
        collection_ids: list[str],
        visibility: str,
        published_by: str,
    ) -> dict[str, Any]:
        now = utcnow_iso()
        normalized_collection_ids = []
        for index, collection_id in enumerate(collection_ids or []):
            if collection_id and collection_id not in normalized_collection_ids:
                normalized_collection_ids.append(collection_id)

        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        '''
                        insert into scene_publications (
                          source_generated_scene_id, public_scene_id, category_id, visibility, published_by, published_at, created_at, updated_at
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (source_generated_scene_id) do update set
                          public_scene_id = excluded.public_scene_id,
                          category_id = excluded.category_id,
                          visibility = excluded.visibility,
                          published_by = excluded.published_by,
                          published_at = excluded.published_at,
                          updated_at = excluded.updated_at
                        ''',
                        (
                            source_generated_scene_id,
                            public_scene_id,
                            category_id or None,
                            visibility or 'public',
                            published_by,
                            _parse_iso(now),
                            _parse_iso(now),
                            _parse_iso(now),
                        ),
                    )
                    cursor.execute(
                        'delete from scene_publication_collections where public_scene_id = %s',
                        (public_scene_id,),
                    )
                    for sort_order, collection_id in enumerate(normalized_collection_ids):
                        cursor.execute(
                            '''
                            insert into scene_publication_collections (
                              id, public_scene_id, collection_id, sort_order, created_at, updated_at
                            ) values (%s, %s, %s, %s, %s, %s)
                            ''',
                            (
                                build_object_id('scene_collection_item'),
                                public_scene_id,
                                collection_id,
                                sort_order,
                                _parse_iso(now),
                                _parse_iso(now),
                            ),
                        )
        return self.get_scene_publication_by_source(source_generated_scene_id)

    def batch_update_publication_category(self, public_scene_ids: list[str], category_id: str) -> int:
        if not public_scene_ids:
            return 0
        now = utcnow_iso()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    update scene_publications
                    set category_id = %s, updated_at = %s
                    where public_scene_id = any(%s)
                    ''',
                    (category_id, _parse_iso(now), public_scene_ids),
                )
                return cursor.rowcount

    def get_membership_summary(self, user_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select *
                    from user_entitlements
                    where user_id = %s
                      and entitlement_type = 'membership'
                      and status = 'active'
                      and starts_at <= now()
                      and (expires_at is null or expires_at > now())
                    order by expires_at desc nulls last, created_at desc
                    limit 1
                    ''',
                    (user_id,),
                )
                entitlement = cursor.fetchone()
                if not entitlement:
                    return {
                        'isActive': False,
                        'entitlementCode': '',
                        'expiresAt': None,
                    }
                return {
                    'isActive': True,
                    'entitlementCode': entitlement.get('entitlement_code', ''),
                    'expiresAt': _to_iso(entitlement.get('expires_at')),
                }

    def _get_active_membership_row(self, cursor, user_id: str, for_update: bool = False) -> dict[str, Any] | None:
        sql = '''
            select *
            from user_entitlements
            where user_id = %s
              and entitlement_type = 'membership'
              and status = 'active'
              and starts_at <= now()
              and (expires_at is null or expires_at > now())
            order by expires_at desc nulls last, created_at desc
            limit 1
        '''
        if for_update:
            sql = sql.rstrip() + ' for update'
        cursor.execute(sql, (user_id,))
        return cursor.fetchone()

    def _validate_tier_purchase(self, cursor, user_id: str, target_tier: str) -> dict[str, Any]:
        current = self._get_active_membership_row(cursor, user_id, for_update=True)
        if not current:
            return {'action': 'fresh', 'current_membership': None}

        current_tier = current.get('entitlement_code', '').lower()
        target_tier_lower = target_tier.lower()
        current_rank = TIER_RANK.get(current_tier, 0)
        target_rank = TIER_RANK.get(target_tier_lower, 0)

        if current_rank == target_rank:
            return {'action': 'renewal', 'current_membership': current}
        if current_rank < target_rank:
            return {'action': 'upgrade', 'current_membership': current}
        raise ValueError('当前会员等级更高，无法降级购买')

    def preview_tier_purchase(self, user_id: str, sku_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                bundle = self._fetch_sku_bundle(cursor, sku_id)
                if not bundle:
                    raise ValueError('sku not found')

                target_tier = ''
                for benefit in bundle.get('benefits', []):
                    if benefit.get('benefitType') == 'membership':
                        target_tier = (benefit.get('benefitValue') or '').lower()
                        break
                if not target_tier or target_tier not in TIER_RANK:
                    raise ValueError('sku does not contain a valid membership benefit')

                try:
                    validation = self._validate_tier_purchase(cursor, user_id, target_tier)
                except ValueError:
                    return {
                        'action': 'blocked',
                        'currentTier': '',
                        'targetTier': target_tier,
                        'remainingDays': 0,
                        'convertedDays': 0,
                        'newDurationDays': 0,
                        'newExpiresAt': None,
                    }

                action = validation['action']
                now = datetime.now(timezone.utc)

                if action == 'fresh':
                    return {
                        'action': 'fresh',
                        'currentTier': '',
                        'targetTier': target_tier,
                        'remainingDays': 0,
                        'convertedDays': 0,
                        'newDurationDays': TIER_DAYS,
                        'newExpiresAt': _to_iso(now + timedelta(days=TIER_DAYS)),
                    }

                membership = validation['current_membership']
                current_tier = membership.get('entitlement_code', '').lower()
                expires_at = _parse_iso(membership.get('expires_at'))
                remaining_days = max(0, (expires_at - now).days) if expires_at else 0

                if action == 'renewal':
                    new_start = max(expires_at, now) if expires_at else now
                    new_expires = new_start + timedelta(days=TIER_DAYS)
                    return {
                        'action': 'renewal',
                        'currentTier': current_tier,
                        'targetTier': target_tier,
                        'remainingDays': remaining_days,
                        'convertedDays': 0,
                        'newDurationDays': TIER_DAYS,
                        'newExpiresAt': _to_iso(new_expires),
                    }

                # upgrade
                converted = int(remaining_days * TIER_PRICE.get(current_tier, Decimal('0')) / TIER_PRICE.get(target_tier, Decimal('1')))
                new_expires = now + timedelta(days=converted + TIER_DAYS)
                return {
                    'action': 'upgrade',
                    'currentTier': current_tier,
                    'targetTier': target_tier,
                    'remainingDays': remaining_days,
                    'convertedDays': converted,
                    'newDurationDays': converted + TIER_DAYS,
                    'newExpiresAt': _to_iso(new_expires),
                }

    def get_credit_summary(self, user_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select *
                    from user_credit_accounts
                    where user_id = %s
                    order by credit_type asc
                    ''',
                    (user_id,),
                )
                rows = cursor.fetchall()

        accounts = [{
            'accountId': row.get('id', ''),
            'creditType': row.get('credit_type', ''),
            'balance': int(row.get('balance') or 0),
            'frozenBalance': int(row.get('frozen_balance') or 0),
            'updatedAt': _to_iso(row.get('updated_at')),
        } for row in rows]

        scene_generate_balance = 0
        for account in accounts:
            if account['creditType'] in {'scene_generation_credits', 'diy_scene_generation'}:
                scene_generate_balance = account['balance']
                break

        return {
            'sceneGenerateBalance': scene_generate_balance,
            'accounts': accounts,
        }

    def list_user_entitlements(self, user_id: str, entitlement_type: str = '', entitlement_code: str = '') -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                conditions = ['user_id = %s']
                params: list[Any] = [user_id]
                if entitlement_type:
                    conditions.append('entitlement_type = %s')
                    params.append(entitlement_type)
                if entitlement_code:
                    conditions.append('entitlement_code = %s')
                    params.append(entitlement_code)
                where_clause = ' and '.join(conditions)
                cursor.execute(
                    f'''
                    select *
                    from user_entitlements
                    where {where_clause}
                    order by created_at desc
                    ''',
                    tuple(params),
                )
                return [{
                    'entitlementId': row.get('id', ''),
                    'userId': row.get('user_id', ''),
                    'sourceType': row.get('source_type', ''),
                    'sourceId': row.get('source_id'),
                    'entitlementType': row.get('entitlement_type', ''),
                    'entitlementCode': row.get('entitlement_code', ''),
                    'status': row.get('status', ''),
                    'startsAt': _to_iso(row.get('starts_at')),
                    'expiresAt': _to_iso(row.get('expires_at')),
                    'payloadJson': row.get('payload_json') or {},
                    'createdAt': _to_iso(row.get('created_at')),
                    'updatedAt': _to_iso(row.get('updated_at')),
                } for row in cursor.fetchall()]

    def get_credit_balance(self, user_id: str, credit_type: str) -> int:
        """Return the current balance for a specific credit type."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select balance from user_credit_accounts
                    where user_id = %s and credit_type = %s
                    limit 1
                    ''',
                    (user_id, credit_type),
                )
                row = cursor.fetchone()
                return int(row.get('balance') or 0) if row else 0

    def deduct_credit(self, *, user_id: str, credit_type: str, amount: int, reason_type: str, reason_id: str = '', remark: str = '') -> dict[str, Any]:
        """Deduct credits atomically. Raises ValueError if insufficient balance."""
        amount = max(1, int(amount))
        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        '''
                        select id, balance from user_credit_accounts
                        where user_id = %s and credit_type = %s
                        limit 1
                        for update
                        ''',
                        (user_id, credit_type),
                    )
                    account = cursor.fetchone()
                    if not account:
                        raise ValueError(f'积分不足：余额为 0')
                    current_balance = int(account.get('balance') or 0)
                    if current_balance < amount:
                        raise ValueError(f'积分不足：余额 {current_balance}，需要 {amount}')
                    new_balance = current_balance - amount
                    cursor.execute(
                        '''
                        update user_credit_accounts
                        set balance = %s, updated_at = now()
                        where id = %s
                        ''',
                        (new_balance, account.get('id', '')),
                    )
                    cursor.execute(
                        '''
                        insert into credit_ledger (
                          id, user_id, credit_type, change_amount, balance_after, reason_type, reason_id, remark, created_at
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, now())
                        ''',
                        (
                            build_object_id('ledger'),
                            user_id,
                            credit_type,
                            -amount,
                            new_balance,
                            reason_type,
                            reason_id,
                            remark or f'{reason_type} deduction',
                        ),
                    )
                    return {'balance': new_balance, 'accountId': account.get('id', '')}

    def upsert_product(self, product: dict[str, Any]) -> None:
        now = utcnow_iso()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into products (
                      id, product_code, product_type, name, subtitle, description, status, cover_url, sort_order, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      product_code = excluded.product_code,
                      product_type = excluded.product_type,
                      name = excluded.name,
                      subtitle = excluded.subtitle,
                      description = excluded.description,
                      status = excluded.status,
                      cover_url = excluded.cover_url,
                      sort_order = excluded.sort_order,
                      created_at = excluded.created_at,
                      updated_at = excluded.updated_at
                    ''',
                    (
                        product.get('id') or build_object_id('product'),
                        product.get('productCode') or '',
                        product.get('productType') or '',
                        product.get('name') or '',
                        product.get('subtitle') or '',
                        product.get('description') or '',
                        product.get('status') or 'draft',
                        product.get('coverUrl') or '',
                        int(product.get('sortOrder') or 0),
                        _parse_iso(product.get('createdAt')) or _parse_iso(now),
                        _parse_iso(product.get('updatedAt')) or _parse_iso(now),
                    ),
                )

    def upsert_sku(self, sku: dict[str, Any]) -> None:
        now = utcnow_iso()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into product_skus (
                      id, product_id, sku_code, name, billing_type, duration_days, status, list_price, sale_price, currency, stock_type, stock_count, sort_order, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      product_id = excluded.product_id,
                      sku_code = excluded.sku_code,
                      name = excluded.name,
                      billing_type = excluded.billing_type,
                      duration_days = excluded.duration_days,
                      status = excluded.status,
                      list_price = excluded.list_price,
                      sale_price = excluded.sale_price,
                      currency = excluded.currency,
                      stock_type = excluded.stock_type,
                      stock_count = excluded.stock_count,
                      sort_order = excluded.sort_order,
                      created_at = excluded.created_at,
                      updated_at = excluded.updated_at
                    ''',
                    (
                        sku.get('id') or build_object_id('sku'),
                        sku.get('productId') or '',
                        sku.get('skuCode') or '',
                        sku.get('name') or '',
                        sku.get('billingType') or 'one_time',
                        sku.get('durationDays'),
                        sku.get('status') or 'draft',
                        Decimal(str(sku.get('listPrice') or '0')),
                        Decimal(str(sku.get('salePrice') or '0')),
                        sku.get('currency') or 'CNY',
                        sku.get('stockType') or 'unlimited',
                        sku.get('stockCount'),
                        int(sku.get('sortOrder') or 0),
                        _parse_iso(sku.get('createdAt')) or _parse_iso(now),
                        _parse_iso(sku.get('updatedAt')) or _parse_iso(now),
                    ),
                )

    def replace_sku_benefits(self, sku_id: str, benefits: list[dict[str, Any]]) -> None:
        now = utcnow_iso()
        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute('delete from sku_benefits where sku_id = %s', (sku_id,))
                    for benefit in benefits:
                        cursor.execute(
                            '''
                            insert into sku_benefits (
                              id, sku_id, benefit_type, benefit_value, benefit_json, created_at, updated_at
                            ) values (%s, %s, %s, %s, %s::jsonb, %s, %s)
                            ''',
                            (
                                benefit.get('id') or build_object_id('benefit'),
                                sku_id,
                                benefit.get('benefitType') or '',
                                benefit.get('benefitValue') or '',
                                json.dumps(benefit.get('benefitJson') or {}, ensure_ascii=False),
                                _parse_iso(benefit.get('createdAt')) or _parse_iso(now),
                                _parse_iso(benefit.get('updatedAt')) or _parse_iso(now),
                            ),
                        )

    def grant_entitlement(self, entitlement: dict[str, Any]) -> None:
        now = utcnow_iso()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into user_entitlements (
                      id, user_id, source_type, source_id, entitlement_type, entitlement_code, status, starts_at, expires_at, payload_json, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    on conflict (id) do update set
                      user_id = excluded.user_id,
                      source_type = excluded.source_type,
                      source_id = excluded.source_id,
                      entitlement_type = excluded.entitlement_type,
                      entitlement_code = excluded.entitlement_code,
                      status = excluded.status,
                      starts_at = excluded.starts_at,
                      expires_at = excluded.expires_at,
                      payload_json = excluded.payload_json,
                      created_at = excluded.created_at,
                      updated_at = excluded.updated_at
                    ''',
                    (
                        entitlement.get('id') or build_object_id('entitlement'),
                        entitlement.get('userId') or '',
                        entitlement.get('sourceType') or 'system_grant',
                        entitlement.get('sourceId'),
                        entitlement.get('entitlementType') or '',
                        entitlement.get('entitlementCode') or '',
                        entitlement.get('status') or 'active',
                        _parse_iso(entitlement.get('startsAt')) or _parse_iso(now),
                        _parse_iso(entitlement.get('expiresAt')),
                        json.dumps(entitlement.get('payloadJson') or {}, ensure_ascii=False),
                        _parse_iso(entitlement.get('createdAt')) or _parse_iso(now),
                        _parse_iso(entitlement.get('updatedAt')) or _parse_iso(now),
                    ),
                )

    def set_credit_account(self, account: dict[str, Any]) -> None:
        now = utcnow_iso()
        account_id = account.get('id') or build_object_id('credit')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    insert into user_credit_accounts (
                      id, user_id, credit_type, balance, frozen_balance, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s)
                    on conflict (user_id, credit_type) do update set
                      balance = excluded.balance,
                      frozen_balance = excluded.frozen_balance,
                      updated_at = excluded.updated_at
                    ''',
                    (
                        account_id,
                        account.get('userId') or '',
                        account.get('creditType') or '',
                        int(account.get('balance') or 0),
                        int(account.get('frozenBalance') or 0),
                        _parse_iso(account.get('createdAt')) or _parse_iso(now),
                        _parse_iso(account.get('updatedAt')) or _parse_iso(now),
                    ),
                )

    def _fetch_sku_bundle(self, cursor, sku_id: str) -> dict[str, Any] | None:
        cursor.execute(
            '''
            select
              s.*,
              p.name as product_name,
              p.product_code,
              p.product_type,
              p.status as product_status
            from product_skus s
            join products p on p.id = s.product_id
            where s.id = %s
            limit 1
            ''',
            (sku_id,),
        )
        sku_row = cursor.fetchone()
        if not sku_row:
            return None

        cursor.execute(
            'select * from sku_benefits where sku_id = %s order by created_at asc',
            (sku_id,),
        )
        benefits = [{
            'benefitId': row.get('id', ''),
            'benefitType': row.get('benefit_type', ''),
            'benefitValue': row.get('benefit_value', ''),
            'benefitJson': row.get('benefit_json') or {},
        } for row in cursor.fetchall()]
        return {
            'sku': sku_row,
            'benefits': benefits,
        }

    def _fetch_order_row(self, cursor, order_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        if user_id:
            cursor.execute('select * from orders where id = %s and user_id = %s limit 1', (order_id, user_id))
        else:
            cursor.execute('select * from orders where id = %s limit 1', (order_id,))
        return cursor.fetchone()

    def _fetch_order_items(self, cursor, order_id: str) -> list[dict[str, Any]]:
        cursor.execute(
            'select * from order_items where order_id = %s order by created_at asc',
            (order_id,),
        )
        return cursor.fetchall()

    def _fetch_order_payments(self, cursor, order_id: str) -> list[dict[str, Any]]:
        cursor.execute(
            'select * from payments where order_id = %s order by created_at asc',
            (order_id,),
        )
        return cursor.fetchall()

    def _serialize_order_detail(self, cursor, order_row: dict[str, Any]) -> dict[str, Any]:
        items = [_serialize_order_item(row) for row in self._fetch_order_items(cursor, order_row.get('id', ''))]
        payments = [_serialize_payment(row) for row in self._fetch_order_payments(cursor, order_row.get('id', ''))]
        return _serialize_order(order_row, items, payments)

    def _grant_benefits_for_order(self, cursor, order_row: dict[str, Any], items: list[dict[str, Any]]) -> None:
        for item in items:
            quantity = int(item.get('quantity') or 1)
            benefits = item.get('benefit_snapshot') or []
            self._grant_sku_benefits(
                cursor,
                user_id=order_row.get('user_id', ''),
                benefits=benefits,
                quantity=quantity,
                source_type='order',
                source_id=order_row.get('id', ''),
                extra_payload={'orderId': order_row.get('id', ''), 'orderNo': order_row.get('order_no', '')},
                sku_name=item.get('sku_name', ''),
                reason_remark=f'payment grant via order {order_row.get("order_no", "")}',
            )

    def _grant_sku_benefits(self, cursor, *, user_id: str, benefits: list[dict[str, Any]], quantity: int, source_type: str, source_id: str, extra_payload: dict | None = None, sku_name: str = '', reason_remark: str = '') -> None:
        # Resolve membership action (fresh / renewal / upgrade / downgrade-blocked)
        membership_benefit = None
        for b in benefits:
            if b.get('benefitType') == 'membership':
                membership_benefit = b
                break

        membership_action = 'fresh'
        current_membership_row = None
        if membership_benefit:
            target_tier = (membership_benefit.get('benefitValue') or '').lower()
            validation = self._validate_tier_purchase(cursor, user_id, target_tier)
            membership_action = validation['action']
            current_membership_row = validation.get('current_membership')

        # Track the final membership expires_at so feature benefits can inherit it
        final_membership_expires_at = None
        final_membership_starts_at = None

        for benefit in benefits:
            benefit_type = benefit.get('benefitType', '')
            benefit_value = benefit.get('benefitValue', '')
            benefit_json = benefit.get('benefitJson') or {}

            if benefit_type == 'membership':
                duration_days = int(benefit_json.get('durationDays') or TIER_DAYS)
                now = datetime.now(timezone.utc)

                if membership_action == 'fresh':
                    starts_at = now
                    expires_at = now + timedelta(days=duration_days * quantity)
                elif membership_action == 'renewal':
                    old_expires = _parse_iso(current_membership_row.get('expires_at')) if current_membership_row else None
                    starts_at = max(old_expires, now) if old_expires else now
                    expires_at = starts_at + timedelta(days=duration_days * quantity)
                elif membership_action == 'upgrade':
                    old_tier = (current_membership_row.get('entitlement_code') or '').lower()
                    old_expires = _parse_iso(current_membership_row.get('expires_at'))
                    remaining_days = max(0, (old_expires - now).days) if old_expires else 0
                    converted = int(remaining_days * TIER_PRICE.get(old_tier, Decimal('0')) / TIER_PRICE.get(target_tier, Decimal('1')))
                    starts_at = now
                    expires_at = now + timedelta(days=converted + duration_days * quantity)

                    # Mark old membership and its feature entitlements as superseded
                    cursor.execute(
                        "update user_entitlements set status = 'superseded', updated_at = now() where id = %s",
                        (current_membership_row.get('id', ''),),
                    )
                    cursor.execute(
                        """
                        update user_entitlements
                        set status = 'superseded', updated_at = now()
                        where user_id = %s
                          and entitlement_type = 'feature'
                          and status = 'active'
                          and source_id = %s
                        """,
                        (user_id, current_membership_row.get('source_id', '')),
                    )

                payload = dict(extra_payload or {})
                payload['skuName'] = sku_name
                payload['benefit'] = benefit_json
                cursor.execute(
                    '''
                    insert into user_entitlements (
                      id, user_id, source_type, source_id, entitlement_type, entitlement_code, status, starts_at, expires_at, payload_json, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), now())
                    ''',
                    (
                        build_object_id('entitlement'),
                        user_id,
                        source_type,
                        source_id,
                        'membership',
                        benefit_value or 'membership',
                        'active',
                        starts_at,
                        expires_at,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
                final_membership_starts_at = starts_at
                final_membership_expires_at = expires_at
                continue

            if benefit_type == 'credits':
                credit_type = benefit_json.get('creditType') or benefit_value or 'scene_generation_credits'
                amount = int(benefit_json.get('amount') or 0) * quantity
                cursor.execute(
                    'select * from user_credit_accounts where user_id = %s and credit_type = %s limit 1',
                    (user_id, credit_type),
                )
                account = cursor.fetchone()
                balance_after = int(account.get('balance') or 0) + amount if account else amount
                if account:
                    cursor.execute(
                        '''
                        update user_credit_accounts
                        set balance = %s, updated_at = now()
                        where id = %s
                        ''',
                        (balance_after, account.get('id', '')),
                    )
                    account_id = account.get('id', '')
                else:
                    account_id = build_object_id('credit')
                    cursor.execute(
                        '''
                        insert into user_credit_accounts (
                          id, user_id, credit_type, balance, frozen_balance, created_at, updated_at
                        ) values (%s, %s, %s, %s, %s, now(), now())
                        ''',
                        (account_id, user_id, credit_type, balance_after, 0),
                    )

                cursor.execute(
                    '''
                    insert into credit_ledger (
                      id, user_id, credit_type, change_amount, balance_after, reason_type, reason_id, remark, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, now())
                    ''',
                    (
                        build_object_id('ledger'),
                        user_id,
                        credit_type,
                        amount,
                        balance_after,
                        f'{source_type}_grant',
                        source_id,
                        reason_remark or f'{source_type} grant',
                    ),
                )
                continue

            if benefit_type == 'feature':
                if final_membership_expires_at and final_membership_starts_at:
                    starts_at = final_membership_starts_at
                    expires_at = final_membership_expires_at
                else:
                    membership_days = TIER_DAYS
                    for other_benefit in benefits:
                        if other_benefit.get('benefitType') == 'membership':
                            membership_days = int((other_benefit.get('benefitJson') or {}).get('durationDays') or TIER_DAYS)
                            break
                    starts_at = datetime.now(timezone.utc)
                    expires_at = starts_at + timedelta(days=membership_days * quantity)
                payload = dict(extra_payload or {})
                payload['benefit'] = benefit_json
                cursor.execute(
                    '''
                    insert into user_entitlements (
                      id, user_id, source_type, source_id, entitlement_type, entitlement_code, status, starts_at, expires_at, payload_json, created_at, updated_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), now())
                    ''',
                    (
                        build_object_id('entitlement'),
                        user_id,
                        source_type,
                        source_id,
                        'feature',
                        benefit_value or 'feature',
                        'active',
                        starts_at,
                        expires_at,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
                continue

    def create_order(self, *, user_id: str, sku_id: str, quantity: int = 1) -> dict[str, Any]:
        quantity = max(1, int(quantity or 1))
        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    bundle = self._fetch_sku_bundle(cursor, sku_id)
                    if not bundle:
                        raise ValueError('sku not found')

                    sku_row = bundle['sku']
                    if sku_row.get('status') != 'active' or sku_row.get('product_status') != 'active':
                        raise ValueError('sku unavailable')

                    # Validate tier purchase constraints (downgrade blocked)
                    for b in bundle.get('benefits', []):
                        if b.get('benefitType') == 'membership':
                            target_tier = (b.get('benefitValue') or '').lower()
                            if target_tier in TIER_RANK:
                                self._validate_tier_purchase(cursor, user_id, target_tier)
                            break

                    order_id = build_object_id('order')
                    order_no = _build_business_no('ORD')
                    unit_price = Decimal(sku_row.get('sale_price') or 0)
                    total_price = unit_price * quantity
                    now = datetime.now(timezone.utc)

                    cursor.execute(
                        '''
                        insert into orders (
                          id, order_no, user_id, status, total_amount, payable_amount, paid_amount, currency, payment_status, created_at, updated_at
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''',
                        (order_id, order_no, user_id, 'pending', total_price, total_price, None, sku_row.get('currency') or 'CNY', 'pending', now, now),
                    )
                    cursor.execute(
                        '''
                        insert into order_items (
                          id, order_id, product_id, sku_id, product_name, sku_name, quantity, unit_price, total_price, benefit_snapshot, created_at, updated_at
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                        ''',
                        (
                            build_object_id('order_item'),
                            order_id,
                            sku_row.get('product_id', ''),
                            sku_id,
                            sku_row.get('product_name', ''),
                            sku_row.get('name', ''),
                            quantity,
                            unit_price,
                            total_price,
                            json.dumps(bundle['benefits'], ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                    order_row = self._fetch_order_row(cursor, order_id)
                    return self._serialize_order_detail(cursor, order_row)

    def list_orders(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'select * from orders where user_id = %s order by created_at desc',
                    (user_id,),
                )
                rows = cursor.fetchall()
                return [self._serialize_order_detail(cursor, row) for row in rows]

    def list_orders_admin(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, int(limit or 100))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select *
                    from orders
                    order by created_at desc
                    limit %s
                    ''',
                    (limit,),
                )
                rows = cursor.fetchall()
                return [self._serialize_order_detail(cursor, row) for row in rows]

    def delete_orders_admin(self, order_ids: list[str]) -> int:
        if not order_ids:
            return 0
        with self._connect() as connection:
            with connection.cursor() as cursor:
                placeholders = ', '.join(['%s'] * len(order_ids))
                cursor.execute(f'delete from order_items where order_id in ({placeholders})', tuple(order_ids))
                cursor.execute(f'delete from payments where order_id in ({placeholders})', tuple(order_ids))
                cursor.execute(f'delete from orders where id in ({placeholders})', tuple(order_ids))
                deleted = cursor.rowcount
                return deleted

    def get_admin_overview(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('select count(*) as count from products')
                product_count = int((cursor.fetchone() or {}).get('count') or 0)

                cursor.execute("select count(*) as count from products where status = 'active'")
                active_product_count = int((cursor.fetchone() or {}).get('count') or 0)

                cursor.execute('select count(*) as count from orders')
                order_count = int((cursor.fetchone() or {}).get('count') or 0)

                cursor.execute("select count(*) as count from orders where status = 'paid'")
                paid_order_count = int((cursor.fetchone() or {}).get('count') or 0)

                cursor.execute("select coalesce(sum(paid_amount), 0) as total from orders where status = 'paid'")
                paid_amount_total = _to_amount((cursor.fetchone() or {}).get('total'))

                cursor.execute(
                    '''
                    select count(*) as count
                    from orders
                    where created_at >= date_trunc('day', now())
                    '''
                )
                today_order_count = int((cursor.fetchone() or {}).get('count') or 0)

                cursor.execute(
                    '''
                    select coalesce(sum(paid_amount), 0) as total
                    from orders
                    where status = 'paid'
                      and paid_at >= date_trunc('day', now())
                    '''
                )
                today_paid_amount_total = _to_amount((cursor.fetchone() or {}).get('total'))

                cursor.execute(
                    '''
                    select count(distinct user_id) as count
                    from user_entitlements
                    where entitlement_type = 'membership'
                      and status = 'active'
                      and starts_at <= now()
                      and (expires_at is null or expires_at > now())
                    '''
                )
                active_member_count = int((cursor.fetchone() or {}).get('count') or 0)

        return {
            'productCount': product_count,
            'activeProductCount': active_product_count,
            'orderCount': order_count,
            'paidOrderCount': paid_order_count,
            'paidAmountTotal': paid_amount_total,
            'todayOrderCount': today_order_count,
            'todayPaidAmountTotal': today_paid_amount_total,
            'activeMemberCount': active_member_count,
        }

    def get_order(self, *, order_id: str, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._fetch_order_row(cursor, order_id, user_id)
                if not row:
                    return None
                return self._serialize_order_detail(cursor, row)

    def get_order_admin(self, order_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._fetch_order_row(cursor, order_id)
                if not row:
                    return None
                return self._serialize_order_detail(cursor, row)

    def get_order_by_order_no(self, order_no: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('select * from orders where order_no = %s limit 1', (order_no,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._serialize_order_detail(cursor, row)

    def start_payment_intent(self, *, order_id: str, user_id: str, payment_mode: str = 'mock') -> dict[str, Any]:
        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    order_row = self._fetch_order_row(cursor, order_id, user_id)
                    if not order_row:
                        raise ValueError('order not found')
                    if order_row.get('status') == 'paid':
                        return {
                            'paymentMode': payment_mode,
                            'order': self._serialize_order_detail(cursor, order_row),
                            'alreadyPaid': True,
                        }

                    items = self._fetch_order_items(cursor, order_id)
                    description = '订单支付'
                    if items:
                        description = items[0].get('product_name') or items[0].get('sku_name') or description
                    payment_id = build_object_id('payment')
                    payment_no = _build_business_no('PAY')
                    now = datetime.now(timezone.utc)
                    cursor.execute(
                        '''
                        insert into payments (
                          id, payment_no, order_id, user_id, channel, status, amount, channel_trade_no, channel_payload, created_at, updated_at
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                        ''',
                        (
                            payment_id,
                            payment_no,
                            order_id,
                            user_id,
                            'wechat_pay',
                            'pending',
                            order_row.get('payable_amount'),
                            None,
                            json.dumps({
                                'paymentMode': payment_mode,
                            }, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                    return {
                        'paymentMode': payment_mode,
                        'paymentId': payment_id,
                        'paymentNo': payment_no,
                        'orderId': order_id,
                        'orderNo': order_row.get('order_no', ''),
                        'description': description,
                        'amount': _to_amount(order_row.get('payable_amount')),
                        'currency': order_row.get('currency', 'CNY'),
                        'order': self._serialize_order_detail(cursor, order_row),
                        'alreadyPaid': False,
                    }

    def update_payment_channel_payload(
        self,
        *,
        payment_id: str,
        channel_payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute('select * from payments where id = %s limit 1', (payment_id,))
                    row = cursor.fetchone()
                    if not row:
                        return None
                    payload = (row.get('channel_payload') or {}) | (channel_payload or {})
                    cursor.execute(
                        '''
                        update payments
                        set channel_payload = %s::jsonb,
                            updated_at = now()
                        where id = %s
                        returning *
                        ''',
                        (json.dumps(payload, ensure_ascii=False), payment_id),
                    )
                    return _serialize_payment(cursor.fetchone())

    def create_payment_intent(self, *, order_id: str, user_id: str, payment_mode: str = 'mock') -> dict[str, Any]:
        started = self.start_payment_intent(order_id=order_id, user_id=user_id, payment_mode=payment_mode)
        if started.get('alreadyPaid'):
            return started
        nonce = secrets.token_hex(8)
        package_value = f'mock_{started.get("paymentNo", "")}'
        payload = {
            'paymentMode': payment_mode,
            'timeStamp': str(int(time.time())),
            'nonceStr': nonce,
            'package': f'prepay_id={package_value}',
            'signType': 'RSA',
            'paySign': f'mock_sign_{nonce}',
        }
        self.update_payment_channel_payload(payment_id=started.get('paymentId', ''), channel_payload=payload)
        return {
            'paymentMode': payment_mode,
            'paymentId': started.get('paymentId', ''),
            'orderId': order_id,
            'requestPayment': {
                'timeStamp': payload.get('timeStamp', ''),
                'nonceStr': payload.get('nonceStr', ''),
                'package': payload.get('package', ''),
                'signType': payload.get('signType', 'RSA'),
                'paySign': payload.get('paySign', ''),
            },
            'order': started.get('order', {}),
            'alreadyPaid': False,
        }

    def complete_wechat_payment(
        self,
        *,
        order_no: str,
        transaction_id: str,
        payment_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payment_payload = payment_payload or {}
        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute('select * from orders where order_no = %s limit 1', (order_no,))
                    order_row = cursor.fetchone()
                    if not order_row:
                        raise ValueError('order not found')
                    if order_row.get('status') == 'paid':
                        return self._serialize_order_detail(cursor, order_row)

                    cursor.execute(
                        '''
                        select *
                        from payments
                        where order_id = %s
                        order by created_at desc
                        limit 1
                        ''',
                        (order_row.get('id', ''),),
                    )
                    payment_row = cursor.fetchone()
                    if not payment_row:
                        raise ValueError('payment not found')

                    channel_payload = (payment_row.get('channel_payload') or {}) | payment_payload
                    now = datetime.now(timezone.utc)
                    cursor.execute(
                        '''
                        update payments
                        set status = %s,
                            channel_trade_no = %s,
                            channel_payload = %s::jsonb,
                            paid_at = %s,
                            updated_at = %s
                        where id = %s
                        ''',
                        (
                            'success',
                            transaction_id,
                            json.dumps(channel_payload, ensure_ascii=False),
                            now,
                            now,
                            payment_row.get('id', ''),
                        ),
                    )
                    cursor.execute(
                        '''
                        update orders
                        set status = %s,
                            payment_status = %s,
                            paid_amount = payable_amount,
                            paid_at = %s,
                            updated_at = %s
                        where id = %s
                        ''',
                        ('paid', 'success', now, now, order_row.get('id', '')),
                    )
                    order_row = self._fetch_order_row(cursor, order_row.get('id', ''))
                    items = self._fetch_order_items(cursor, order_row.get('id', ''))
                    self._grant_benefits_for_order(cursor, order_row, items)
                    return self._serialize_order_detail(cursor, order_row)

    def complete_mock_payment(self, *, order_id: str, user_id: str, payment_id: str = '') -> dict[str, Any]:
        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    order_row = self._fetch_order_row(cursor, order_id, user_id)
                    if not order_row:
                        raise ValueError('order not found')
                    if order_row.get('status') == 'paid':
                        return self._serialize_order_detail(cursor, order_row)

                    if payment_id:
                        cursor.execute(
                            'select * from payments where id = %s and order_id = %s and user_id = %s limit 1',
                            (payment_id, order_id, user_id),
                        )
                    else:
                        cursor.execute(
                            '''
                            select *
                            from payments
                            where order_id = %s and user_id = %s
                            order by created_at desc
                            limit 1
                            ''',
                            (order_id, user_id),
                        )
                    payment_row = cursor.fetchone()
                    if not payment_row:
                        raise ValueError('payment not found')

                    now = datetime.now(timezone.utc)
                    cursor.execute(
                        '''
                        update payments
                        set status = %s, channel_trade_no = %s, paid_at = %s, updated_at = %s
                        where id = %s
                        ''',
                        ('success', f'mock_trade_{payment_row.get("payment_no", "")}', now, now, payment_row.get('id', '')),
                    )
                    cursor.execute(
                        '''
                        update orders
                        set status = %s, payment_status = %s, paid_amount = payable_amount, paid_at = %s, updated_at = %s
                        where id = %s
                        ''',
                        ('paid', 'success', now, now, order_id),
                    )
                    order_row = self._fetch_order_row(cursor, order_id, user_id)
                    items = self._fetch_order_items(cursor, order_id)
                    self._grant_benefits_for_order(cursor, order_row, items)
                    return self._serialize_order_detail(cursor, order_row)

    # ------------------------------------------------------------------
    # CDK (Card Key) methods
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_cdk_code(prefix: str) -> str:
        charset = string.ascii_uppercase + string.digits
        groups = [''.join(random.choices(charset, k=4)) for _ in range(4)]
        return f'{prefix}-{groups[0]}-{groups[1]}-{groups[2]}-{groups[3]}'

    @staticmethod
    def _sku_code_to_prefix(sku_code: str) -> str:
        mapping = {
            'tier_pro': 'PRO',
            'tier_plus': 'PLUS',
            'tier_max': 'MAX',
        }
        for key, prefix in mapping.items():
            if sku_code.startswith(key):
                return prefix
        return 'CDK'

    def generate_cdk_batch(self, *, sku_id: str, quantity: int, note: str = '', batch_id: str | None = None) -> list[dict[str, Any]]:
        batch_id = batch_id or build_object_id('batch')
        results: list[dict[str, Any]] = []

        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    sku_bundle = self._fetch_sku_bundle(cursor, sku_id)
                    if not sku_bundle:
                        raise ValueError(f'SKU not found: {sku_id}')
                    sku_row = sku_bundle['sku']
                    sku_code = sku_row.get('sku_code', '')
                    prefix = self._sku_code_to_prefix(sku_code)

                    for _ in range(quantity):
                        cdk_id = build_object_id('cdk')
                        code = self._generate_cdk_code(prefix)
                        cursor.execute(
                            '''
                            insert into cdk_codes (id, code, sku_id, status, batch_id, note, created_at, updated_at)
                            values (%s, %s, %s, %s, %s, %s, now(), now())
                            returning *
                            ''',
                            (cdk_id, code, sku_id, 'unused', batch_id, note),
                        )
                        row = cursor.fetchone()
                        if row:
                            row['sku_name'] = sku_row.get('name', '')
                            results.append(_serialize_cdk(row))

        return results

    def list_cdk_codes(self, *, status: str = '', sku_id: str = '', limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                clauses = []
                params: list[Any] = []
                if status:
                    clauses.append('c.status = %s')
                    params.append(status)
                if sku_id:
                    clauses.append('c.sku_id = %s')
                    params.append(sku_id)
                where = f'where {" and ".join(clauses)}' if clauses else ''

                cursor.execute(
                    f'''
                    select c.*, s.name as sku_name
                    from cdk_codes c
                    left join product_skus s on s.id = c.sku_id
                    {where}
                    order by c.created_at desc
                    limit %s offset %s
                    ''',
                    params + [limit, offset],
                )
                return [_serialize_cdk(row) for row in cursor.fetchall()]

    def get_cdk_by_code(self, code: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select c.*, s.name as sku_name
                    from cdk_codes c
                    left join product_skus s on s.id = c.sku_id
                    where c.code = %s
                    limit 1
                    ''',
                    (code,),
                )
                row = cursor.fetchone()
                return _serialize_cdk(row) if row else None

    def list_user_cdk_redemptions(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select c.*, s.name as sku_name
                    from cdk_codes c
                    left join product_skus s on s.id = c.sku_id
                    where c.redeemed_by = %s and c.status = 'redeemed'
                    order by c.redeemed_at desc
                    ''',
                    (user_id,),
                )
                return [_serialize_cdk(row) for row in cursor.fetchall()]

    def redeem_cdk(self, *, code: str, user_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        'select * from cdk_codes where code = %s for update',
                        (code,),
                    )
                    cdk_row = cursor.fetchone()
                    if not cdk_row:
                        raise ValueError('卡密不存在')
                    if cdk_row.get('status') != 'unused':
                        raise ValueError('卡密已被使用或已失效')

                    now = datetime.now(timezone.utc)
                    cursor.execute(
                        '''
                        update cdk_codes
                        set status = %s, redeemed_by = %s, redeemed_at = %s, updated_at = %s
                        where id = %s
                        ''',
                        ('redeemed', user_id, now, now, cdk_row.get('id', '')),
                    )

                    sku_bundle = self._fetch_sku_bundle(cursor, cdk_row.get('sku_id', ''))
                    if not sku_bundle:
                        raise ValueError('SKU not found for CDK')
                    benefits = sku_bundle.get('benefits', [])
                    sku_row = sku_bundle.get('sku', {})

                    self._grant_sku_benefits(
                        cursor,
                        user_id=user_id,
                        benefits=benefits,
                        quantity=1,
                        source_type='cdk',
                        source_id=cdk_row.get('id', ''),
                        extra_payload={'cdkId': cdk_row.get('id', ''), 'cdkCode': code},
                        sku_name=sku_row.get('name', ''),
                        reason_remark=f'CDK redemption: {code}',
                    )

                    cursor.execute(
                        '''
                        select c.*, s.name as sku_name
                        from cdk_codes c
                        left join product_skus s on s.id = c.sku_id
                        where c.id = %s
                        ''',
                        (cdk_row.get('id', ''),),
                    )
                    updated = cursor.fetchone()
                    return _serialize_cdk(updated) if updated else {}

    def delete_cdk_batch(self, cdk_ids: list[str]) -> int:
        if not cdk_ids:
            return 0
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'delete from cdk_codes where id = any(%s)',
                    (cdk_ids,),
                )
                return cursor.rowcount
