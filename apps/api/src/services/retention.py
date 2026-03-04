"""GDPR retention: document expiry and cleanup.

Single place for retention logic (DRY): compute_expires_at is used when
creating documents; delete_document_files and run_retention_cleanup
are used by the cleanup script and DELETE /v1/users/me.
"""

from datetime import datetime, timedelta


def compute_expires_at(retention_days: int) -> datetime:
    """Compute expiry datetime as now + retention_days (UTC, naive).

    Used when creating documents so expiry lives in one place.
    """
    return datetime.utcnow() + timedelta(days=retention_days)
