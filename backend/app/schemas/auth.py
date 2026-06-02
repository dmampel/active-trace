from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PartialTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partial_token: str
    requires_2fa: bool = True


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    new_password: str = Field(min_length=8)


class TOTPEnrollResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    otpauth_uri: str
    qr_base64: str


class TOTPConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partial_token: str
    code: str = Field(min_length=6, max_length=6)


class TOTPVerifyEnrollRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=6)
