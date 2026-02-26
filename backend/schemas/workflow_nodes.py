from pydantic import BaseModel, Field, conint
from typing import Literal, Union, Dict, Any, Optional, Annotated
from uuid import UUID

class BaseNodeConfig(BaseModel):
    """Common fields for all node data/config."""
    label: Optional[str] = None

class StartNodeConfig(BaseNodeConfig):
    type: Literal["start"] = "start"

class EmailNodeConfig(BaseNodeConfig):
    type: Literal["email"] = "email"
    template_id: Union[UUID, str, None] = None # Optional for initial config

class DelayNodeConfig(BaseNodeConfig):
    type: Literal["delay"] = "delay"
    seconds: Optional[int] = None
    hours: Optional[int] = 1 # Default to 1 hour
    
    @property
    def total_seconds(self) -> int:
        if self.seconds: return self.seconds
        if self.hours: return self.hours * 3600
        return 0

class ConditionNodeConfig(BaseNodeConfig):
    type: Literal["condition"] = "condition"
    condition: Dict[str, Any] = Field(default_factory=dict)

class ActionNodeConfig(BaseNodeConfig):
    type: Literal["action"] = "action"
    action: str = "update_lead_status"
    status: Optional[str] = None
    message: Optional[str] = None

class EndNodeConfig(BaseNodeConfig):
    type: Literal["end"] = "end"

# Discriminated Union for validation
WorkflowNodeConfig = Union[
    StartNodeConfig,
    EmailNodeConfig,
    DelayNodeConfig,
    ConditionNodeConfig,
    ActionNodeConfig,
    EndNodeConfig
]

# Use Pydantic's discriminator feature for better error messages
from pydantic import RootModel
class WorkflowNodeConfigModel(RootModel):
    root: Annotated[
        WorkflowNodeConfig,
        Field(discriminator='type')
    ]
