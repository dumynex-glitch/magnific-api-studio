# Magnific API Studio

A full-stack FastAPI web application for integrating with the Magnific AI API. Provides a unified interface for generating images, videos, audio, and more across 76+ AI models from providers like Kling, Runway, Google Veo, PixVerse, LTX, Seedance, WAN, MiniMax, and more.

## Features

- **76+ AI Models** across 5 categories: Image, Video, Audio, Prompt Tools, and Lip Sync
- **Dynamic Form Generation** — UI automatically adapts to each model's schema
- **Multi-Model Support** — Text-to-Video, Image-to-Video, Reference-to-Video, Transitions, VFX, and more
- **API Key Management** — Store and switch between up to 5 API keys with validation
- **Async Task Handling** — Polling and webhook support for long-running generations
- **Rate Limiting** — Configurable sliding window rate limiter
- **Docker Ready** — Containerized with health checks

## Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/magnific-api-studio.git
cd magnific-api-studio

# Configure environment
cp .env.example .env
# Edit .env with your Magnific API key

# Build and run
docker compose up -d

# Open in browser
open http://localhost:8000
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Magnific API key

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Open in browser
open http://localhost:8000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MAGNIFIC_API_KEY` | Your Magnific API key (fallback) | - |
| `MAGNIFIC_BASE_URL` | Magnific API base URL | `https://api.magnific.com` |
| `POLL_INTERVAL` | Polling interval in seconds | `3` |
| `MAX_POLL_ATTEMPTS` | Maximum polling attempts | `200` |
| `WEBHOOK_SECRET` | HMAC secret for webhook verification | - |
| `RATE_LIMIT_MAX` | Max requests per window | `60` |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | `60` |

## API Documentation

Once running, access the interactive API docs at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Model Categories

### Image Generation (5 models)
- Mystic, Flux 2 Pro, Flux Kontext Pro, Flux Kontext Max, Hyper-Flux

### Video Generation (66 models)
- **Kling**: v2, 2.1 Master/Pro/Std, 3 Pro/Std, 3 Omni, 3 Motion Control, O1 Pro/Std
- **Runway**: Act Two, Gen4 Turbo, Gen 4.5 (T2V/I2V)
- **Google Veo 3.1**: T2V, I2V, Ref2V, Fast variants
- **PixVerse**: V5, V5 Transition, V5.5, V6
- **LTX Video 2.0**: Pro/Fast (T2V/I2V)
- **Seedance 1.5 Pro**: 480p, 720p, 1080p
- **WAN**: 2.6, 2.5, 2.2 (T2V/I2V)
- **MiniMax**: Hailuo 02, 2.3, Video 01 Live
- **Happy Horse 1.0**: T2V, I2V, R2V, Video Edit
- **VFX**: 8 cinematic visual effects filters
- **OmniHuman 1.5**: Audio-driven human animation

### Audio Generation (2 models)
- Music Generation, Sound Effects

### Prompt Tools (2 models)
- Prompt Enhancer, Prompt Optimizer

### Lip Sync (1 model)
- Lip Sync Pro

## Project Structure

```
magnific-api-studio/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Settings and environment
│   ├── models.py             # Pydantic models
│   ├── client.py             # Async Magnific API client
│   ├── registry.py           # Model registry (76+ models)
│   ├── routes/
│   │   ├── generate.py       # Generation endpoints
│   │   └── webhooks.py       # Webhook handler
│   └── static/
│       ├── index.html        # Main UI
│       ├── css/style.css     # Styles
│       └── js/app.js         # Frontend logic
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT
