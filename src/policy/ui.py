import streamlit as st
import pandas as pd
from typing import Dict, List, Any
from src.policy.data import load_policies, parse_change_value, get_indicator_with_number


def render_synergy_tradeoff_item(item: Dict, policy_title: str, is_synergy: bool = True):
    """Render a single synergy or trade-off item using Streamlit components only."""
    title_prefix = "🟢" if is_synergy else "🔴"
    header_text = f"{title_prefix} {item.get('title', 'Item')}"

    with st.expander(header_text, expanded=False):
        st.write(item.get('description', ''))
        category = item.get('category')
        if category:
            st.caption(f"Category: {category}")

        indicators = item.get('affected_indicators')
        if indicators:
            st.markdown("**Affected indicators:**")
            for ind in indicators:
                indicator = ind.get('indicator')
                change = ind.get('expected_change')
                if indicator is not None and change is not None:
                    st.write(f"- {indicator}: {change}")


def render_policy_details(policy: Dict):
    """Render detailed view of a single policy"""
    with st.expander(f"📋 {policy['title']}", expanded=False):

        st.write(policy['description'])

        col1, col2, col3 = st.columns(3)
 
        with col1:
            st.markdown("**Implementation Details:**")
            st.write(f"• **Time:** {policy['avg_completion_time']}")
            st.write(f"• **Cost:** {policy['avg_realization_cost']}")
            st.write(f"• **Maintenance:** {policy['avg_maintenance_cost']}")
            st.write(f"• **Type:** {policy['policy_type']}")
        
        with col2:
            st.markdown("**Performance Metrics:**")
            st.write(f"• **Resilience Score:** {policy['resilience_score']}")
            st.write(f"• **Stakeholder Involvement:** {policy['stakeholder_involvement']}")
            st.write(f"• **CO2 Reduction:** {policy['co2_reduction']}")
            st.write(f"• **Biodiversity Impact:** {policy['biodiversity_impact']}")
        
        with col3:
            unique_add_key = f"add_{policy['title']}".replace(" ", "_").replace("-", "_")
            if st.button("➕ Add Policy", key=unique_add_key):
                if 'selected_policies' not in st.session_state:
                    st.session_state.selected_policies = []
                if policy['title'] not in st.session_state.selected_policies:
                    st.session_state.selected_policies.append(policy['title'])
                st.rerun()
        
        st.divider()
        
        col_syn, col_trade = st.columns(2)
        
        with col_syn:
            st.markdown("#### 🟢 Synergies")
            if 'synergies' in policy and policy['synergies']:
                for synergy in policy['synergies']:
                    render_synergy_tradeoff_item(synergy, policy['title'], is_synergy=True)
            else:
                st.info("No synergies identified for this policy.")
        
        with col_trade:
            st.markdown("#### 🔴 Trade-offs")
            if 'trade_offs' in policy and policy['trade_offs']:
                for trade_off in policy['trade_offs']:
                    render_synergy_tradeoff_item(trade_off, policy['title'], is_synergy=False)
            else:
                st.info("No trade-offs identified for this policy.")


