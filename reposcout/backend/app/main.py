"""
RepoScout Backend Application.
Entry point for FastAPI server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import router as api_router

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Intelligent GitHub repository discovery backend service.",
    debug=settings.DEBUG
)

# Configure Cross-Origin Resource Sharing (CORS)
# Ensures Chrome Extension popups (chrome-extension://*) and local Vite dev servers can query the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits extension and local frontend origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    """Root metadata endpoint."""
    return {
        "service": "reposcout",
        "version": "0.1.0",
        "documentation": "/docs",
        "health": "/api/health",
        "search": "/api/search?q=RAG"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

