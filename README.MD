# Moms Verdict 2.0

## Overview
AI system that converts messy multilingual reviews into structured, grounded insights.

## How to Run
1. Set `OPENROUTER_API_KEY` in your environment
2. pip install -r requirements.txt
3. python server.py
4. Open `http://127.0.0.1:8000` in a browser

## Architecture
- LLM generation through OpenRouter
- Strict Pydantic validation
- Evidence-level grounding in the schema
- Lightweight evaluation runner for confidence and traceability checks
- Single-file UI served by a tiny local Python server

## Evals
- 10 defined test cases in `eval_runner.py`
- Metrics: grounding, structure, uncertainty, multilingual signal
- Cached outputs supported for offline inspection

## Tradeoffs
- No full RAG due to time constraint
- Small review set, so grounding is local to provided inputs
- Focused on reliability and evaluation transparency over UI

## Failure Modes
- Conflicting reviews
- Sparse data
- Language imbalance

## Tooling
- OpenRouter (LLM)
- Pydantic for schema enforcement
- Requests for API calls
- Manual + scripted evaluation loop
