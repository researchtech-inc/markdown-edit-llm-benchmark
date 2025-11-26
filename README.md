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
| `morph` | LLM generates edited doc, Morph model merges into original |

All algorithms except `morph` accept a configurable model parameter.

### Algorithm Categories

**Full Document**
- `full_rewrite`: Output the entire edited document. Simple but expensive for long documents.
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
└── complex/         # Large documents, complex edit patterns
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
