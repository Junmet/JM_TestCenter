from fastapi import FastAPI

from app.api.v1.router import api_router


app = FastAPI(title="JM Test Center Backend", version="0.1.0")
app.include_router(api_router, prefix="")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}

