"""
Download a small mixed-modality corpus for integration testing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from biblicus.corpus import Corpus

DEFAULT_HTML_URL = "https://example.com"
DEFAULT_IMAGE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/Example.jpg"
DEFAULT_PDF_URL = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
DEFAULT_DOCX_URL = "https://calibre-ebook.com/downloads/demos/demo.docx"


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for integration downloads.

    :param path: Corpus path.
    :type path: Path
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :return: Corpus instance.
    :rtype: Corpus
    :raises ValueError: If the target path is non-empty without force.
    """
    if (path / ".biblicus" / "config.json").is_file():
        corpus = Corpus.open(path)
        if force:
            corpus.purge(confirm=corpus.name)
        return corpus
    if path.exists() and any(path.iterdir()) and not force:
        raise ValueError("Target corpus directory is not empty. Use --force to initialize anyway.")
    return Corpus.init(path, force=True)


def _blank_single_page_pdf_bytes() -> bytes:
    """
    Build a minimal Portable Document Format payload with no extractable text.

    :return: Portable Document Format bytes.
    :rtype: bytes
    """
    objects: list[bytes] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length 0 >>\nstream\nendstream")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body_parts: list[bytes] = [header]

    offsets: list[int] = [0]
    current_offset = len(header)
    for index, obj in enumerate(objects, start=1):
        offsets.append(current_offset)
        obj_bytes = f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
        body_parts.append(obj_bytes)
        current_offset += len(obj_bytes)

    xref_start = current_offset
    xref_lines: list[bytes] = []
    xref_lines.append(b"xref\n")
    xref_lines.append(f"0 {len(objects) + 1}\n".encode("ascii"))
    xref_lines.append(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
        + b"startxref\n"
        + f"{xref_start}\n".encode("ascii")
        + b"%%EOF\n"
    )

    return b"".join(body_parts + xref_lines + [trailer])


def download_mixed_samples(
    *,
    corpus_path: Path,
    force: bool,
    html_url: str,
    image_url: str,
    pdf_url: str,
    docx_url: str,
) -> Dict[str, int]:
    """
    Download a small set of mixed modality items into a corpus.

    This script downloads public files at runtime. The repository does not include those files.

    The corpus includes:

    - A Markdown note created locally
    - A downloaded Hypertext Markup Language page
    - A downloaded image
    - A downloaded Office Open Extensible Markup Language document
    - A downloaded Portable Document Format file with extractable text
    - A generated Portable Document Format file with no extractable text (blank page)

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param html_url: Hypertext Markup Language page uniform resource locator.
    :type html_url: str
    :param image_url: Image uniform resource locator.
    :type image_url: str
    :param pdf_url: Portable Document Format uniform resource locator.
    :type pdf_url: str
    :param docx_url: Office Open Extensible Markup Language uniform resource locator.
    :type docx_url: str
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """
    corpus = _prepare_corpus(corpus_path, force=force)
    ingested = 0
    failed = 0

    corpus.ingest_note(
        "Hello from a mixed integration corpus.",
        title="Mixed corpus note",
        tags=["mixed", "note"],
        source_uri="text",
    )
    ingested += 1

    try:
        corpus.ingest_source(html_url, tags=["mixed", "html"], source_uri=html_url)
        ingested += 1
    except Exception:
        failed += 1

    try:
        corpus.ingest_source(image_url, tags=["mixed", "image"], source_uri=image_url)
        ingested += 1
    except Exception:
        failed += 1

    try:
        corpus.ingest_source(docx_url, tags=["mixed", "docx", "docx-sample"], source_uri=docx_url)
        ingested += 1
    except Exception:
        failed += 1

    try:
        corpus.ingest_source(pdf_url, tags=["mixed", "pdf", "pdf-sample"], source_uri=pdf_url)
        ingested += 1
    except Exception:
        failed += 1

    try:
        corpus.ingest_item(
            _blank_single_page_pdf_bytes(),
            filename="scan.pdf",
            media_type="application/pdf",
            source_uri="generated:scan.pdf",
            tags=["mixed", "pdf", "scanned"],
        )
        ingested += 1
    except Exception:
        failed += 1

    corpus.reindex()
    return {"ingested": ingested, "failed": failed}


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Download mixed-modality samples into Biblicus.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--force", action="store_true", help="Purge existing corpus content.")
    parser.add_argument(
        "--html-url",
        default=DEFAULT_HTML_URL,
        help="Hypertext Markup Language page uniform resource locator.",
    )
    parser.add_argument(
        "--image-url", default=DEFAULT_IMAGE_URL, help="Image uniform resource locator."
    )
    parser.add_argument(
        "--docx-url",
        default=DEFAULT_DOCX_URL,
        help="Office Open Extensible Markup Language uniform resource locator.",
    )
    parser.add_argument(
        "--pdf-url",
        default=DEFAULT_PDF_URL,
        help="Portable Document Format uniform resource locator.",
    )
    return parser


def main() -> int:
    """
    Entry point for the mixed sample download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    stats = download_mixed_samples(
        corpus_path=Path(args.corpus).resolve(),
        force=bool(args.force),
        html_url=str(args.html_url),
        image_url=str(args.image_url),
        docx_url=str(args.docx_url),
        pdf_url=str(args.pdf_url),
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
