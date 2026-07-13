"""
Document processing pipeline.

Handles PDF text extraction with multi-strategy fallback:
  1. pdfminer.six (best for text-based PDFs)
  2. PyMuPDF/fitz (fallback for complex layouts)
"""

import io
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

    def extract_pages_text(self, pdf_source: str | bytes) -> list[dict[str, str]]:
        """
        Extract text from each page of a PDF.

        Args:
            pdf_source: A local file path, or the raw PDF bytes (used when the
                file lives in object storage rather than on local disk).

        Returns:
            List of dicts with 'page_number' and 'text' keys.
        """
        pages = []
        is_bytes = isinstance(pdf_source, bytes)
        source_label = "<bytes>" if is_bytes else pdf_source

        try:
            pdfminer_input = io.BytesIO(pdf_source) if is_bytes else pdf_source
            for i, page_layout in enumerate(extract_pages(pdfminer_input)):
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
                path=source_label,
                strategy="pdfminer",
                total_pages=len(pages),
            )

        except Exception as e:
            logger.warning(
                "pdfminer_extraction_failed",
                path=source_label,
                error=str(e),
            )
            # Fallback to PyMuPDF
            pages = self._extract_with_pymupdf(pdf_source)

        if not pages:
            raise PDFParsingError(f"No text could be extracted from PDF: {source_label}")

        return pages

    def _extract_with_pymupdf(self, pdf_source: str | bytes) -> list[dict[str, str]]:
        """Fallback extraction using PyMuPDF."""
        try:
            import fitz  # PyMuPDF

            pages = []
            if isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            else:
                doc = fitz.open(pdf_source)

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
                path="<bytes>" if isinstance(pdf_source, bytes) else pdf_source,
                strategy="pymupdf",
                total_pages=len(pages),
            )

            return pages

        except Exception as e:
            raise PDFParsingError(f"Both PDF extraction strategies failed: {str(e)}")

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
