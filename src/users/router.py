from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.users.dependencies import get_user_service
from src.users.schemas import UserCreate, UserList, UserRead, UserUpdate
from src.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    responses={
        409: {"description": "Username or email already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.create(payload)
    return UserRead.model_validate(user)


@router.get(
    "",
    response_model=UserList,
    summary="List users with pagination and optional active filter",
)
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active: bool | None = Query(
        None,
        description="Filter by active status. Omit to list all users.",
    ),
    service: UserService = Depends(get_user_service),
) -> UserList:
    items, total = await service.list_(limit=limit, offset=offset, active=active)
    return UserList(
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user by ID",
    responses={404: {"description": "User not found"}},
)
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.get_by_id(user_id)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Partially update a user",
    responses={
        404: {"description": "User not found"},
        409: {"description": "Username or email already exists"},
    },
)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.update(user_id, payload)
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/activate",
    response_model=UserRead,
    summary="Activate a user (idempotent)",
    responses={404: {"description": "User not found"}},
)
async def activate_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.activate(user_id)
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserRead,
    summary="Deactivate a user (idempotent)",
    responses={404: {"description": "User not found"}},
)
async def deactivate_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.deactivate(user_id)
    return UserRead.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user (physical delete)",
    responses={404: {"description": "User not found"}},
)
async def delete_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> None:
    await service.delete(user_id)
