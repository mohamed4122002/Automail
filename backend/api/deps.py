from uuid import UUID
from fastapi import Depends, HTTPException, status
from ..models import User

from jose import JWTError, jwt
from ..config import settings
from ..auth import oauth2_scheme
import logging

logger = logging.getLogger(__name__)

async def get_current_user_id(
    token: str = Depends(oauth2_scheme)
) -> UUID:
    """
    Extract and verify user ID from JWT token.
    Enforces authentication for all dependent routes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
        
    # Verify user exists and is active
    user = await User.find_one(User.id == user_id, User.is_active == True)
    
    if not user:
        logger.warning(f"User {user_id} not found or inactive")
        raise credentials_exception
        
    return user.id
