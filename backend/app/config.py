"""
Configuration management.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    app_name: str = "AutoClean"
    database_url: str = "sqlite:///./autoclean.db"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    rag_index_path: str = "./rag_knowledge"
    storage_root: str = "./data/storage"
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # RAG
    chroma_db_path: str = "./data/chroma_db"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Reinforcement learning configuration path
    # Path to a JSON file storing per‑extractor strictness scores.  The system
    # will automatically create this file if it does not exist and will
    # persist updates when users approve or reject rules.  You can override
    # this path via an environment variable `RL_CONFIG_PATH` if you wish to
    # store the state elsewhere (e.g., in a mounted volume).
    rl_config_path: str = os.getenv("RL_CONFIG_PATH", "./data/rl_config.json")

    # Ollama / Local LLM
    # Base URL for Ollama's API (e.g. http://localhost:11434). Can be overridden in .env.
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # Model name for Ollama (e.g. llama3.1:8b). Can be overridden in .env.
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    
    @property
    def OPENAI_API_KEY(self) -> Optional[str]:
        return self.openai_api_key or os.getenv("OPENAI_API_KEY")
    
    @property
    def ANTHROPIC_API_KEY(self) -> Optional[str]:
        return self.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

    @property
    def OLLAMA_BASE_URL(self) -> str:
        """Return Ollama base URL from settings or environment."""
        return os.getenv("OLLAMA_BASE_URL", self.ollama_base_url)

    @property
    def OLLAMA_MODEL(self) -> str:
        """Return Ollama model name from settings or environment."""
        return os.getenv("OLLAMA_MODEL", self.ollama_model)

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


settings = Settings()

