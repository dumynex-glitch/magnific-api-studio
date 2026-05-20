import asyncio
import base64
import json
import mimetypes
import time
import logging
from typing import Optional

import httpx
from app.config import settings
from app.registry import MODEL_REGISTRY

logger = logging.getLogger(__name__)


class MagnificAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class MagnificRateLimitError(MagnificAPIError):
    pass


class MagnificTimeoutError(MagnificAPIError):
    pass


class MagnificClient:
    def __init__(self):
        self.base_url = settings.magnific_base_url
        self.default_api_key = settings.magnific_api_key
        self.max_retries = 3
        self.retry_delay = 2

    def _get_headers(self, api_key: Optional[str] = None) -> dict:
        return {
            "x-magnific-api-key": api_key or self.default_api_key,
            "Content-Type": "application/json",
        }

    def _encode_file(self, file_bytes: bytes, filename: str = "") -> str:
        return base64.b64encode(file_bytes).decode("utf-8")

    def _file_to_data_url(self, file_bytes: bytes, filename: str = "") -> str:
        mime, _ = mimetypes.guess_type(filename or "file.bin")
        if not mime:
            if filename and filename.endswith((".mp4", ".mov", ".webm", ".m4v")):
                mime = "video/mp4"
            elif filename and filename.endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            elif filename and filename.endswith(".png"):
                mime = "image/png"
            elif filename and filename.endswith(".webp"):
                mime = "image/webp"
            else:
                mime = "application/octet-stream"
        encoded = self._encode_file(file_bytes)
        return f"data:{mime};base64,{encoded}"

    async def _request_with_retry(self, method: str, url: str, headers: Optional[dict] = None, **kwargs):
        timeout = kwargs.pop("timeout", 60.0)
        request_headers = headers or self._get_headers()
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, headers=request_headers, **kwargs)

                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", self.retry_delay * (2 ** attempt)))
                        logger.warning(f"Rate limited, waiting {retry_after}s before retry {attempt + 1}/{self.max_retries}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        raise MagnificRateLimitError(
                            f"Rate limit exceeded after {self.max_retries} retries",
                            status_code=429,
                        )

                    if response.status_code == 503:
                        if attempt < self.max_retries - 1:
                            wait = self.retry_delay * (2 ** attempt)
                            logger.warning(f"Service unavailable, retrying in {wait}s (attempt {attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(wait)
                            continue
                        raise MagnificAPIError(
                            f"Service unavailable after {self.max_retries} retries",
                            status_code=503,
                        )

                    if response.status_code == 401:
                        raise MagnificAPIError(
                            "Invalid API key or unauthorized access",
                            status_code=401,
                            response_body=response.text,
                        )

                    if response.status_code == 403:
                        raise MagnificAPIError(
                            "Access forbidden - check API permissions",
                            status_code=403,
                            response_body=response.text,
                        )

                    if response.status_code >= 500:
                        if attempt < self.max_retries - 1:
                            wait = self.retry_delay * (2 ** attempt)
                            logger.warning(f"Server error {response.status_code}, retrying in {wait}s")
                            await asyncio.sleep(wait)
                            continue
                        raise MagnificAPIError(
                            f"Server error {response.status_code}",
                            status_code=response.status_code,
                            response_body=response.text,
                        )

                    if response.status_code >= 400:
                        raise MagnificAPIError(
                            f"Client error {response.status_code}: {response.text[:200]}",
                            status_code=response.status_code,
                            response_body=response.text,
                        )

                    try:
                        return response.json()
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        raise MagnificAPIError(
                            f"Invalid JSON response from API",
                            status_code=response.status_code,
                            response_body=response.text[:500],
                        )

            except httpx.ConnectTimeout as e:
                last_error = MagnificTimeoutError(f"Connection timeout: {e}", status_code=0)
                logger.warning(f"Connection timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue

            except httpx.ReadTimeout as e:
                last_error = MagnificTimeoutError(f"Read timeout: {e}", status_code=0)
                logger.warning(f"Read timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    retry_after = int(e.response.headers.get("Retry-After", self.retry_delay * (2 ** attempt)))
                    await asyncio.sleep(retry_after)
                    continue
                if e.response.status_code == 503 and attempt < self.max_retries - 1:
                    wait = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait)
                    continue
                raise MagnificAPIError(
                    f"HTTP error {e.response.status_code}: {str(e)}",
                    status_code=e.response.status_code,
                    response_body=e.response.text[:500] if hasattr(e.response, 'text') else "",
                )

            except httpx.RequestError as e:
                last_error = MagnificAPIError(f"Request error: {e}", status_code=0)
                logger.warning(f"Request error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    wait = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait)
                    continue

        raise last_error or MagnificAPIError(f"Request failed after {self.max_retries} retries")

    def _is_url_field(self, key: str) -> bool:
        return key.endswith("_url")

    async def generate(self, category: str, model_key: str, params: dict, files: Optional[dict] = None, api_key: Optional[str] = None) -> dict:
        if category not in MODEL_REGISTRY:
            raise MagnificAPIError(f"Invalid category: {category}", status_code=400)

        model_info = MODEL_REGISTRY[category]["models"]
        if model_key not in model_info:
            raise MagnificAPIError(f"Invalid model: {model_key}", status_code=400)

        model_info = model_info[model_key]
        endpoint = model_info["endpoint"]
        url = f"{self.base_url}{endpoint}"
        fields = model_info.get("fields", {})

        payload = {}

        mode_value = params.pop("mode", None)

        for key, value in list(params.items()):
            if value is None or value == "":
                continue

            field_def = fields.get(key, {})
            field_type = field_def.get("type", "")

            if field_type == "url_or_file":
                file_key = key
                if model_key == "minimax-live" and key == "image_url":
                    file_key = "minimax_image_url"

                if files and file_key in files:
                    file_data = files[file_key]
                    filename = files.get(f"{file_key}_filename", "")
                    if isinstance(file_data, bytes):
                        payload[key] = self._file_to_data_url(file_data, filename)
                    elif isinstance(file_data, str):
                        payload[key] = file_data
                elif value and not value.startswith("data:"):
                    payload[key] = value
                continue

            if key in ("first_frame_image", "last_frame_image", "input_image", "input_image_2",
                       "input_image_3", "input_image_4", "image", "structure_reference", "style_reference",
                       "image_tail", "static_mask", "video_url",
                       "first_frame", "last_frame",
                       "image_url", "start_image_url", "end_image_url"):
                if files and key in files:
                    file_data = files[key]
                    if isinstance(file_data, bytes):
                        payload[key] = self._encode_file(file_data)
                    elif isinstance(file_data, str):
                        payload[key] = file_data
                continue

            if key.startswith("reference_image_") and files and key in files:
                file_data = files[key]
                if isinstance(file_data, bytes):
                    if "reference_images" not in payload:
                        payload["reference_images"] = []
                    payload["reference_images"].append(self._encode_file(file_data))
                elif isinstance(file_data, str):
                    if "reference_images" not in payload:
                        payload["reference_images"] = []
                    payload["reference_images"].append(file_data)
                continue

            payload[key] = value

        if model_key == "happy-horse-1-r2v":
            image_urls = []
            for i in range(1, 10):
                ref_key = f"ref_image_{i}"
                if files and ref_key in files:
                    file_data = files[ref_key]
                    if isinstance(file_data, bytes):
                        image_urls.append({"url": self._file_to_data_url(file_data, files.get(f"{ref_key}_filename", ""))})
                    elif isinstance(file_data, str):
                        image_urls.append({"url": file_data})
            if image_urls:
                payload["image_urls"] = image_urls

        if model_key == "happy-horse-1-video-edit":
            image_urls = []
            for i in range(1, 6):
                ref_key = f"edit_ref_image_{i}"
                if files and ref_key in files:
                    file_data = files[ref_key]
                    if isinstance(file_data, bytes):
                        image_urls.append(self._file_to_data_url(file_data, files.get(f"{ref_key}_filename", "")))
                    elif isinstance(file_data, str):
                        image_urls.append(file_data)
            if image_urls:
                payload["image_urls"] = image_urls

        if model_key == "runway-act-two":
            character_type = payload.pop("character_type", "image")
            character_value = payload.pop("character", None)
            reference_video = payload.pop("reference_video", None)

            if character_value:
                if isinstance(character_value, bytes):
                    character_uri = self._file_to_data_url(character_value, files.get("character_filename", "") if files else "")
                elif not character_value.startswith("data:"):
                    character_uri = character_value
                else:
                    character_uri = character_value
                payload["character"] = {"type": character_type, "uri": character_uri}

            if reference_video:
                payload["reference"] = {"type": "video", "uri": reference_video}

        if model_key == "veo-3-1-ref2v":
            image_urls = []
            for i in range(1, 4):
                ref_key = f"ref_image_{i}"
                ref_value = payload.pop(ref_key, None)
                if ref_value:
                    image_urls.append(ref_value)
            if image_urls:
                payload["image_urls"] = image_urls

        if "multi_prompt" in payload and isinstance(payload["multi_prompt"], str):
            lines = [line.strip() for line in payload["multi_prompt"].split("\n") if line.strip()]
            if model_key in ("kling-v3-pro", "kling-v3-std"):
                payload["multi_prompt"] = [{"prompt": line, "duration": "5"} for line in lines]
            else:
                payload["multi_prompt"] = lines
            if "shot_type" not in payload:
                payload["shot_type"] = "customize"
            if "multi_shot" not in payload:
                payload["multi_shot"] = True

        if mode_value:
            if model_key in ("kling-v3-pro", "kling-v3-std"):
                if mode_value == "text":
                    payload.pop("start_image_url", None)
                    payload.pop("end_image_url", None)
                    payload.pop("multi_prompt", None)
                    payload.pop("shot_type", None)
                    payload.pop("multi_shot", None)
                elif mode_value == "image":
                    payload.pop("multi_prompt", None)
                    payload.pop("shot_type", None)
                    payload.pop("multi_shot", None)
                elif mode_value == "multi-shot":
                    payload.pop("start_image_url", None)
                    payload.pop("end_image_url", None)
                    payload["multi_shot"] = True
                    if "shot_type" not in payload:
                        payload["shot_type"] = "customize"
            else:
                if mode_value == "text":
                    payload.pop("image", None)
                    payload.pop("first_frame_image", None)
                    payload.pop("last_frame_image", None)
                    payload.pop("image_url", None)
                    payload.pop("start_image_url", None)
                    payload.pop("end_image_url", None)
                    payload.pop("multi_prompt", None)
                    payload.pop("shot_type", None)
                elif mode_value == "image":
                    payload.pop("last_frame_image", None)
                    payload.pop("multi_prompt", None)
                    payload.pop("shot_type", None)
                elif mode_value == "multi-shot":
                    payload.pop("image", None)
                    payload.pop("first_frame_image", None)
                    payload.pop("last_frame_image", None)
                    payload.pop("image_url", None)
                    payload.pop("start_image_url", None)
                    payload.pop("end_image_url", None)
                    if "shot_type" not in payload:
                        payload["shot_type"] = "customize"

        response = await self._request_with_retry("POST", url, headers=self._get_headers(api_key), json=payload)
        return response

    async def get_task_status(self, category: str, model_key: str, task_id: str, api_key: Optional[str] = None) -> dict:
        model_info = MODEL_REGISTRY[category]["models"][model_key]
        task_endpoint = model_info["task_endpoint"].replace("{task_id}", task_id)
        url = f"{self.base_url}{task_endpoint}"
        response = await self._request_with_retry("GET", url, headers=self._get_headers(api_key))
        return response

    async def poll_task(self, category: str, model_key: str, task_id: str, api_key: Optional[str] = None) -> dict:
        for _ in range(settings.max_poll_attempts):
            result = await self.get_task_status(category, model_key, task_id, api_key)
            data = result.get("data", {})
            status = data.get("status", "")
            if status in ("COMPLETED", "FAILED"):
                return result
            await asyncio.sleep(settings.poll_interval)
        return {"data": {"task_id": task_id, "status": "TIMEOUT", "generated": []}}

    async def list_tasks(self, category: str, model_key: str, api_key: Optional[str] = None) -> dict:
        model_info = MODEL_REGISTRY[category]["models"][model_key]
        endpoint = model_info.get("list_endpoint", model_info["endpoint"])
        url = f"{self.base_url}{endpoint}"
        response = await self._request_with_retry("GET", url, headers=self._get_headers(api_key))
        return response

    async def validate_key(self, api_key: str) -> dict:
        try:
            url = f"{self.base_url}/v1/ai/mystic"
            async with httpx.AsyncClient(timeout=15.0) as c:
                response = await c.post(url, headers=self._get_headers(api_key), json={"prompt": "test"})
                status = response.status_code
                body = ""
                try:
                    data = response.json()
                    body = json.dumps(data)
                except Exception:
                    body = response.text[:500]

                return {"status_code": status, "body": body}
        except httpx.ConnectTimeout:
            return {"status_code": 0, "body": "Connection timeout — could not reach Magnific API"}
        except httpx.ReadTimeout:
            return {"status_code": 0, "body": "Read timeout — Magnific API took too long to respond"}
        except Exception as e:
            return {"status_code": 0, "body": f"Connection error: {str(e)}"}



client = MagnificClient()
