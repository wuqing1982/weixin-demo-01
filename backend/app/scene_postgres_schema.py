SCENE_POSTGRES_SCHEMA_SQL = """
create table if not exists scenes (
  scene_id       varchar(128) primary key,
  title          varchar(255) not null default '',
  category       varchar(64)  not null default '',
  visibility     varchar(32)  not null default 'public',
  scene_type     varchar(32)  not null default 'public',
  cover_path     text         not null default '',
  background_path text        not null default '',
  items          jsonb        not null default '[]'::jsonb,
  verbs          jsonb        not null default '[]'::jsonb,
  meta_json      jsonb        not null default '{}'::jsonb,
  owner_id       varchar(128),
  created_at     timestamptz  not null default now(),
  updated_at     timestamptz  not null default now()
);

create index if not exists idx_scenes_scene_type  on scenes(scene_type);
create index if not exists idx_scenes_owner_id    on scenes(owner_id) where owner_id is not null;
create index if not exists idx_scenes_category    on scenes(category);
create index if not exists idx_scenes_created_at  on scenes(created_at desc);
""".strip()


def ensure_scene_postgres_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(SCENE_POSTGRES_SCHEMA_SQL)
