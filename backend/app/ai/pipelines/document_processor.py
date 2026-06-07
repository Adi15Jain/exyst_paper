"""
Document processing pipeline.

Handles PDF text extraction with multi-strategy fallback:
  1. pdfminer.six (best for text-based PDFs)
  2. PyMuPDF/fitz (fallback for complex layouts)

Also extracts metadata (year, course code, marks) from the text.
"""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

from app.core.exceptions import PDFParsingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentProcessor:
    """
    Processes uploaded PDF documents into structured text.
    """

    def extract_pages_text(self, pdf_path: str) -> List[Dict[str, str]]:
        """
        Extract text from each page of a PDF.

        Returns:
            List of dicts with 'page_number' and 'text' keys.
        """
        pages = []

        try:
            for i, page_layout in enumerate(extract_pages(pdf_path)):
                text = ""
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        text += element.get_text()
                text = text.strip()

                if text:  # Only include non-empty pages
                    pages.append({
                        "page_number": i + 1,
                        "text": text,
                    })

            logger.info(
                "pdf_extraction_complete",
                path=pdf_path,
                strategy="pdfminer",
                total_pages=len(pages),
            )

        except Exception as e:
            logger.warning(
                "pdfminer_extraction_failed",
                path=pdf_path,
                error=str(e),
            )
            # Fallback to PyMuPDF
            pages = self._extract_with_pymupdf(pdf_path)

        if not pages:
            raise PDFParsingError(f"No text could be extracted from PDF: {pdf_path}")

        return pages

    def _extract_with_pymupdf(self, pdf_path: str) -> List[Dict[str, str]]:
        """Fallback extraction using PyMuPDF."""
        try:
            import fitz  # PyMuPDF

            pages = []
            doc = fitz.open(pdf_path)

            for i, page in enumerate(doc):
                text = page.get_text().strip()
                if text:
                    pages.append({
                        "page_number": i + 1,
                        "text": text,
                    })

            doc.close()

            logger.info(
                "pdf_extraction_complete",
                path=pdf_path,
                strategy="pymupdf",
                total_pages=len(pages),
            )

            return pages

        except Exception as e:
            raise PDFParsingError(f"Both PDF extraction strategies failed: {str(e)}")

    def extract_metadata(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract exam metadata from text using regex patterns.

        Extracts: university, course_code, subject, max_marks, academic_session, duration.
        """
        metadata: Dict[str, Optional[str]] = {
            "university": self._extract_university(text),
            "course_code": self._extract_course_code(text),
            "subject": self._extract_subject(text),
            "max_marks": self._extract_max_marks(text),
            "academic_session": self._extract_session(text),
            "duration": self._extract_duration(text),
        }

        logger.info("metadata_extracted", **{k: v for k, v in metadata.items() if v})
        return metadata

    def compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of a file for deduplication."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def split_papers_by_session(self, text: str) -> List[Dict[str, str]]:
        """
        Split concatenated question paper text into individual papers by session year.

        Detects patterns like: 2023-24, 2024-25, May 2024, Dec 2023
        """
        # Pattern to match academic sessions
        session_pattern = r"((?:20\d{2}[-–]\d{2})|(?:(?:May|Dec|Jan|Jun|Jul|Nov)\s+20\d{2}))"
        parts = re.split(f"({session_pattern})", text)

        papers = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and re.match(session_pattern, parts[i + 1] if i + 1 < len(parts) else ""):
                # Skip the pre-match text, take the session and content
                session = parts[i + 1].strip() if i + 1 < len(parts) else "Unknown"
                content = parts[i + 2].strip() if i + 2 < len(parts) else ""
                if content:
                    papers.append({"session": session, "text": f"{session}\n{content}"})
                i += 3
            else:
                i += 1

        # If no sessions were found, treat entire text as one paper
        if not papers and text.strip():
            papers = [{"session": "Unknown", "text": text}]

        logger.info("papers_split", num_papers=len(papers))
        return papers

    # --- Private extraction helpers ---

    def _extract_university(self, text: str) -> Optional[str]:
        patterns = [
            r"([A-Z][A-Z\s]+UNIVERSITY[A-Z\s–-]*)",
            r"TEERTHANKER MAHAVEER UNIVERSITY",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_course_code(self, text: str) -> Optional[str]:
        patterns = [
            r"Course\s*Code\s*[:：]\s*([A-Z]+\d+)",
            r"\b([A-Z]{2,}\d{3,})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_subject(self, text: str) -> Optional[str]:
        """Extract subject from context — not hardcoded to any specific subject."""
        # Look for explicit subject/course name markers
        patterns = [
            r"Subject\s*[:：]\s*(.+?)(?:\n|$)",
            r"Course\s*(?:Title|Name)\s*[:：]\s*(.+?)(?:\n|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_max_marks(self, text: str) -> Optional[str]:
        patterns = [
            r"Max\.?\s*Marks?\s*[:：]\s*(\d+)",
            r"Maximum\s*Marks?\s*[:：]\s*(\d+)",
            r"Total\s*Marks?\s*[:：]\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_session(self, text: str) -> Optional[str]:
        patterns = [
            r"(20\d{2}[-–]\d{2})",
            r"((?:May|Dec|Jan|Jun|Jul|Nov)\s+20\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_duration(self, text: str) -> Optional[str]:
        patterns = [
            r"Time\s*[:：]\s*([\d.]+\s*(?:Hours?|Hrs?))",
            r"Duration\s*[:：]\s*([\d.]+\s*(?:Hours?|Hrs?))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
