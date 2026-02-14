# Metrics Reference

Complete guide to understanding evaluation metrics used in Biblicus benchmarks.

## Overview

Biblicus uses three categories of metrics to evaluate extraction quality:

1. **Set-Based Metrics**: Measure word-finding ability (position-agnostic)
2. **Order-Aware Metrics**: Measure reading order preservation (sequence quality)
3. **N-gram Overlap**: Measure local ordering quality (word pair/triple accuracy)

Each metric tells you something different about extraction quality. A good extraction pipeline needs:
- **High F1** for accuracy (finding the right words)
- **Low WER** for reading order (words in correct sequence)
- **High bigram/trigram** for local ordering (adjacent words correct)

## Set-Based Metrics (Position-Agnostic)

Set-based metrics measure how well the extraction finds words, regardless of their order. These are the primary accuracy metrics.

### F1 Score

**Harmonic mean of precision and recall.**

- **Range:** 0.0 to 1.0 (higher is better)
- **Primary metric for overall accuracy**
- **Balances precision and recall**

**Formula:**
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

**Interpretation:**
- **F1 ≥ 0.75:** Excellent accuracy
- **F1 ≥ 0.65:** Good accuracy
- **F1 ≥ 0.50:** Acceptable for some use cases
- **F1 < 0.50:** Poor accuracy

**Example:**
- Ground truth: "hello world from biblicus"
- Extracted: "hello world form"
- Precision: 2/3 = 0.667 (2 correct out of 3 extracted)
- Recall: 2/4 = 0.500 (2 found out of 4 ground truth)
- F1: 2 × (0.667 × 0.500) / (0.667 + 0.500) = 0.571

**When to prioritize:**
- General-purpose OCR evaluation
- Comparing pipeline overall quality
- Production system benchmarking

---

### Precision

**Percentage of extracted words that are correct.**

- **Range:** 0.0 to 1.0 (higher is better)
- **Measures false positive rate**
- **High precision = few extra/wrong words**

**Formula:**
```
Precision = TP / (TP + FP)

Where:
  TP = True Positives (correct words found)
  FP = False Positives (incorrect words extracted)
```

**Interpretation:**
- **High Precision, Low Recall:** Conservative extraction (misses text but rarely wrong)
- **Low Precision, High Recall:** Aggressive extraction (finds everything but noisy)
- **Balanced:** Best for most use cases

**Example:**
- Extracted: "hello world form biblicus"
- Ground truth: "hello world from biblicus"
- Correct words: hello, world, biblicus (3 out of 4 extracted)
- Precision: 3/4 = 0.750

**When to prioritize:**
- Noise is expensive (false positives costly)
- Downstream processing assumes clean text
- Indexing/search where quality matters

---

### Recall

**Percentage of ground truth words that were found.**

- **Range:** 0.0 to 1.0 (higher is better)
- **Measures completeness**
- **High recall = finds most words**

**Formula:**
```
Recall = TP / (TP + FN)

Where:
  TP = True Positives (correct words found)
  FN = False Negatives (ground truth words missed)
```

**Interpretation:**
- **Recall ≥ 0.80:** Excellent completeness
- **Recall ≥ 0.70:** Good completeness
- **Recall ≥ 0.60:** Acceptable for some use cases
- **Recall < 0.60:** Missing too much content

**Example:**
- Ground truth: "hello world from biblicus system"
- Extracted: "hello world biblicus"
- Found words: hello, world, biblicus (3 out of 5)
- Recall: 3/5 = 0.600

