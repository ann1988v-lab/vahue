import asyncio
import os

from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

from bot import run_bot

load_dotenv()

app = FastAPI()

@app.get("/")
async def root():
    return {"ok": True, "service": "sakura-bot"}

@app.get("/health")
async def health():
    return {"ok": True}

async def web():
    cfg = uvicorn.Config(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "3000")),
        log_level="info",
    )
    await uvicorn.Server(cfg).serve()

async def main():
    await asyncio.gather(run_bot(), web())

if __name__ == "__main__":
    asyncio.run(main())
