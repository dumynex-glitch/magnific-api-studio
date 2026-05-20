from fastapi import APIRouter, HTTPException, Request
from app.config import settings
import hashlib
import hmac
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["webhooks"])

task_callbacks = {}


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    if not settings.webhook_secret:
        return True
    expected = hmac.new(
        settings.webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def receive_webhook(request: Request):
    signature = request.headers.get("x-magnific-signature", "")
    body = await request.body()

    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    task_id = payload.get("task_id", "")
    status = payload.get("status", "")
    category = payload.get("category", "")
    model = payload.get("model", "")

    logger.info(f"Webhook received: task_id={task_id}, status={status}")

    if task_id and task_id in task_callbacks:
        callback = task_callbacks.pop(task_id)
        try:
            await callback(payload)
        except Exception as e:
            logger.error(f"Webhook callback failed for task {task_id}: {e}")

    return {"status": "received", "task_id": task_id}


@router.get("/webhook/tasks/{task_id}")
async def get_webhook_task_status(task_id: str):
    if not task_id:
        raise HTTPException(status_code=400, detail="Task ID required")
    return {"task_id": task_id, "registered": task_id in task_callbacks}


def register_webhook_callback(task_id: str, callback):
    task_callbacks[task_id] = callback
    logger.info(f"Registered webhook callback for task {task_id}")


def unregister_webhook_callback(task_id: str):
    task_callbacks.pop(task_id, None)