**When to prioritize:**
- Missing content is expensive
- Legal/compliance documents (can't skip text)
- Search applications (need everything indexed)
- Maximum extraction scenarios

---

### Character Accuracy

**Character-level correctness metric.**

- **Range:** 0.0 to 1.0 (higher is better)
- **More fine-grained than word-level metrics**
- **Useful for partial word matches**

**When to use:**
- OCR quality assessment at character level
- Evaluating partial word extraction
- Fine-grained accuracy analysis

---

## Order-Aware Metrics (Sequence Quality)

Order-aware metrics measure whether words appear in the correct sequence. These are critical for layout-aware OCR evaluation.

### Word Error Rate (WER)

**Edit distance normalized by ground truth length.**

- **Range:** 0.0+ (lower is better, can exceed 1.0)
- **Critical for layout-aware OCR**
- **Counts insertions, deletions, substitutions**

**Formula:**
```
WER = (Insertions + Deletions + Substitutions) / Total_Ground_Truth_Words
```

**Interpretation:**
- **WER ≤ 0.30:** Excellent reading order
- **WER ≤ 0.50:** Good reading order
- **WER ≤ 0.70:** Acceptable for some use cases
- **WER > 1.0:** More errors than words (very poor)

**Example:**
- Ground truth: "hello world from biblicus"
- Extracted: "hello form world biblicus"
- Operations: 1 substitution (form→from) + 0 deletions + 0 insertions = 1
- WER: 1/4 = 0.250

**Why WER can exceed 1.0:**
If you have 100 ground truth words but extract 200 words (100 correct + 100 insertions), WER = 100/100 = 1.0. More insertions push it higher.

**When to prioritize:**
- Multi-column layouts (reading order critical)
- Document understanding (semantic flow)
- Reading aloud applications
- Content summarization

---

### Sequence Accuracy

**Percentage of words in correct sequential position.**

- **Range:** 0.0 to 1.0 (higher is better)
- **Strict metric: word must be at exact position**
- **Very sensitive to small ordering changes**

**Formula:**
```
Sequence Accuracy = Correct_Position_Words / Total_Ground_Truth_Words
```

**Example:**
- Ground truth: ["hello", "world", "from", "biblicus"]
- Extracted: ["hello", "form", "world", "biblicus"]
- Only "hello" at position 0 is correct
- Sequence Accuracy: 1/4 = 0.250

**Interpretation:**
- Very strict metric
- Useful for exact order preservation
- Often lower than other metrics

**When to use:**
- Exact position matters (tables, forms)
- Structured data extraction
- Column-sensitive applications

---

### LCS Ratio (Longest Common Subsequence)

**Ratio of longest ordered subsequence to total.**

- **Range:** 0.0 to 1.0 (higher is better)
- **More forgiving than sequence accuracy**
- **Measures longest preserved ordering**

**Formula:**
```
LCS Ratio = Length(LCS(ground_truth, extracted)) / Length(ground_truth)
```

**Example:**
- Ground truth: "the quick brown fox jumps"
- Extracted: "the brown quick fox"
- LCS: "the brown fox" (length 3)
- LCS Ratio: 3/5 = 0.600

**Interpretation:**
- **LCS ≥ 0.80:** Excellent order preservation
- **LCS ≥ 0.65:** Good order preservation
- **LCS ≥ 0.50:** Acceptable ordering
- **LCS < 0.50:** Poor ordering

**When to use:**
- Primary metric for academic papers
- Multi-column document evaluation
- When partial ordering is acceptable

---

## N-gram Overlap (Local Ordering)

N-gram metrics measure whether adjacent words (bigrams) or word triples (trigrams) appear in the correct order.

### Bigram Overlap

**Percentage of word pairs in correct order.**

- **Range:** 0.0 to 1.0 (higher is better)
- **Good for detecting column mixing**
- **Measures local ordering quality**

**Formula:**
```
Bigram Overlap = Matching_Bigrams / Total_Bigrams

Where a bigram is a pair of adjacent words: ("word1", "word2")
```

**Example:**
- Ground truth: "hello world from biblicus"
- Ground truth bigrams: ("hello", "world"), ("world", "from"), ("from", "biblicus")
- Extracted: "hello world biblicus from"
- Extracted bigrams: ("hello", "world"), ("world", "biblicus"), ("biblicus", "from")
- Matching: ("hello", "world") only
- Bigram Overlap: 1/3 = 0.333

**Interpretation:**
- **Bigram ≥ 0.70:** Excellent local ordering
- **Bigram ≥ 0.55:** Good local ordering
- **Bigram ≥ 0.40:** Acceptable ordering
- **Bigram < 0.40:** Poor local ordering

**When to prioritize:**
- Layout-aware OCR evaluation
- Multi-column document assessment
- Reading flow quality

---

### Trigram Overlap

**Percentage of word triples in correct order.**

- **Range:** 0.0 to 1.0 (higher is better)
- **More sensitive than bigram**
- **Stricter local ordering requirement**

**Formula:**
```
Trigram Overlap = Matching_Trigrams / Total_Trigrams

Where a trigram is three adjacent words: ("word1", "word2", "word3")
```

**Example:**
- Ground truth: "the quick brown fox"
- Ground truth trigrams: ("the", "quick", "brown"), ("quick", "brown", "fox")
- Extracted: "the brown quick fox"
- Extracted trigrams: ("the", "brown", "quick"), ("brown", "quick", "fox")
- Matching: none
- Trigram Overlap: 0/2 = 0.0

**Interpretation:**
- Usually lower than bigram overlap
- More strict ordering requirement
- Good for detailed analysis

**When to use:**
- Fine-grained ordering analysis
- Detailed pipeline comparison
- Academic evaluation

---

## Metric Trade-offs

### Precision vs. Recall

Different pipelines optimize for different trade-offs:

**High Precision, Lower Recall (Conservative):**
- Example: Baseline Tesseract (Precision: 0.615, Recall: 0.599)
- Few false positives, but misses some text
- Best for: Clean text applications, noise-sensitive systems

**Lower Precision, High Recall (Aggressive):**
- Example: Heron + Tesseract (Precision: 0.384, Recall: 0.810)
- Finds most text, but includes noise
- Best for: Legal/compliance, maximum extraction

**Balanced:**
- Example: PaddleOCR (Precision: 0.792, Recall: 0.782, F1: 0.787)
- Good accuracy and completeness
- Best for: General-purpose applications

### Accuracy vs. Reading Order

You can have high F1 (finds words) but poor WER (wrong order):

**Good F1, Poor WER:**
- Finds the right words but in wrong order
- Common in multi-column documents
- Example: Column text mixed together

**Good F1, Good WER:**
- Finds the right words in right order
- Ideal for most applications
- Example: PaddleOCR with layout detection

**Poor F1, Good WER:**
- Rare but possible - finds few words but in correct order
- Usually indicates incomplete extraction

---

## Choosing Metrics for Your Use Case

### Forms (FUNSD-like)

**Primary Metric:** F1 Score
- Measures field extraction accuracy
- Balance of precision and recall matters

**Secondary Metrics:**
- Recall (don't miss fields)
- WER (fields should be in order)

**Target:**
- F1 ≥ 0.75 for production
- Recall ≥ 0.70 minimum

---

### Receipts (Dense Text)

**Primary Metric:** F1 Score
- Entity extraction accuracy critical
- Dense text needs high precision

**Secondary Metrics:**
- Precision (avoid noise in entities)
- Bigram (local ordering for amounts/dates)

**Target:**
- F1 ≥ 0.80 for production
- Precision ≥ 0.75 minimum

---

### Academic Papers (Multi-Column)

**Primary Metric:** LCS Ratio
- Reading order preservation critical
- Multi-column layout understanding

**Secondary Metrics:**
- F1 (overall accuracy)
- WER (sequence quality)
- Bigram (column mixing detection)

**Target:**
- LCS ≥ 0.75 for production
- Bigram ≥ 0.60 minimum

---

### Legal/Compliance Documents

**Primary Metric:** Recall
- Cannot miss any content
- Completeness over accuracy

**Secondary Metrics:**
- F1 (but tolerate lower precision)
- WER (reading order matters)

**Target:**
- Recall ≥ 0.90 minimum
- F1 ≥ 0.70 acceptable

---

## Interpreting Benchmark Results

### Example Report

```json
{
  "pipeline_name": "paddleocr",
  "metrics": {
    "set_based": {
      "avg_precision": 0.792,
      "avg_recall": 0.782,
      "avg_f1": 0.787
    },
    "order_aware": {
      "avg_wer": 0.533,
      "avg_sequence_accuracy": 0.031,
      "avg_lcs_ratio": 0.621
    },
    "ngram": {
      "avg_bigram_overlap": 0.521,
      "avg_trigram_overlap": 0.412
    }
  }
}
```

### Interpretation

**Set-Based Metrics:**
- F1: 0.787 → **Excellent** accuracy (finds 78.7% of words correctly)
- Balanced precision (79.2%) and recall (78.2%)

**Order-Aware Metrics:**
- WER: 0.533 → **Good** reading order (53% error rate acceptable for forms)
- LCS: 0.621 → **Good** longest sequence preservation

**N-gram Metrics:**
- Bigram: 0.521 → **Good** local ordering (52% word pairs correct)

**Overall:** Strong all-around pipeline. High F1 for accuracy, acceptable reading order for forms.

---

### Comparing Two Pipelines

**Scenario: PaddleOCR vs. Heron+Tesseract**

| Metric | PaddleOCR | Heron+Tesseract | Winner |
|--------|-----------|-----------------|--------|
| F1 | 0.787 | 0.519 | PaddleOCR |
| Recall | 0.782 | 0.810 | Heron |
| Precision | 0.792 | 0.384 | PaddleOCR |
| WER | 0.533 | 0.612 | PaddleOCR |
| Bigram | 0.521 | 0.561 | Heron |

**Analysis:**
- **PaddleOCR:** Better overall accuracy (F1), cleaner output (precision), better reading order (WER)
- **Heron+Tesseract:** Finds more text (recall), better local ordering (bigram)

**Choose PaddleOCR if:** You need clean, accurate extraction
**Choose Heron if:** You need maximum extraction, can tolerate noise

---

## Metric Calculation Details

### Set-Based Calculation

Words are normalized before comparison:
- Lowercase
- Remove punctuation
- Trim whitespace

Example:
- Ground truth: "Hello, World!"
- Extracted: "hello world"
- Match: Both normalize to ["hello", "world"]

### Order-Aware Calculation

Word sequences are compared position-by-position:
- Insertions: Extra words in extracted text
- Deletions: Missing words from ground truth
- Substitutions: Wrong words in extracted text

Example:
- Ground truth: ["the", "quick", "fox"]
- Extracted: ["the", "slow", "fox"]
- Operations: 1 substitution (quick→slow)
- WER: 1/3 = 0.333

### N-gram Calculation

Sliding window over word sequences:
- Bigram: Window size 2
- Trigram: Window size 3

Example bigram calculation:
- Ground truth: ["a", "b", "c"]
- Bigrams: [("a", "b"), ("b", "c")]
- Extracted: ["a", "c", "b"]
- Bigrams: [("a", "c"), ("c", "b")]
- Matching: none
- Bigram overlap: 0/2 = 0.0

---

## Tools and Libraries

Biblicus uses:
- **editdistance** (optional): Fast Levenshtein distance for WER
- **difflib**: Python standard library for sequence matching
- **nltk** (optional): Advanced text normalization

Without editdistance, WER calculation falls back to difflib (slower but works).

---

## Next Steps

- **[Run benchmarks](quickstart-benchmarking.md)** to generate metrics on your data
- **[Explore pipelines](pipeline-catalog.md)** to understand trade-offs
- **[View current results](benchmark-results.md)** to see metric examples
- **[OCR Benchmarking Guide](ocr-benchmarking.md)** for practical evaluation

---

## References

- Metrics implementation: `src/biblicus/evaluation/ocr_benchmark.py`
- Benchmark runner: `src/biblicus/evaluation/benchmark_runner.py`
- [Multi-Category Benchmark Framework](document-understanding-benchmark.md)
- [Benchmarking Overview](benchmarking-overview.md)
