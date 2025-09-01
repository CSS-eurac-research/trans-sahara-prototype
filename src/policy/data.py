import json
import os
from typing import Dict, List, Any
import streamlit as st


def load_policies():
    """Load policies from JSON file"""
    try:
        with open(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'policies.json'), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Policies file not found!")
        return []


def get_policy_categories(policies: List[Dict]) -> List[str]:
    """Extract unique policy categories from policies"""
    categories = set()
    for policy in policies:
        if 'policy_type' in policy:
            categories.add(policy['policy_type'])
    return sorted(list(categories))


def get_policies_by_category(policies: List[Dict], category: str) -> List[Dict]:
    """Get policies filtered by category"""
    return [policy for policy in policies if policy.get('policy_type') == category]


def load_pillars_definitions():
    """Load pillars definitions from JSON file"""
    try:
        with open(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'pillars.json'), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Pillars definitions file not found!")
        return {}


def infer_policy_pillar(policy: Dict) -> str:
    """Infer primary WEFE pillar for a policy. Returns one of 'water', 'energy', 'food', 'ecosystems'."""
    title = policy.get('title', '').lower()

    # 1) Look at synergy/trade-off categories first
    def map_category_to_pillar(category: str) -> str | None:
        c = category.strip().lower()
        if c.startswith('water'):
            return 'water'
        if c.startswith('energy'):
            return 'energy'
        if c.startswith('food') or 'agri' in c:
            return 'food'
        if 'ecosystem' in c or 'biodiversity' in c or 'land' in c or 'marine' in c or 'climate' in c:
            return 'ecosystems'
        return None

    for coll_key in ('synergies', 'trade_offs'):
        for item in policy.get(coll_key, []) or []:
            pillar = map_category_to_pillar(str(item.get('category', '')))
            if pillar:
                return pillar

    # 2) Fall back to title keywords
    if 'water' in title:
        return 'water'
    if 'energy' in title or 'renewable' in title:
        return 'energy'
    if 'agri' in title or 'food' in title or 'farm' in title:
        return 'food'
    if 'eco' in title or 'biodiversity' in title or 'green' in title or 'marine' in title or 'climate' in title:
        return 'ecosystems'

    # 3) Default bucket
    return 'ecosystems'


def parse_change_value(raw: Any) -> float:
    """Parse change value from policy indicators, handling various formats"""
    if raw is None:
        return 0
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        s = str(raw).strip()
        # Remove any units except % and sign
        if s.endswith('%'):
            return float(s.replace('%', ''))
        # Fallback: extract leading signed float
        return float(s)
    except Exception:
        return 0


def get_all_indicators() -> List[str]:
    """Get all available indicators from pillars definitions"""
    pillars = load_pillars_definitions()
    indicators = []
    
    for pillar_data in pillars.get('wefe_pillars', {}).values():
        for category_data in pillar_data.get('categories', {}).values():
            for indicator_key in category_data.get('indicators', {}).keys():
                indicators.append(indicator_key)
    
    return sorted(indicators)


def get_indicator_numbering() -> Dict[str, int]:
    """Get a mapping of indicator keys to their sequential numbers"""
    pillars = load_pillars_definitions()
    indicator_numbering = {}
    counter = 1
    
    for pillar_data in pillars.get('wefe_pillars', {}).values():
        for category_data in pillar_data.get('categories', {}).values():
            for indicator_key in category_data.get('indicators', {}).keys():
                indicator_numbering[indicator_key] = counter
                counter += 1
    
    return indicator_numbering


def get_indicator_with_number(indicator_key: str) -> str:
    """Get indicator key with its number prefix"""
    numbering = get_indicator_numbering()
    indicator_num = numbering.get(indicator_key, 0)
    return f"{indicator_num:02d}. {indicator_key}" if indicator_num > 0 else indicator_key


def get_all_indicators_with_numbers() -> List[str]:
    """Get all available indicators with their numbers"""
    indicators = get_all_indicators()
    return [get_indicator_with_number(ind) for ind in indicators]


def get_policies_by_indicator(policies: List[Dict], indicator: str) -> List[Dict]:
    """Get policies that provide improvement (synergy) to a specific indicator, sorted by improvement magnitude in descending order"""
    improving_policies = []
    
    for policy in policies:
        for synergy in policy.get('synergies', []):
            for affected_ind in synergy.get('affected_indicators', []):
                if affected_ind.get('indicator') == indicator:
                    change_value = parse_change_value(affected_ind.get('expected_change'))
                    if change_value > 0:
                        improving_policies.append({
                            'policy': policy,
                            'improvement_value': change_value,
                            'expected_change': affected_ind.get('expected_change')
                        })
                        break
            if any(item['policy'] == policy for item in improving_policies):
                break
    
    improving_policies.sort(key=lambda x: x['improvement_value'], reverse=True)
    
    return [item['policy'] for item in improving_policies]
