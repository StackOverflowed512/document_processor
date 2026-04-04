import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application configuration"""
    
    # API Keys
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    huggingface_api_key: Optional[str] = os.getenv("HUGGINGFACE_API_KEY")
    
    # Model Configuration
    primary_vlm_model: str = os.getenv("PRIMARY_VLM_MODEL", "qwen-vl")
    vision_model_api_base: str = os.getenv("VISION_MODEL_API_BASE", "https://api.openrouter.ai/v1")
    llm_model_for_cleansing: str = os.getenv("LLM_MODEL_FOR_CLEANSING", "llama-3.1-8b-instant")
    
    # OCR Settings
    ocr_engine: str = os.getenv("OCR_ENGINE", "tesseract")
    tesseract_path: str = os.getenv("TESSERACT_PATH", "/usr/bin/tesseract")
    
    # File Settings
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", 10485760))
    allowed_extensions: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".txt", ".eml"]
    temp_dir: Path = Path(os.getenv("TEMP_DIR", "./temp_uploads"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Rate Limiting
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", 60))
    rate_limit_period: int = int(os.getenv("RATE_LIMIT_PERIOD", 60))
    
    # Cache
    redis_url: Optional[str] = os.getenv("REDIS_URL")
    cache_ttl: int = int(os.getenv("CACHE_TTL", 3600))
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Create temp directory if it doesn't exist
settings.temp_dir.mkdir(parents=True, exist_ok=True)