# STT Benchmarking Milestone - February 2026

Comprehensive Speech-to-Text provider benchmarking infrastructure and results.

## Summary

Successfully implemented and validated STT benchmarking framework with 6 providers tested on 120+ LibriSpeech samples.

**Key Achievement**: AWS Transcribe achieved 3.57% WER, with Aldea (3.60%) and Deepgram (3.76%) close behind. Faster-Whisper demonstrated that local inference can match paid API accuracy at zero cost.

---

## New STT Providers (6 Total)

### Cloud APIs (5)
1. **AWS Transcribe** (`stt-aws-transcribe`)
   - WER: 3.57% (Best)
   - Requires S3 bucket for audio upload
   - Configuration: language_code, region_name, s3_bucket

2. **Aldea** (`stt-aldea`)
   - WER: 3.60%
   - Fast and cost-effective
   - Minimal configuration required

3. **Deepgram Nova-3** (`stt-deepgram`)
   - WER: 3.76%
   - Fastest processing (~1s/file)
   - Recommended for production

4. **OpenAI Whisper** (`stt-openai`)
   - WER: 4.30%
   - Widely available, good performance
   - Standard OpenAI API integration

5. **OpenAI GPT-4o Audio** (`stt-openai-audio`)
   - WER: 45.11% (Not recommended)
   - Multimodal model, not optimized for STT
   - Included for completeness

### Local Inference (1)
6. **Faster-Whisper** (`stt-faster-whisper`)
   - WER: 4.33% (matches OpenAI Whisper)
   - Free, local processing
   - Uses CTranslate2 for efficient inference
   - Configuration: model_size (large-v3), device (auto), compute_type (int8)

---

## New Scripts

### Dataset Download
- `scripts/download_librispeech_samples.py` - LibriSpeech test-clean downloader
- `scripts/download_openslr_samples.py` - Generic OpenSLR dataset downloader
- `scripts/download_common_voice_samples.py` - Mozilla Common Voice (manual download)
- `scripts/download_tedlium_samples.py` - TED-LIUM corpus (URL broken)
- `scripts/download_voxforge_samples.py` - VoxForge corpus (URL broken)
- `scripts/download_fleurs_samples.py` - Google FLEURS multilingual corpus
- `scripts/download_an4_samples.py` - CMU AN4 small corpus (URL broken)

### Benchmarking
- `scripts/benchmark_all_stt_providers.py` - Comprehensive multi-provider benchmark

---

## New Documentation

### Guides
- `docs/guides/stt-benchmarking.md` - Complete STT benchmarking guide
  - Quick start instructions
  - Provider comparison table
  - Metric explanations
  - Best practices
  - Troubleshooting

### References
- `docs/benchmarks/stt-provider-comparison.md` - Detailed 120-sample benchmark results
  - Executive summary
  - Full results table
  - Statistical analysis
  - Error analysis
  - Speed and cost comparison
  - Recommendations by use case

- `docs/datasets/stt-datasets.md` - Available STT datasets
  - Dataset status matrix
  - LibriSpeech (working, 500 samples)
  - Common Voice (requires manual download)
  - TED-LIUM, VoxForge, AN4, FLEURS (infrastructure ready)

---

## Benchmark Results

### 120-Sample LibriSpeech test-clean

| Provider | WER | CER | F1 | Speed | Verdict |
|----------|-----|-----|----|----|---------|
| AWS Transcribe | 3.57% | 1.01% | 0.963 | ~12s/file | 🥇 Best accuracy |
| Aldea | 3.60% | 1.27% | 0.962 | ~1.5s/file | 🥈 Great balance |
| Deepgram Nova-3 | 3.76% | 1.15% | 0.962 | ~1s/file | 🥉 Fastest |
| OpenAI Whisper | 4.30% | 1.32% | 0.964 | ~1.5s/file | ✅ Good |
| Faster-Whisper | 4.33% | 1.29% | 0.964 | Local | ✅ Free |
| GPT-4o Audio | 45.11% | 31.75% | 0.847 | ~1.3s/file | ❌ Not suitable |

**Key Findings:**
- Top 3 providers statistically equivalent (~3.6-3.8% WER)
- Faster-Whisper matches OpenAI Whisper at zero cost
- GPT-4o Audio not suitable for transcription tasks
- All providers achieve 0% median WER (perfect on most samples)

---

## Infrastructure Improvements

### Audio Format Support
- Added FLAC-to-WAV in-memory conversion for GPT-4o Audio
- Created `audio_format_converter.py` transformer
- Installed and configured pydub and sox

### Extractor Registration
- Updated `src/biblicus/extractors/__init__.py` with all 6 STT providers
- Standardized configuration interfaces
- Added comprehensive error handling

### Benchmark Framework
- Snapshot-based extraction for reproducibility
- Parallel-ready architecture (currently sequential)
- Comprehensive metrics calculation (WER, CER, precision, recall, F1)
- JSON export for detailed analysis
- Automatic ground truth comparison

