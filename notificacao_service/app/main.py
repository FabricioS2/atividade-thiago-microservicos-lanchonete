from fastapi import FastAPI
from .database import engine, Base
from .routes import router
from .consumer import consume
import asyncio

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Notificacao Service")
app.include_router(router)

@app.on_event("startup")
async def start_consumer():
    loop = asyncio.get_event_loop()
    loop.create_task(consume())

@app.get("/health")
def health():
    return {"status": "ok"}