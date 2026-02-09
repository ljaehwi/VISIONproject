import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import ai, camera, dataset, logs, pipeline, vision
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )


setup_logging()
app = FastAPI(title='ACA Backend')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(logs.router)
app.include_router(camera.router)
app.include_router(vision.router)
app.include_router(pipeline.router)
app.include_router(ai.router)
app.include_router(dataset.router)

app.mount(settings.static_url, StaticFiles(directory=settings.static_dir), name='static')


@app.on_event('startup')
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
