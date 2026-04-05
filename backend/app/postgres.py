import re
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier


_SCHEMA_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def normalize_schema_name(schema_name: str | None) -> str:
    value = (schema_name or 'public').strip() or 'public'
    if not _SCHEMA_PATTERN.fullmatch(value):
        raise ValueError(f'invalid schema name: {value}')
    return value


@contextmanager
def connect_postgres(database_url: str, schema_name: str = 'public') -> Iterator[psycopg.Connection]:
    schema = normalize_schema_name(schema_name)
    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(SQL('create schema if not exists {}').format(Identifier(schema)))
            cursor.execute(SQL('set search_path to {}, public').format(Identifier(schema)))
        yield connection
