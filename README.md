# Markdown Edit LLM Benchmark

A benchmark suite for evaluating different LLM-based approaches to editing markdown documents.

## Results Summary

> **TL;DR**: Full rewrite beats all diff/patch algorithms. Use **grok-4-fast** for most documents ($0.004/doc), **glm-4.6** for very long documents (2000+ lines). Most other models introduce critical errors on long content.

### Quick Reference

| Use Case | Recommended Model | Cost | Why |
|----------|-------------------|------|-----|
| **Short/Medium docs** | grok-4-fast | $0.004/doc | Cheapest reliable option, 73% exact match, ~90% usable |
| **Complex docs** | grok-4-fast or glm-4.6 | $0.004-0.03/doc | Both produce usable output even on "failures" |
| **Very long docs (2000+ lines)** | glm-4.6 | $0.03/doc | Only model without critical errors |
| **Speed-critical** | qwen3-235b | $0.014/doc | 7s avg, but use only for short docs |

### What We Tested

- **14 algorithms**: full rewrite, git diff, search/replace, JSON ops, Aider formats, Codex patches, etc.
- **15 models**: grok-4-fast, gpt-5-mini, gemini-2.5-flash, qwen3, glm-4.6, and more
- **11 fixtures**: simple → medium → complex → hard (up to 2000+ lines)

### Key Findings

1. **Full rewrite wins** — Diff/patch formats fail due to hallucinated line numbers and inexact text matching. Simpler is better.

2. **Benchmark overstates failures** — Many "failures" (0.85-0.99 scores) are actually production-ready with only cosmetic differences.

3. **Very long documents are genuinely hard** — Most models introduce 1000x numerical errors or truncate content. Only glm-4.6 is safe.

4. **Cost ≠ quality** — grok-4-fast ($0.044 total) beats models costing 5x more.

---

## Deep Dive: Benchmark Results

### Model Performance (Full Rewrite Algorithm)

Tested on 11 fixtures across simple, medium, complex, and hard categories (November 2025):

| Model | Pass Rate | Total Cost | Avg Time | Notes |
|-------|-----------|------------|----------|-------|
| **grok-4-fast** | 73% (8/11) | $0.044 | 30s | **Best value** — cheapest reliable option |
| grok-code-fast-1 | 73% (8/11) | $0.058 | 27s | Good speed, slightly higher cost |
| qwen3-next-80b | 73% (8/11) | $0.107 | 35s | Dangerous on long docs (numerical errors) |
| gpt-4.1-mini | 73% (8/11) | $0.133 | 88s | Reliable but slower |
| gpt-5-mini | 73% (8/11) | $0.203 | 116s | Template pollution on long docs |
| gemini-2.5-flash | 64% (7/11) | $0.230 | 30s | Fast, but fabricates data on long docs |
| minimax-m2 | 64% (7/11) | $0.102 | 64s | Deletes sections silently |
| **glm-4.6** | 64% (7/11) | $0.343 | 56s | **Only safe option for very long docs** |
| kimi-k2-0905 | 64% (7/11) | $0.228 | 25s | Context limit failures |
| qwen3-235b | 45% (5/11) | $0.153 | 7s | Very fast but unreliable |
| mistral-nemo | 18% (2/11) | $0.021 | 27s | Too small for this task |

### Why Full Rewrite Beats Other Algorithms

After testing 14 algorithms, full document rewrite is the most reliable approach:

| Approach | Problem |
|----------|---------|
| **Unified diff** | LLMs hallucinate line numbers, fail to match exact text |
| **Search/replace** | LLMs paraphrase instead of copying exact strings |
| **JSON operations** | Parsing failures, section targeting errors |
| **Aider formats** | Complex syntax leads to malformed output |
| **Full rewrite** | ✅ Simple, consistent, no parsing needed |

**Why this matters for complex edits**: Our test cases require 50+ changes scattered across different sections. Diff-based approaches force the model to spend significant compute on reasoning about line numbers, exact text matching, and format compliance. Models with extended thinking burn tokens on this overhead; models without thinking produce unreliable output.

Full rewrite sidesteps this entirely — the model just outputs the edited document without complex formatting logic.

**Our production setup at Research.tech**: We use `full_rewrite` with **grok-4-fast** for documents up to ~50 KB. The extra output tokens cost less than retry logic and error recovery from failed diffs.

---

## Deep Dive: The Long Document Problem

The `hard/very_long` fixture (2000+ lines) exposes critical model limitations. We analyzed every diff to understand what went wrong.

### Usability Analysis

