import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    magnific_api_key: str = os.getenv("MAGNIFIC_API_KEY", "")
    magnific_base_url: str = os.getenv("MAGNIFIC_BASE_URL", "https://api.magnific.com")
    poll_interval: int = int(os.getenv("POLL_INTERVAL", "3"))
    max_poll_attempts: int = int(os.getenv("MAX_POLL_ATTEMPTS", "200"))
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")


settings = Settings()
