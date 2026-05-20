from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header, Request
from typing import Optional
import base64
import json
import logging

from app.client import client, MagnificAPIError, MagnificRateLimitError, MagnificTimeoutError
from app.registry import MODEL_REGISTRY
from app.models import GenerateRequest, GenerateResponse, TaskStatusRequest, TaskStatusResponse, RegistryResponse, CategoryInfo, ModelInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/validate-key")
async def validate_key(request: Request):
    body = await request.json()
    api_key = body.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    try:
        result = await client.validate_key(api_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.get("/registry", response_model=RegistryResponse)
async def get_registry():
    categories = []
    for cat_key, cat_data in MODEL_REGISTRY.items():
        models = []
        for model_key, model_data in cat_data["models"].items():
            models.append(ModelInfo(
                key=model_key,
                label=model_data["label"],
                description=model_data["description"],
                endpoint=model_data["endpoint"],
            ))
        categories.append(CategoryInfo(
            key=cat_key,
            label=cat_data["label"],
            models=models,
        ))
    return RegistryResponse(categories=categories)


@router.get("/registry/{category}/{model_key}")
async def get_model_schema(category: str, model_key: str):
    if category not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    if model_key not in MODEL_REGISTRY[category]["models"]:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found in category '{category}'")
    return MODEL_REGISTRY[category]["models"][model_key]


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    category: str = Form(...),
    model: str = Form(...),
    params: str = Form(...),
    x_magnific_api_key: Optional[str] = Header(None),
    image: Optional[UploadFile] = File(None),
    input_image: Optional[UploadFile] = File(None),
    input_image_2: Optional[UploadFile] = File(None),
    input_image_3: Optional[UploadFile] = File(None),
    input_image_4: Optional[UploadFile] = File(None),
    structure_reference: Optional[UploadFile] = File(None),
    style_reference: Optional[UploadFile] = File(None),
    first_frame_image: Optional[UploadFile] = File(None),
    last_frame_image: Optional[UploadFile] = File(None),
    image_url: Optional[UploadFile] = File(None),
    video_url: Optional[UploadFile] = File(None),
    image_tail: Optional[UploadFile] = File(None),
    static_mask: Optional[UploadFile] = File(None),
    first_frame: Optional[UploadFile] = File(None),
    last_frame: Optional[UploadFile] = File(None),
    reference_image_1: Optional[UploadFile] = File(None),
    reference_image_2: Optional[UploadFile] = File(None),
    reference_image_3: Optional[UploadFile] = File(None),
    reference_image_4: Optional[UploadFile] = File(None),
    reference_image_5: Optional[UploadFile] = File(None),
    reference_image_6: Optional[UploadFile] = File(None),
    reference_image_7: Optional[UploadFile] = File(None),
    start_image_url: Optional[UploadFile] = File(None),
    end_image_url: Optional[UploadFile] = File(None),
    minimax_image_url: Optional[UploadFile] = File(None),
):
    if category not in MODEL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    if model not in MODEL_REGISTRY[category]["models"]:
        raise HTTPException(status_code=400, detail=f"Invalid model: {model}")

    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid params JSON")

    files = {}
    file_map = {
        "image": image,
        "input_image": input_image,
        "input_image_2": input_image_2,
        "input_image_3": input_image_3,
        "input_image_4": input_image_4,
        "structure_reference": structure_reference,
        "style_reference": style_reference,
        "first_frame_image": first_frame_image,
        "last_frame_image": last_frame_image,
        "image_url": image_url,
        "video_url": video_url,
        "image_tail": image_tail,
        "static_mask": static_mask,
        "first_frame": first_frame,
        "last_frame": last_frame,
        "reference_image_1": reference_image_1,
        "reference_image_2": reference_image_2,
        "reference_image_3": reference_image_3,
        "reference_image_4": reference_image_4,
        "reference_image_5": reference_image_5,
        "reference_image_6": reference_image_6,
        "reference_image_7": reference_image_7,
        "start_image_url": start_image_url,
        "end_image_url": end_image_url,
        "minimax_image_url": minimax_image_url,
    }

    for key, upload in file_map.items():
        if upload:
            content = await upload.read()
            files[key] = content
            files[f"{key}_filename"] = upload.filename or ""

    try:
        result = await client.generate(category, model, params_dict, files, api_key=x_magnific_api_key)
    except MagnificRateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limited: {str(e)}")
    except MagnificTimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Request timeout: {str(e)}")
    except MagnificAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=f"Magnific API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in generate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    data = result.get("data", {})
    return GenerateResponse(
        task_id=data.get("task_id", ""),
        status=data.get("status", "UNKNOWN"),
        category=category,
        model=model,
    )


