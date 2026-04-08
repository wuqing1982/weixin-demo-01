-- CDK (Card Key) system for membership redemption
-- Run this after commerce_postgres_schema.sql (depends on product_skus table)

CREATE TABLE IF NOT EXISTS cdk_codes (
    id          varchar(128) PRIMARY KEY,
    code        varchar(64)  NOT NULL UNIQUE,
    sku_id      varchar(128) NOT NULL REFERENCES product_skus(id),
    status      varchar(32)  NOT NULL DEFAULT 'unused',
    batch_id    varchar(128),
    redeemed_by varchar(128),
    redeemed_at timestamptz,
    note        text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cdk_codes_status ON cdk_codes(status);
CREATE INDEX IF NOT EXISTS idx_cdk_codes_sku_id ON cdk_codes(sku_id);
CREATE INDEX IF NOT EXISTS idx_cdk_codes_batch_id ON cdk_codes(batch_id);
CREATE INDEX IF NOT EXISTS idx_cdk_codes_redeemed_by ON cdk_codes(redeemed_by);
