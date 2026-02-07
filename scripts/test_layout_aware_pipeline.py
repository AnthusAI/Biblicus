#!/usr/bin/env python3
"""
Test the layout-aware OCR pipeline with PaddleOCR PP-Structure + Tesseract.

This implements production's workflow for non-selectable files.
"""

import json
from pathlib import Path

from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot

def main() -> None:
    print("=" * 70)
    print("TESTING LAYOUT-AWARE OCR PIPELINE")
    print("=" * 70)
    print()

    corpus = Corpus(Path("corpora/funsd_demo").resolve())

    config = {
        "extractor_id": "pipeline",
        "config": {
            "stages": [
                {
                    "extractor_id": "paddleocr-layout",
                    "config": {
                        "lang": "en"
                    }
                },
                {
                    "extractor_id": "ocr-tesseract",
                    "config": {
                        "use_layout_metadata": True,
                        "min_confidence": 0.0,
                        "lang": "eng",
                        "psm": 3,
                        "oem": 3
                    }
                }
            ]
        }
    }

    print("Pipeline Configuration:")
    print(json.dumps(config, indent=2))
    print()

    print("Building extraction snapshot...")
    snapshot = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="layout-aware-tesseract",
        configuration=config["config"]
    )
    print(f"✓ Snapshot created: {snapshot.snapshot_id}")
    print()

    snapshot_dir = corpus.extraction_snapshot_dir(
        extractor_id="pipeline",
        snapshot_id=snapshot.snapshot_id,
    )

    print("=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    print()

    layout_step_dir = snapshot_dir / "stages" / "01-paddleocr-layout"
    if layout_step_dir.exists():
        print("✓ Layout detection step exists")

        metadata_dir = layout_step_dir / "metadata"
        if metadata_dir.exists():
            metadata_files = list(metadata_dir.glob("*.json"))
            print(f"✓ Found {len(metadata_files)} layout metadata files")

            if metadata_files:
                with open(metadata_files[0]) as handle:
                    metadata = json.load(handle)
                print(f"\n  Sample metadata ({metadata_files[0].name}):")
                print(f"    Detector: {metadata.get('layout_detector', 'N/A')}")
                print(f"    Regions: {metadata.get('num_regions', 0)}")

                if metadata.get("regions"):
                    print("\n    Region details:")
                    for region in metadata["regions"][:3]:
                        bbox_preview = region["bbox"][:2]
                        print(
                            f"      - {region['type']}: order={region['order']}, "
                            f"bbox={bbox_preview}..."
                        )
        else:
            print("✗ No layout metadata found")
    else:
        print("✗ Layout detection step not found")

    print()

    ocr_step_dir = snapshot_dir / "stages" / "02-ocr-tesseract"
    if ocr_step_dir.exists():
        print("✓ OCR step exists")

        text_dir = snapshot_dir / "text"
        if text_dir.exists():
            text_files = list(text_dir.glob("*.txt"))
            print(f"✓ Found {len(text_files)} text output files")

            if text_files:
                text = text_files[0].read_text()
                print(f"\n  Sample text ({text_files[0].name}):")
                print(f"    Length: {len(text)} characters")
                print(f"    Preview: {text[:200]}...")
        else:
            print("✗ No text output found")
    else:
        print("✗ OCR step not found")

    print()
    print("=" * 70)
    print(f"Snapshot ID: {snapshot.snapshot_id}")
    print("=" * 70)


if __name__ == "__main__":
    main()
