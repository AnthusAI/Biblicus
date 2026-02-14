# STT Provider Benchmarking Guide

Practical how-to guide for benchmarking Speech-to-Text providers in Biblicus using labeled ground truth data.

> **New to benchmarking?** Start with the [Benchmarking Overview](benchmarking-overview.md) for a platform introduction.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Benchmark Dataset](#benchmark-dataset)
4. [Running Benchmarks](#running-benchmarks)
5. [Understanding Metrics](#understanding-metrics)
6. [Results Analysis](#results-analysis)
7. [Dependencies](#dependencies)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This guide provides practical instructions for running STT benchmarks. It covers:
- Setting up benchmark datasets
- Running evaluation scripts
- Testing multiple STT providers
- Analyzing WER, CER, and accuracy metrics
- Troubleshooting common issues

**Key Features:**
- Multiple evaluation metrics (WER, CER, precision, recall, F1)
- Support for any STT provider
- Per-audio and aggregate results
- JSON export for analysis
- Comparison between provider configurations

---

## Quick Start

```bash
# 1. Download the LibriSpeech test-clean dataset
python scripts/download_librispeech_samples.py \
  --corpus corpora/librispeech_benchmark \
  --count 20

# 2. Run benchmark on all STT providers
python scripts/benchmark_all_stt_providers.py \
  --corpus corpora/librispeech_benchmark \
  --output results/stt_benchmark.json

# 3. View results
cat results/stt_benchmark.json | jq '.providers[] | {name, wer: .metrics.wer.avg}'
```

---

## Benchmark Dataset

### LibriSpeech Test-Clean

**What is LibriSpeech?**
- Corpus of ~1000 hours of 16kHz read English speech
- Derived from LibriVox audiobook recordings
- Test-clean subset: 5.4 hours of high-quality audio
- ~2600 utterances with ground truth transcriptions

**Download:**
```bash
python scripts/download_librispeech_samples.py \
  --corpus corpora/librispeech_benchmark \
  --count 100
```

This will:
1. Download LibriSpeech test-clean (~346 MB)
2. Extract FLAC audio files
3. Parse ground truth transcriptions from .trans.txt files
4. Create corpus at `corpora/librispeech_benchmark/`
5. Store ground truth in `metadata/ground_truth/`

**Dataset structure:**
```
corpora/librispeech_benchmark/
├── metadata/
│   ├── config.json
│   ├── catalog.json
│   └── ground_truth/
│       ├── <audio-id>.txt        # Ground truth transcription
│       └── ...
├── <audio-id>.flac                # Audio file
└── ...
```

### Using Your Own Dataset

To benchmark on custom audio:

1. **Prepare ground truth files:**
   ```
   corpus_dir/metadata/ground_truth/
   ├── <audio-id>.txt
   └── ...
   ```

2. **Ingest audio:**
   ```python
   from biblicus import Corpus
   from pathlib import Path

   corpus = Corpus(Path("my_corpus"))
   corpus.ingest_file("audio.flac", tags=["benchmark", "speech"])
   ```

3. **Run evaluation:**
   ```python
   from biblicus.evaluation.stt_benchmark import STTBenchmark

   benchmark = STTBenchmark(corpus)
   report = benchmark.evaluate_extraction(
       snapshot_reference="<snapshot-id>",
       ground_truth_dir=corpus.root / "metadata" / "ground_truth"
   )
   ```

---

## Available STT Providers

Biblicus includes 3 STT provider integrations:

| Provider | Model | Strengths | API Required |
|----------|-------|-----------|--------------|
| **OpenAI Whisper** | whisper-1 | General-purpose, multilingual | OPENAI_API_KEY |
| **Deepgram Nova-3** | nova-3 | Fast, accurate, features | DEEPGRAM_API_KEY |
| **Aldea** | (default) | Custom STT service | ALDEA_API_KEY |

---

## Understanding Metrics

Biblicus STT benchmarks use three categories of metrics:

### Word Error Rate (WER)

**Primary metric for STT accuracy.**

```
WER = (Substitutions + Deletions + Insertions) / Total Words
```

- **Substitutions**: Wrong word transcribed
- **Deletions**: Word missed
- **Insertions**: Extra word added
- **Lower is better** (0.0 = perfect, 1.0 = all words wrong)

**Interpretation:**
- **WER < 0.05**: Excellent (human-level)
- **WER < 0.10**: Very good (production-ready)
- **WER < 0.20**: Good (acceptable for many uses)
- **WER > 0.30**: Poor (needs improvement)

### Character Error Rate (CER)

**Character-level accuracy metric.**

```
CER = (Character Substitutions + Deletions + Insertions) / Total Characters
```

- More granular than WER
- Better for languages without clear word boundaries
- **Lower is better**

### Word-Level Metrics

**Precision, Recall, F1 Score** (bag-of-words)

- **Precision**: What % of transcribed words are correct
- **Recall**: What % of actual words were transcribed
- **F1 Score**: Harmonic mean of precision and recall

These ignore word order and focus on vocabulary accuracy.

For detailed explanations, see the [Metrics Reference](metrics-reference.md).

---

## Running Benchmarks

### Benchmark All Providers

```bash
python scripts/benchmark_all_stt_providers.py \
  --corpus corpora/librispeech_benchmark \
  --output results/stt_comparison.json
```

**What it does:**
1. Tests all 3 STT providers (OpenAI, Deepgram, Aldea)
2. Transcribes all audio files in the corpus
3. Calculates WER, CER, and word-level metrics
4. Generates comprehensive comparison report

**Output:**
- `results/stt_comparison.json` - Full results with all metrics
- Console table showing provider comparison

**Example output:**
```
================================================================================
COMPREHENSIVE STT PROVIDER COMPARISON
================================================================================

Provider                       WER      CER      Precision  Recall     F1       Status
------------------------------------------------------------------------------------------------
OpenAI Whisper                0.045    0.023    0.982      0.975      0.978    ✓ OK
Deepgram Nova-3               0.052    0.028    0.976      0.968      0.972    ✓ OK
Aldea                         0.068    0.035    0.965      0.952      0.958    ✓ OK
------------------------------------------------------------------------------------------------

🏆 Best Word Accuracy (Lowest WER): OpenAI Whisper
   WER: 0.045, Median: 0.042

🏆 Best Character Accuracy (Lowest CER): OpenAI Whisper
   CER: 0.023, Median: 0.021

🏆 Best Word Finding (F1): OpenAI Whisper
   F1: 0.978, Precision: 0.982, Recall: 0.975
```

### Benchmark Specific Providers

```bash
# Test only OpenAI and Deepgram
python scripts/benchmark_all_stt_providers.py \
  --corpus corpora/librispeech_benchmark \
  --providers stt-openai stt-deepgram \
  --output results/openai_vs_deepgram.json
```

### Quick Test with Fewer Files

```bash
python scripts/benchmark_all_stt_providers.py \
  --corpus corpora/librispeech_benchmark \
  --limit 5 \
  --output results/quick_test.json
```

---

## Results Analysis

### JSON Output Structure

```json
{
  "benchmark_timestamp": "2026-02-13T20:00:00",
  "corpus_path": "corpora/librispeech_benchmark",
  "total_providers": 3,
  "successful_providers": 3,
  "failed_providers": 0,
  "providers": [
    {
      "name": "OpenAI Whisper",
      "snapshot_id": "abc123...",
      "success": true,
      "metrics": {
        "wer": {
          "avg": 0.045,
          "median": 0.042,
          "avg_substitutions": 2.3,
          "avg_deletions": 0.8,
          "avg_insertions": 0.5
        },
        "cer": {
          "avg": 0.023,
          "median": 0.021
        },
        "word_level": {
          "avg_precision": 0.982,
          "avg_recall": 0.975,
          "avg_f1": 0.978,
          "median_f1": 0.980
        }
      },
      "provider_configuration": { ... },
      "total_audio_files": 100
    }
  ],
  "best_performers": {
    "lowest_wer": "OpenAI Whisper",
    "lowest_cer": "OpenAI Whisper",
    "best_f1": "OpenAI Whisper"
  }
}
```

### Analyzing Results

**Find best provider:**
```bash
cat results/stt_comparison.json | jq '.providers | sort_by(.metrics.wer.avg) | .[0] | {name, wer: .metrics.wer.avg}'
```

**Compare WER across providers:**
```bash
cat results/stt_comparison.json | jq '.providers[] | {name, wer: .metrics.wer.avg, cer: .metrics.cer.avg}' | jq -s 'sort_by(.wer)'
```

**Find audio files with high WER:**
```python
import json

with open('results/stt_comparison.json') as f:
    data = json.load(f)

# Assuming per-audio results are stored (implementation detail)
# You can analyze which utterances have highest error rates
```

---

## Dependencies

### Installing STT Provider Dependencies

Different providers require different dependencies:

**OpenAI Whisper:**
```bash
pip install "biblicus[openai]"
export OPENAI_API_KEY="sk-..."
```

**Deepgram:**
```bash
pip install "biblicus[deepgram]"
export DEEPGRAM_API_KEY="..."
```

**Aldea:**
```bash
pip install "biblicus[aldea]"
export ALDEA_API_KEY="..."
```

**All providers:**
```bash
pip install "biblicus[openai,deepgram,aldea]"
```

### Checking Dependencies

```bash
# Test OpenAI
python -c "from openai import OpenAI; print('OpenAI OK')"

# Test Deepgram
python -c "from deepgram import DeepgramClient; print('Deepgram OK')"

# Test Aldea
python -c "import httpx; print('Aldea OK')"
```

---

## Troubleshooting

### Common Issues

**Issue: "API key not found"**
```
Solution: Set environment variable or configure in ~/.biblicus/config.yml:
  openai:
    api_key: "sk-..."
  deepgram:
    api_key: "..."
  aldea:
    api_key: "..."
```

**Issue: "Ground truth directory not found"**
```
Solution: Run python scripts/download_librispeech_samples.py first
```

**Issue: "Audio format not supported"**
```
Solution: LibriSpeech uses FLAC format. Ensure audio files are valid FLAC.
```

**Issue: "API rate limit exceeded"**
```
Solution:
- Reduce --limit parameter
- Add delays between API calls
- Use provider with higher rate limits
```

**Issue: "Results don't match expected WER"**
```
Solution: Check:
- Correct ground truth files loaded
- Audio quality is good
- Provider configuration is appropriate
- Punctuation/formatting settings
```

**Issue: "High API costs"**
```
Solution:
- Start with --limit 5 or --limit 10 for testing
- Use quick.yaml config (20 files) instead of full (2600 files)
- Calculate costs: ~$0.006 per minute of audio (varies by provider)
```

---

## Benchmark Modes

Use configuration files for different benchmark scales:

**Quick (20 audio files, ~2-5 minutes):**
```bash
# Manually specify count
python scripts/download_librispeech_samples.py --corpus corpora/librispeech_benchmark --count 20
python scripts/benchmark_all_stt_providers.py --corpus corpora/librispeech_benchmark --output results/quick.json
```

**Standard (100 audio files, ~10-20 minutes):**
```bash
python scripts/download_librispeech_samples.py --corpus corpora/librispeech_benchmark --count 100
python scripts/benchmark_all_stt_providers.py --corpus corpora/librispeech_benchmark --output results/standard.json
```

**Full (all audio files, ~2-4 hours):**
```bash
# Download full test-clean dataset
python scripts/download_librispeech_samples.py --corpus corpora/librispeech_benchmark --count 2600
python scripts/benchmark_all_stt_providers.py --corpus corpora/librispeech_benchmark --output results/full.json
```

---

## Cost Estimation

STT benchmarking involves API costs:

| Provider | Cost per Hour | 20 Files (~10 min) | 100 Files (~50 min) | Full (~5.4 hours) |
|----------|---------------|-------------------|---------------------|-------------------|
| OpenAI Whisper | $0.36/hr | ~$0.06 | ~$0.30 | ~$1.94 |
| Deepgram Nova-3 | $0.36/hr | ~$0.06 | ~$0.30 | ~$1.94 |
| Aldea | (varies) | (varies) | (varies) | (varies) |

**Cost-saving tips:**
- Start with `--limit 5` for development
- Use quick config (20 files) for iteration
- Run full benchmarks only for final results

---

## See Also

**Benchmarking Documentation:**
- [Benchmarking Overview](benchmarking-overview.md) - Platform introduction
- [Metrics Reference](metrics-reference.md) - Understanding WER, CER, and other metrics
- [OCR Benchmarking Guide](ocr-benchmarking.md) - OCR pipeline benchmarking

**STT Documentation:**
- [Speech to Text](../stt.md) - STT extraction guide

**External References:**
- [LibriSpeech Dataset](https://www.openslr.org/12)
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [Deepgram API](https://developers.deepgram.com/)
