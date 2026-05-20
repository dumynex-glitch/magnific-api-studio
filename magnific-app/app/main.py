from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import time
import logging
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from app.routes.generate import router as generate_router
from app.routes.webhooks import router as webhook_router
from app.log_store import log_store

app = FastAPI(title="Magnific API Studio", version="1.0.0")


class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_allowed(self, client_ip: str) -> tuple[bool, dict]:
        now = time.time()
        window_start = now - self.window_seconds

        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > window_start
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - self.requests[client_ip][0]))
            return False, {"retry_after": max(1, retry_after)}

        self.requests[client_ip].append(now)
        remaining = self.max_requests - len(self.requests[client_ip])
        return True, {"remaining": remaining, "limit": self.max_requests}


rate_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_MAX", "60")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    allowed, info = rate_limiter.is_allowed(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded. Try again in {info['retry_after']} seconds"},
            headers={"Retry-After": str(info["retry_after"])},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(info.get("limit", 60))
    response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate_router)
app.include_router(webhook_router)

@app.get("/api/logs")
async def get_logs(last_id: int = 0):
    return {"entries": log_store.get_since(last_id), "total": len(log_store.entries)}

@app.post("/api/logs/clear")
async def clear_logs():
    log_store.clear()
    return {"status": "cleared"}

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))
