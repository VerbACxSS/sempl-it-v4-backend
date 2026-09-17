import logging
import time
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request as FastAPIRequest
from fastapi.concurrency import run_in_threadpool

from app.models.AnalysisRequest import TextAnalysisRequest, ComparisonAnalysisRequest
from app.models.AnalysisResponse import TextAnalysisResponse, ComparisonAnalysisResponse
from app.services.analysis_service import AnalysisService
from app.services.service_loader import get_analysis_service, get_monitoring_service, MonitoringService

# Initialize logging
logger = logging.getLogger()

router = APIRouter()


async def _run_local_analysis(http_request: FastAPIRequest, request_id: str, operation: str, analysis_function, **kwargs):
    analysis_semaphore = http_request.app.state.analysis_semaphore
    waiting_started = time.monotonic()
    print(f"[LOCAL_ANALYSIS] request_id={request_id} operation={operation} waiting")
    await analysis_semaphore.acquire()
    try:
        print(
            f"[LOCAL_ANALYSIS] request_id={request_id} operation={operation} admitted "
            f"wait_duration={time.monotonic() - waiting_started:.2f}s"
        )
        return await run_in_threadpool(analysis_function, request_id=request_id, **kwargs)
    finally:
        analysis_semaphore.release()
        print(f"[LOCAL_ANALYSIS] request_id={request_id} operation={operation} released")


@router.post("/text", response_model=TextAnalysisResponse)
async def analyze_text(request: TextAnalysisRequest,
                       http_request: FastAPIRequest,
                       background_tasks: BackgroundTasks,
                       analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
                       monitoring_service: Annotated[MonitoringService, Depends(get_monitoring_service)]):
    try:
        logger.info("Text analysis request received (consent: %s)", request.consent)

        # Analyze the text
        request_id = uuid.uuid4().hex[:8]
        text_evaluation = await _run_local_analysis(
            http_request,
            request_id,
            "text_analysis",
            analysis_service.do_text_analysis,
            text=request.text
        )

        # Build the response
        response = TextAnalysisResponse(text=request.text, text_evaluation=text_evaluation)

        # Save the text analysis result if consent is given
        if request.consent:
            background_tasks.add_task(monitoring_service.send_text_analysis_result, text_analysis_result=response)

        # Return the response
        return response
    except Exception as exception:
        logger.exception("An error occurred during text analysis.")
        raise HTTPException(status_code=500, detail="An error occurred during text analysis.")


@router.post("/comparison", response_model=ComparisonAnalysisResponse)
async def compare_texts(request: ComparisonAnalysisRequest,
                        http_request: FastAPIRequest,
                        background_tasks: BackgroundTasks,
                        analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
                        monitoring_service: Annotated[MonitoringService, Depends(get_monitoring_service)]):
    try:
        logger.info("Comparison analysis request received (consent: %s)", request.consent)

        # Compare the texts
        request_id = uuid.uuid4().hex[:8]
        comparison = await _run_local_analysis(
            http_request,
            request_id,
            "text_comparison",
            analysis_service.do_text_comparison,
            text1=request.text1,
            text2=request.text2
        )

        # Build the response
        response = ComparisonAnalysisResponse(
            text1=request.text1,
            text2=request.text2,
            metrics1=comparison.reference_text_evaluation,
            metrics2=comparison.simplified_text_evaluation,
            similarity=comparison.similarity_evaluation,
            diff=comparison.diff_evaluation
        )

        # Save the comparison result if consent is given
        if request.consent:
            background_tasks.add_task(monitoring_service.send_texts_comparison_analysis_result, texts_comparison_analysis_result=response)

        # Return the response
        return response
    except Exception as exception:
        logger.exception("An exception occurred during comparison analysis.")
        raise HTTPException(status_code=500, detail="An exception occurred during comparison analysis.")
