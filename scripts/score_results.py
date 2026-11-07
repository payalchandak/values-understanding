#!/usr/bin/env python3
"""Score saved survey responses and report means by model and condition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from values_understanding.run import default_output_dir, summarize_results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the -2 to +2 Likert scale to saved values-understanding "
            "results and report means."
        )
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=default_output_dir(),
        help="Results directory. Default: repository results/.",
    )
    parser.add_argument(
        "--model",
        action="append",
        help="Only score this model id (repeatable). Default: every model.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text.",
    )
    args = parser.parse_args()

    summaries = summarize_results(args.results_dir, model_ids=args.model)
    if not summaries:
        parser.error(f"No completed results found in {args.results_dir}")

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "model": summary.model_id,
                        "condition": summary.condition,
                        "mean_score": summary.mean_score,
                        "n": summary.n,
                    }
                    for summary in summaries
                ],
                indent=2,
            )
        )
    else:
        for summary in summaries:
            print(
                f"{summary.model_id} / {summary.condition}: "
                f"mean={summary.mean_score:.2f} (n={summary.n})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
