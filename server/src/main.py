import uvicorn
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.src.api.router import router

app = FastAPI(
    title="Auto Video Localizer API",
    description="LAN-based distributed video localization orchestrator",
    version="1.0.0"
)

# Allow React client to communicate if hosted directly or via electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Serve built frontend (production mode)
# Run `cd client && npm run build` to generate client/dist
client_dist = Path("client/dist")
if client_dist.exists():
    app.mount("/", StaticFiles(directory=str(client_dist), html=True), name="static")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Server"}

if __name__ == "__main__":
    uvicorn.run("server.src.main:app", host="0.0.0.0", port=8080, reload=False)
