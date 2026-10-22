"""Append-only database guards for the stock ledger and audit trail.

The services never update or delete posted movements/audit events, but the
database enforces the invariant even for future code, scripts or mistakes.
Django's test flush uses TRUNCATE and is unaffected.
"""

from __future__ import annotations

from django.db import migrations

FORWARD = r"""
CREATE OR REPLACE FUNCTION corn_prevent_append_only_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'append-only relation % cannot be modified', TG_TABLE_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS stock_movements_append_only ON stock_movements;
CREATE TRIGGER stock_movements_append_only
    BEFORE UPDATE OR DELETE ON stock_movements
    FOR EACH ROW EXECUTE FUNCTION corn_prevent_append_only_mutation();

DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events;
CREATE TRIGGER audit_events_append_only
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION corn_prevent_append_only_mutation();
"""

REVERSE = r"""
DROP TRIGGER IF EXISTS stock_movements_append_only ON stock_movements;
DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events;
DROP FUNCTION IF EXISTS corn_prevent_append_only_mutation();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("corn", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FORWARD, REVERSE),
    ]
