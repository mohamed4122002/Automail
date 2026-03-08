from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

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
    user_id: UUID = Depends(get_current_user_id)
):
    """List all workflows."""
    workflows = await Workflow.find_all().sort("-created_at").to_list()
    return orm_list_to_pydantic(workflows, WorkflowResponse)


@router.post("", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new workflow."""
    workflow = Workflow(
        name=request.name,
        description=request.description,
        campaign_id=request.campaign_id,
        is_active=True
    )
    
    await workflow.insert()
    return orm_to_pydantic(workflow, WorkflowResponse)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get a workflow by ID."""
    workflow = await Workflow.find_one(Workflow.id == workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return orm_to_pydantic(workflow, WorkflowResponse)


@router.post("/{workflow_id}/graph")
async def save_workflow_graph(
    workflow_id: UUID,
    graph: WorkflowGraphRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Save workflow graph (nodes and edges) from React Flow.
    Converts React Flow format to database models.
    """
    workflow = await Workflow.find_one(Workflow.id == workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Delete existing nodes and edges
    await WorkflowNode.find(WorkflowNode.workflow_id == workflow_id).delete()
    await WorkflowEdge.find(WorkflowEdge.workflow_id == workflow_id).delete()
    
    # Create node ID mapping (React Flow ID -> DB UUID)
    node_id_map = {}
    
    from ..schemas.workflow_nodes import WorkflowNodeConfigModel
    from pydantic import ValidationError
    
    for react_node in graph.nodes:
        try:
            node_type = react_node.type
            if node_type == 'trigger' or 'contact_added' in node_type:
                node_type = 'start'
            elif node_type == 'send_email':
                node_type = 'email'
            elif node_type == 'wait':
                node_type = 'delay'
            
            clean_data = {k: v for k, v in react_node.data.items() if k != 'type'}
            
            if not clean_data.get('label'):
                clean_data['label'] = f"{node_type.capitalize()} Node"
            
            validation_data = {"type": node_type, **clean_data}
            WorkflowNodeConfigModel.model_validate(validation_data)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid configuration for {react_node.type} node '{react_node.id}': {e.errors()}"
            )

        react_node.data['label'] = clean_data['label']

        db_node = WorkflowNode(
            workflow_id=workflow_id,
            type=node_type,
            config={
                "position": react_node.position,
                "data": react_node.data,
                "react_flow_id": react_node.id
            }
        )
        await db_node.insert()
        node_id_map[react_node.id] = db_node.id
    
    # Save edges
    for react_edge in graph.edges:
        source_uuid = node_id_map.get(react_edge.source)
        target_uuid = node_id_map.get(react_edge.target)
        
        if not source_uuid or not target_uuid:
            continue
        
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
        await db_edge.insert()
    
    return {
        "message": "Workflow graph saved successfully",
        "workflow_id": str(workflow_id),
        "nodes_count": len(graph.nodes),
        "edges_count": len(graph.edges)
    }


@router.get("/{workflow_id}/graph", response_model=WorkflowGraphResponse)
async def load_workflow_graph(
    workflow_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Load workflow graph from database and convert to React Flow format.
    """
    workflow = await Workflow.find_one(Workflow.id == workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db_nodes = await WorkflowNode.find(WorkflowNode.workflow_id == workflow_id).to_list()
    db_edges = await WorkflowEdge.find(WorkflowEdge.workflow_id == workflow_id).to_list()
    
    uuid_to_react_id = {}
    react_nodes = []
    
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
    user_id: UUID = Depends(get_current_user_id)
):
    """Partially update a workflow."""
    workflow = await Workflow.find_one(Workflow.id == workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if request.name is not None:
        workflow.name = request.name
    if request.description is not None:
        workflow.description = request.description
    if request.campaign_id is not None:
        workflow.campaign_id = request.campaign_id
    if request.is_active is not None:
        workflow.is_active = request.is_active
        
    await workflow.save()
    return orm_to_pydantic(workflow, WorkflowResponse)


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete a workflow and all its nodes/edges."""
    workflow = await Workflow.find_one(Workflow.id == workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    await WorkflowNode.find(WorkflowNode.workflow_id == workflow_id).delete()
    await WorkflowEdge.find(WorkflowEdge.workflow_id == workflow_id).delete()
    await workflow.delete()
    
    return {"message": "Workflow deleted successfully"}
