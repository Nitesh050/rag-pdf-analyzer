from pydantic import BaseModel, Field, field_validator


class SignupRequest(BaseModel):
    # Loose on purpose: a real check is sending a confirmation email.
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8)
    display_name: str | None = None

    # mode="before" so stray spaces are removed before the pattern check.
    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, email):
        return email.strip() if isinstance(email, str) else email

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, password: str) -> str:
        # bcrypt only reads the first 72 bytes and rejects longer input.
        if len(password.encode()) > 72:
            raise ValueError("Password must be at most 72 bytes.")
        return password


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
