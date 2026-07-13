"""
Analysis endpoints — trigger and retrieve analysis results.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.schemas.analysis import AnalysisResponse, AnalysisStatusResponse
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["Analysis"])

analysis_service = AnalysisService()

# Each run costs several LLM calls — protect the provider quota.
run_rate_limit = rate_limit("analysis_run", max_requests=10, window_seconds=600)


@router.post(
    "/{document_id}/run",
    response_model=AnalysisStatusResponse,
    status_code=202,
    dependencies=[Depends(run_rate_limit)],
)
async def run_analysis(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the analysis pipeline for a document.

    Creates a PROCESSING analysis record, schedules the pipeline to run in the
    background, and returns 202 immediately. Poll ``GET /analysis/{id}/status``
    for progress.
    """
    analysis = await analysis_service.create_pending_analysis(document_id, user_id, db)
    # Commit before the response so the background task (which opens its own
    # session) can see the PROCESSING record.
    await db.commit()

    background_tasks.add_task(
        analysis_service.run_analysis_background,
        document_id,
        user_id,
        analysis.id,
    )

    return AnalysisStatusResponse(
        id=analysis.id,
        status=analysis.status.value,
        processing_time_seconds=analysis.processing_time_seconds,
        error_message=analysis.error_message,
    )


@router.get("/{document_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Check the status of an analysis."""
    analysis = await analysis_service.get_analysis(document_id, user_id, db)

    if not analysis:
        raise NotFoundError("Analysis", str(document_id))

    return AnalysisStatusResponse(
        id=analysis.id,
        status=analysis.status.value,
        processing_time_seconds=analysis.processing_time_seconds,
        error_message=analysis.error_message,
    )


@router.get("/{document_id}/result", response_model=AnalysisResponse)
async def get_analysis_result(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get full analysis results for a document."""
    analysis = await analysis_service.get_analysis(document_id, user_id, db)

    if not analysis:
        raise NotFoundError("Analysis", str(document_id))

    return AnalysisResponse(
        id=analysis.id,
        document_id=analysis.document_id,
        status=analysis.status.value,
        syllabus_structure=analysis.syllabus_structure,
        question_papers=analysis.question_papers or [],
        topic_frequency=analysis.topic_frequency or [],
        pattern_analysis=analysis.pattern_analysis,
        num_pages_processed=analysis.num_pages_processed,
        num_papers_found=analysis.num_papers_found,
        processing_time_seconds=analysis.processing_time_seconds,
        model_used=analysis.model_used,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )
