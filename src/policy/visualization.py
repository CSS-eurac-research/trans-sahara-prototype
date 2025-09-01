import streamlit as st
import plotly.graph_objects as go
import numpy as np
import streamviz
from src.core.wefe_calculations import normalize_indicator, get_indicators_to_invert
from src.policy.data import load_policies, load_pillars_definitions, parse_change_value


def create_indicators_heatmap(lab_info):
    """Create a heatmap showing indicators (rows) vs pillars (columns) with normalized values organized in parallel"""
    if not lab_info or 'wefe_pillars' not in lab_info:
        return None
    
    pillars_def = load_pillars_definitions()
    if not pillars_def:
        return None
    
    wefe_pillars_def = pillars_def.get('wefe_pillars', {})
    indicators_to_invert = get_indicators_to_invert()
    
    pillar_columns = ['Water', 'Energy', 'Food', 'Ecosystems']
    pillar_keys = ['water', 'energy', 'food', 'ecosystems']
    
    pillar_indicators = {}
    for pillar_key in pillar_keys:
        pillar_def = wefe_pillars_def.get(pillar_key, {})
        indicators_list = []
        
        for category_name, category_def in pillar_def.get('categories', {}).items():
            for indicator_name, indicator_def in category_def.get('indicators', {}).items():
                indicators_list.append({
                    'key': indicator_name,
                    'name': indicator_def.get('name', indicator_name.replace('_', ' ').title()),
                    'min_value': indicator_def.get('min_value'),
                    'max_value': indicator_def.get('max_value'),
                    'category': category_name
                })
        
        pillar_indicators[pillar_key] = indicators_list
    
    max_indicators = max(len(indicators) for indicators in pillar_indicators.values())
    
    heatmap_matrix = []
    indicator_rows = []
    
    for i in range(max_indicators):
        row_values = []
        indicator_rows.append(f"Indicator {i+1}")
        
        for pillar_key in pillar_keys:
            indicators_list = pillar_indicators[pillar_key]
            
            if i < len(indicators_list):
                indicator_info = indicators_list[i]
                indicator_name = indicator_info['key']
                
                pillar_data = lab_info['wefe_pillars'].get(pillar_key, {})
                indicator_value = None
                
                for category_name, category_data in pillar_data.get('indicators', {}).items():
                    if isinstance(category_data, dict) and indicator_name in category_data:
                        indicator_value = category_data[indicator_name]
                        break
                
                # Normalize the value if found
                if indicator_value is not None:
                    min_val = indicator_info['min_value']
                    max_val = indicator_info['max_value']
                    should_invert = indicator_name in indicators_to_invert
                    
                    normalized_value = normalize_indicator(indicator_value, min_val, max_val, invert=should_invert)
                    if normalized_value is not None:
                        row_values.append(normalized_value)
                    else:
                        row_values.append(np.nan)
                else:
                    row_values.append(np.nan)
            else:
                row_values.append(np.nan)
        
        heatmap_matrix.append(row_values)
    
    heatmap_array = np.array(heatmap_matrix)
    
    hover_text = []
    for i in range(max_indicators):
        hover_row = []
        for pillar_key in pillar_keys:
            indicators_list = pillar_indicators[pillar_key]
            if i < len(indicators_list):
                indicator_name = indicators_list[i]['name']
                hover_row.append(indicator_name)
            else:
                hover_row.append("No indicator")
        hover_text.append(hover_row)
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_array,
        x=pillar_columns,
        y=indicator_rows,
        text=hover_text,
        colorscale=[
            [0.0, '#d32f2f'],    # Red for low values
            [0.5, '#ffc107'],    # Yellow for medium values  
            [1.0, '#4caf50']     # Green for high values
        ],
        colorbar=dict(
            title="Normalized Score<br>(0-100)"
        ),
        hoverongaps=False,
        hovertemplate='<b>%{text}</b><br>' +
                      '<b>%{x} Pillar</b><br>' +
                      'Score: %{z:.1f}<br>' +
                      '<extra></extra>',
        zmin=0,
        zmax=100
    ))
    
    fig.update_layout(
        title="WEFE Indicators Evaluation Heatmap",
        xaxis_title="WEFE Pillars",
        yaxis_title="Indicator Position",
        height=max(400, max_indicators * 30), 
        margin=dict(l=100, r=100, t=60, b=50)
    )
    
    return fig


