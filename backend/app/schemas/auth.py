from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailRequest(BaseModel):
    email: EmailStr = Field(max_length=320)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(EmailRequest):
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class LoginRequest(EmailRequest):
    password: str = Field(min_length=1, max_length=128)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=30, max_length=200)
    password: str = Field(min_length=10, max_length=128)
