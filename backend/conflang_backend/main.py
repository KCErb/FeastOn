"""
FeastOn Backend

FastAPI server that:
- Serves processed talk data from the pipeline
- Proxies on-demand LLM calls for word analysis
- Manages user preferences and flashcards

Feast upon the words of Christ — in any language.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_app_config
from .routes import health, talks, analyze


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    # Initialize providers via DI
    config = get_app_config()
    app.state.config = config

    print(f"✓ Backend started with {type(config.persistence).__name__}")
    print(f"✓ Data directory: {config.data_dir}")

    yield

    print("✓ Backend shutting down")


app = FastAPI(
    title="FeastOn API",
    version="0.1.0",
    description="Study languages through General Conference talks",
    lifespan=lifespan
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router)
app.include_router(talks.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
