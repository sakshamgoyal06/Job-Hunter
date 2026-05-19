"""India-focused compensation math + AI talking points."""

from __future__ import annotations

from typing import Any

from src.ai_client import chat_json
from src.prompts import compensation_prompt


def _f(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def compute_compensation_metrics(inputs: dict[str, Any]) -> dict[str, Any]:
    cur_fixed = _f(inputs.get("current_fixed"))
    cur_var = _f(inputs.get("current_variable"))
    cur_esop = _f(inputs.get("current_esop_annual"))
    new_fixed = _f(inputs.get("new_fixed"))
    new_var = _f(inputs.get("new_variable"))
    join_bonus = _f(inputs.get("joining_bonus"))
    retention = _f(inputs.get("retention_bonus"))
    new_esop = _f(inputs.get("new_esop_value"))
    tax_rate = _f(inputs.get("tax_rate_pct"))  # optional, 0-100
    relocation = _f(inputs.get("relocation_cost"))

    current_total = cur_fixed + cur_var + cur_esop
    new_total = new_fixed + new_var + new_esop + join_bonus + retention
    fixed_delta_pct = (
        ((new_fixed - cur_fixed) / cur_fixed * 100) if cur_fixed > 0 else None
    )
    total_delta_pct = (
        ((new_total - current_total) / current_total * 100)
        if current_total > 0
        else None
    )

    # Simple risk adjustment: discount variable + ESOP by 25% vs fixed weighting
    risk_adj_new = (
        new_fixed
        + 0.75 * new_var
        + 0.5 * new_esop
        + join_bonus
        + 0.5 * retention
        - relocation
    )
    risk_adj_current = cur_fixed + 0.75 * cur_var + 0.5 * cur_esop

    monthly_fixed = new_fixed / 12.0 if new_fixed else 0.0
    monthly_fixed_after_tax = (
        monthly_fixed * (1 - tax_rate / 100.0) if tax_rate else monthly_fixed
    )

    weak_fixed = new_total > current_total and new_fixed < cur_fixed

    return {
        "current_total_ctc": round(current_total, 2),
        "new_total_ctc": round(new_total, 2),
        "fixed_increase_pct": None if fixed_delta_pct is None else round(fixed_delta_pct, 2),
        "total_increase_pct": None if total_delta_pct is None else round(total_delta_pct, 2),
        "risk_adjusted_offer_value": round(risk_adj_new, 2),
        "risk_adjusted_current_value": round(risk_adj_current, 2),
        "monthly_pre_tax_fixed": round(monthly_fixed, 2),
        "monthly_pre_tax_fixed_after_tax_estimate": round(monthly_fixed_after_tax, 2),
        "paper_ctc_up_fixed_weak": weak_fixed,
    }


def ai_compensation_advice(inputs: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """LLM brief layered on top of deterministic CTC math."""
    combined = {**inputs, "computed_summary": metrics}
    sys_p, usr_p = compensation_prompt(combined)
    return chat_json(system=sys_p, user=usr_p)