@router.post("/generate/json", response_model=GenerateResponse)
async def generate_json(request: GenerateRequest, x_magnific_api_key: Optional[str] = Header(None)):
    if request.category not in MODEL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Invalid category: {request.category}")
    if request.model not in MODEL_REGISTRY[request.category]["models"]:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model}")

    try:
        result = await client.generate(request.category, request.model, request.params, api_key=x_magnific_api_key)
    except MagnificRateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limited: {str(e)}")
    except MagnificTimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Request timeout: {str(e)}")
    except MagnificAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=f"Magnific API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in generate_json: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    data = result.get("data", {})
    return GenerateResponse(
        task_id=data.get("task_id", ""),
        status=data.get("status", "UNKNOWN"),
        category=request.category,
        model=request.model,
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    category: str,
    model: str,
    x_magnific_api_key: Optional[str] = Header(None),
):
    if category not in MODEL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    if model not in MODEL_REGISTRY[category]["models"]:
        raise HTTPException(status_code=400, detail=f"Invalid model: {model}")

    try:
        result = await client.get_task_status(category, model, task_id, api_key=x_magnific_api_key)
    except MagnificRateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limited: {str(e)}")
    except MagnificTimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Request timeout: {str(e)}")
    except MagnificAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=f"Magnific API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_task_status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    data = result.get("data", {})
    return TaskStatusResponse(
        task_id=data.get("task_id", task_id),
        status=data.get("status", "UNKNOWN"),
        generated=data.get("generated", []),
        category=category,
        model=model,
    )


@router.post("/tasks/{task_id}/poll", response_model=TaskStatusResponse)
async def poll_task(
    task_id: str,
    category: str,
    model: str,
    x_magnific_api_key: Optional[str] = Header(None),
):
    if category not in MODEL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    if model not in MODEL_REGISTRY[category]["models"]:
        raise HTTPException(status_code=400, detail=f"Invalid model: {model}")

    try:
        result = await client.poll_task(category, model, task_id, api_key=x_magnific_api_key)
    except MagnificRateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limited: {str(e)}")
    except MagnificTimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Request timeout: {str(e)}")
    except MagnificAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=f"Magnific API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in poll_task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    data = result.get("data", {})
    return TaskStatusResponse(
        task_id=data.get("task_id", task_id),
        status=data.get("status", "UNKNOWN"),
        generated=data.get("generated", []),
        category=category,
        model=model,
    )


@router.get("/tasks", response_model=list[TaskStatusResponse])
async def list_tasks(
    category: str,
    model: str,
    x_magnific_api_key: Optional[str] = Header(None),
):
    if category not in MODEL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    if model not in MODEL_REGISTRY[category]["models"]:
        raise HTTPException(status_code=400, detail=f"Invalid model: {model}")

    try:
        result = await client.list_tasks(category, model, api_key=x_magnific_api_key)
    except MagnificRateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limited: {str(e)}")
    except MagnificTimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Request timeout: {str(e)}")
    except MagnificAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=f"Magnific API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in list_tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    tasks = result.get("data", [])
    return [
        TaskStatusResponse(
            task_id=t.get("task_id", ""),
            status=t.get("status", "UNKNOWN"),
            generated=t.get("generated", []),
            category=category,
            model=model,
        )
        for t in tasks
    ]
