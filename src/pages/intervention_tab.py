import streamlit as st
import pandas as pd
import random
from src.core.data_loader import get_map_data

def render_intervention_tab():
    """Render the intervention management interface"""
    st.title("Intervention Management")
    sim_result = st.session_state.get("policy_simulation_result")
    if sim_result:
        st.markdown("### Recommended interventions (from policy simulation)")
        selected = sim_result.get('selected_interventions', [])
        if selected:
            df = pd.DataFrame([
                {
                    "Title": iv.get('title'),
                    "CAPEX (USD)": iv.get('capex_usd'),
                    "Contributing indicators": ", ".join(sorted(list(iv.get('indicators', {}).keys())))
                }
                for iv in selected
            ])
            st.dataframe(df, use_container_width=True)

            st.markdown("#### Coverage summary vs. policy targets")
            coverage = sim_result.get('coverage', {})
            unmet = sim_result.get('unmet', {})
            if coverage:
                cov_rows = []
                for k in sorted(coverage.keys()):
                    cov_rows.append({
                        "Indicator": k,
                        "Covered change": round(float(coverage.get(k, 0.0)), 2),
                        "Unmet": round(float(unmet.get(k, 0.0)), 2)
                    })
                cov_df = pd.DataFrame(cov_rows)
                st.dataframe(cov_df, use_container_width=True)

            st.info(f"Total CAPEX (USD): {int(sim_result.get('total_capex_usd', 0)):,}")
        else:
            st.warning("No suitable combination of interventions found to meet targets.")
    else:
        st.caption("Run a policy simulation from the Policy tab to see recommendations here.")