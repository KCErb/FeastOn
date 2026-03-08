"""
Development server entry point for the backend.

Run this with: python run.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "conflang_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
