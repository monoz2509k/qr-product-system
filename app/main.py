from fastapi import FastAPI

from app.api.health import router

app = FastAPI(openapi_url=None)
app.include_router(router)
