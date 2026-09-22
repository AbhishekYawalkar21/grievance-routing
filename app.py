"""
Streamlit Frontend - Intelligent Grievance Routing
Deploy to: https://streamlit.io/cloud
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
from grievance_router import GrievanceRouter, RoutingDecision
import plotly.graph_objects as go
import plotly.express as px
from supabase_client import SupabaseGraphClient

# ============================================================================
# HELPER FUNCTIONS (Defined early to avoid NameError)
# ============================================================================

def create_path_visualization(graph_path):
    """Create Plotly visualization of routing path"""
    if not graph_path:
        return go.Figure()

    nodes = []
    edges_x = []
    edges_y = []

    # Extract unique nodes
    for source, rel, target in graph_path:
        if source not in nodes:
            nodes.append(source)
        if target not in nodes:
            nodes.append(target)

    # Create positions
    pos = {node: (i * 2, 0 if i % 2 == 0 else -1) for i, node in enumerate(nodes)}

    # Create edges
    for source, rel, target in graph_path:
        x0, y0 = pos[source]
        x1, y1 = pos[target]

        edges_x.extend([x0, x1, None])
        edges_y.extend([y0, y1, None])

    # Create figure
    fig = go.Figure()

    # Add edges
    fig.add_trace(
        go.Scatter(
            x=edges_x,
            y=edges_y,
            mode="lines",
            line=dict(width=2, color="#1f77b4"),
            hoverinfo="none",
            showlegend=False,
        )
    )

    # Add nodes
    node_x = [pos[node][0] for node in nodes]
    node_y = [pos[node][1] for node in nodes]

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=nodes,
            textposition="top center",
            hoverinfo="text",
            marker=dict(
                size=20, color="#1f77b4", line=dict(width=2, color="white")
            ),
            showlegend=False,
        )
    )

    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        margin=dict(b=0, l=0, r=0, t=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )

    return fig


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Grievance Routing Engine",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .routing-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    .critical-box {
        background-color: #f8d7da;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "router" not in st.session_state:
    try:
        st.session_state.router = GrievanceRouter()
        st.session_state.db = SupabaseGraphClient()
    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {str(e)}")
        st.stop()

if "routing_history" not in st.session_state:
    st.session_state.routing_history = []

if "last_decision" not in st.session_state:
    st.session_state.last_decision = None

# ============================================================================
# HEADER & NAVIGATION
# ============================================================================

st.title("⚖️ Intelligent Government Grievance Routing")
st.markdown("""
This system uses a **Knowledge Graph** to intelligently route citizen grievances 
to the correct government department. Built on Supabase + Streamlit.

**No local setup needed. Completely free to use.**
""")

# Sidebar Navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select Page:",
        [
            "🏠 Route Grievance",
            "📊 Analytics",
            "📚 Knowledge Graph",
            "📋 History",
            "ℹ️ About",
        ],
    )

    st.divider()
    st.caption("v1.0 - Knowledge Graph Edition")

# ============================================================================
# PAGE 1: ROUTE GRIEVANCE
# ============================================================================

if page == "🏠 Route Grievance":

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Submit Your Grievance")
        st.markdown(
            "Describe your issue. Our Knowledge Graph will analyze it and route to the right authority."
        )

    with col2:
        st.subheader("Quick Templates")
        preset = st.selectbox(
            "Or use a template:",
            [
                "Custom",
                "PM-Kisan Payment Delayed",
                "Aadhaar Mismatch",
                "Bank Account Linking Failed",
                "Payment Rejected",
            ],
        )

    # Grievance input
    grievance_text = st.text_area(
        "Describe your grievance:",
        height=150,
        placeholder="""Example: My PM-Kisan payment has not come because my identity detail