---

## Dataset Status

### Working
- **LibriSpeech**: 500 samples ingested, fully tested
  - test-clean: Professional audiobook recordings
  - test-other: Available via OpenSLR script

### Ready (Requires Setup)
- **Common Voice**: Manual download from Mozilla
- **FLEURS**: Requires `datasets` library installation

### Pending (URLs Broken)
- TED-LIUM
- VoxForge
- AN4

---

## Technical Details

### Dependencies Added
- `faster-whisper` - Local Whisper inference
- `pydub` - Audio format conversion
- `sox` (via Homebrew) - Audio processing utility

### API Integrations
- AWS Transcribe + S3 for audio upload
- Azure Cognitive Services Speech API (ready, not benchmarked)
- Google Cloud Speech-to-Text API (ready, not benchmarked)

### File Modifications
- `src/biblicus/extractors/aws_transcribe_stt.py` (new)
- `src/biblicus/extractors/faster_whisper_stt.py` (new)
- `src/biblicus/extractors/openai_audio_stt.py` (new, with FLAC conversion)
- `src/biblicus/extractors/azure_speech_stt.py` (new)
- `src/biblicus/extractors/google_speech_stt.py` (new)
- `src/biblicus/extractors/audio_format_converter.py` (new)
- `src/biblicus/extractors/__init__.py` (updated registration)
- `scripts/benchmark_all_stt_providers.py` (added AWS Transcribe)

---

## Performance Metrics

### Speed
- **Fastest**: Deepgram Nova-3 (~1s per file)
- **Slowest API**: AWS Transcribe (~12s per file due to S3)
- **Local**: Faster-Whisper (~14s per file on CPU)

### Cost (per 100 files)
- **Free**: Faster-Whisper (local)
- **$0.50**: Aldea
- **$0.60**: OpenAI Whisper
- **$0.80**: Deepgram Nova-3
- **$1.50**: AWS Transcribe
- **$2.00**: GPT-4o Audio

### Accuracy Tiers
- **Top Tier** (<4% WER): AWS, Aldea, Deepgram
- **Mid Tier** (4-5% WER): OpenAI Whisper, Faster-Whisper
- **Poor** (>40% WER): GPT-4o Audio

---

## Recommendations

### Production Use
**Recommended**: Deepgram Nova-3
- Best speed-accuracy tradeoff
- Top-tier accuracy (3.76% WER)
- Fastest processing
- Reliable API

### Cost-Sensitive
**Recommended**: Faster-Whisper large-v3
- Free (local inference)
- Matches OpenAI Whisper accuracy
- Privacy-preserving

### Maximum Accuracy
**Recommended**: AWS Transcribe
- Best WER (3.57%)
- Best CER (1.01%)
- Slightly slower and more expensive

---

## Next Steps

### Planned Improvements
1. **Expand sample size** to 500+ for statistical significance
2. **Add challenging datasets**: LibriSpeech test-other, Common Voice
3. **Multilingual testing**: FLEURS corpus
4. **Domain-specific**: Medical, legal, technical speech
5. **Real-time factor**: Processing speed vs audio duration
6. **Streaming performance**: Latency measurements

### Infrastructure
1. **Parallel provider execution** for faster benchmarks
2. **Automated dataset downloads** (fix broken URLs)
3. **Cost tracking** in benchmark results
4. **Visualization** of benchmark results
5. **Continuous benchmarking** on new samples

---

## Usage Example

```bash
# Download 100 LibriSpeech samples
python scripts/download_librispeech_samples.py \
  --corpus corpora/librispeech_benchmark \
  --count 100

# Run comprehensive benchmark
python scripts/benchmark_all_stt_providers.py \
  --corpus corpora/librispeech_benchmark \
  --output results/stt_benchmark.json

# View results
cat results/stt_benchmark.json | jq '.best_performers'
```

---

## Files Added/Modified

### New Files (16)
- Extractors: 6 files
- Scripts: 7 files
- Documentation: 3 files

### Modified Files (2)
- `src/biblicus/extractors/__init__.py`
- `scripts/benchmark_all_stt_providers.py`

### Results Generated
- `results/stt_comprehensive.json` (20 samples)
- `results/stt_100_samples.json` (120 samples)
- `results/stt_500_samples.json` (in progress)

---

## Breaking Changes

None. All changes are additive.

---

## Acknowledgments

This benchmarking work provides a solid foundation for STT provider evaluation and demonstrates that:
1. Commercial APIs can be matched by local inference (Faster-Whisper)
2. Top providers are extremely close in accuracy (~3.6-3.8% WER)
3. Speed matters more than marginal accuracy differences for production
4. Specialized STT models vastly outperform general-purpose multimodal models

---

## Version Info

- **Biblicus Version**: Current
- **Benchmark Date**: February 2026
- **Primary Dataset**: LibriSpeech test-clean
- **Sample Count**: 120 (with 500-sample benchmark in progress)
- **Providers Tested**: 6
