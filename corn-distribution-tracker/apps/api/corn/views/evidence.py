"""Evidence upload intents, private object ingestion and signed view URLs."""

from __future__ import annotations

import uuid

from django.db import transaction
from django.http import HttpResponse
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import BaseParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..errors import NotFoundError, RateLimitedError
from ..models import UploadIntent
from ..rate_limit import hit
from ..services import evidence as evidence_service
from ..storage import verify_blob_signature
from .helpers import json_response, response_ctx


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_upload_intent(request):
    from ..serializers import UploadIntentSerializer

    serializer = UploadIntentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    allowed, retry_after = hit("evidence.upload_intent", str(request.user.id))
    if not allowed:
        raise RateLimitedError(retry_after=retry_after)
    data = serializer.validated_data
    with transaction.atomic():
        intent, upload_url, upload_headers = evidence_service.create_upload_intent(
            user=request.user,
            content_type=data["content_type"],
            purpose=data["purpose"],
            ctx=response_ctx(request),
        )
    if upload_url is None:
        upload_url = f"/api/v1/evidence/objects/{intent.id}"
    return json_response(
        {
            "intent_id": intent.id,
            "expires_at": intent.expires_at,
            "upload_method": "PUT",
            "upload_url": upload_url,
            "headers": upload_headers,
        },
        status=201,
    )


class RawBodyParser(BaseParser):
    media_type = "*/*"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


@api_view(["PUT"])
@parser_classes([RawBodyParser])
@permission_classes([IsAuthenticated])
def put_object(request, intent_id: uuid.UUID):
    intent = UploadIntent.objects.filter(id=intent_id).first()
    if intent is None or intent.user_id != request.user.id:
        raise NotFoundError("Upload intent not found.")
    with transaction.atomic():
        evidence_service.store_intent_upload(
            intent=intent,
            data=request.body,
            content_type=intent.content_type,
        )
    return Response(status=204)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_upload_intent(request, intent_id: uuid.UUID):
    """Verify a direct-to-object-storage upload before it can become evidence."""
    with transaction.atomic():
        intent = (
            UploadIntent.objects.select_for_update()
            .filter(id=intent_id, user_id=request.user.id)
            .first()
        )
        if intent is None:
            raise NotFoundError("Upload intent not found.")
        intent, completed = evidence_service.finalize_intent_upload(
            intent=intent, ctx=response_ctx(request)
        )
    return json_response(
        {
            "intent_id": intent.id,
            "completed": True,
            "newly_verified": completed,
            "size_bytes": intent.received_bytes,
            "sha256_hex": intent.received_sha256_hex,
            "content_type": intent.content_type,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_url(request, evidence_id: uuid.UUID):
    with transaction.atomic():
        payload = evidence_service.issue_view_url(
            user=request.user, evidence_id=evidence_id, ctx=response_ctx(request)
        )
    return json_response(payload)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def blob(request, evidence_id: uuid.UUID):
    raw_exp = request.query_params.get("exp", "")
    signature = request.query_params.get("sig", "")
    try:
        expires = int(raw_exp)
    except ValueError:
        expires = 0
    if not verify_blob_signature(str(evidence_id), expires, signature):
        return json_response(
            {"error": {"code": "FORBIDDEN", "message": "Signature invalid or expired.", "details": []}},
            status=403,
        )
    data, content_type = evidence_service.load_evidence_bytes(evidence_id=evidence_id)
    response = HttpResponse(data, content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    response["Content-Disposition"] = "inline"
    return response
