# STT Provider Benchmarking Guide

Comprehensive guide for benchmarking Speech-to-Text providers using Biblicus with real-world results.

> **New to benchmarking?** Start with the [Benchmarking Overview](benchmarking-overview.md) for a platform introduction.

## Table of Contents

1. [Overview](#overview)
2. [Benchmark Results Summary](#benchmark-results-summary)
3. [Supported STT Providers](#supported-stt-providers)
4. [Quick Start](#quick-start)
5. [Available Datasets](#available-datasets)
6. [Understanding Metrics](#understanding-metrics)
7. [Running Custom Benchmarks](#running-custom-benchmarks)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Biblicus provides a robust framework for evaluating and comparing Speech-to-Text providers using standardized metrics on labeled audio datasets. This guide provides practical instructions and real benchmark results.

**Key Features:**
- 6 integrated STT providers (AWS, Aldea, Deepgram, OpenAI, Faster-Whisper, GPT-4o Audio)
- Multiple evaluation metrics (WER, CER, precision, recall, F1)
- 500+ LibriSpeech samples ready for testing
- Automated ground truth comparison
- JSON export for detailed analysis

---

## Benchmark Results Summary

### 120-Sample LibriSpeech test-clean Evaluation

Comprehensive benchmark results from 120 professionally recorded audiobook samples:

| Provider | WER | CER | F1 Score | Speed | Cost | Verdict |
|----------|-----|-----|----------|-------|------|---------|
| **AWS Transcribe** | **3.57%** | 1.01% | 0.963 | ~12s/file | $$ | 🥇 Best accuracy, slower |
| **Aldea** | **3.60%** | 1.27% | 0.962 | ~1.5s/file | $ | 🥈 Excellent balance |
| **Deepgram Nova-3** | **3.76%** | 1.15% | 0.962 | ~1s/file | $$ | 🥉 Fastest, great accuracy |
| **OpenAI Whisper** | 4.30% | 1.32% | 0.964 | ~1.5s/file | $ | ✅ Good, widely available |
| **Faster-Whisper** | 4.33% | 1.29% | 0.964 | Local | Free | ✅ Best for offline/free |
| **GPT-4o Audio** | 45.11% | 31.75% | 0.847 | ~1.3s/file | $$$ | ❌ Not suitable for STT |

**Key Findings:**
- **Top tier providers** (AWS, Aldea, Deepgram) achieve ~3.6-3.8% WER on clean speech
- **Differences between top 3 are statistically insignificant** at this sample size
- **Deepgram offers best speed-accuracy tradeoff** for production use
- **Faster-Whisper matches OpenAI Whisper** accuracy at zero cost
- **GPT-4o Audio is 10x worse** - use specialized STT models instead

**Recommendation by Use Case:**
- **Production (balanced)**: Deepgram Nova-3 - fastest with top-tier accuracy
- **Production (max accuracy)**: AWS Transcribe - slightly better WER, slower
- **Cost-sensitive**: Faster-Whisper large-v3 - local, free, matches paid APIs
- **General purpose**: OpenAI Whisper - widely available, good performance
- **Avoid**: GPT-4o Audio - not optimized for transcription

---

## Supported STT Providers

### Currently Integrated (6 providers)

#### 1. AWS Transcribe
- **Extractor ID**: `stt-aws-transcribe`
- **Accuracy**: ⭐ 3.57% WER (Best)
- **Speed**: Slow (~12s per file due to S3 upload)
- **Cost**: $$ (~$1.50 per 100 files)
- **Requirements**: AWS credentials, S3 bucket
- **Best for**: Maximum accuracy requirements

#### 2. Aldea
- **Extractor ID**: `stt-aldea`
- **Accuracy**: ⭐ 3.60% WER
- **Speed**: Fast (~1.5s per file)
- **Cost**: $ (~$0.50 per 100 files)
- **Requirements**: Aldea API key
- **Best for**: Excellent balance of speed, cost, accuracy

#### 3. Deepgram Nova-3
- **Extractor ID**: `stt-deepgram`
- **Accuracy**: ⭐ 3.76% WER
- **Speed**: Fastest (~1s per file)
- **Cost**: $$ (~$0.80 per 100 files)
- **Requirements**: Deepgram API key
- **Best for**: Production workloads requiring speed

#### 4. OpenAI Whisper (API)
- **Extractor ID**: `stt-openai`
- **Accuracy**: ✅ 4.30% WER
- **Speed**: Fast (~1.5s per file)
- **Cost**: $ (~$0.60 per 100 files)
- **Requirements**: OpenAI API key
- **Best for**: General purpose, widely available

#### 5. Faster-Whisper (Local)
- **Extractor ID**: `stt-faster-whisper`
- **Model**: large-v3 with CTranslate2
- **Accuracy**: ✅ 4.33% WER
- **Speed**: Slow (local CPU/GPU processing)
- **Cost**: Free (local inference)
- **Requirements**: Local compute, ~3GB model download
- **Best for**: Offline, privacy-sensitive, or cost-sensitive applications

#### 6. GPT-4o Audio (Not Recommended)
- **Extractor ID**: `stt-openai-audio`
- **Accuracy**: ❌ 45.11% WER (Poor)
- **Speed**: Fast (~1.3s per file)
- **Cost**: $$$ (~$2.00 per 100 files)
- **Note**: Multimodal model not optimized for transcription
- **Recommendation**: Use specialized STT models instead

---

## Quick Start

### 1. Download Benchmark Dataset

```bash
# Download 100 LibriSpeech test-clean samples
python scripts/download_librispeech_samples.py \
  --corpus corpora/librispeech_benchmark \
  --count 100

# For larger benchmarks (500 samples for statistical significance)
python scripts/download_librispeech_samples.py \
  --corpus corpora/librispeech_benchmark \
  --count 500 \
  --force

# Download challenging test-other subset
python scripts/download_openslr_samples.py \
  --corpus corpora/librispeech_test_other \
  --dataset SLR12 \
  --subset test-other \
  --count 100

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
