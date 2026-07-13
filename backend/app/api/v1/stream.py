"""
SSE streaming endpoint — runs the full analysis + prediction pipeline
with real-time progress events via Server-Sent Events.
"""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.services.analysis_service import AnalysisService
from app.services.prediction_service import PredictionService

logger = get_logger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

analysis_service = AnalysisService()
prediction_service = PredictionService()

# Full pipeline = analysis + prediction LLM calls, held open up to 300s.
pipeline_rate_limit = rate_limit("pipeline_stream", max_requests=10, window_seconds=600)


@router.post("/{document_id}/run-stream", dependencies=[Depends(pipeline_rate_limit)])
async def run_pipeline_stream(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Run the full analysis + prediction pipeline with SSE streaming progress.

    Returns a Server-Sent Events stream with real-time stage updates.
    Each event has the format:
        event: stage
        data: {"stage": "...", "progress": N, "detail": "..."}

    On completion:
        event: complete
        data: {"document_id": "...", "prediction_id": "...", "overall_confidence": 0.XX}

    On error:
        event: error
        data: {"error": "..."}
    """

    async def event_generator():
        """Generates SSE events as the pipeline progresses."""
        event_queue: asyncio.Queue[dict] = asyncio.Queue()

        async def progress_callback(stage: str, progress: int, detail: str):
            """Called by services to emit progress events."""
            await event_queue.put({
                "event": "stage",
                "data": {"stage": stage, "progress": progress, "detail": detail},
            })

        # Emit initial event
        yield _format_sse(
            "stage",
            {"stage": "starting", "progress": 0, "detail": "Starting pipeline..."},
        )

        try:
            # Phase 1: Analysis
            yield _format_sse(
                "stage",
                {"stage": "analysis_start", "progress": 5, "detail": "Starting AI analysis..."},
            )

            analysis = await analysis_service.run_analysis(
                document_id=document_id,
                user_id=user_id,
                db=db,
                progress_callback=progress_callback,
            )

            # Drain any queued events from the analysis callback
            while not event_queue.empty():
                event = await event_queue.get()
                yield _format_sse(event["event"], event["data"])

            yield _format_sse(
                "stage",
                {
                    "stage": "analysis_complete",
                    "progress": 70,
                    "detail": f"Analysis complete — {analysis.num_papers_found} papers found",
                },
            )

            # Phase 2: Prediction
            prediction = await prediction_service.generate_prediction(
                document_id=document_id,
                user_id=user_id,
                db=db,
                progress_callback=progress_callback,
            )

            # Drain any queued events from the prediction callback
            while not event_queue.empty():
                event = await event_queue.get()
                yield _format_sse(event["event"], event["data"])

            # Commit all changes
            await db.commit()

            # Emit completion
            yield _format_sse("complete", {
                "document_id": str(document_id),
                "prediction_id": str(prediction.id),
                "overall_confidence": prediction.overall_confidence,
                "generation_time_seconds": prediction.generation_time_seconds,
            })

        except Exception as e:
            await db.rollback()
            logger.error("pipeline_stream_failed", document_id=str(document_id), error=str(e))
            yield _format_sse("error", {"error": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _format_sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
