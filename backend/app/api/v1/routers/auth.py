import uuid
from typing import Union

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, get_current_user, get_sync_db
from app.core.limiter import limiter
from app.core.permissions import require_permission
from app.schemas.auth import (
    ForgotPasswordRequest,
    ImpersonateRequest,
    ImpersonateResponse,
    LoginRequest,
    LogoutRequest,
    PartialTokenResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TOTPConfirmRequest,
    TOTPEnrollResponse,
    TOTPVerifyEnrollRequest,
    TokenResponse,
)
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
@limiter.limit("20/minute")
def refresh_token(
    request: Request,
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
@limiter.limit("5/minute")
def reset_password(
    request: Request,
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


@router.post("/2fa/enroll", response_model=TOTPEnrollResponse)
def totp_enroll(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    try:
        result = AuthService.totp_enroll(db, current_user.tenant_id, current_user.id)
        db.commit()
        return result
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/2fa/enroll/confirm", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def totp_enroll_confirm(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: TOTPVerifyEnrollRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    try:
        AuthService.totp_confirm_enroll(db, current_user.tenant_id, current_user.id, body.code)
        db.commit()
        return {"message": "TOTP successfully enrolled"}
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/2fa/confirm", response_model=TokenResponse)
@limiter.limit("5/minute")
def totp_confirm(
    request: Request,
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


@router.post("/impersonate", response_model=ImpersonateResponse)
def impersonate(
    request: Request,
    body: ImpersonateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _: bool = Depends(require_permission("impersonacion:usar")),
    db: Session = Depends(get_sync_db),
):
    try:
        token = AuthService.impersonate(db, current_user, body.target_user_id, request=request)
        db.commit()
        return ImpersonateResponse(impersonate_token=token)
    except AuthError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.post("/impersonate/end", status_code=status.HTTP_200_OK)
def end_impersonation(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    try:
        AuthService.end_impersonation(db, current_user, request=request)
        db.commit()
        return {"message": "Impersonation session ended"}
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
