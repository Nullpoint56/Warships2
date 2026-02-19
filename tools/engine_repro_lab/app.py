"""Repro Lab presentation helpers."""

from __future__ import annotations

from tools.engine_repro_lab.runner import ValidationRun


def render_result_table(run: ValidationRun) -> str:
    result = run.result
    lines = [
        f"replay={run.replay_path}",
        f"fixed_step_seconds={run.config.fixed_step_seconds:.8f}",
        f"passed={result.passed}",
        f"total_ticks={result.total_ticks}",
        f"commands_applied={result.commands_applied}",
        f"checkpoint_count={result.checkpoint_count}",
        f"mismatches={len(result.mismatches)}",
    ]
    if result.mismatches:
        lines.append("mismatch_samples:")
        for mismatch in result.mismatches[:10]:
            lines.append(
                "- "
                f"tick={mismatch['tick']} "
                f"expected={mismatch['expected_hash']} "
                f"actual={mismatch['actual_hash']}"
            )
    return "\n".join(lines)
