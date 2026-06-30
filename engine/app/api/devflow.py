from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.devflow import DevFlowService


router = APIRouter(prefix="/api", tags=["devflow"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    root_path: str = Field(min_length=1)
    scan_type: Literal["soft", "hard"] = "soft"


class ScanRequest(BaseModel):
    scan_type: Literal["soft", "hard"]


class RequestCreate(BaseModel):
    project_id: int
    original_text: str = Field(min_length=1)


class AdvanceRequest(BaseModel):
    provider_id: str = "mock"


class ApprovalDecision(BaseModel):
    action: Literal["approve", "reject"]
    decided_by: str = Field(default="local-user", min_length=1)


def service(request: Request) -> DevFlowService:
    return request.app.state.devflow


@router.get("/projects")
def list_projects(request: Request):
    return service(request).projects()


@router.post("/projects", status_code=201)
def create_project(payload: ProjectCreate, request: Request):
    try:
        return service(request).add_project(
            payload.name,
            payload.root_path,
            payload.scan_type,
        )
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/projects/{project_id}/scan")
def scan_project(project_id: int, payload: ScanRequest, request: Request):
    try:
        return service(request).scan_project(project_id, payload.scan_type)
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/projects/{project_id}/requests")
def list_requests(project_id: int, request: Request):
    return service(request).requests(project_id)


@router.post("/requests", status_code=201)
def create_request(payload: RequestCreate, request: Request):
    try:
        return service(request).create_request(
            payload.project_id,
            payload.original_text,
        )
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/requests/{request_id}")
def request_detail(request_id: str, request: Request):
    try:
        return service(request).request_detail(request_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/requests/{request_id}/advance")
def advance_request(
    request_id: str,
    payload: AdvanceRequest,
    request: Request,
):
    try:
        return service(request).advance_request(request_id, payload.provider_id)
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/requests/{request_id}/approval")
def decide_approval(
    request_id: str,
    payload: ApprovalDecision,
    request: Request,
):
    try:
        if payload.action == "approve":
            return service(request).approve(request_id, payload.decided_by)
        return service(request).reject(request_id, payload.decided_by)
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/providers")
def providers(request: Request):
    return service(request).provider_options()
