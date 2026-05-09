-- Storage backend configurations
CREATE TABLE IF NOT EXISTS storage_configs (
    id           SERIAL PRIMARY KEY,
    backend_id   VARCHAR(32) NOT NULL UNIQUE,
    name         VARCHAR(100) NOT NULL,
    backend_type VARCHAR(32) NOT NULL,
    enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    config       JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO storage_configs (backend_id, name, backend_type, enabled, config) VALUES
    ('local', '本地存储', 'local', true, '{"root_dir": "assets"}'),
    ('r2', 'Cloudflare R2', 'r2', false, '{}'),
    ('cos', '腾讯云 COS', 'cos', false, '{}')
ON CONFLICT (backend_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS storage_active (
    id         SERIAL PRIMARY KEY,
    backend_id VARCHAR(32) NOT NULL DEFAULT 'local',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO storage_active (backend_id) VALUES ('local')
ON CONFLICT DO NOTHING;
