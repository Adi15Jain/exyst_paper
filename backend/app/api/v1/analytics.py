"""
Analytics endpoints — aggregate statistics and insights.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models import Analysis, Document, Prediction, ProcessingStatus

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_overview(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get high-level analytics overview for the current user.

    Returns document counts, analysis stats, prediction confidence averages.
    """
    # Document stats
    doc_count_stmt = select(func.count()).select_from(Document).where(
        Document.user_id == user_id
    )
    doc_result = await db.execute(doc_count_stmt)
    total_documents = doc_result.scalar() or 0

    # Analysis stats
    analysis_stmt = (
        select(
            func.count().label("total"),
            func.count().filter(Analysis.status == ProcessingStatus.COMPLETED).label("completed"),
            func.avg(Analysis.processing_time_seconds).label("avg_processing_time"),
            func.sum(Analysis.num_pages_processed).label("total_pages"),
            func.sum(Analysis.num_papers_found).label("total_papers"),
        )
        .select_from(Analysis)
        .join(Document)
        .where(Document.user_id == user_id)
    )
    analysis_result = await db.execute(analysis_stmt)
    analysis_row = analysis_result.one()

    # Prediction stats
    prediction_stmt = (
        select(
            func.count().label("total"),
            func.avg(Prediction.overall_confidence).label("avg_confidence"),
            func.max(Prediction.overall_confidence).label("max_confidence"),
            func.avg(Prediction.generation_time_seconds).label("avg_generation_time"),
        )
        .select_from(Prediction)
        .join(Analysis)
        .join(Document)
        .where(Document.user_id == user_id)
    )
    prediction_result = await db.execute(prediction_stmt)
    prediction_row = prediction_result.one()

    return {
        "documents": {
            "total": total_documents,
        },
        "analyses": {
            "total": analysis_row.total or 0,
            "completed": analysis_row.completed or 0,
            "avg_processing_time_seconds": round(float(analysis_row.avg_processing_time or 0), 2),
            "total_pages_processed": analysis_row.total_pages or 0,
            "total_papers_found": analysis_row.total_papers or 0,
        },
        "predictions": {
            "total": prediction_row.total or 0,
            "avg_confidence": round(float(prediction_row.avg_confidence or 0), 3),
            "max_confidence": round(float(prediction_row.max_confidence or 0), 3),
            "avg_generation_time_seconds": round(float(prediction_row.avg_generation_time or 0), 2),
        },
    }


@router.get("/topic-frequency/{document_id}")
async def get_topic_frequency(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get topic frequency analysis for a specific document's analysis.

    Returns frequency data formatted for chart rendering.
    """
    stmt = (
        select(Analysis)
        .join(Document)
        .where(
            Document.id == document_id,
            Document.user_id == user_id,
            Analysis.status == ProcessingStatus.COMPLETED,
        )
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        return {"topics": [], "chart_data": {"labels": [], "values": [], "colors": []}}

    topics = analysis.topic_frequency or []

    # Build chart-ready data
    labels = [t.get("topic", "Unknown") for t in topics[:15]]
    values = [t.get("count", 0) for t in topics[:15]]
    percentages = [t.get("percentage", 0) for t in topics[:15]]
    trends = [t.get("trend", "stable") for t in topics[:15]]

    # Color scheme based on trend
    trend_colors = {
        "rising": "#22c55e",    # green
        "falling": "#ef4444",   # red
        "stable": "#6366f1",    # indigo
    }
    colors = [trend_colors.get(t, "#6366f1") for t in trends]

    return {
        "topics": topics,
        "chart_data": {
            "labels": labels,
            "values": values,
            "percentages": percentages,
            "trends": trends,
            "colors": colors,
        },
    }


@router.get("/confidence-breakdown/{document_id}")
async def get_confidence_breakdown(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get prediction confidence breakdown for charts.

    Returns per-question confidence and aggregate scores.
    """
    stmt = (
        select(Prediction)
        .join(Analysis)
        .join(Document)
        .where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        .order_by(Prediction.generated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    prediction = result.scalar_one_or_none()

    if not prediction:
        return {
            "overall": 0,
            "factors": {},
            "per_question": [],
        }

    confidence_scores = prediction.confidence_scores or {}

    return {
        "overall": prediction.overall_confidence or 0,
        "factors": {
            "topic_coverage": confidence_scores.get("topic_coverage_score", 0),
            "historical_alignment": confidence_scores.get("historical_alignment_score", 0),
            "question_quality": confidence_scores.get("question_quality_score", 0),
        },
        "per_question": confidence_scores.get("per_question_confidence", []),
    }
