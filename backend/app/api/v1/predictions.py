"""
Prediction endpoints — generate and retrieve predictions.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models import Prediction
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/predictions", tags=["Predictions"])

prediction_service = PredictionService()


def _prediction_payload(prediction: Prediction) -> dict[str, Any]:
    """The wire shape of a prediction, shared by generate and fetch."""
    return {
        "id": str(prediction.id),
        "analysis_id": str(prediction.analysis_id),
        "predicted_paper": prediction.predicted_paper,
        "confidence": prediction.confidence_scores,
        "overall_confidence": prediction.overall_confidence,
        "topic_coverage": prediction.topic_coverage,
        "model_used": prediction.model_used,
        "generation_time_seconds": prediction.generation_time_seconds,
        "generated_at": prediction.generated_at.isoformat(),
    }

# Generation is 1–2 LLM calls per request — protect the provider quota.
generate_rate_limit = rate_limit("prediction_generate", max_requests=10, window_seconds=600)


@router.post(
    "/{document_id}/generate",
    status_code=201,
    dependencies=[Depends(generate_rate_limit)],
)
async def generate_prediction(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a predicted question paper for an analyzed document.

    Requires a completed analysis to exist for this document.
    """
    prediction = await prediction_service.generate_prediction(document_id, user_id, db)
    return _prediction_payload(prediction)


@router.get("/{document_id}")
async def get_prediction(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest prediction for a document."""
    prediction = await prediction_service.get_prediction(document_id, user_id, db)

    if not prediction:
        raise NotFoundError("Prediction", str(document_id))

    return _prediction_payload(prediction)


@router.get("/{document_id}/confidence")
async def get_confidence_report(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed confidence report for a prediction."""
    prediction = await prediction_service.get_prediction(document_id, user_id, db)

    if not prediction:
        raise NotFoundError("Prediction", str(document_id))

    return prediction.confidence_scores
