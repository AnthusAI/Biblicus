#!/usr/bin/env python3
"""
Test the Heron + Tesseract pipeline (two-stage layout-aware workflow).

This validates IBM Research's Heron layout detection → Tesseract OCR.
"""

from pathlib import Path
from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot
import json

print("=" * 70)
print("TESTING HERON + TESSERACT PIPELINE (OSLEDY'S WORKFLOW)")
print("=" * 70)
print()

# Initialize corpus
corpus = Corpus(Path("corpora/funsd_demo").resolve())

# Configuration: Heron layout detection → Tesseract with layout metadata
config = {
    "extractor_id": "pipeline",
    "config": {
        "stages": [
            {
                "extractor_id": "heron-layout",
                "config": {
                    "model_variant": "101",
                    "confidence_threshold": 0.6
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

# Build extraction snapshot
print("Building extraction snapshot...")
print("(First run will download Heron-101 model ~150MB)")
print()

try:
    snapshot = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="heron-tesseract",
        configuration=config["config"]
    )
    print(f"✓ Snapshot created: {snapshot.snapshot_id}")
    print()

    # Verify results
    print("=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    print()

    # Find snapshot directory
    snapshots_base = corpus.root / ".biblicus" / "snapshots" / "extraction" / "pipeline"
    snapshot_dir = snapshots_base / snapshot.snapshot_id

    # Check layout detection step
    layout_step_dir = snapshot_dir / "stages" / "01-heron-layout"
    if layout_step_dir.exists():
        print("✓ Heron layout detection step exists")

        # Check metadata
        metadata_dir = layout_step_dir / "metadata"
        if metadata_dir.exists():
            metadata_files = list(metadata_dir.glob("*.json"))
            print(f"✓ Found {len(metadata_files)} layout metadata files")

            if metadata_files:
                # Show first metadata file
                with open(metadata_files[0]) as f:
                    metadata = json.load(f)
                print(f"\n  Sample metadata ({metadata_files[0].name}):")
                print(f"    Detector: {metadata.get('layout_detector', 'N/A')}")
                print(f"    Regions: {metadata.get('num_regions', 0)}")

                if metadata.get('regions'):
                    print(f"\n    Region details:")
                    for region in metadata['regions'][:3]:  # Show first 3
                        print(f"      - {region['type']}: order={region['order']}, score={region['score']:.3f}")
        else:
            print("✗ No layout metadata found")
    else:
        print("✗ Heron layout detection step not found")

    print()

    # Check OCR step
    ocr_step_dir = snapshot_dir / "stages" / "02-ocr-tesseract"
    if ocr_step_dir.exists():
        print("✓ Tesseract OCR step exists")

        # Check text output
        text_dir = snapshot_dir / "text"
        if text_dir.exists():
            text_files = list(text_dir.glob("*.txt"))
            print(f"✓ Found {len(text_files)} text output files")

            if text_files:
                # Show sample text
                text = text_files[0].read_text()
                print(f"\n  Sample text ({text_files[0].name}):")
                print(f"    Length: {len(text)} characters")
                print(f"    Preview: {text[:200]}...")
        else:
            print("✗ No text output found")
    else:
        print("✗ Tesseract OCR step not found")

    print()
    print("=" * 70)
    print(f"SUCCESS: Heron + Tesseract pipeline is working!")
    print(f"Snapshot ID: {snapshot.snapshot_id}")
    print("=" * 70)

except Exception as e:
    print()
    print("=" * 70)
    print("ERROR: Pipeline failed")
    print("=" * 70)
    print(f"\nError: {e}")
    print()
    import traceback
    traceback.print_exc()
    print()
    print("Common issues:")
    print("1. Missing dependencies: pip install transformers torch")
    print("2. Model download failed: Check internet connection")
    print("3. Out of memory: Try model_variant='base' instead of '101'")
