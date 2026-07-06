"""
Document processing pipeline.

Handles PDF text extraction with multi-strategy fallback:
  1. pdfminer.six (best for text-based PDFs)
  2. PyMuPDF/fitz (fallback for complex layouts)

Also extracts metadata (year, course code, marks) from the text.
"""

import re

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

from app.core.exceptions import PDFParsingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentProcessor:
    """
    Processes uploaded PDF documents into structured text.
    """

    def extract_pages_text(self, pdf_path: str) -> list[dict[str, str]]:
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

    def _extract_with_pymupdf(self, pdf_path: str) -> list[dict[str, str]]:
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

    def extract_metadata(self, text: str) -> dict[str, str | None]:
        """
        Extract exam metadata from text using regex patterns.

        Extracts: university, course_code, subject, max_marks, academic_session, duration.
        """
        metadata: dict[str, str | None] = {
            "university": self._extract_university(text),
            "course_code": self._extract_course_code(text),
            "subject": self._extract_subject(text),
            "max_marks": self._extract_max_marks(text),
            "academic_session": self._extract_session(text),
            "duration": self._extract_duration(text),
        }

        logger.info("metadata_extracted", **{k: v for k, v in metadata.items() if v})
        return metadata

    # A paper boundary is an examination header (more reliable than a bare year, which
    # can recur inside a paper). Falls back to a bare academic session if no header exists.
    _EXAM_HEADER_RE = re.compile(
        r"(?:(?:ODD|EVEN|Odd|Even)\s+)?Semester\s+Examination|"
        r"(?:End\s+Term|Mid\s+Term)\s+Examination",
        re.IGNORECASE,
    )
    _SESSION_RE = re.compile(
        r"(?:20\d{2}[-–]\d{2})|(?:(?:May|Dec|Jan|Jun|Jul|Nov)\s+20\d{2})"
    )

    def split_papers_by_session(self, text: str) -> list[dict[str, str]]:
        """
        Split concatenated text into individual question papers.

        Splits on examination-header markers (e.g. "ODD Semester Examination 2021-22")
        when present, otherwise on bare academic-session markers. The full text of each
        paper — not just the marker — is preserved.
        """
        text = text or ""
        if not text.strip():
            return []

        # Prefer exam-header boundaries; they delimit whole papers reliably.
        boundaries = [m.start() for m in self._EXAM_HEADER_RE.finditer(text)]
        if not boundaries:
            boundaries = [m.start() for m in self._SESSION_RE.finditer(text)]

        if not boundaries:
            return [{"session": "Unknown", "text": text}]

        papers: list[dict[str, str]] = []
        for idx, start in enumerate(boundaries):
            end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(text)
            chunk = text[start:end].strip()
            if len(chunk) < 50:  # skip stray markers with no real content
                continue
            session_match = self._SESSION_RE.search(chunk)
            session = session_match.group(0).strip() if session_match else f"paper_{idx}"
            papers.append({"session": session, "text": chunk})

        if not papers:
            papers = [{"session": "Unknown", "text": text}]

        logger.info("papers_split", num_papers=len(papers))
        return papers

    # --- Private extraction helpers ---

    def _extract_university(self, text: str) -> str | None:
        patterns = [
            r"([A-Z][A-Z\s]+UNIVERSITY[A-Z\s–-]*)",
            r"TEERTHANKER MAHAVEER UNIVERSITY",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_course_code(self, text: str) -> str | None:
        patterns = [
            r"Course\s*Code\s*[:：]\s*([A-Z]+\d+)",
            r"\b([A-Z]{2,}\d{3,})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_subject(self, text: str) -> str | None:
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

    def _extract_max_marks(self, text: str) -> str | None:
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

    def _extract_session(self, text: str) -> str | None:
        patterns = [
            r"(20\d{2}[-–]\d{2})",
            r"((?:May|Dec|Jan|Jun|Jul|Nov)\s+20\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_duration(self, text: str) -> str | None:
        patterns = [
            r"Time\s*[:：]\s*([\d.]+\s*(?:Hours?|Hrs?))",
            r"Duration\s*[:：]\s*([\d.]+\s*(?:Hours?|Hrs?))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
