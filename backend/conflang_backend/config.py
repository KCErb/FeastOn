"""
Dependency Injection configuration for the backend.

This is where we wire up concrete implementations of providers.
"""

from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from .providers.persistence_provider import PersistenceProvider, JSONPersistenceProvider
from .providers.identity_provider import IdentityProvider, StubIdentityProvider
from .providers.llm_provider import LLMProvider, MockLLMProvider

load_dotenv()


class AppConfig(BaseModel):
    """Application-wide configuration with injected providers"""

    model_config = {"arbitrary_types_allowed": True}

    data_dir: Path
    persistence: PersistenceProvider
    identity: IdentityProvider
    llm: LLMProvider


_config_instance: AppConfig | None = None


def get_app_config() -> AppConfig:
    """
    Get the singleton app configuration.

    This is where we inject concrete implementations.
    In production, swap out MockLLMProvider for AnthropicLLMProvider, etc.
    """
    global _config_instance

    if _config_instance is None:
        data_dir = Path(os.getenv("DATA_DIR", "../data"))

        _config_instance = AppConfig(
            data_dir=data_dir,
            persistence=JSONPersistenceProvider(base_path=data_dir / "packaged"),
            identity=StubIdentityProvider(),
            llm=MockLLMProvider(),
        )

    return _config_instance