| Model | Score | Usable? | What Went Wrong |
|-------|-------|---------|-----------------|
| **glm-4.6** | 0.89 | ✅ Yes | 87% cosmetic changes, 3 minor content removals |
| gpt-5-mini | 0.88 | ❌ No | ENA governance section corrupted, template phrase pollution |
| qwen3-next-80b | 0.87 | ❌ No | **15 billion → 15 trillion (1000x error)** |
| glm-4.5-air | 0.87 | ❌ No | **15 billion → 15 trillion (1000x error)** |
| qwen3-235b | 0.81 | ❌ No | Text truncated mid-word ("vote on sy..."), Basel III error |
| minimax-m2 | 0.78 | ❌ No | Entire October 2025 stress event section deleted |
| gemini-2.5-flash | 0.75 | ❌ No | **15B→15T (4 times)**, fabricated volume data |
| grok-4-fast | 0.73 | ❌ No | Final summary removed, FAQ truncated mid-sentence |
| gpt-4.1-mini | 0.46 | ❌ No | Significant truncation |
| kimi-k2 | 0.03 | ❌ No | Context limit exceeded |
| mistral-nemo | 0.00 | ❌ No | Complete failure |

**Critical insight**: High similarity scores (0.75-0.88) don't guarantee usability. Multiple models introduced **catastrophic factual errors** that would be dangerous in production.

### Failure Patterns

**1. Numerical Hallucination** (qwen3-next, glm-4.5-air, gemini-2.5-flash)
- Changed "15 billion" to "15 trillion" — a 1000x error
- Appeared multiple times in the same document
- Models with highest similarity scores had this error

**2. Context Truncation** (grok-4-fast, qwen3-235b, gpt-5-mini)
- Truncated mid-sentence: "vote on sy..."
- Silently dropped final summary section
- Removed stress event analysis without indication

**3. Template Injection** (gpt-5-mini)
- Inserted generic phrases repeatedly throughout
- "Institutional adoption has accelerated..." appeared 10+ times
- Polluted document with marketing language

**4. Section Deletion** (minimax-m2, gemini-2.5-flash)
- Removed 18-line Collateral and Yield section entirely
- Deleted October 2025 stress event (critical case study)
- No indication of removal

### Why glm-4.6 Succeeded

The only model producing safe output on very long documents:

- 87% of changes were cosmetic (sentence reordering)
- Only 3 minor content removals (secondary price source, Binance Labs details, historical APY)
- Zero factual errors introduced
- No text corruption or truncation
- Document structure fully preserved

---

## Deep Dive: Complex Document "Failures"

We analyzed fixtures where models scored 0.85-0.99 but failed the exact-match test.

**Key finding: Most "failures" are false negatives** — outputs are production-usable.

### Detailed Analysis

| Fixture | Model | Score | Actual Issue | Usable? |
|---------|-------|-------|--------------|---------|
| audit_security | glm-4.6 | 0.99 | 3 number differences ($3M→$3.5M, 4→5 findings) | ✅ Yes |
| audit_security | grok-4-fast | 0.99 | Sentence reordering, timeline swap | ✅ Yes |
| audit_security | qwen3-next | 0.93 | Count inconsistencies, date ordering | ✅ Yes |
| collateral_hedging | glm-4.6 | 0.96 | Used consistent $10.2B throughout (arguably better) | ✅ Yes |
| collateral_hedging | grok-4-fast | 0.94 | Same + added useful clarifications | ✅ Yes |
| collateral_hedging | deepseek | 0.95 | Supply figure, text consolidation | ✅ Yes |
| contract_maturity | grok-4-fast | 0.85 | Paragraph merging only (100% identical content) | ✅ Yes |
| contract_maturity | glm-4.5-air | 0.85 | Paragraph merging only (100% identical content) | ✅ Yes |

### Why the Benchmark Over-Penalizes

The 0.85-0.99 scores penalize acceptable deviations:

**1. Paragraph Formatting** (contract_maturity)
- Models merged two paragraphs into one
- Zero content changes, just whitespace
- Score dropped to 0.85 for pure formatting

**2. Editorial Judgment** (collateral_hedging)
- Models chose $10.2B consistently instead of mixing $9.65B and $10.2B
- This is arguably *better* than the expected output
- Penalized as a "failure"

**3. Precision Differences** (audit_security)
- "100.7%" → "100.65%"
- "$3 million" → "$3,500,000"
- No semantic difference

**4. Added Clarifications**
- Models added "Low confidence" or "Exact percentage not disclosed"
- Improvements penalized as deviations

### Adjusted Usability Rates

