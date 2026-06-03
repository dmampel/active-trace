import uuid
from typing import Union

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.dependencies import get_sync_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LogoutRequest,
    PartialTokenResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TOTPConfirmRequest,
    TokenResponse,
    LoginRequest,
)
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


def _resolve_tenant(x_tenant_id: str = Header(..., alias="X-Tenant-ID")) -> uuid.UUID:
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")


@router.post("/login", response_model=Union[TokenResponse, PartialTokenResponse])
@limiter.limit("5/minute")
def login(
    request: Request,
    body: LoginRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: Session = Depends(get_sync_db),
):
    try:
        result = AuthService.login(db, tenant_id, body.email, body.password)
        db.commit()
        return result
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    body: RefreshRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: Session = Depends(get_sync_db),
):
    try:
        result = AuthService.refresh(db, tenant_id, body.refresh_token)
        db.commit()
        return result
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: LogoutRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: Session = Depends(get_sync_db),
):
    AuthService.logout(db, tenant_id, body.refresh_token)
    db.commit()


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    body: ForgotPasswordRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: Session = Depends(get_sync_db),
):
    # Always returns 200 — no enumeration
    AuthService.forgot_password(db, tenant_id, body.email)
    db.commit()
    return {"message": "If the email exists, a recovery link was sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(
    body: ResetPasswordRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: Session = Depends(get_sync_db),
):
    try:
        AuthService.reset_password(db, tenant_id, body.token, body.new_password)
        db.commit()
        return {"message": "Password updated successfully."}
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


from app.core.dependencies import get_sync_db, get_current_user, CurrentUser

@router.post("/2fa/enroll")
def totp_enroll(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    try:
        from app.schemas.auth import TOTPEnrollResponse
        result = AuthService.totp_generate_secret(db, current_user.tenant_id, current_user.id)
        db.commit()
        return result
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/2fa/enroll/confirm", status_code=status.HTTP_200_OK)
def totp_enroll_confirm(
    body: TOTPConfirmRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    try:
        AuthService.totp_confirm_enrollment(db, current_user.tenant_id, current_user.id, body.code)
        db.commit()
        return {"message": "TOTP successfully enrolled"}
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/2fa/confirm", response_model=TokenResponse)
def totp_confirm(
    body: TOTPConfirmRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: Session = Depends(get_sync_db),
):
    try:
        result = AuthService.totp_verify_gate(db, tenant_id, body.partial_token, body.code)
        db.commit()
        return result
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code or token")