def create_and_display_indicator_table(lab_info, selected_policy_titles):
    """Create and display the indicator table showing policy impacts on indicators"""
    all_indicator_rows: List[str] = []
    indicator_to_row: Dict[str, str] = {}
    wefe = lab_info.get('wefe_pillars', {}) or {}
    for pillar_key, pillar_obj in wefe.items():
        indicators_obj = (pillar_obj or {}).get('indicators', {}) or {}
        for category_key, indicator_group in indicators_obj.items():
            if isinstance(indicator_group, dict):
                for indicator_key in indicator_group.keys():
                    numbered_indicator = get_indicator_with_number(indicator_key)
                    row_name = f"{pillar_key} / {category_key} / {numbered_indicator}"
                    all_indicator_rows.append(row_name)
                    indicator_to_row[indicator_key] = row_name

    policies_by_title = {p['title']: p for p in load_policies()}

    if not all_indicator_rows:
        st.info("No indicators available for this living lab.")
    elif not selected_policy_titles:
        st.info("No policies selected. Add policies to populate table columns.")
    else:
        influenced_indicators: set[str] = set()
        for policy_title in selected_policy_titles:
            policy_obj = policies_by_title.get(policy_title)
            if not policy_obj:
                continue
            for coll_key in ('synergies', 'trade_offs'):
                for item in policy_obj.get(coll_key, []) or []:
                    for ind in (item.get('affected_indicators') or []):
                        indicator_key = ind.get('indicator')
                        if indicator_key and indicator_key in indicator_to_row:
                            influenced_indicators.add(indicator_key)
        
        # Filter to only include indicators that are influenced by at least one policy
        indicator_rows = [indicator_to_row[ind_key] for ind_key in influenced_indicators 
                         if ind_key in indicator_to_row]
        
        if not indicator_rows:
            st.info("No indicators are influenced by the selected policies.")
        else:
            policy_columns_with_percent = [f"{title} (%)" for title in selected_policy_titles]
            value_table = pd.DataFrame(0, index=indicator_rows, columns=policy_columns_with_percent)

            for idx, policy_title in enumerate(selected_policy_titles):
                policy_column = policy_columns_with_percent[idx]
                policy_obj = policies_by_title.get(policy_title)
                if not policy_obj:
                    continue
                for coll_key in ('synergies', 'trade_offs'):
                    for item in policy_obj.get(coll_key, []) or []:
                        for ind in (item.get('affected_indicators') or []):
                            indicator_key = ind.get('indicator')
                            change_value = parse_change_value(ind.get('expected_change'))
                            row_name = indicator_to_row.get(indicator_key)
                            if row_name is not None and row_name in value_table.index:
                                current_value = value_table.at[row_name, policy_column]
                                new_value = current_value + change_value
                                value_table.at[row_name, policy_column] = round(new_value, 2)

            # Prepare meta columns for display
            numbers_col: List[str] = []
            names_col: List[str] = []
            wefe_col: List[str] = []
            dim_col: List[str] = []
            actual_values = []
            for row_name in indicator_rows:
                parts = row_name.split(' / ')
                if len(parts) == 3:
                    pillar_key, category_key, indicator_key = parts
                    # Remove numeric prefix (e.g., "01. ") from indicator key for lookup
                    raw_indicator_key = indicator_key.split('. ', 1)[1] if '. ' in indicator_key else indicator_key
                    # Extract number and indicator name for display
                    if '. ' in indicator_key:
                        num_str, ind_name = indicator_key.split('. ', 1)
                    else:
                        num_str, ind_name = '', indicator_key
                    numbers_col.append(num_str)
                    names_col.append(ind_name)
                    # Map WEFE pillar to initials
                    pillar_map = {
                        'water': 'W',
                        'energy': 'E',
                        'food': 'F',
                        'ecosystems': 'EC'
                    }
                    wefe_col.append(pillar_map.get(pillar_key, pillar_key[:1].upper()))
                    # Map category to required codes
                    dim_map = {
                        'access': 'AC',
                        'availability': 'AV',
                        'biodiversity': 'B',
                        'ecosystem_services': 'Es'
                    }
                    dim_col.append(dim_map.get(category_key, category_key[:2].upper()))
                    try:
                        actual_value = wefe[pillar_key]['indicators'][category_key][raw_indicator_key]
                        actual_values.append(round(actual_value, 2))
                    except (KeyError, TypeError):
                        actual_values.append(0.00)
                else:
                    numbers_col.append('')
                    names_col.append('')
                    wefe_col.append('')
                    dim_col.append('')
                    actual_values.append(0.00)
            
            # Insert meta columns at the beginning
            value_table.insert(0, 'No.', numbers_col)
            value_table.insert(1, 'Indicator', names_col)
            value_table.insert(2, 'WEFE', wefe_col)
            value_table.insert(3, 'DIM', dim_col)
            # Then insert computed numeric columns
            value_table.insert(4, 'Actual Value', actual_values)
            value_table['Total Improvement (%)']  = value_table[policy_columns_with_percent].sum(axis=1)
            
            value_of_improvement = []
            for idx, actual_val in enumerate(actual_values):
                total_improvement_percent = value_table.iloc[idx]['Total Improvement (%)']
                concrete_improvement = (actual_val * total_improvement_percent) / 100
                value_of_improvement.append(round(concrete_improvement, 2))
            
            value_table['Value of Improvement'] = value_of_improvement
            
            final_states = value_table['Actual Value'] + value_table['Value of Improvement']
            value_table['Final State'] = final_states.round(2)
            
            numeric_columns = ['Actual Value', 'Total Improvement (%)', 'Value of Improvement', 'Final State'] + policy_columns_with_percent
            for col in numeric_columns:
                if col in value_table.columns:
                    value_table[col] = value_table[col].astype(float)

            # Ensure the original combined index is not displayed as a first column
            value_table = value_table.reset_index(drop=True)

            # Sort rows by WEFE category (W, E, F, EC), then by indicator number and name
            _wefe_sort_map = {'W': 0, 'E': 1, 'F': 2, 'EC': 3}
            value_table['__wefe_order'] = value_table['WEFE'].map(lambda x: _wefe_sort_map.get(x, 999))
            def _parse_num(s):
                try:
                    return int(str(s))
                except Exception:
                    return 9999
            value_table['__num_order'] = value_table['No.'].map(_parse_num)
            value_table = value_table.sort_values(by=['__wefe_order', '__num_order', 'Indicator']).reset_index(drop=True)
            value_table = value_table.drop(columns=['__wefe_order', '__num_order'])

            # Compute alternating background per WEFE category for easier scanning
            wefe_values = list(value_table['WEFE']) if 'WEFE' in value_table.columns else []
            wefe_row_bg: List[str] = []
            last_wefe = None
            toggle = False
            for w in wefe_values:
                if w != last_wefe:
                    toggle = not toggle
                    last_wefe = w
                wefe_row_bg.append('background-color: #f7f7f7' if toggle else 'background-color: #ffffff')

            def _style_cell(val, row_idx, col_name):
                try:
                    num = float(val)
                except Exception:
                    # Non-numeric cells get the base WEFE banding
                    if row_idx is not None and 0 <= row_idx < len(wefe_row_bg):
                        return wefe_row_bg[row_idx]
                    return ''

                # Do not apply numeric styling to metadata columns; use base WEFE banding
                if col_name in ['No.', 'Indicator', 'WEFE', 'DIM']:
                    if row_idx is not None and 0 <= row_idx < len(wefe_row_bg):
                        return wefe_row_bg[row_idx]
                    return ''

                if col_name == 'Actual Value':
                    return 'background-color: #f8f9fa; color: #495057'
                
                if col_name == 'Value of Improvement':
                    if num > 0:
                        return 'background-color: #e8f5e9; color: #1b5e20'
                    elif num < 0:
                        return 'background-color: #ffebee; color: #b71c1c'
                    else:
                        return 'background-color: #f8f9fa; color: #495057'
                
                # Style Final State: green if > actual value, red if < actual value
                if col_name == 'Final State':
                    if row_idx is not None:
                        try:
                            actual_val = float(value_table.iloc[row_idx]['Actual Value'])
                            if num > actual_val:
                                return 'background-color: #e8f5e9; color: #1b5e20'
                            elif num < actual_val:
                                return 'background-color: #ffebee; color: #b71c1c'
                            else:
                                return 'background-color: #f8f9fa; color: #495057'
                        except:
                            return 'background-color: #e3f2fd; color: #1565c0'
                    else:
                        return 'background-color: #e3f2fd; color: #1565c0'
                
                if num > 0:
                    return 'background-color: #e8f5e9; color: #1b5e20'
                if num < 0:
                    return 'background-color: #ffebee; color: #b71c1c'
                # Zero-change numeric cells get base WEFE banding
                if row_idx is not None and 0 <= row_idx < len(wefe_row_bg):
                    return wefe_row_bg[row_idx]
                return ''

            # Only format numeric columns; leave meta columns unformatted
            format_dict = {}
            for col in numeric_columns:
                if col in ['Actual Value', 'Value of Improvement', 'Final State']:
                    format_dict[col] = "{:.2f}"
                else:
                    format_dict[col] = "{:.2f}%"
            
            styled = value_table.style.format(format_dict)
            
            def apply_styling(df):
                styled_df = pd.DataFrame('', index=df.index, columns=df.columns)
                for row_idx in range(len(df)):
                    for col in df.columns:
                        styled_df.iloc[row_idx, styled_df.columns.get_loc(col)] = _style_cell(df.iloc[row_idx, df.columns.get_loc(col)], row_idx, col)
                return styled_df
            
            styled = styled.apply(apply_styling, axis=None)
            st.dataframe(styled, use_container_width=True, hide_index=True)


