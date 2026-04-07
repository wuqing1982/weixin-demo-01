-- Scene storage schema
-- Used by PostgresSceneStore for both public and generated scenes.

CREATE TABLE IF NOT EXISTS scenes (
  scene_id       varchar(128) PRIMARY KEY,
  title          varchar(255) NOT NULL DEFAULT '',
  category       varchar(64)  NOT NULL DEFAULT '',
  visibility     varchar(32)  NOT NULL DEFAULT 'public',
  scene_type     varchar(32)  NOT NULL DEFAULT 'public',
  cover_path     text         NOT NULL DEFAULT '',
  background_path text        NOT NULL DEFAULT '',
  items          jsonb        NOT NULL DEFAULT '[]'::jsonb,
  verbs          jsonb        NOT NULL DEFAULT '[]'::jsonb,
  meta_json      jsonb        NOT NULL DEFAULT '{}'::jsonb,
  owner_id       varchar(128),
  created_at     timestamptz  NOT NULL DEFAULT now(),
  updated_at     timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scenes_scene_type  ON scenes(scene_type);
CREATE INDEX IF NOT EXISTS idx_scenes_owner_id    ON scenes(owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_scenes_category    ON scenes(category);
CREATE INDEX IF NOT EXISTS idx_scenes_created_at  ON scenes(created_at DESC);
