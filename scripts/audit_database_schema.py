"""Read-only comparison of Django's managed models with the connected database.

Run against a restored production clone, never by pointing development commands at
the live primary database. Exit code 1 means the schema cannot be baselined safely.
"""

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import connection  # noqa: E402


def main():
    expected = {
        model._meta.db_table: {
            field.column
            for field in model._meta.local_fields
            if field.column
        }
        for model in apps.get_models()
        if model._meta.managed and not model._meta.proxy
    }
    with connection.cursor() as cursor:
        actual_tables = set(connection.introspection.table_names(cursor))
        actual_columns = {
            table: {
                column.name
                for column in connection.introspection.get_table_description(cursor, table)
            }
            for table in actual_tables
        }

    missing_tables = sorted(set(expected) - actual_tables)
    column_drift = {
        table: {
            'missing': sorted(columns - actual_columns.get(table, set())),
            'unexpected': sorted(actual_columns.get(table, set()) - columns),
        }
        for table, columns in expected.items()
        if table in actual_tables and columns != actual_columns.get(table, set())
    }
    report = {
        'database_vendor': connection.vendor,
        'missing_tables': missing_tables,
        'column_drift': column_drift,
        'safe_to_prepare_baseline': not missing_tables and not column_drift,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['safe_to_prepare_baseline'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