def render_selected_policies_section(selected_policies):
    """Render the selected policies section with management controls"""
    st.markdown("### Selected Policies")
    policies_by_title = {p['title']: p for p in load_policies()}
    
    if selected_policies:
        for sel_title in selected_policies:
            p = policies_by_title.get(sel_title)
            if not p:
                continue
            safe_key = sel_title.replace(" ", "_").replace("-", "_")
            row_c1, row_c2, row_c3, row_c4 = st.columns([0.55, 0.15, 0.15, 0.15])
            with row_c1:
                st.markdown(f"**{sel_title}**")
            with row_c2:
                st.button("View similar", key=f"view_sim_{safe_key}")
            with row_c3:
                st.button("View details", key=f"view_details_{safe_key}")
            with row_c4:
                if st.button("Remove", key=f"remove_sel_{safe_key}"):
                    st.session_state.selected_policies = [t for t in selected_policies if t != sel_title]
                    st.rerun()
    else:
        st.info("No policies selected yet.")


def render_display_controls(selected_policies):
    """Render the display control checkboxes"""
    col_check1, col_check2 = st.columns(2)
    
    with col_check1:
        show_original = st.checkbox("Show Original Heatmap", value=True, key="show_original_heatmap")
    
    with col_check2:
        show_table = st.checkbox(
            "Show Policy Impact Table", 
            value=bool(selected_policies), 
            disabled=not bool(selected_policies), 
            key="show_policy_table",
            help="Select policies to enable this option"
        )
    return show_original, show_table
