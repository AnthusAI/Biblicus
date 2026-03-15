"""
Prepare scanned research paper samples for layout-aware OCR testing.

This script helps convert PDFs with selectable text into image-based PDFs
that simulate scanned documents, perfect for testing OCR pipelines.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from biblicus.corpus import Corpus


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 300) -> List[Path]:
    """
    Convert PDF pages to PNG images.

    :param pdf_path: Path to input PDF.
    :type pdf_path: Path
    :param output_dir: Directory for output images.
    :type output_dir: Path
    :param dpi: Resolution in dots per inch.
    :type dpi: int
    :return: List of created image paths.
    :rtype: list[Path]
    :raises ImportError: If pdf2image is not installed.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError as e:
        raise ImportError(
            "pdf2image is required. Install with: pip install pdf2image\n"
            "Also requires poppler: brew install poppler (macOS) or "
            "apt-get install poppler-utils (Ubuntu)"
        ) from e

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Converting PDF to images at {dpi} DPI...")
    images = convert_from_path(pdf_path, dpi=dpi)

    image_paths = []
    for i, image in enumerate(images, start=1):
        output_path = output_dir / f"{pdf_path.stem}_page_{i:03d}.png"
        image.save(output_path, "PNG")
        image_paths.append(output_path)
        print(f"  ✓ Page {i} → {output_path.name}")

    return image_paths


def images_to_pdf(image_paths: List[Path], output_pdf: Path) -> Path:
    """
    Combine PNG images into a single PDF (simulating scanned document).

    :param image_paths: List of image file paths.
    :type image_paths: list[Path]
    :param output_pdf: Output PDF path.
    :type output_pdf: Path
    :return: Path to created PDF.
    :rtype: Path
    :raises ImportError: If PIL is not installed.
    """
    try:
        from PIL import Image
    except ImportError as e:
        raise ImportError("Pillow is required. Install with: pip install Pillow") from e

    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    print(f"Creating image-based PDF: {output_pdf.name}")

    # Open all images
    images = [Image.open(img_path).convert("RGB") for img_path in image_paths]

    # Save as PDF
    if len(images) == 1:
        images[0].save(output_pdf, "PDF", resolution=100.0)
    else:
        images[0].save(output_pdf, "PDF", resolution=100.0, save_all=True, append_images=images[1:])

    print(f"  ✓ Created {output_pdf}")
    return output_pdf


def prepare_scanned_sample(
    input_pdf: Path,
    output_dir: Path,
    corpus_path: Path | None = None,
    tags: List[str] | None = None,
    dpi: int = 300,
    keep_images: bool = False,
) -> Dict[str, object]:
    """
    Convert a PDF into a scanned-like image PDF and optionally ingest to corpus.

    :param input_pdf: Source PDF file.
    :type input_pdf: Path
    :param output_dir: Directory for outputs.
    :type output_dir: Path
    :param corpus_path: Optional corpus to ingest into.
    :type corpus_path: Path | None
    :param tags: Tags to apply when ingesting.
    :type tags: list[str] | None
    :param dpi: Resolution for conversion.
    :type dpi: int
    :param keep_images: Whether to keep intermediate PNG files.
    :type keep_images: bool
    :return: Processing statistics.
    :rtype: dict[str, object]
    """
    print("=" * 70)
    print(f"PREPARING SCANNED SAMPLE: {input_pdf.name}")
    print("=" * 70)
    print()

    # Create temp directory for images
    images_dir = output_dir / "temp_images" / input_pdf.stem

    # Step 1: PDF → PNG images
    image_paths = pdf_to_images(input_pdf, images_dir, dpi=dpi)
    print(f"\n✓ Converted {len(image_paths)} pages to images")

    # Step 2: PNG images → image-based PDF
    output_pdf = output_dir / f"{input_pdf.stem}_scanned.pdf"
    images_to_pdf(image_paths, output_pdf)
    print(f"✓ Created image-based PDF: {output_pdf}")

    # Step 3: Optionally ingest to corpus
    item_id = None
    if corpus_path:
        print(f"\nIngesting to corpus: {corpus_path}")
        corpus = Corpus.open(corpus_path) if corpus_path.exists() else Corpus.init(corpus_path)
        result = corpus.ingest_source(output_pdf, tags=tags or ["scanned", "multi-column"])
        item_id = result.item_id
        print(f"✓ Ingested as: {item_id}")

    # Step 4: Cleanup intermediate files
    if not keep_images:
        import shutil

        shutil.rmtree(images_dir)
        print("✓ Cleaned up temporary images")

    print()
    return {
        "input_pdf": str(input_pdf),
        "output_pdf": str(output_pdf),
        "pages": len(image_paths),
        "item_id": item_id,
        "images_kept": keep_images,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        description="Convert PDFs to scanned-like images for OCR testing"
    )
    parser.add_argument("input_pdf", type=Path, help="Input PDF file to convert")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("scanned_samples"),
        help="Output directory (default: scanned_samples/)",
    )
    parser.add_argument("--corpus", type=Path, help="Corpus to ingest the result into")
    parser.add_argument("--tag", action="append", dest="tags", help="Tag to apply (repeatable)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI resolution (default: 300)")
    parser.add_argument("--keep-images", action="store_true", help="Keep intermediate PNG files")
    return parser


def main() -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.input_pdf.exists():
        print(f"ERROR: Input PDF not found: {args.input_pdf}")
        return 1

    result = prepare_scanned_sample(
        input_pdf=args.input_pdf,
        output_dir=args.output_dir,
        corpus_path=args.corpus,
        tags=args.tags,
        dpi=args.dpi,
        keep_images=args.keep_images,
    )

    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
