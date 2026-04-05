import json
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from .commerce_postgres_schema import ensure_commerce_postgres_schema
from .postgres import connect_postgres
from .store_utils import build_object_id, utcnow_iso


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

    def list_user_entitlements(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    select *
                    from user_entitlements
                    where user_id = %s
                    order by created_at desc
                    ''',
                    (user_id,),
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
            for benefit in benefits:
                benefit_type = benefit.get('benefitType', '')
                benefit_value = benefit.get('benefitValue', '')
                benefit_json = benefit.get('benefitJson') or {}

                if benefit_type == 'membership':
                    duration_days = int(benefit_json.get('durationDays') or 0)
                    starts_at = datetime.now(timezone.utc)
                    expires_at = starts_at if duration_days <= 0 else starts_at + timedelta(days=duration_days * quantity)
                    cursor.execute(
                        '''
                        insert into user_entitlements (
                          id, user_id, source_type, source_id, entitlement_type, entitlement_code, status, starts_at, expires_at, payload_json, created_at, updated_at
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), now())
                        ''',
                        (
                            build_object_id('entitlement'),
                            order_row.get('user_id', ''),
                            'order',
                            order_row.get('id', ''),
                            'membership',
                            benefit_value or 'membership',
                            'active',
                            starts_at,
                            expires_at,
                            json.dumps({
                                'orderId': order_row.get('id', ''),
                                'skuName': item.get('sku_name', ''),
                                'benefit': benefit_json,
                            }, ensure_ascii=False),
                        ),
                    )
                    continue

                if benefit_type == 'credits':
                    credit_type = benefit_json.get('creditType') or benefit_value or 'scene_generation_credits'
                    amount = int(benefit_json.get('amount') or 0) * quantity
                    cursor.execute(
                        'select * from user_credit_accounts where user_id = %s and credit_type = %s limit 1',
                        (order_row.get('user_id', ''), credit_type),
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
                            (account_id, order_row.get('user_id', ''), credit_type, balance_after, 0),
                        )

                    cursor.execute(
                        '''
                        insert into credit_ledger (
                          id, user_id, credit_type, change_amount, balance_after, reason_type, reason_id, remark, created_at
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, now())
                        ''',
                        (
                            build_object_id('ledger'),
                            order_row.get('user_id', ''),
                            credit_type,
                            amount,
                            balance_after,
                            'order_grant',
                            order_row.get('id', ''),
                            f'mock payment grant via order {order_row.get("order_no", "")}',
                        ),
                    )

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

    def get_order(self, *, order_id: str, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._fetch_order_row(cursor, order_id, user_id)
                if not row:
                    return None
                return self._serialize_order_detail(cursor, row)

    def create_payment_intent(self, *, order_id: str, user_id: str, payment_mode: str = 'mock') -> dict[str, Any]:
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

                    payment_id = build_object_id('payment')
                    payment_no = _build_business_no('PAY')
                    now = datetime.now(timezone.utc)
                    nonce = secrets.token_hex(8)
                    package_value = f'prepay_id=mock_{payment_no}'
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
                                'timeStamp': str(int(now.timestamp())),
                                'nonceStr': nonce,
                                'package': package_value,
                                'signType': 'RSA',
                                'paySign': f'mock_sign_{nonce}',
                            }, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                    cursor.execute('select * from payments where id = %s limit 1', (payment_id,))
                    payment_row = cursor.fetchone()
                    payload = payment_row.get('channel_payload') or {}
                    return {
                        'paymentMode': payment_mode,
                        'paymentId': payment_id,
                        'orderId': order_id,
                        'requestPayment': {
                            'timeStamp': payload.get('timeStamp', ''),
                            'nonceStr': payload.get('nonceStr', ''),
                            'package': payload.get('package', ''),
                            'signType': payload.get('signType', 'RSA'),
                            'paySign': payload.get('paySign', ''),
                        },
                        'order': self._serialize_order_detail(cursor, order_row),
                        'alreadyPaid': False,
                    }

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
