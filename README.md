# values-understanding

Ask structured five-option survey questions under the system-prompt conditions
shipped by [`values-harness`](https://github.com/payalchandak/values-harness).

The survey contains six Shared Decision-Making questions. They contrast whether
the model could **allow** versus **require** a requested treatment in three
situations: treatment outside the patient's best interests, treatment that is
not medically indicated, and treatment that is ethically inappropriate.

Every question uses this scale:

1. Strongly disagree
2. Disagree
3. Neither agree nor disagree
4. Agree
5. Strongly agree

Answers are scored from −2 to 2:
`Strongly disagree = -2`, `Disagree = -1`, `Neither = 0`, `Agree = 1`,
and `Strongly agree = 2`.

## Setup

```bash
uv sync
cp .env.example .env
# Add OPENROUTER_API_KEY to .env.
```

The `values-harness` dependency is the source of truth for system prompts. This
repo resolves the harness's packaged prompt tree through its `PromptManager`,
using the same `conditions/<condition>/system.md` layout. Nested conditions
such as `autonomy_primacy/v1` therefore work without prompt text being copied
into this repo.

## Run

Inspect the default prompts and questions without making an API call:

```bash
uv run python -m values_understanding --dry-run
```

By default, a run uses `control` and every available
`autonomy_primacy/v*` condition, requests 10 independent responses per
question/condition/model, and runs up to 250 calls concurrently:

```bash
uv run python -m values_understanding --model openai/gpt-5.5
```

Override the sampling or concurrency with `--trials` and `--threads`.

Choose conditions explicitly, repeat models, or sweep the whole harness:

```bash
uv run python -m values_understanding \
  --condition control \
  --condition autonomy_primacy/v2 \
  --model openai/gpt-5.5 \
  --model anthropic/claude-opus-4.8

uv run python -m values_understanding --all-conditions --model openai/gpt-5.5
```

Useful inspection commands:

```bash
uv run python -m values_understanding --list-questions
uv run python -m values_understanding --list-conditions
uv run python -m values_understanding --summarize
```

Score saved results without making model calls:

```bash
uv run python scripts/score_results.py
uv run python scripts/score_results.py --model google/gemini-3.1-pro-preview
uv run python scripts/score_results.py --json
```

Results are stored at:

```text
results/<question>/<condition>/<provider>__<model>[__trial_NN].json
```

Each result includes the exact rendered system prompt, user prompt, selected
option, numeric score, and full provider response. Complete results are skipped
on rerun; pass `--force` to replace them. Summary calculations also support
older result files without a stored score by deriving it from `choice_id`.

## Add a question

Add `questions/<id>.yaml` containing an `id` matching the filename and a
`stem`. The five options are centralized in `questions/scale.yaml`.
