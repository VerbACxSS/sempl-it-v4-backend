import asyncio
from contextlib import asynccontextmanager
import os
import threading

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import torch

import anyio.to_thread
from app.services.analysis_service import AnalysisService
from app.services.monitoring_service import MonitoringService
from app.services.simplification_service import SimplificationService

load_dotenv()

from . import router


def _process_thread_count() -> int:
    try:
        return len(os.listdir("/proc/self/task"))
    except OSError:
        return threading.active_count()


def _analysis_concurrency_limit() -> int:
    limit = int(os.getenv("ANALYSIS_CONCURRENCY_LIMIT", "2"))
    if limit < 1:
        raise ValueError("ANALYSIS_CONCURRENCY_LIMIT must be at least 1")
    return limit


def _thread_pool_concurrency() -> int:
    limit = int(os.getenv("THREAD_POOL_CONCURRENCY", "100"))
    if limit < 1:
        raise ValueError("THREAD_POOL_CONCURRENCY must be at least 1")
    return limit


@asynccontextmanager
async def lifespan(app: FastAPI):
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = _thread_pool_concurrency()
    print(f"[THREAD_POOL] concurrency_limit={limiter.total_tokens}")
    analysis_concurrency_limit = _analysis_concurrency_limit()
    app.state.analysis_semaphore = asyncio.Semaphore(analysis_concurrency_limit)
    print(f"[LOCAL_ANALYSIS] concurrency_limit={analysis_concurrency_limit}")
    sentence_transformers_model = app.state.analysis_service.simplification_analyzer.similarity_analyzer.sentence_transformers_model
    print(
        "[RUNTIME] "
        f"cpu_count={os.cpu_count()} "
        f"torch_num_threads={torch.get_num_threads()} "
        f"torch_num_interop_threads={torch.get_num_interop_threads()} "
        f"sentence_transformer_device={sentence_transformers_model.device} "
        f"process_thread_count={_process_thread_count()}"
    )
    yield

# Initialize the FastAPI application
app = FastAPI(title="VerbACxSS SEMPL-IT API", openapi_url="/api/openapi.json", lifespan=lifespan)

# Add middlewares (CORS)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Initialize services
app.state.analysis_service = AnalysisService()
app.state.monitoring_service = MonitoringService()
app.state.simplification_service = SimplificationService()

# Include routers
app.include_router(router.router, prefix='/api/v1', tags=["api"])
