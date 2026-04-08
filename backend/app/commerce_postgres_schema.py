COMMERCE_POSTGRES_SCHEMA_SQL = """
create table if not exists products (
  id varchar(128) primary key,
  product_code varchar(64) not null unique,
  product_type varchar(32) not null,
  name varchar(128) not null,
  subtitle varchar(255) not null default '',
  description text not null default '',
  status varchar(32) not null default 'draft',
  cover_url text not null default '',
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists product_skus (
  id varchar(128) primary key,
  product_id varchar(128) not null references products(id),
  sku_code varchar(64) not null unique,
  name varchar(128) not null,
  billing_type varchar(32) not null,
  duration_days int,
  status varchar(32) not null default 'draft',
  list_price numeric(10,2) not null default 0,
  sale_price numeric(10,2) not null default 0,
  currency varchar(16) not null default 'CNY',
  stock_type varchar(32) not null default 'unlimited',
  stock_count int,
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists sku_benefits (
  id varchar(128) primary key,
  sku_id varchar(128) not null references product_skus(id),
  benefit_type varchar(64) not null,
  benefit_value varchar(128) not null default '',
  benefit_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_product_skus_product_id on product_skus(product_id);
create index if not exists idx_sku_benefits_sku_id on sku_benefits(sku_id);

create table if not exists user_entitlements (
  id varchar(128) primary key,
  user_id varchar(128) not null,
  source_type varchar(32) not null,
  source_id varchar(128),
  entitlement_type varchar(64) not null,
  entitlement_code varchar(64) not null,
  status varchar(32) not null default 'active',
  starts_at timestamptz not null,
  expires_at timestamptz,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_user_entitlements_user_id on user_entitlements(user_id);
create index if not exists idx_user_entitlements_code on user_entitlements(entitlement_code);

create table if not exists user_credit_accounts (
  id varchar(128) primary key,
  user_id varchar(128) not null,
  credit_type varchar(64) not null,
  balance int not null default 0,
  frozen_balance int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, credit_type)
);

create table if not exists credit_ledger (
  id varchar(128) primary key,
  user_id varchar(128) not null,
  credit_type varchar(64) not null,
  change_amount int not null,
  balance_after int not null,
  reason_type varchar(64) not null,
  reason_id varchar(128),
  remark text,
  created_at timestamptz not null default now()
);

create index if not exists idx_credit_ledger_user_id on credit_ledger(user_id);

create table if not exists orders (
  id varchar(128) primary key,
  order_no varchar(64) not null unique,
  user_id varchar(128) not null,
  status varchar(32) not null default 'pending',
  total_amount numeric(10,2) not null,
  payable_amount numeric(10,2) not null,
  paid_amount numeric(10,2),
  currency varchar(16) not null default 'CNY',
  payment_status varchar(32) not null default 'pending',
  paid_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists order_items (
  id varchar(128) primary key,
  order_id varchar(128) not null references orders(id),
  product_id varchar(128) not null references products(id),
  sku_id varchar(128) not null references product_skus(id),
  product_name varchar(128) not null,
  sku_name varchar(128) not null,
  quantity int not null default 1,
  unit_price numeric(10,2) not null,
  total_price numeric(10,2) not null,
  benefit_snapshot jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists payments (
  id varchar(128) primary key,
  payment_no varchar(64) not null unique,
  order_id varchar(128) not null references orders(id),
  user_id varchar(128) not null,
  channel varchar(32) not null,
  status varchar(32) not null default 'pending',
  amount numeric(10,2) not null,
  channel_trade_no varchar(128),
  channel_payload jsonb not null default '{}'::jsonb,
  paid_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_orders_user_id on orders(user_id);
create index if not exists idx_orders_status on orders(status);
create index if not exists idx_order_items_order_id on order_items(order_id);
create index if not exists idx_payments_order_id on payments(order_id);

create table if not exists scene_categories (
  id varchar(128) primary key,
  category_code varchar(64) not null unique,
  name varchar(128) not null,
  description text not null default '',
  status varchar(32) not null default 'active',
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists scene_collections (
  id varchar(128) primary key,
  collection_code varchar(64) not null unique,
  name varchar(128) not null,
  description text not null default '',
  status varchar(32) not null default 'active',
  cover_url text not null default '',
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists scene_publications (
  source_generated_scene_id varchar(128) primary key,
  public_scene_id varchar(128) not null unique,
  category_id varchar(128) references scene_categories(id),
  visibility varchar(32) not null default 'public',
  published_by varchar(128) not null,
  published_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists scene_publication_collections (
  id varchar(128) primary key,
  public_scene_id varchar(128) not null,
  collection_id varchar(128) not null references scene_collections(id),
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(public_scene_id, collection_id)
);

create index if not exists idx_scene_categories_status on scene_categories(status);
create index if not exists idx_scene_collections_status on scene_collections(status);
create index if not exists idx_scene_publications_public_scene_id on scene_publications(public_scene_id);
create index if not exists idx_scene_publications_category_id on scene_publications(category_id);
create index if not exists idx_scene_publication_collections_public_scene_id on scene_publication_collections(public_scene_id);
create index if not exists idx_scene_publication_collections_collection_id on scene_publication_collections(collection_id);

create table if not exists cdk_codes (
  id varchar(128) primary key,
  code varchar(64) not null unique,
  sku_id varchar(128) not null references product_skus(id),
  status varchar(32) not null default 'unused',
  batch_id varchar(128),
  redeemed_by varchar(128),
  redeemed_at timestamptz,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_cdk_codes_status on cdk_codes(status);
create index if not exists idx_cdk_codes_sku_id on cdk_codes(sku_id);
create index if not exists idx_cdk_codes_batch_id on cdk_codes(batch_id);
create index if not exists idx_cdk_codes_redeemed_by on cdk_codes(redeemed_by);
""".strip()


def ensure_commerce_postgres_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(COMMERCE_POSTGRES_SCHEMA_SQL)
