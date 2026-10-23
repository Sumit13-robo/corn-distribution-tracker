"""Template context shared by every page."""

from __future__ import annotations

from .models import Delivery


def pending_review(request) -> dict[str, int]:
    if request.user.is_authenticated and request.user.is_admin:
        return {
            "pending_review_count": Delivery.objects.filter(
                status=Delivery.Status.SUBMITTED
            ).count()
        }
    return {"pending_review_count": 0}
