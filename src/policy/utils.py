"""
Policy-specific utility functions and constants
"""
import json
import os
from typing import Dict

HEATMAP_COLORS = [
    [0.0, '#d32f2f'],    # Red for low values
    [0.5, '#ffc107'],    # Yellow for medium values  
    [1.0, '#4caf50']     # Green for high values
]

PILLAR_COLUMNS = ['Water', 'Energy', 'Food', 'Ecosystems']
PILLAR_KEYS = ['water', 'energy', 'food', 'ecosystems']

# Styling constants for tables
TABLE_STYLES = {
    'neutral': 'background-color: #f8f9fa; color: #495057',
    'positive': 'background-color: #e8f5e9; color: #1b5e20',
    'negative': 'background-color: #ffebee; color: #b71c1c',
    'info': 'background-color: #e3f2fd; color: #1565c0'
}


def load_policies_as_dict():
    """Load policies from JSON file and return as dictionary (for compatibility with legacy code)"""
    try:
        json_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'policies.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            policies_list = json.load(f)
        return {p['title']: p for p in policies_list}
    except FileNotFoundError:
        print(f"Error: Could not find policies.json at {json_path}")
        current_dir_path = os.path.join('..', '..', 'data', 'policies.json')
        if os.path.exists(current_dir_path):
            print(f"Found policies.json in current directory: {current_dir_path}")
            with open(current_dir_path, 'r', encoding='utf-8') as f:
                policies_list = json.load(f)
            return {p['title']: p for p in policies_list}
        else:
            print(f"Also checked current directory path: {current_dir_path} - not found")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Files in current directory: {os.listdir('.')}")
            if os.path.exists('data'):
                print(f"Files in data directory: {os.listdir('data')}")
            return {}
    except Exception as e:
        print(f"Error loading policies: {e}")
        return {}


# Policy details dictionary for legacy compatibility
POLICY_DETAILS = load_policies_as_dict()


# Utility functions removed - were not being used
