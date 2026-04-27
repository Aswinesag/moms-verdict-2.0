# TRADEOFFS.md

## Problem Selection Rationale

I chose to build Moms Verdict 2.0, a system that converts raw product reviews into structured, grounded insights.

### Why this problem

- High user impact: parents rely heavily on reviews for purchase decisions
- Clear pain point: information overload plus conflicting opinions
- Strong AI fit:
  - Requires reasoning over unstructured text
  - Needs uncertainty handling
  - Benefits from multilingual support

### Alternatives considered

1. Gift recommendation system
   - Rejected: harder to evaluate objectively

2. Customer support classifier
   - Rejected: more straightforward, less depth

3. Product content generator
   - Rejected: higher hallucination risk, harder grounding

---

## Architecture Decisions

### 1. No full RAG pipeline

**Decision:**
- Used direct input instead of full retrieval system

**Why:**
- Time constraint, around 5 hours
- Dataset is small and controlled

**Tradeoff:**
- Not scalable to large datasets
- Still sufficient to demonstrate grounding and reasoning

### 2. Structured output with Pydantic

**Decision:**
- Enforced strict schema validation

**Why:**
- Prevents malformed outputs
- Makes failures explicit instead of silent

**Tradeoff:**
- Adds complexity
- Significantly improves reliability

### 3. Single LLM vs multi-model system

**Decision:**
- Used one model for generation

**Why:**
- Faster to implement
- Simpler pipeline

**Tradeoff:**
- No specialized evaluator model
- Could improve with an ensemble approach

### 4. Prompt-based grounding vs retrieval-based grounding

**Decision:**
- Relied on prompt constraints plus evidence IDs

**Why:**
- Faster to implement
- Works well for small inputs

**Tradeoff:**
- Less robust than true RAG with embeddings
- Could fail with larger datasets

---

## Uncertainty Handling

### Approach

- Confidence score from 0 to 1
- Disagreement detection
- Insufficient-data flags
- Explicit warning when confidence is low

### Tradeoff

- Heuristic-based, not probabilistically calibrated
- Still effective for demonstrating system awareness

---

## Multilingual Design

### Approach

- Generate English and Arabic outputs independently

### Tradeoff

- No explicit language detection pipeline
- Relies on model capability and prompt discipline

---

## What Was Cut

Due to the time limit, the following were not implemented:

- Full RAG with a vector database
- UI layer
- Automated semantic evaluation pipeline
- Fine-tuning for Arabic quality

---

## Known Failure Modes

- Sparse or low-quality reviews lead to weak summaries
- Highly conflicting reviews lead to ambiguous outputs
- Arabic quality depends on model capability
- No protection against adversarial prompt injection

---

## What I Would Build Next

### 1. Retrieval-augmented generation
- Chunk reviews
- Use embeddings for better grounding

### 2. Confidence calibration
- Train a calibration model
- Improve reliability of confidence scores

### 3. UI layer
- Simple interface for product managers
- Visual display of pros, cons, and confidence

### 4. Better Arabic optimization
- Fine-tune or prompt-tune for native fluency

---

## Final Reflection

The system prioritizes:
- Reliability over creativity
- Explicit uncertainty over false confidence
- Structured outputs over free text

That aligns with production requirements for e-commerce systems, where trust and correctness matter.
