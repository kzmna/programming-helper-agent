"""Configuration management for the multi-agent system."""
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for the application."""
    
    # vLLM OpenAI-compatible server settings
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "http://localhost:8000/v1")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "EMPTY")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "default-model")
    
    # Database settings
    # DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///papers.db")
    
    # Agent settings
    MAX_RECURSION_LIMIT: int = int(os.getenv("MAX_RECURSION_LIMIT", "50"))
    SEARCH_MAX_RESULTS: int = int(os.getenv("SEARCH_MAX_RESULTS", "10"))
    
    # Model parameters
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS: Optional[int] = int(os.getenv("MAX_TOKENS", "2048")) if os.getenv("MAX_TOKENS") else None
    
    @classmethod
    def validate(cls):
        """Validate configuration settings."""
        if not cls.OPENAI_API_BASE:
            raise ValueError("OPENAI_API_BASE must be set")
        if not cls.MODEL_NAME or cls.MODEL_NAME == "default-model":
            raise ValueError("MODEL_NAME must be set in .env file")
    
    @classmethod
    def get_llm_config(cls) -> dict:
        """Get LLM configuration dictionary."""
        return {
            "base_url": cls.OPENAI_API_BASE,
            "api_key": cls.OPENAI_API_KEY,
            "model": cls.MODEL_NAME,
            "temperature": cls.TEMPERATURE,
            "max_tokens": cls.MAX_TOKENS,
        }
