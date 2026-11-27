from pathlib import Path
from typing import List, Dict, Any, Optional
import pdfplumber
import pypdf

class PDFParser:
    """Extracts text, tables, and page-level metadata from PDF documents."""

    @staticmethod
    def parse(pdf_path: Path, source_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parses a PDF file and returns a list of chunks, one per page,
        with exact page numbers for reference citations.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        source_name = source_id or pdf_path.stem
        pages_data = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_num = idx + 1
                    text = page.extract_text(layout=True) or ""
                    
                    # Also extract tables if present
                    tables = page.extract_tables()
                    formatted_tables = []
                    for t in tables:
                        if t and len(t) > 0:
                            # format table as markdown
                            header = t[0]
                            rows = t[1:]
                            # filter None values
                            header_str = " | ".join([str(c or "").replace("\n", " ").strip() for c in header])
                            separator = " | ".join(["---"] * len(header))
                            row_strs = [" | ".join([str(c or "").replace("\n", " ").strip() for c in row]) for row in rows]
                            table_md = f"| {header_str} |\n| {separator} |\n" + "\n".join([f"| {r} |" for r in row_strs])
                            formatted_tables.append(table_md)

                    pages_data.append({
                        "source_id": source_name,
                        "filename": pdf_path.name,
                        "page": page_num,
                        "text": text.strip(),
                        "tables": formatted_tables,
                        "content_type": "pdf_page",
                    })
        except Exception as e:
            # Fallback to pypdf if pdfplumber encounters an error
            reader = pypdf.PdfReader(pdf_path)
            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                text = page.extract_text() or ""
                pages_data.append({
                    "source_id": source_name,
                    "filename": pdf_path.name,
                    "page": page_num,
                    "text": text.strip(),
                    "tables": [],
                    "content_type": "pdf_page",
                    "parse_warning": str(e)
                })

        return pages_data
