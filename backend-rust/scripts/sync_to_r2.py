#!/usr/bin/env python3
"""Sync valid scene files from local disk to Cloudflare R2."""

import os
import sys
import json
import subprocess

import boto3
from botocore.config import Config

LOCAL_ROOT = "/www/wwwroot/stag.cps.vin/weixin-demo-01/assets"
R2_ACCOUNT_ID = "917624716dbc5b97ca049f77f3d2b422"
R2_ACCESS_KEY_ID = "843814a57684175715c6f7d56308e17d"
R2_BUCKET = "wx-cjrh"


def get_db_url():
    with open("/www/wwwroot/stag.cps.vin/weixin-demo-01/backend-rust/env") as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                return line.strip().split("=", 1)[1]
    return None


def run_sql(sql):
    dburl = get_db_url() or ""
    import re
    m = re.search(r"://[^:]*:([^@]+)@", dburl)
    pgpass = m.group(1) if m else ""
    r = subprocess.run(
        ["psql", "-h", "localhost", "-U", "postgres", "-d", "weixin_saas_rust", "-t", "-A", "-c", sql],
        capture_output=True, text=True, env={**os.environ, "PGPASSWORD": pgpass},
    )
    return [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]


def main():
    # Get R2 secret
    rows = run_sql("SELECT config->>'secret_access_key' FROM storage_configs WHERE backend_id='r2';")
    secret = rows[0] if rows else None
    if not secret:
        print("ERROR: Cannot find R2 secret"); sys.exit(1)

    # Get active scene dirs
    dirs = run_sql("SELECT DISTINCT substring(background_path from 'generated/([^/]+)') FROM scenes WHERE background_path LIKE '%generated%' AND background_path != '';")
    print(f"Scene dirs from DB: {len(dirs)}")

    # Build file list
    files = []
    for d in dirs:
        local_dir = os.path.join(LOCAL_ROOT, "generated", d)
        if not os.path.isdir(local_dir):
            continue
        for fname in os.listdir(local_dir):
            fpath = os.path.join(local_dir, fname)
            if os.path.isfile(fpath):
                files.append((fpath, f"generated/{d}/{fname}"))

    print(f"Files to upload: {len(files)}")

    s3 = boto3.client("s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=secret,
        config=Config(signature_version="s3v4"),
        region_name="auto")

    ct_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
              ".mp3": "audio/mpeg", ".mp4": "video/mp4", ".webp": "image/webp"}

    uploaded = errors = 0
    for i, (path, key) in enumerate(files):
        ext = os.path.splitext(path)[1].lower()
        ct = ct_map.get(ext, "application/octet-stream")
        try:
            s3.upload_file(path, R2_BUCKET, key, ExtraArgs={"ContentType": ct})
            uploaded += 1
            if uploaded <= 3 or uploaded % 50 == 0:
                print(f"  [{uploaded}/{len(files)}] {key}", flush=True)
        except Exception as e:
            errors += 1
            print(f"  ERROR: {key}: {e}", flush=True)

    print(f"\nDone: uploaded={uploaded} errors={errors}", flush=True)


if __name__ == "__main__":
    main()