def create_improved_indicators_heatmap(lab_info, selected_policy_titles):
    """Create a heatmap showing indicators (rows) vs pillars (columns) with values after policy improvements"""
    if not lab_info or 'wefe_pillars' not in lab_info:
        return None
    
    if not selected_policy_titles:
        return None
    
    pillars_def = load_pillars_definitions()
    if not pillars_def:
        return None
    
    wefe_pillars_def = pillars_def.get('wefe_pillars', {})
    indicators_to_invert = get_indicators_to_invert()
    
    pillar_columns = ['Water', 'Energy', 'Food', 'Ecosystems']
    pillar_keys = ['water', 'energy', 'food', 'ecosystems']
    
    pillar_indicators = {}
    for pillar_key in pillar_keys:
        pillar_def = wefe_pillars_def.get(pillar_key, {})
        indicators_list = []
        
        for category_name, category_def in pillar_def.get('categories', {}).items():
            for indicator_name, indicator_def in category_def.get('indicators', {}).items():
                indicators_list.append({
                    'key': indicator_name,
                    'name': indicator_def.get('name', indicator_name.replace('_', ' ').title()),
                    'min_value': indicator_def.get('min_value'),
                    'max_value': indicator_def.get('max_value'),
                    'category': category_name
                })
        
        pillar_indicators[pillar_key] = indicators_list
    
    policies_by_title = {p['title']: p for p in load_policies()}
    indicator_improvements = {}
    
    for policy_title in selected_policy_titles:
        policy_obj = policies_by_title.get(policy_title)
        if not policy_obj:
            continue
        for coll_key in ('synergies', 'trade_offs'):
            for item in policy_obj.get(coll_key, []) or []:
                for ind in (item.get('affected_indicators') or []):
                    indicator_key = ind.get('indicator')
                    change_value = parse_change_value(ind.get('expected_change'))
                    if indicator_key:
                        if indicator_key not in indicator_improvements:
                            indicator_improvements[indicator_key] = 0
                        indicator_improvements[indicator_key] += change_value
    
    max_indicators = max(len(indicators) for indicators in pillar_indicators.values())

    heatmap_matrix = []
    indicator_rows = []
    
    for i in range(max_indicators):
        row_values = []
        indicator_rows.append(f"Indicator {i+1}")
        
        for pillar_key in pillar_keys:
            indicators_list = pillar_indicators[pillar_key]
            
            if i < len(indicators_list):
                indicator_info = indicators_list[i]
                indicator_name = indicator_info['key']
                
                pillar_data = lab_info['wefe_pillars'].get(pillar_key, {})
                indicator_value = None
                
                for category_name, category_data in pillar_data.get('indicators', {}).items():
                    if isinstance(category_data, dict) and indicator_name in category_data:
                        indicator_value = category_data[indicator_name]
                        break
                
                # Apply improvements and normalize the value if found
                if indicator_value is not None:
                    improvement_percent = indicator_improvements.get(indicator_name, 0)
                    improved_value = indicator_value + (indicator_value * improvement_percent / 100)
                    
                    min_val = indicator_info['min_value']
                    max_val = indicator_info['max_value']
                    should_invert = indicator_name in indicators_to_invert
                    
                    normalized_value = normalize_indicator(improved_value, min_val, max_val, invert=should_invert)
                    if normalized_value is not None:
                        # Clamp to 0-100 range
                        normalized_value = max(0, min(100, normalized_value))
                        row_values.append(normalized_value)
                    else:
                        row_values.append(np.nan)
                else:
                    row_values.append(np.nan)
            else:
                row_values.append(np.nan)
        
        heatmap_matrix.append(row_values)
    
    heatmap_array = np.array(heatmap_matrix)
    
    # Create custom hover text that shows the actual indicator names
    hover_text = []
    for i in range(max_indicators):
        hover_row = []
        for pillar_key in pillar_keys:
            indicators_list = pillar_indicators[pillar_key]
            if i < len(indicators_list):
                indicator_name = indicators_list[i]['name']
                hover_row.append(indicator_name)
            else:
                hover_row.append("No indicator")
        hover_text.append(hover_row)
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_array,
        x=pillar_columns,
        y=indicator_rows,
        text=hover_text,
        colorscale=[
            [0.0, '#d32f2f'],    # Red for low values
            [0.5, '#ffc107'],    # Yellow for medium values  
            [1.0, '#4caf50']     # Green for high values
        ],
        colorbar=dict(
            title="Normalized Score<br>(0-100)<br>After Improvements"
        ),
        hoverongaps=False,
        hovertemplate='<b>%{text}</b><br>' +
                      '<b>%{x} Pillar</b><br>' +
                      'Improved Score: %{z:.1f}<br>' +
                      '<extra></extra>',
        zmin=0,
        zmax=100
    ))
    
    fig.update_layout(
        title="WEFE Indicators Evaluation Heatmap - After Policy Improvements",
        xaxis_title="WEFE Pillars",
        yaxis_title="Indicator Position",
        height=max(400, max_indicators * 30), 
        margin=dict(l=100, r=100, t=60, b=50)
    )
    
    return fig


def create_and_display_gauge_scoring(lab_info, selected_policies):
    """
    Create and display gauge charts for WEFE score comparison before and after policies
    """
    if not lab_info or 'wefe_pillars' not in lab_info:
        return None, None
    
    try:
        # Import here to avoid circular imports
        from src.core.wefe_calculations import calculate_overall_wefe_score, calculate_new_wefe_score_after_policies
        
        original_score, _ = calculate_overall_wefe_score(lab_info)
        new_score = calculate_new_wefe_score_after_policies(lab_info, selected_policies) if selected_policies else None
        
        if original_score is not None:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Original Score**")
                streamviz.gauge(
                    original_score / 100, 
                    gSize="MED", 
                    sFix="%", 
                    gcHigh="#27ae60", 
                    gcLow="#e74c3c", 
                    gcMid="#f39c12"
                )
            
            with col2:
                if new_score is not None:
                    st.markdown("**After Policies**")
                    streamviz.gauge(
                        new_score / 100, 
                        gSize="MED", 
                        sFix="%", 
                        gcHigh="#27ae60", 
                        gcLow="#e74c3c", 
                        gcMid="#f39c12"
                    )
                    
                    # improvement = new_score - original_score
                    # if improvement > 0:
                    #     st.success(f"📈 +{improvement:.1f} points")
                    # elif improvement < 0:
                    #     st.error(f"📉 {improvement:.1f} points")
                    # else:
                    #     st.info("➡️ No change")
                else:
                    st.markdown("**After Policies**")
                    st.info("Select policies to see impact")
        else:
            st.warning("Unable to calculate WEFE scores.")
        
        return original_score, new_score
        
    except Exception as e:
        st.error(f"Error displaying gauge charts: {e}")
        return None, None
