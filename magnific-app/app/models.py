from typing import Optional, Any
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    category: str = Field(..., description="Generation category: image, video, audio, prompt, lipsync")
    model: str = Field(..., description="Model key within the category")
    params: dict = Field(..., description="Model-specific parameters")


class GenerateResponse(BaseModel):
    task_id: str
    status: str
    category: str
    model: str


class TaskStatusRequest(BaseModel):
    task_id: str
    category: str
    model: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    generated: list[str] = []
    category: str
    model: str


class ModelInfo(BaseModel):
    key: str
    label: str
    description: str
    endpoint: str


class CategoryInfo(BaseModel):
    key: str
    label: str
    models: list[ModelInfo]


class RegistryResponse(BaseModel):
    categories: list[CategoryInfo]
