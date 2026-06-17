import uuid
from typing import Union

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
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
async def login(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: LoginRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await AuthService.login(db, tenant_id, body.email, body.password)
        await db.commit()
        return result
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: RefreshRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await AuthService.refresh(db, tenant_id, body.refresh_token)
        await db.commit()
        return result
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: AsyncSession = Depends(get_db),
):
    await AuthService.logout(db, tenant_id, body.refresh_token)
    await db.commit()


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: ForgotPasswordRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: AsyncSession = Depends(get_db),
):
    await AuthService.forgot_password(db, tenant_id, body.email)
    await db.commit()
    return {"message": "If the email exists, a recovery link was sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: ResetPasswordRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: AsyncSession = Depends(get_db),
):
    try:
        await AuthService.reset_password(db, tenant_id, body.token, body.new_password)
        await db.commit()
        return {"message": "Password updated successfully."}
    except AuthError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")


@router.post("/2fa/enroll", response_model=TOTPEnrollResponse)
@limiter.limit("5/minute")
async def totp_enroll(
    request: Request,  # noqa: ARG001 — required by slowapi
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await AuthService.totp_enroll(db, current_user.tenant_id, current_user.id)
        await db.commit()
        return result
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/2fa/enroll/confirm", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def totp_enroll_confirm(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: TOTPVerifyEnrollRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await AuthService.totp_confirm_enroll(db, current_user.tenant_id, current_user.id, body.code)
        await db.commit()
        return {"message": "TOTP successfully enrolled"}
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/2fa/confirm", response_model=TokenResponse)
@limiter.limit("5/minute")
async def totp_confirm(
    request: Request,  # noqa: ARG001 — required by slowapi
    body: TOTPConfirmRequest,
    tenant_id: uuid.UUID = Depends(_resolve_tenant),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await AuthService.totp_verify_gate(db, tenant_id, body.partial_token, body.code)
        await db.commit()
        return result
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code or token")


@router.post("/impersonate", response_model=ImpersonateResponse)
@limiter.limit("5/minute")
async def impersonate(
    request: Request,
    body: ImpersonateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    _: bool = Depends(require_permission("impersonacion:usar")),
    db: AsyncSession = Depends(get_db),
):
    try:
        token = await AuthService.impersonate(db, current_user, body.target_user_id, request=request)
        await db.commit()
        return ImpersonateResponse(impersonate_token=token)
    except AuthError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.post("/impersonate/end", status_code=status.HTTP_200_OK)
async def end_impersonation(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await AuthService.end_impersonation(db, current_user, request=request)
        await db.commit()
        return {"message": "Impersonation session ended"}
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