| Document Type | Benchmark Pass Rate | True Usability (after analysis) |
|---------------|---------------------|--------------------------------|
| Short/Medium | 73% | ~90%+ |
| Complex | 64-73% | ~85%+ |
| Very Long (2000+ lines) | 0% | ~10% (only glm-4.6) |

---

## The Problem

At [Research.tech](https://research.tech), we work with long-form markdown documents—research reports, technical documentation, and structured content that often exceeds 2,000 lines. When users request changes to these documents through natural language instructions, we need LLMs to apply those edits accurately.

The challenge: **there's no clear consensus on the best way to have LLMs edit long documents.**

Common approaches each have significant tradeoffs:

| Approach | Problem |
|----------|---------|
| **Full rewrite** | Expensive for long documents (input + output tokens), risk of unintended changes |
| **Unified diff (git-style)** | LLMs frequently hallucinate line numbers and fail to match exact text |
| **Search/replace blocks** | Requires exact text matching; LLMs often paraphrase instead of copying |
| **Apply models (Morph, etc.)** | Adds latency and cost from two-step process |

We built this benchmark to systematically evaluate these approaches and find what actually works.

## Scope

This benchmark is specifically designed for **markdown prose documents**, not code files.

We focus on:
- Documents with standard markdown structure (headers, paragraphs, lists, tables)
- Natural language edit instructions ("add a paragraph about X", "update the statistics in section Y")
- Accuracy of applying changes without corrupting surrounding content

We do **not** benchmark:
- Code editing (different challenges around syntax, indentation, AST awareness)
- Complex nested structures requiring precise character-level edits
- Real-time collaborative editing scenarios

## Algorithms

| Algorithm | Description |
|-----------|-------------|
| `full_rewrite` | LLM outputs the complete edited document |
| `git_diff` | LLM generates unified diff format, parsed and applied with fuzzy matching |
| `search_replace` | LLM outputs search/replace blocks (Aider-style) |
| `aider_editblock` | Aider's edit block format with `<<<<<<< SEARCH` / `>>>>>>> REPLACE` markers |
| `aider_udiff` | Aider's unified diff format |
| `aider_patch` | Aider's V4A patch format with `@@` section markers |
| `aider_diff_fenced` | Aider's diff format wrapped in fenced code blocks |
| `codex_patch` | OpenAI Codex/GPT-4.1 patch format with anchor-based hunks |
| `udiff_tagged` | Unified diff with explicit `[CTX]`/`[DEL]`/`[ADD]` tags |
| `json_ops` | Structured JSON operations (replace/insert/delete by section + snippet) |
| `str_replace_editor` | Exact-match string replace commands in JSON (OpenHands-style) |
| `section_rewrite` | Rewrite individual markdown sections by heading |
| `partial_rewrite` | LLM outputs full document with `...` markers for unchanged blocks |
| `morph` | LLM generates edited doc, Morph model merges into original |

All algorithms except `morph` accept a configurable model parameter.

### Algorithm Categories

**Full Document**
- `full_rewrite`: Output the entire edited document. Simple but expensive for long documents.
- `partial_rewrite`: Output full document with `...` markers to skip unchanged blocks.
- `morph`: Two-step approach—LLM generates edits, then Morph model merges them into the original.

**Diff-Based**
- `git_diff`: Standard unified diff format (`-` for deletions, `+` for additions).
- `aider_udiff`, `aider_patch`, `aider_diff_fenced`: Various Aider diff formats with fuzzy matching.
- `codex_patch`: OpenAI's patch format using `@@` anchors instead of line numbers.
- `udiff_tagged`: Explicit tags (`[CTX]`, `[DEL]`, `[ADD]`) to guide LLM output.

**Search/Replace**
- `search_replace`, `aider_editblock`: Block-based search and replace with markers.
- `str_replace_editor`: JSON array of exact-match string replacements.

**Structured**
- `json_ops`: JSON operations targeting sections by heading name and match text.
- `section_rewrite`: Output only modified sections wrapped in `### SECTION:` blocks.

## Installation

```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -e .
```

## Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Required:
```
OPENROUTER_API_KEY=your_api_key_here
```

Optional:
```
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LMNR_PROJECT_API_KEY=your_laminar_key_here  # For Laminar tracing
```

## Usage

```bash
# Run all algorithms on all fixtures
md-edit-bench

# Test specific algorithms
md-edit-bench -a full_rewrite -a git_diff -a json_ops

# Test with specific models (OpenRouter format)
md-edit-bench -m anthropic/claude-sonnet-4 -m openai/gpt-4.1

# Filter by fixture category
md-edit-bench -c simple
md-edit-bench -c medium
md-edit-bench -c complex
md-edit-bench -c hard

# Show detailed failure output
md-edit-bench -v           # Verbose (show failure details)
md-edit-bench -d           # Show diffs from expected output
```

## Fixtures

Test cases are organized by complexity:

```
fixtures/
├── simple/          # Short documents, straightforward changes
├── medium/          # Longer documents, multiple changes
├── complex/         # Large documents, complex edit patterns
└── hard/            # Very large documents (2000+ lines), stress tests
```

Each fixture has three files:
- `{name}.initial.md` — The original document
- `{name}.changes.md` — Natural language change instructions
- `{name}.final.md` — Expected result

### Adding Fixtures

1. Create files in `fixtures/{category}/`:
   - `{name}.initial.md`
   - `{name}.changes.md`
   - `{name}.final.md`
2. Fixtures are auto-discovered on next run

## Metrics

| Metric | Description |
|--------|-------------|
| **Match** | Exact match with expected output (pass/fail) |
| **Warn** | Number of warnings (e.g., failed fuzzy matches that were retried) |
| **Score** | Similarity score 0-1 (line + character similarity) |
| **Time** | Execution time per test |
| **Cost** | USD cost from OpenRouter usage data |

## Example Output

```
                        Diff Algorithm Benchmark Results
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Algorithm      ┃ Model           ┃ Fixture      ┃ Match ┃ Warn ┃ Score ┃  Time ┃    Cost ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ full_rewrite   │ claude-sonnet-4 │ basic_report │   ✓   │    - │  1.00 │  8.2s │ $0.0312 │
│ json_ops       │ claude-sonnet-4 │ basic_report │   ✓   │    - │  1.00 │  5.4s │ $0.0089 │
│ section_rewr…  │ claude-sonnet-4 │ basic_report │   ✓   │    - │  1.00 │  4.8s │ $0.0076 │
│ codex_patch    │ claude-sonnet-4 │ basic_report │   ✗   │    2 │  0.94 │  6.1s │ $0.0102 │
└────────────────┴─────────────────┴──────────────┴───────┴──────┴───────┴───────┴─────────┘

Summary by Algorithm:
  full_rewrite: 2/2 (100%) avg: 8.3s  $0.0624  lines: -0.0/+0.0
  json_ops: 2/2 (100%) avg: 5.2s  $0.0178  lines: -0.0/+0.0
  section_rewrite: 2/2 (100%) avg: 4.9s  $0.0152  lines: -0.0/+0.0
  codex_patch: 1/2 (50%) avg: 6.3s  $0.0204  lines: -2.5/+1.0  warnings: 3
```

## Adding New Algorithms

Each algorithm is a directory under `md_edit_bench/algorithms/` containing:
- `__init__.py` — Re-exports the algorithm class
- `{name}.py` — Algorithm implementation
- `system.jinja2` — System prompt template
- `user.jinja2` — User prompt template
- `retry.jinja2` — (Optional) Retry prompt for failed operations
- `format_spec.jinja2` — (Optional) Format specification included in prompts

Example implementation:

```python
from md_edit_bench.algorithms.base import Algorithm
from md_edit_bench.llm import call_llm
from md_edit_bench.models import AlgorithmResult
from md_edit_bench.utils import PromptManager

pm = PromptManager(__file__)

class MyAlgorithm(Algorithm):
    name = "my_algorithm"
    description = "Description of the approach"

    async def apply(self, initial: str, changes: str, model: str) -> AlgorithmResult:
        system_prompt = pm.get("system.jinja2")
        user_prompt = pm.get("user.jinja2", initial=initial, changes=changes)

        output, usage = await call_llm(model, user_prompt, system_prompt)

        # Parse and apply the output...
        result = apply_changes(initial, output)

        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
            warnings=[],  # List of warning messages
        )
```

Then add to `md_edit_bench/algorithms/__init__.py`.

## Observability

With `LMNR_PROJECT_API_KEY` set, runs are traced to [Laminar](https://www.lmnr.ai/) with hierarchical spans:
- `benchmark_run` — Top-level span for the entire run
- `fixture:{name}` — Span per fixture
- `algorithm:{name}({model})` — Span per algorithm/model combination

Results are also saved to `results/` directory with:
- `result.json` — Metrics and metadata
- `output.md` — Algorithm's output
- `diff.txt` — Diff from expected output
- `llm_request.txt` / `llm_response.txt` — Raw LLM calls

## License

MIT

---

Built by [Research.tech](https://research.tech)
