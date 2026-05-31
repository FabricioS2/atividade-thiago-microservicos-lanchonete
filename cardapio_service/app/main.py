from fastapi import FastAPI
from .database import engine, Base
from .routes import router

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Cardapio Service")
app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}