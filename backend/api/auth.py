from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from ..auth import authenticate_user, create_access_token, get_password_hash, get_current_active_user
from ..config import settings
from ..models import User


router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str | None = None
    last_name: str | None = None


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return TokenResponse(access_token=access_token)


@router.post("/users", response_model=TokenResponse, status_code=201)
async def register_user(
    payload: UserCreate
) -> TokenResponse:
    existing = await User.find_one(User.email == payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    await user.insert()
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=User)
async def get_my_profile(user: User = Depends(get_current_active_user)):
    """Get the current logged-in user's profile."""
    return user
