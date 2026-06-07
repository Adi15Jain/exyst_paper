"""
ChromaDB-based RAG (Retrieval-Augmented Generation) pipeline.

Stores historical question paper content as vector embeddings, enabling:
- Semantic similarity search across past questions
- Context retrieval for more accurate predictions
- Topic clustering and trend analysis
"""

import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Collection names
QUESTIONS_COLLECTION = "exam_questions"
TOPICS_COLLECTION = "syllabus_topics"


class RAGPipeline:
    """
    Vector-based retrieval pipeline using ChromaDB.

    Stores question embeddings and retrieves similar historical questions
    to augment prediction prompts with relevant examples.
    """

    def __init__(self):
        settings = get_settings()
        persist_dir = os.path.join(settings.OUTPUTS_DIR, "chromadb")
        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Question embeddings collection
        self.questions_collection = self.client.get_or_create_collection(
            name=QUESTIONS_COLLECTION,
            metadata={"description": "Historical exam questions with topic metadata"},
        )

        # Syllabus topics collection
        self.topics_collection = self.client.get_or_create_collection(
            name=TOPICS_COLLECTION,
            metadata={"description": "Syllabus topics for semantic matching"},
        )

    def index_questions(
        self,
        questions: List[Dict[str, Any]],
        document_id: str,
        session: str = "unknown",
    ) -> int:
        """
        Index extracted questions into the vector store.

        Args:
            questions: List of question dicts with 'question_text', 'topic', 'marks'.
            document_id: Source document ID for filtering.
            session: Academic session (e.g., "2023-24").

        Returns:
            Number of questions indexed.
        """
        if not questions:
            return 0

        documents = []
        metadatas = []
        ids = []

        for i, q in enumerate(questions):
            text = q.get("question_text", q.get("text", ""))
            if not text or len(text.strip()) < 5:
                continue

            doc_text = f"{q.get('topic', '')} | {text}"
            documents.append(doc_text)

            metadatas.append({
                "document_id": document_id,
                "session": session,
                "topic": q.get("topic", "unknown"),
                "marks": str(q.get("marks", 0)),
                "question_type": q.get("question_type", "medium"),
                "question_number": str(q.get("question_number", i + 1)),
            })

            ids.append(f"{document_id}_{session}_{i}")

        if not documents:
            return 0

        try:
            self.questions_collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(
                "questions_indexed",
                count=len(documents),
                document_id=document_id,
                session=session,
            )
            return len(documents)

        except Exception as e:
            logger.error("question_indexing_failed", error=str(e))
            return 0

    def index_topics(
        self,
        topics: List[str],
        document_id: str,
        unit: str = "unknown",
    ) -> int:
        """
        Index syllabus topics into the vector store.

        Args:
            topics: List of topic strings.
            document_id: Source document ID.
            unit: The unit/module these topics belong to.

        Returns:
            Number of topics indexed.
        """
        if not topics:
            return 0

        documents = []
        metadatas = []
        ids = []

        for i, topic in enumerate(topics):
            if not topic.strip():
                continue
            documents.append(topic)
            metadatas.append({
                "document_id": document_id,
                "unit": unit,
            })
            ids.append(f"{document_id}_topic_{unit}_{i}")

        if not documents:
            return 0

        try:
            self.topics_collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(
                "topics_indexed",
                count=len(documents),
                document_id=document_id,
            )
            return len(documents)

        except Exception as e:
            logger.error("topic_indexing_failed", error=str(e))
            return 0

    def retrieve_similar_questions(
        self,
        query: str,
        n_results: int = 10,
        topic_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar historical questions using semantic search.

        Args:
            query: The query text (e.g., a topic name or question).
            n_results: Maximum number of results to return.
            topic_filter: Optional topic to filter by.

        Returns:
            List of similar question dicts with scores.
        """
        try:
            where_filter = None
            if topic_filter:
                where_filter = {"topic": {"$eq": topic_filter}}

            results = self.questions_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )

            similar_questions = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0

                    similar_questions.append({
                        "text": doc,
                        "topic": metadata.get("topic", ""),
                        "session": metadata.get("session", ""),
                        "marks": metadata.get("marks", ""),
                        "similarity_score": round(1 - distance, 3),  # Convert distance to similarity
                    })

            logger.info(
                "similar_questions_retrieved",
                query_length=len(query),
                results_count=len(similar_questions),
            )

            return similar_questions

        except Exception as e:
            logger.warning("retrieval_failed", error=str(e))
            return []

    def retrieve_related_topics(
        self,
        query: str,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find semantically related syllabus topics.

        Args:
            query: Topic or concept to find related topics for.
            n_results: Max results.

        Returns:
            List of related topic dicts with similarity scores.
        """
        try:
            results = self.topics_collection.query(
                query_texts=[query],
                n_results=n_results,
            )

            related = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0

                    related.append({
                        "topic": doc,
                        "unit": metadata.get("unit", ""),
                        "similarity_score": round(1 - distance, 3),
                    })

            return related

        except Exception as e:
            logger.warning("topic_retrieval_failed", error=str(e))
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        return {
            "total_questions": self.questions_collection.count(),
            "total_topics": self.topics_collection.count(),
        }
