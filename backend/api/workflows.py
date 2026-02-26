from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..db import get_db
from ..models import Workflow, WorkflowNode, WorkflowEdge, Campaign
from ..schemas.utils import orm_to_pydantic, orm_list_to_pydantic
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/workflows", tags=["workflows"])


class ReactFlowNode(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]


class ReactFlowEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class WorkflowGraphRequest(BaseModel):
    nodes: List[ReactFlowNode]
    edges: List[ReactFlowEdge]


class WorkflowGraphResponse(BaseModel):
    nodes: List[ReactFlowNode]
    edges: List[ReactFlowEdge]


class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    campaign_id: Optional[UUID] = None


class WorkflowResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    campaign_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    campaign_id: Optional[UUID] = None
    is_active: Optional[bool] = None


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all workflows."""
    q = await db.execute(
        select(Workflow).order_by(Workflow.created_at.desc())
    )
    workflows = q.scalars().all()
    
    return orm_list_to_pydantic(workflows, WorkflowResponse)


@router.post("", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new workflow."""
    workflow = Workflow(
        name=request.name,
        description=request.description,
        campaign_id=request.campaign_id,
        is_active=True
    )
    
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    
    return orm_to_pydantic(workflow, WorkflowResponse)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a workflow by ID."""
    q = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = q.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return orm_to_pydantic(workflow, WorkflowResponse)


@router.post("/{workflow_id}/graph")
async def save_workflow_graph(
    workflow_id: UUID,
    graph: WorkflowGraphRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Save workflow graph (nodes and edges) from React Flow.
    Converts React Flow format to database models.
    """
    # Verify workflow exists
    q = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = q.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Delete existing nodes and edges
    await db.execute(
        delete(WorkflowNode).where(WorkflowNode.workflow_id == workflow_id)
    )
    await db.execute(
        delete(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow_id)
    )
    
    # Create node ID mapping (React Flow ID -> DB UUID)
    node_id_map = {}
    
    # Save nodes
    from ..schemas.workflow_nodes import WorkflowNodeConfigModel
    from pydantic import ValidationError
    
    for react_node in graph.nodes:
        # Validate data against strict schemas
        try:
            # Normalize type to match literal expectations (start, email, delay, etc.)
            node_type = react_node.type
            if node_type == 'trigger' or 'contact_added' in node_type:
                node_type = 'start'
            elif node_type == 'send_email':
                node_type = 'email'
            elif node_type == 'wait':
                node_type = 'delay'
            
            # Ensure it's one of the valid literals
            valid_types = ["start", "email", "delay", "condition", "action", "end"]
            if node_type not in valid_types:
                pass

            # Reconstruct for validation: { "type": node_type, **data }
            clean_data = {k: v for k, v in react_node.data.items() if k != 'type'}
            
            # Auto-populate label if missing for better UI experience
            if not clean_data.get('label'):
                clean_data['label'] = f"{node_type.capitalize()} Node"
            
            validation_data = {"type": node_type, **clean_data}
            
            # Use RootModel for clean discriminator validation
            WorkflowNodeConfigModel.model_validate(validation_data)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid configuration for {react_node.type} node '{react_node.id}': {e.errors()}"
            )

        # Update the react_node.data so the saved config in DB has the auto-populated label
        react_node.data['label'] = clean_data['label']

        db_node = WorkflowNode(
            workflow_id=workflow_id,
            type=node_type, # Use the normalized type
            config={
                "position": react_node.position,
                "data": react_node.data,
                "react_flow_id": react_node.id
            }
        )
        db.add(db_node)
        await db.flush()
        
        # Map React Flow ID to DB UUID
        node_id_map[react_node.id] = db_node.id
    
    # Save edges
    for react_edge in graph.edges:
        # Find source and target node UUIDs
        source_uuid = node_id_map.get(react_edge.source)
        target_uuid = node_id_map.get(react_edge.target)
        
        if not source_uuid or not target_uuid:
            continue  # Skip invalid edges
        
        db_edge = WorkflowEdge(
            workflow_id=workflow_id,
            from_node_id=source_uuid,
            to_node_id=target_uuid,
            condition={
                "sourceHandle": react_edge.sourceHandle,
                "targetHandle": react_edge.targetHandle,
                "data": react_edge.data or {},
                "react_flow_id": react_edge.id
            }
        )
        db.add(db_edge)
    
    await db.commit()
    
    return {
        "message": "Workflow graph saved successfully",
        "workflow_id": str(workflow_id),
        "nodes_count": len(graph.nodes),
        "edges_count": len(graph.edges)
    }


@router.get("/{workflow_id}/graph", response_model=WorkflowGraphResponse)
async def load_workflow_graph(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Load workflow graph from database and convert to React Flow format.
    """
    # Get workflow
    q_workflow = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = q_workflow.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Get nodes
    q_nodes = await db.execute(
        select(WorkflowNode).where(WorkflowNode.workflow_id == workflow_id)
    )
    db_nodes = q_nodes.scalars().all()
    
    # Get edges
    q_edges = await db.execute(
        select(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow_id)
    )
    db_edges = q_edges.scalars().all()
    
    # Create UUID -> React Flow ID mapping
    uuid_to_react_id = {}
    react_nodes = []
    
    # Convert nodes
    for db_node in db_nodes:
        config = db_node.config or {}
        react_flow_id = config.get("react_flow_id", str(db_node.id))
        uuid_to_react_id[str(db_node.id)] = react_flow_id
        
        react_nodes.append(ReactFlowNode(
            id=react_flow_id,
            type=db_node.type,
            position=config.get("position", {"x": 0, "y": 0}),
            data=config.get("data", {})
        ))
    
    # Convert edges
    react_edges = []
    for db_edge in db_edges:
        condition = db_edge.condition or {}
        react_flow_id = condition.get("react_flow_id", str(db_edge.id))
        
        source_id = uuid_to_react_id.get(str(db_edge.from_node_id))
        target_id = uuid_to_react_id.get(str(db_edge.to_node_id))
        
        if source_id and target_id:
            react_edges.append(ReactFlowEdge(
                id=react_flow_id,
                source=source_id,
                target=target_id,
                sourceHandle=condition.get("sourceHandle"),
                targetHandle=condition.get("targetHandle"),
                data=condition.get("data")
            ))
    
    return WorkflowGraphResponse(
        nodes=react_nodes,
        edges=react_edges
    )


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def patch_workflow(
    workflow_id: UUID,
    request: WorkflowUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Partially update a workflow."""
    q = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = q.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Update fields if provided
    if request.name is not None:
        workflow.name = request.name
    if request.description is not None:
        workflow.description = request.description
    if request.campaign_id is not None:
        workflow.campaign_id = request.campaign_id
    if request.is_active is not None:
        workflow.is_active = request.is_active
        
    await db.commit()
    await db.refresh(workflow)
    
    return orm_to_pydantic(workflow, WorkflowResponse)


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete a workflow and all its nodes/edges."""
    q = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = q.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    await db.delete(workflow)
    await db.commit()
    
    return {"message": "Workflow deleted successfully"}
