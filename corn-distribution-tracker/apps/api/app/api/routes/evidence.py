"""Evidence routes: upload intents, local-mode object ingestion, signed view URLs."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUserDep, RequestCtx, get_db
from app.schemas.evidence import UploadIntentIn, UploadIntentOut, ViewURLOut
from app.services import evidence_service
from app.services.storage_service import verify_blob_signature

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("/upload-intents", response_model=UploadIntentOut, status_code=201)
def create_upload_intent(payload: UploadIntentIn, user: CurrentUserDep, db: DbDep, ctx: RequestCtx):
    intent, upload_url = evidence_service.create_upload_intent(
        db, user=user.user, content_type=payload.content_type, purpose=payload.purpose, ctx=ctx
    )
    db.commit()
    if upload_url is None:
        # Local development mode: PATCH the object through the authorized API endpoint.
        upload_url = f"/api/v1/evidence/objects/{intent.id}"
    return UploadIntentOut(
        intent_id=intent.id,
        expires_at=intent.expires_at,
        upload_method=("PUT" if payload.content_type else "PUT"),
        upload_url=upload_url,
        headers={"Content-Type": payload.content_type},
    )


@router.put("/objects/{intent_id}", status_code=204)
async def put_object(intent_id: uuid.UUID, request: Request, user: CurrentUserDep, db: DbDep):
    from app.core.errors import NotFoundError
    from app.models import UploadIntent

    intent = db.get(UploadIntent, intent_id)
    if intent is None or intent.user_id != user.user.id:
        raise NotFoundError("Upload intent not found.")
    data = await request.body()
    evidence_service.store_intent_upload(db, intent=intent, data=data, content_type=intent.content_type)
    db.commit()
    return Response(status_code=204)


@router.get("/{evidence_id}/view-url", response_model=ViewURLOut)
def view_url(evidence_id: uuid.UUID, user: CurrentUserDep, db: DbDep, ctx: RequestCtx):
    payload = evidence_service.issue_view_url(db, user=user.user, evidence_id=evidence_id, ctx=ctx)
    db.commit()
    return ViewURLOut.model_validate(payload)


@router.get("/blob/{evidence_id}")
def blob(evidence_id: uuid.UUID, exp: int, sig: str, db: DbDep):
    """Local-mode signed object delivery. Token is HMAC-bound to evidence id + expiry."""
    from fastapi import HTTPException

    if not verify_blob_signature(str(evidence_id), exp, sig):
        raise HTTPException(
            status_code=403,
            detail={
                "error": {"code": "FORBIDDEN", "message": "Signature invalid or expired.", "details": []}
            },
        )
    data, content_type = evidence_service.load_evidence_bytes(
        db,
        evidence_id=evidence_id,  # type: ignore[arg-type]
    )
    import io

    return StreamingResponse(
        io.BytesIO(data), media_type=content_type, headers={"Cache-Control": "private, no-store"}
    )
