"""Intervention optimizer removed. Stub left to avoid import errors."""

from typing import Any, Dict, List


def run_policy_simulation(base_dir: str, selected_policies: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"selected_interventions": [], "coverage": {}, "unmet": {}, "total_capex_usd": 0}


