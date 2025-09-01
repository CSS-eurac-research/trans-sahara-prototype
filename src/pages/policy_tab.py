import streamlit as st
import os
from src.pages.initial_page import get_selected_lab_info
from src.policy.data import get_policy_categories, get_policies_by_category, load_policies, get_all_indicators_with_numbers, get_policies_by_indicator, get_indicator_numbering
from src.policy.visualization import create_indicators_heatmap, create_improved_indicators_heatmap, create_and_display_gauge_scoring
from src.policy.ui import (
    render_policy_details, 
    create_and_display_indicator_table, 
    render_selected_policies_section,
    render_display_controls
)
from src.core.intervention_optimizer import run_policy_simulation


def render_policy_tab():
    """Main function to render the entire policy tab"""
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"Policy View - {st.session_state.selected_lab}")
        
        policies = load_policies()
        if not policies:
            st.error("No policies available!")
            return
        
        # Add checkbox for search by indicator
        search_by_indicator = st.checkbox("🔍 Search by Indicator", key="search_by_indicator_checkbox")
        
        if search_by_indicator:
            # Show indicator selection instead of category selection
            all_indicators_with_numbers = get_all_indicators_with_numbers()
            indicator_numbering = get_indicator_numbering()
            
            selected_indicator_with_number = st.selectbox(
                "Select Indicator to Search:",
                all_indicators_with_numbers,
                key="indicator_select",
                help="Select an indicator to find policies that improve it"
            )
            
            if selected_indicator_with_number:
                # Extract the actual indicator key from the numbered display
                selected_indicator = selected_indicator_with_number.split('. ', 1)[1] if '. ' in selected_indicator_with_number else selected_indicator_with_number
                
                # Get policies that improve the selected indicator
                improving_policies = get_policies_by_indicator(policies, selected_indicator)
                
                if improving_policies:
                    st.success(f"Found {len(improving_policies)} policies that improve '{selected_indicator_with_number}' (sorted by improvement magnitude, largest to smallest)")
                    
                    # Get improvement details for display
                    improvement_details = []
                    for policy in improving_policies:
                        for synergy in policy.get('synergies', []):
                            for affected_ind in synergy.get('affected_indicators', []):
                                if affected_ind.get('indicator') == selected_indicator:
                                    improvement_details.append({
                                        'policy': policy,
                                        'expected_change': affected_ind.get('expected_change'),
                                        'description': synergy.get('title', '')
                                    })
                                    break
                            else:
                                continue
                            break
                    
                    # Display policies with improvement information
                    for detail in improvement_details:
                        with st.expander(f"📈 {detail['policy']['title']} - Improvement: {detail['expected_change']}"):
                            render_policy_details(detail['policy'])
                            st.info(f"**Improvement to {selected_indicator_with_number}**: {detail['expected_change']}")
                            if detail['description']:
                                st.caption(f"**Synergy**: {detail['description']}")
                else:
                    st.info(f"No policies found that improve the '{selected_indicator_with_number}' indicator.")
            else:
                st.info("Please select an indicator to search for improving policies.")
        else:
            # Original category-based filtering
            categories = get_policy_categories(policies)
            selected_category = st.selectbox(
                "Select Policy Category:",
                categories,
                key="policy_category_select"
            )
            if selected_category:
                category_policies = get_policies_by_category(policies, selected_category)
                if category_policies:                
                    for policy in category_policies:
                        render_policy_details(policy)
                else:
                    st.info(f"No policies found in the {selected_category} category.")
            else:
                st.info("Please select a policy category to view available policies.")
            
        selected_policies = st.session_state.get('selected_policies', [])
        render_selected_policies_section(selected_policies)
        if selected_policies:
            if st.button("🚀 Run Policy Simulation", key="run_policy_simulation_btn"):
                policies_by_title = {p['title']: p for p in load_policies()}
                selected_policy_objs = [policies_by_title[t] for t in selected_policies if t in policies_by_title]
                base_dir = os.path.dirname(__file__)
                result = run_policy_simulation(base_dir, selected_policy_objs)
                st.session_state["policy_simulation_result"] = result
                # Prepare a simple list to surface on the interventions tab
                st.session_state["active_interventions"] = [iv['title'] for iv in result.get('selected_interventions', [])]
                st.success("Simulation completed. Navigate to the Intervention tab to view recommended interventions.")
            
    with col2:
        selected_lab_name = st.session_state.get('selected_lab')
        lab_info = get_selected_lab_info(selected_lab_name) if selected_lab_name else None
        if lab_info and 'wefe_pillars' in lab_info:
            selected_policies = st.session_state.get('selected_policies', [])
            
            show_heatmaps, show_table = render_display_controls(selected_policies)
            
            st.markdown("---")
            st.subheader("WEFE Score Comparison")
            create_and_display_gauge_scoring(lab_info, selected_policies)

            if show_heatmaps:
                
                heatmap_col1, heatmap_col2 = st.columns(2)
                
                with heatmap_col1:
                    heatmap_fig = create_indicators_heatmap(lab_info)
                    if heatmap_fig:
                        st.plotly_chart(heatmap_fig, use_container_width=True)
                    else:
                        st.info("Original heatmap data not available.")
                
                with heatmap_col2:
                    if selected_policies:
                        improved_heatmap_fig = create_improved_indicators_heatmap(lab_info, selected_policies)
                        if improved_heatmap_fig:
                            st.plotly_chart(improved_heatmap_fig, use_container_width=True)
                        else:
                            st.info("Unable to generate improved heatmap.")
                    else:
                        st.markdown("**After Policy Improvements**")
                        st.info("Select policies to see improvements")
            
            if show_table:
                create_and_display_indicator_table(lab_info, selected_policies)            
        else:
            st.info("WEFE scores not available for the selected living lab.")