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
`autonomy_primacy/v*` condition:

```bash
uv run python -m values_understanding --model openai/gpt-5.5
```

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
```

Results are stored at:

```text
results/<question>/<condition>/<provider>__<model>.json
```

Each result includes the exact rendered system prompt, user prompt, selected
option and full provider response. Complete results are skipped on rerun; pass
`--force` to replace them.

## Add a question

Add `questions/<id>.yaml` containing an `id` matching the filename and a
`stem`. The five options are centralized in `questions/scale.yaml`.
