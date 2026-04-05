AUTH_POSTGRES_SCHEMA_SQL = """
create table if not exists users (
  id varchar(128) primary key,
  status varchar(32) not null default 'active',
  display_name varchar(120),
  avatar_url text,
  mobile varchar(32),
  mobile_verified boolean not null default false,
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_users_mobile on users(mobile);
create index if not exists idx_users_status on users(status);

create table if not exists user_identities (
  id varchar(128) primary key,
  user_id varchar(128) not null references users(id),
  provider varchar(32) not null,
  provider_uid varchar(128) not null,
  union_id varchar(128),
  session_key_encrypted text,
  meta_json jsonb not null default '{}'::jsonb,
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(provider, provider_uid)
);

create index if not exists idx_user_identities_user_id on user_identities(user_id);
create index if not exists idx_user_identities_union_id on user_identities(union_id);
create index if not exists idx_user_identities_provider_union_id on user_identities(provider, union_id);

create table if not exists auth_refresh_tokens (
  id varchar(128) primary key,
  user_id varchar(128) not null references users(id),
  token_hash varchar(255) not null unique,
  device_type varchar(32),
  device_id varchar(128),
  app_version varchar(32),
  ip inet,
  user_agent text,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_auth_refresh_tokens_user_id on auth_refresh_tokens(user_id);
create index if not exists idx_auth_refresh_tokens_expires_at on auth_refresh_tokens(expires_at);

create table if not exists user_mobile_bind_logs (
  id varchar(128) primary key,
  user_id varchar(128) not null references users(id),
  mobile varchar(32) not null,
  bind_source varchar(32) not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_user_mobile_bind_logs_user_id on user_mobile_bind_logs(user_id);
""".strip()


def ensure_auth_postgres_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(AUTH_POSTGRES_SCHEMA_SQL)
