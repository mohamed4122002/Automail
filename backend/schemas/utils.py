"""
Reusable utilities for ORM to Pydantic model conversion.
Ensures type-safe, validated conversions across all API endpoints.
"""
from typing import TypeVar, Type, Any, List
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


def orm_to_pydantic(orm_obj: Any, pydantic_model: Type[T]) -> T:
    """
    Safely convert SQLAlchemy ORM object to Pydantic model.
    
    Args:
        orm_obj: SQLAlchemy model instance
        pydantic_model: Target Pydantic model class
        
    Returns:
        Validated Pydantic model instance
        
    Usage:
        user_profile = orm_to_pydantic(user_orm, UserProfile)
    """
    return pydantic_model.model_validate(orm_obj, from_attributes=True)


def orm_list_to_pydantic(orm_list: List[Any], pydantic_model: Type[T]) -> List[T]:
    """
    Convert list of ORM objects to list of Pydantic models.
    
    Args:
        orm_list: List of SQLAlchemy model instances
        pydantic_model: Target Pydantic model class
        
    Returns:
        List of validated Pydantic model instances
        
    Usage:
        notes = orm_list_to_pydantic(notes_orm, UserNote)
    """
    return [pydantic_model.model_validate(obj, from_attributes=True) for obj in orm_list]
