"""
API Key management routes.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..billing.database import get_db, ApiKey
from ..billing.tiers import get_max_api_keys
from ..auth import verify_api_key, CustomerContext
from .generator import generate_api_key, mask_api_key, rotate_api_key

router = APIRouter(prefix="/v1/keys", tags=["API Keys"])


class KeyCreateRequest(BaseModel):
    name: str = "Default"
    permissions: str = "full"


class KeyCreateResponse(BaseModel):
    id: str
    key: str  # Only returned on creation
    name: str
    created_at: datetime


class KeyInfo(BaseModel):
    id: str
    name: str
    key_prefix: str
    permissions: str
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime


class KeyRotateResponse(BaseModel):
    id: str
    new_key: str
    name: str


@router.post("", response_model=KeyCreateResponse)
async def create_key(
    request: KeyCreateRequest,
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Generate a new API key.
    """
    with get_db() as db:
        # Check key limit
        existing_keys = (
            db.query(ApiKey)
            .filter(
                ApiKey.customer_id == customer.customer_id,
                ApiKey.is_active == True,
            )
            .count()
        )

        max_keys = get_max_api_keys(customer.tier)
        if max_keys and existing_keys >= max_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum API keys reached ({max_keys} for {customer.tier} tier). Upgrade to create more.",
            )

        # Generate key
        raw_key, key_record = generate_api_key(
            customer_id=customer.customer_id,
            name=request.name,
            permissions=request.permissions,
        )
        db.add(key_record)
        db.flush()

        return KeyCreateResponse(
            id=key_record.id,
            key=raw_key,
            name=key_record.name,
            created_at=key_record.created_at,
        )


@router.get("", response_model=List[KeyInfo])
async def list_keys(
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    List all API keys (masked).
    """
    with get_db() as db:
        keys = (
            db.query(ApiKey)
            .filter(ApiKey.customer_id == customer.customer_id)
            .order_by(ApiKey.created_at.desc())
            .all()
        )

        return [
            KeyInfo(
                id=k.id,
                name=k.name,
                key_prefix=mask_api_key(k.key_prefix),
                permissions=k.permissions,
                is_active=k.is_active,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
            for k in keys
        ]


@router.get("/{key_id}", response_model=KeyInfo)
async def get_key(
    key_id: str,
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Get a specific API key.
    """
    with get_db() as db:
        key = (
            db.query(ApiKey)
            .filter(
                ApiKey.id == key_id,
                ApiKey.customer_id == customer.customer_id,
            )
            .first()
        )

        if not key:
            raise HTTPException(status_code=404, detail="API key not found")

        return KeyInfo(
            id=key.id,
            name=key.name,
            key_prefix=mask_api_key(key.key_prefix),
            permissions=key.permissions,
            is_active=key.is_active,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
        )


@router.delete("/{key_id}")
async def revoke_key(
    key_id: str,
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Revoke an API key.
    """
    with get_db() as db:
        key = (
            db.query(ApiKey)
            .filter(
                ApiKey.id == key_id,
                ApiKey.customer_id == customer.customer_id,
            )
            .first()
        )

        if not key:
            raise HTTPException(status_code=404, detail="API key not found")

        key.is_active = False
        key.revoked_at = datetime.utcnow()

    return {"status": "revoked", "key_id": key_id}


@router.post("/{key_id}/rotate", response_model=KeyRotateResponse)
async def rotate_key_endpoint(
    key_id: str,
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Rotate an API key (generate new, revoke old).
    """
    with get_db() as db:
        old_key = (
            db.query(ApiKey)
            .filter(
                ApiKey.id == key_id,
                ApiKey.customer_id == customer.customer_id,
                ApiKey.is_active == True,
            )
            .first()
        )

        if not old_key:
            raise HTTPException(status_code=404, detail="Active API key not found")

        # Generate new key
        new_raw_key, new_key_record = rotate_api_key(customer.customer_id, old_key)
        db.add(new_key_record)

        # Revoke old key
        old_key.is_active = False
        old_key.revoked_at = datetime.utcnow()

        db.flush()

        return KeyRotateResponse(
            id=new_key_record.id,
            new_key=new_raw_key,
            name=new_key_record.name,
        )


class KeyUpdateRequest(BaseModel):
    name: Optional[str] = None
    permissions: Optional[str] = None


@router.patch("/{key_id}", response_model=KeyInfo)
async def update_key(
    key_id: str,
    request: KeyUpdateRequest,
    customer: CustomerContext = Depends(verify_api_key),
):
    """
    Update API key name or permissions.
    """
    with get_db() as db:
        key = (
            db.query(ApiKey)
            .filter(
                ApiKey.id == key_id,
                ApiKey.customer_id == customer.customer_id,
            )
            .first()
        )

        if not key:
            raise HTTPException(status_code=404, detail="API key not found")

        if request.name:
            key.name = request.name
        if request.permissions:
            key.permissions = request.permissions

        return KeyInfo(
            id=key.id,
            name=key.name,
            key_prefix=mask_api_key(key.key_prefix),
            permissions=key.permissions,
            is_active=key.is_active,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
        )
