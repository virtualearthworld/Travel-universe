from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Travel Universe API", version="0.1.0", description="Travel content, reconstruction jobs, and social discovery API.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["*"])

@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "travel-universe-api"}

@app.get("/api/v1", tags=["meta"])
async def api_root() -> dict[str, str]:
    return {"name": "Travel Universe API", "version": "0.1.0"}
