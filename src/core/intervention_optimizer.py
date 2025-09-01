"""
Intervention selection optimizer to match or exceed policy-driven indicator improvements.

Greedy cost-effectiveness heuristic:
- Targets are aggregated expected indicator changes from selected policies.
- Each intervention contributes indicator deltas from its outcomes.indicators array.
- We iteratively select the intervention that maximizes reduction of unmet targets per unit CAPEX,
  until all targets are met or no further progress is possible.

Outputs a list of selected interventions with coverage metrics.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple


@dataclass
class InterventionImpact:
    file_name: str
    title: str
    capex_usd: float
    indicators: Dict[str, float]


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace('%', '')
        return float(s)
    except Exception:
        return default


def load_interventions(base_dir: str) -> List[InterventionImpact]:
    interventions_dir = os.path.join(base_dir, '..', '..', 'data', 'interventions')
    impacts: List[InterventionImpact] = []
    if not os.path.isdir(interventions_dir):
        return impacts

    for name in sorted(os.listdir(interventions_dir)):
        if not name.endswith('.json'):
            continue
        path = os.path.join(interventions_dir, name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                obj = json.load(f)
        except Exception:
            continue

        title = obj.get('title', name)
        needs = obj.get('needs', {}) or {}
        capex = _safe_float(needs.get('capex_usd'), 0.0)

        indicators: Dict[str, float] = {}
        outcomes = obj.get('outcomes', {}) or {}
        for rec in outcomes.get('indicators', []) or []:
            ind_key = rec.get('indicator')
            if not ind_key:
                continue
            delta = _safe_float(rec.get('expected_change'), 0.0)
            # Sum contributions per indicator
            indicators[ind_key] = indicators.get(ind_key, 0.0) + delta

        impacts.append(InterventionImpact(file_name=name, title=title, capex_usd=capex, indicators=indicators))

    return impacts


def aggregate_policy_targets(selected_policies: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate expected indicator changes across selected policies.

    Returns mapping indicator -> required change (sum of synergies and trade-offs).
    """
    targets: Dict[str, float] = {}
    for pol in selected_policies:
        for coll_key in ('synergies', 'trade_offs'):
            for item in pol.get(coll_key, []) or []:
                for ind in (item.get('affected_indicators') or []):
                    key = ind.get('indicator')
                    if not key:
                        continue
                    val = _safe_float(ind.get('expected_change'), 0.0)
                    targets[key] = targets.get(key, 0.0) + val
    return targets


def _coverage_gain(unmet: Dict[str, float], intervention: InterventionImpact) -> float:
    gain = 0.0
    for k, required in unmet.items():
        if required <= 0:
            continue
        contrib = intervention.indicators.get(k, 0.0)
        if contrib > 0:
            gain += min(contrib, required)
    return gain


def select_interventions_to_meet_targets(
    interventions: List[InterventionImpact],
    targets: Dict[str, float]
) -> Tuple[List[InterventionImpact], Dict[str, float]]:
    """
    Greedy selection to meet or exceed targets with minimal CAPEX.
    Returns (selected_interventions, unmet_after_selection)
    """
    unmet: Dict[str, float] = {k: max(0.0, float(v)) for k, v in targets.items()}
    selected: List[InterventionImpact] = []
    remaining = interventions.copy()

    while True:
        # Check if all met
        if all(v <= 0.000001 for v in unmet.values()):
            break

        best = None
        best_score = 0.0
        for iv in remaining:
            gain = _coverage_gain(unmet, iv)
            if gain <= 0:
                continue
            cost = max(iv.capex_usd, 1.0)
            score = gain / cost
            if score > best_score:
                best_score = score
                best = iv

        if best is None:
            # No further progress possible
            break

        # Apply selection and reduce unmet
        selected.append(best)
        remaining = [iv for iv in remaining if iv is not best]
        for k in list(unmet.keys()):
            contrib = best.indicators.get(k, 0.0)
            if contrib > 0:
                unmet[k] = max(0.0, unmet[k] - contrib)

    return selected, unmet


def run_policy_simulation(base_dir: str, selected_policies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute end-to-end simulation given selected policy objects.
    Returns dict with selected interventions, coverage summary, and leftover unmet indicators.
    """
    interventions = load_interventions(base_dir)
    targets = aggregate_policy_targets(selected_policies)
    chosen, unmet = select_interventions_to_meet_targets(interventions, targets)

    total_capex = sum(iv.capex_usd for iv in chosen)
    coverage = {k: float(targets.get(k, 0.0)) - float(unmet.get(k, 0.0)) for k in targets.keys()}

    return {
        'targets': targets,
        'coverage': coverage,
        'unmet': unmet,
        'total_capex_usd': total_capex,
        'selected_interventions': [
            {
                'file_name': iv.file_name,
                'title': iv.title,
                'capex_usd': iv.capex_usd,
                'indicators': iv.indicators,
            }
            for iv in chosen
        ]
    }


