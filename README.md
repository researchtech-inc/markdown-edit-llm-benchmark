# Markdown Edit LLM Benchmark

A benchmark suite for evaluating different LLM-based approaches to editing markdown documents.

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

| Algorithm | Description | Model Configurable |
|-----------|-------------|:------------------:|
| `full_rewrite` | LLM outputs the complete edited document | Yes |
| `git_diff` | LLM generates unified diff format, then parsed and applied | Yes |
| `search_replace` | LLM outputs search/replace blocks (Aider-style), then applied | Yes |
| `morph` | LLM generates edited doc, Morph model merges into original | No |

### How They Work

**Full Rewrite**: The simplest approach. Give the LLM the document and changes, ask for the complete edited document. Simple but expensive for long documents since you pay for outputting the entire document.

**Git Diff**: Ask the LLM to output a unified diff (the format used by `git diff`). Then parse and apply the diff to the original. In theory more efficient, but LLMs struggle with exact line numbers and matching original text precisely.

**Search/Replace**: Inspired by [Aider's](https://aider.chat) approach. The LLM outputs blocks like:
```
<<<<<<< SEARCH
exact text to find
=======
replacement text
>>>>>>> REPLACE
```
Requires the LLM to copy text exactly, which they often fail to do.

**Morph**: A two-step approach using specialized "apply" models. First, a capable LLM generates the edited document. Then, a specialized model (Morph) merges the edits back into the original, preserving unchanged content. Adds latency but may improve accuracy.

## Installation

```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -e .

# With optional observability support
uv sync --extra tracing
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
LMNR_PROJECT_API_KEY=your_laminar_key_here  # For tracing
```

## Usage

```bash
# Run all algorithms on all fixtures
md-edit-bench

# Test specific algorithms
md-edit-bench -a full_rewrite -a git_diff

# Test with specific models
md-edit-bench -m anthropic/claude-sonnet-4 -m openai/gpt-oss-120b

# Filter by fixture complexity
md-edit-bench -c simple
md-edit-bench -c medium

# Show detailed failure output
md-edit-bench -v           # Verbose
md-edit-bench -d           # Show diffs
```

## Fixtures

Test cases are organized by complexity:

```
fixtures/
├── simple/          # Short documents, straightforward changes
└── medium/          # Longer documents, multiple changes
```

Each fixture has three files:
- `{name}.initial.md` — The original document
- `{name}.changes.md` — Natural language change instructions
- `{name}.final.md` — Expected result

### Change Instruction Format

For reproducible benchmarks, we use specific change instructions:

```markdown
### Section: Executive Summary

- **Modify**: Change "Sales increased" to "Sales increased by 23% compared to Q2"
- **Add**: Insert a new paragraph after the first sentence with quarterly comparison data
- **Delete**: Remove the outdated reference to Q1 projections
```

This format tells the LLM exactly what to change and where, making it possible to verify correctness against expected output.

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
| **Score** | Similarity score 0-1 (line + character similarity) |
| **Time** | Execution time per test |
| **Cost** | USD cost from OpenRouter usage data |

## Example Output

```
                    Diff Algorithm Benchmark Results
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Algorithm    ┃ Model        ┃ Fixture      ┃ Match ┃ Score ┃  Time ┃    Cost ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ full_rewrite │ gpt-4.1-mini │ basic_report │   ✓   │  1.00 │ 11.4s │ $0.0212 │
│ git_diff     │ gpt-4.1-mini │ basic_report │   ✗   │  0.85 │ 16.8s │ $0.0174 │
│ morph        │ -            │ basic_report │   ✓   │  1.00 │ 15.2s │ $0.0324 │
│ search_repl… │ gpt-4.1-mini │ basic_report │   ✗   │  0.92 │ 14.1s │ $0.0176 │
└──────────────┴──────────────┴──────────────┴───────┴───────┴───────┴─────────┘

Summary by Algorithm:
  full_rewrite: 2/2 (100%) avg: 11.3s  total: $0.0394
  git_diff: 0/2 (0%) avg: 14.7s  total: $0.0323
  morph: 2/2 (100%) avg: 15.2s  total: $0.0591
  search_replace: 1/2 (50%) avg: 14.5s  total: $0.0334
```

## Adding New Algorithms

1. Create `md_edit_bench/algorithms/my_algorithm.py`
2. Implement the `Algorithm` base class:

```python
from md_edit_bench.algorithms import Algorithm, register_algorithm
from md_edit_bench.llm import call_llm_simple
from md_edit_bench.models import AlgorithmResult

@register_algorithm
class MyAlgorithm(Algorithm):
    name = "my_algorithm"
    description = "Description of the approach"
    accepts_model = True
    default_model = "openai/gpt-oss-120b"

    async def apply(
        self,
        initial: str,
        changes: str,
        model: str | None = None,
    ) -> AlgorithmResult:
        model = model or self.default_model
        result, usage = await call_llm_simple(model, SYSTEM_PROMPT, user_prompt)
        return AlgorithmResult(
            output=result,
            success=True,
            error=None,
            usage=usage,
        )
```

3. Import in `md_edit_bench/algorithms/__init__.py`

## Observability

With `LMNR_PROJECT_API_KEY` set, runs are traced to [Laminar](https://www.lmnr.ai/):
- Trace name: `diff:{algorithm}/{fixture}`
- Tags: algorithm, fixture, model

## Contributing

We welcome contributions:
- New algorithms to benchmark
- Additional test fixtures (especially longer documents)
- Improvements to scoring methodology

## License

MIT

---

Built by [Research.tech](https://research.tech)
