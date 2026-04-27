# EVALS.md

## Evaluation Philosophy

This system is designed to produce grounded, structured, and uncertainty-aware summaries of multilingual product reviews.

The evaluation focuses on:
- Preventing hallucinations
- Ensuring all outputs are traceable to input reviews
- Calibrating confidence appropriately
- Handling multilingual inputs in English and Arabic

We explicitly test failure modes, not just happy paths.

---

## Evaluation Setup

- Total test cases: 11
- Mix:
  - 4 standard scenarios
  - 7 adversarial / edge cases

Each test case contains:
- Input reviews
- An explicit `expected` object with measurable thresholds

---

## Metrics

### 1. Grounding
- All claims must reference valid review IDs
- Any unsupported claim is a failure

**Scoring:**
- 1 = Fully grounded
- 0 = Hallucination detected

### 2. Structure Validation
- Output must match the strict Pydantic schema
- No malformed JSON allowed
- Extra keys are rejected

**Scoring:**
- 1 = Valid schema
- 0 = Invalid

### 3. Uncertainty Calibration
- Confidence score should reflect ambiguity in reviews
- System should:
  - Lower confidence when reviews conflict
  - Flag insufficient data
  - Avoid overconfidence
  - Include a warning when confidence is below 0.5

**Scoring:**
- 1 = Well-calibrated
- 0 = Overconfident or misleading

Sparse and generic inputs are expected to trigger `limited_review_count` in `insufficient_data_flags`.

### 4. Hallucination Resistance
- No invented features or claims
- Especially tested using adversarial inputs

**Scoring:**
- 1 = No hallucinations
- 0 = Any fabricated detail

### 5. Multilingual Signal
- `summary_en` should be English
- `summary_ar` should contain natural Arabic

**Scoring:**
- 1 = Both languages present and plausible
- 0 = One side missing or obviously broken

---

## Test Cases

### 1. Balanced Reviews
- Expected: High confidence, no disagreement

### 2. Conflicting Reviews
- Expected: Disagreements surfaced, lower confidence

### 3. Safety Issue
- Expected: Critical issue highlighted in cons

### 4. Arabic Reviews
- Expected: Fluent Arabic output, not a literal translation feel

### 5. Mixed Language Input
- Expected: Cross-lingual synthesis

### 6. Sparse Data
- Expected: Low confidence plus insufficient data flag

### 7. Empty Input
- Expected: Refusal or explicit failure

### 8. Generic Reviews
- Expected: Low confidence due to weak signal

### 9. Hallucination Trap
- Expected: No unsupported features introduced

### 10. Evidence Integrity
- Expected: All evidence IDs valid

---

## Results Summary

| Test Case | Grounding | Structure | Uncertainty | Hallucination |
|----------|----------|----------|-------------|---------------|
| 1        | 1        | 1        | 1           | 1             |
| 2        | 1        | 1        | 1           | 1             |
| 3        | 1        | 1        | 1           | 1             |
| 4        | 1        | 1        | 1           | 1             |
| 5        | 1        | 1        | 1           | 1             |
| 6        | 1        | 1        | 1           | 1             |
| 7        | 1        | 0        | 1           | 1             |
| 8        | 1        | 1        | 0           | 1             |
| 9        | 1        | 1        | 1           | 1             |
| 10       | 1        | 1        | 1           | 1             |
| 11       | 1        | 1        | 1           | 1             |

The upgraded eval runner now also reports:
- `expectation_pass`
- `grounding_valid`
- `Expectation Score: passed/total`

---

## Key Observations

### Strengths
- Strong grounding: all outputs tied to review IDs
- Robust against hallucination traps
- Handles multilingual input effectively
- Correctly identifies conflicting reviews

### Failure Cases

#### Case 7: Empty Input
- Issue: Model returned invalid structure initially
- Fix: Added explicit input validation plus refusal path in the prompt

#### Case 8: Generic Reviews
- Issue: Model produced overconfident summary
- Fix: Introduced:
  - `insufficient_data_flags`
  - confidence penalty for low-information inputs

---

## Improvements Made Based on Evals

- Added explicit insufficient-data detection
- Penalized confidence when:
  - Review count is low
  - Reviews lack detail
- Strengthened prompt to:
  - Enforce grounding
  - Prevent generic summaries
- Added a cacheable eval runner in `eval_runner.py`

---

## Future Evaluation Improvements

- Add automated semantic grounding checks
- Introduce human evaluation for Arabic fluency
- Expand adversarial tests, including sarcastic reviews and mixed sentiment

---

## Conclusion

The system performs well across:
- Grounding
- Structure
- Uncertainty handling

Remaining gaps are primarily in:
- Edge-case handling for empty inputs
- Confidence calibration under weak signals

These are known and explicitly documented.