name doesn't match my bank account. The bank says to contact the identity authority, 
and they say to contact the bank. I'm not receiving any money.""",
        key="grievance_input",
    )

    # Apply preset template
    if preset != "Custom" and not grievance_text:
        templates = {
            "PM-Kisan Payment Delayed": "I have not received my PM-Kisan payment for the last 3 months. My application was approved but the payment is stuck in DBT system.",
            "Aadhaar Mismatch": "My identity record name is 'Rajesh Kumar Singh' but my bank account has 'R K Singh'. The payment system is rejecting my PM-Kisan payments due to this mismatch.",
            "Bank Account Linking Failed": "I linked my identity card to my bank account but the DBT system still says my account is not verified. I cannot receive my PM-Kisan payment.",
            "Payment Rejected": "My PM-Kisan payment was rejected by the bank. The error message says 'Beneficiary verification failed' but I don't know what to do.",
        }
        grievance_text = templates.get(preset, "")

    # Metadata
    col1, col2, col3 = st.columns(3)

    with col1:
        applicant_name = st.text_input(
            "Your Name (Optional)", key="name_input"
        )

    with col2:
        state = st.selectbox(
            "State",
            [
                "Select",
                "Uttar Pradesh",
                "Maharashtra",
                "Bihar",
                "Punjab",
                "Madhya Pradesh",
                "Other",
            ],
            key="state_select",
        )

    with col3:
        st.write("")  # Spacing

    # Submit button
    if st.button(
        "🚀 Analyze & Route", key="submit_btn", use_container_width=True
    ):

        if not grievance_text.strip():
            st.error("❌ Please enter your grievance")
        else:
            with st.spinner(
                "🔍 Analyzing grievance using Knowledge Graph..."
            ):
                try:
                    # Route the grievance
                    routing_decision = (
                        st.session_state.router.route_grievance(
                            grievance_text
                        )
                    )

                    # Store in session
                    st.session_state.last_decision = routing_decision
                    st.session_state.routing_history.append({
                        "timestamp": datetime.now(),
                        "grievance": grievance_text[:100],
                        "owner": routing_decision.primary_owner,
                        "confidence": routing_decision.confidence_score,
                        "full_decision": routing_decision,
                    })
                    try:
                        st.session_state.db.log_grievance(
                            grievance_text=grievance_text,
                            owner_dept_id=routing_decision.primary_owner,
                            confidence=routing_decision.confidence_score,
                            failure_types=routing_decision.failure_types if hasattr(routing_decision, 'failure_types') else [],
                            explanation=routing_decision.explanation if hasattr(routing_decision, 'explanation') else ""
                        )
                        st.toast("✅ Saved to database audit log!")
                    except Exception as log_err:
                        st.warning(f"⚠️ Could not save audit log to Supabase: {log_err}")

                    st.success("✅ Routing analysis complete!")

                    # ============================================================
                    # MAIN RESULT CARD
                    # ============================================================

                    st.markdown(
                        f"""
                    <div class="success-box">
                    <h3>🎯 Primary Owner (Department)</h3>
                    <h2>{routing_decision.primary_owner}</h2>
                    <p><strong>Confidence Score:</strong> {routing_decision.confidence_score:.1%}</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    # ============================================================
                    # TABBED INTERFACE
                    # ============================================================

                    tab1, tab2, tab3, tab4, tab5 = st.tabs([
                        "🔍 Root Causes",
                        "✅ Resolution Paths",
                        "📈 Graph Path",
                        "🗣️ Full Explanation",
                        "📋 Details",
                    ])

                    # TAB 1: Root Causes
                    with tab1:
                        st.subheader("Identified Failure Types")
                        if routing_decision.failure_types:
                            for i, failure in enumerate(
                                routing_decision.failure_types, 1
                            ):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"**{i}. {failure}**")
                                with col2:
                                    if i == 1:
                                        st.markdown("`Primary`")
                        else:
                            st.info("No specific failures identified")

                    # TAB 2: Resolution Paths
                    with tab2:
                        st.subheader("Recommended Resolution Steps")

                        if routing_decision.resolution_paths:
                            for i, resolution in enumerate(
                                routing_decision.resolution_paths, 1
                            ):
                                with st.expander(
                                    f"Step {i}: {resolution['name']}"
                                ):
                                    col1, col2, col3 = st.columns(3)

                                    with col1:
                                        st.metric(
                                            "Authority",
                                            resolution["authority"],
                                            delta=None,
                                        )

                                    with col2:
                                        st.metric(
                                            "Time",
                                            resolution["timeToResolve"],
                                            delta=None,
                                        )

                                    with col3:
                                        st.metric(
                                            "Steps",
                                            resolution["steps"],
                                            delta=None,
                                        )
                        else:
                            st.info("No resolution paths found")

                    # TAB 3: Graph Path
                    with tab3:
                        st.subheader("Why was this routed here?")
                        st.markdown(
                            "**Knowledge Graph Reasoning Chain:**"
                        )

                        if routing_decision.graph_path:
                            # Show path as text
                            path_text = ""
                            for (
                                source,
                                relationship,
                                target,
                            ) in routing_decision.graph_path:
                                path_text += f"{source}\n  ↓ [{relationship}]\n{target}\n\n"

                            st.code(path_text, language="text")

                            # Visualize path
                            fig = create_path_visualization(
                                routing_decision.graph_path
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info(
                                "Graph path construction in progress..."
                            )

                    # TAB 4: Full Explanation
                    with tab4:
                        st.markdown(routing_decision.explanation)

                    # TAB 5: Details
                    with tab5:
                        st.subheader("Appeal Authorities")

                        if routing_decision.appeal_authorities:
                            auth_data = []
                            for (
                                auth
                            ) in routing_decision.appeal_authorities:
                                auth_data.append({
                                    "Authority": auth["name"],
                                    "Level": auth["level"],
                                    "Contact": auth.get("contact", "N/A"),
                                })

                            st.dataframe(
                                pd.DataFrame(auth_data),
                                use_container_width=True,
                            )

                        st.divider()
                        st.subheader("Raw Routing Data")
                        st.json({
                            "owner": routing_decision.primary_owner,
                            "confidence": routing_decision.confidence_score,
                            "failures": routing_decision.failure_types,
                            "resolutions_count": len(
                                routing_decision.resolution_paths
                            ),
                        })

                    # ============================================================
                    # ACTION BUTTONS
                    # ============================================================

                    st.divider()
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button(
                            "📧 Email to Department",
                            use_container_width=True,
                        ):
                            st.success("✅ Email sent to department!")

                    with col2:
                        ticket_id = f"GR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        if st.button(
                            "🔗 Generate Ticket", use_container_width=True
                        ):
                            st.info(f"📋 Ticket ID: `{ticket_id}`")

                    with col3:
                        if st.button(
                            "📥 Download Report", use_container_width=True
                        ):
                            report_data = {
                                "grievance": grievance_text,
                                "owner": routing_decision.primary_owner,
                                "confidence": routing_decision.confidence_score,
                                "failures": routing_decision.failure_types,
                                "timestamp": datetime.now().isoformat(),
                            }
                            st.download_button(
                                label="Download JSON",
                                data=json.dumps(report_data, indent=2),
                                file_name=f"grievance_{ticket_id}.json",
                                mime="application/json",
                            )

                except Exception as e:
                    st.error(f"❌ Routing failed: {str(e)}")
                    st.exception(e)

# ============================================================================
# PAGE 2: ANALYTICS
# ============================================================================

elif page == "📊 Analytics":

    st.header("System Analytics & Dashboard")

    # Get data from database
    audit_summary = st.session_state.db.get_audit_summary()

    if audit_summary["total"] == 0:
        st.info(
            "No grievances routed yet. Go to 'Route Grievance' page to get started!"
        )
    else:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Grievances Routed", audit_summary["total"])

        with col2:
            st.metric(
                "Average Confidence",
                f"{audit_summary['avg_confidence']:.1%}",
            )

        with col3:
            st.metric(
                "Departments Involved", len(audit_summary["by_department"])
            )

        with col4:
            st.metric(
                "Failure Types", len(audit_summary["by_failure_type"])
            )

        st.divider()

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            if audit_summary["by_department"]:
                dept_counts = {}
                # Get department names
                for dept_id in audit_summary["by_department"].keys():
                    dept_counts[f"Dept {dept_id}"] = audit_summary[
                        "by_department"
                    ][dept_id]

                fig = px.pie(
                    values=list(dept_counts.values()),
                    names=list(dept_counts.keys()),
                    title="Grievances by Department",
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            if audit_summary["by_failure_type"]:
                failure_counts = audit_summary["by_failure_type"]

                fig = px.bar(
                    x=list(failure_counts.keys()),
                    y=list(failure_counts.values()),
                    title="Grievances by Failure Type",
                    labels={"x": "Failure Type", "y": "Count"},
                )
                st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# PAGE 3: KNOWLEDGE GRAPH
# ============================================================================

elif page == "📚 Knowledge Graph":

    st.header("Knowledge Graph Explorer")

    st.markdown("""
    This is the semantic knowledge graph that powers intelligent routing.
    It contains relationships between schemes, departments, services, failure types, and resolutions.
    """)

    # Get all schemes
    all_schemes = st.session_state.db.get_all_schemes()

    if all_schemes:
        st.subheader("Available Schemes")
        scheme_data = []
        for scheme in all_schemes:
            scheme_data.append({
                "Scheme": scheme["name"],
                "Description": (
                    scheme["description"][:60] + "..."
                    if scheme["description"]
                    else "N/A"
                ),
            })
        st.dataframe(pd.DataFrame(scheme_data), use_container_width=True)

        st.divider()

        # Explore individual scheme
        selected_scheme = st.selectbox(
            "Explore Scheme Dependencies:", [s["name"] for s in all_schemes]
        )

        if selected_scheme:
            scheme = next(
                (s for s in all_schemes if s["name"] == selected_scheme),
                None,
            )
            if scheme:
                col1, col2, col3 = st.columns(3)

                with col1:
                    services = st.session_state.db.get_services_by_scheme(
                        scheme["id"]
                    )
                    st.metric(
                        "Services Used", len(services) if services else 0
                    )

                with col2:
                    all_failures = (
                        st.session_state.db.get_all_failure_types()
                    )
                    st.metric(
                        "Possible Failures",
                        len(all_failures) if all_failures else 0,
                    )

                with col3:
                    all_authorities = (
                        st.session_state.db.client.table(
                            "appeal_authorities"
                        )
                        .select("*")
                        .execute()
                    )
                    st.metric(
                        "Appeal Authorities",
                        len(all_authorities.data)
                        if all_authorities.data
                        else 0,
                    )

                st.markdown(f"**Description:** {scheme['description']}")
    else:
        st.info("No schemes found in knowledge graph")

# ============================================================================
# PAGE 4: HISTORY
# ============================================================================

elif page == "📋 History":

    st.header("Routing History & Audit Log")

    # Get audit history from database
    audit_history = st.session_state.db.get_audit_history(limit=50)

    if not audit_history:
        st.info("No grievances routed yet.")
    else:
        # Display history
        st.subheader(f"Recent Grievances ({len(audit_history)})")

        for i, audit in enumerate(reversed(audit_history), 1):
            with st.expander(
                f"#{i} - {audit['submitted_at'][:10]} | Score: {audit['confidence_score']:.1%}"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(
                        f"**Grievance:** {audit['grievance_text'][:200]}..."
                    )
                    st.write(
                        f"**Department:** {audit['owner_department_id']}"
                    )

                with col2:
                    st.write(
                        f"**Confidence:** {audit['confidence_score']:.1%}"
                    )
                    if audit["failure_types"]:
                        st.write("**Failures:**")
                        for failure in audit["failure_types"]:
                            st.write(f"  - {failure}")

        # Export options
        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📥 Export as CSV", use_container_width=True):
                export_df = pd.DataFrame(audit_history)
                st.download_button(
                    "Download CSV",
                    export_df.to_csv(index=False),
                    "audit_history.csv",
                    "text/csv",
                )

        with col2:
            if st.button("📊 Export as JSON", use_container_width=True):
                st.download_button(
                    "Download JSON",
                    json.dumps(audit_history, indent=2, default=str),
                    "audit_history.json",
                    "application/json",
                )

# ============================================================================
# PAGE 5: ABOUT
# ============================================================================

elif page == "ℹ️ About":

    st.header("About This System")

    st.markdown("""
    ### What is this?
    
    An **intelligent grievance routing system** that uses a **Knowledge Graph** to analyze 
    citizen complaints and route them to the correct government department.
    
    ### Key Features
    
    ✅ **Knowledge Graph-Based**: Uses PostgreSQL (Supabase) to store semantic relationships
    
    ✅ **Explainable Routing**: Shows the exact reasoning path for every decision
    
    ✅ **Multi-level Authority**: Routes to correct department + provides appeal path
    
    ✅ **Audit Trail**: Complete logging of all routing decisions
    
    ✅ **Zero Cost**: Completely free using Supabase free tier
    
    ### How It Works
    
    1. **Input**: Citizen writes grievance in natural language
    2. **Analysis**: System extracts entities (scheme, service, failure type)
    3. **Graph Query**: Knowledge graph finds semantic relationships
    4. **Routing**: Identifies correct department and resolution path
    5. **Explanation**: Shows WHY the decision was made (the killer feature)
    
    ### Technology Stack
    
    - **Frontend**: Streamlit (deployed on Streamlit Cloud - FREE)
    - **Database**: Supabase (PostgreSQL - FREE tier)
    - **Knowledge Graph**: SQL queries on relational schema
    - **Backend**: Python
    
    ### Total Cost
    
    **$0 - Completely Free**
    
    - Streamlit Cloud: Free
    - Supabase: Free tier
    - GitHub: Free public repo
    
    ### Limitations
    
    - Supabase free tier pauses after 7 days of inactivity (use GitHub Actions to auto-wake)
    - Database limited to 500 MB (sufficient for MVP)
    - Limited to 2 active projects on free tier
    
    ---
    
    **Built for FDE (Frontend Data Engineering) Interview Preparation**
    
    This project demonstrates:
    - Knowledge graph design and implementation
    - Semantic routing with explainability
    - SQL schema design for relationships
    - End-to-end full stack application
    
    """)

    with st.expander("📚 Learn More"):
        st.markdown("""
        - [Supabase Documentation](https://supabase.com/docs)
        - [Streamlit Docs](https://docs.streamlit.io)
        - [Knowledge Graphs](https://en.wikipedia.org/wiki/Knowledge_graph)
        """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
---
**Intelligent Grievance Routing System** | Zero-Cost Knowledge Graph Edition
Powered by Supabase + Streamlit | Built for Government Domain
""")