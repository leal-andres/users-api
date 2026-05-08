from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.users.models import UserRole


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "ada.lovelace",
                    "email": "ada@example.com",
                    "first_name": "Ada",
                    "last_name": "Lovelace",
                    "role": "user",
                }
            ]
        }
    )


class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$"
    )
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: UserRole | None = None
    active: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"first_name": "Augusta", "active": False}]}
    )


class UserRead(UserBase):
    id: UUID
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    items: list[UserRead]
    total: int
    limit: int
    offset: int
