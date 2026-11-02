import os
import sys
import json
import time
import asyncio
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.config import settings
from core.database import (
    init_db,
    SessionLocal,
    get_application,
    list_applications_records,
    get_audit_logs,
    get_dashboard_metrics,
    ApplicationModel
)
from core.schemas import LoanApplicationInput
from core.policies import FinalDecisionEnum
from tools.emi_calculator import compute_emi
from tools.sample_pdf_generator import generate_sample_application_pdf
from agents.underwriting_manager import UnderwritingManager

# Initialize Database on startup
init_db()

# Streamlit Page Configuration
st.set_page_config(
    page_title="FinCore AI | Autonomous Multi-Agent Underwriting Swarm",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------------------------------------------
# ADVANCED FINTECH DESIGN SYSTEM & DYNAMIC CSS ANIMATIONS
# -------------------------------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg-primary: #070913;
    --card-bg: rgba(15, 23, 42, 0.75);
    --card-border: rgba(255, 255, 255, 0.08);
    --accent-indigo: #6366f1;
    --accent-cyan: #06b6d4;
    --accent-emerald: #10b981;
    --accent-rose: #f43f5e;
    --accent-amber: #f59e0b;
    --glow-indigo: rgba(99, 102, 241, 0.25);
}

/* Global Font & Fluid Background */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    color: #e2e8f0;
}

h1, h2, h3, h4, .brand-title {
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.5px;
}

.stApp {
    background: radial-gradient(circle at 15% 15%, #0f172a 0%, #070913 70%);
    background-attachment: fixed;
}

/* Shimmer & Glow Keyframes */
@keyframes fluidShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes pulseGlow {
    0%, 100% {
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.3), inset 0 0 15px rgba(99, 102, 241, 0.15);
    }
    50% {
        box-shadow: 0 0 30px rgba(99, 102, 241, 0.6), inset 0 0 25px rgba(99, 102, 241, 0.3);
    }
}

@keyframes floatSlow {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-5px); }
}

@keyframes radarPing {
    0% { transform: scale(0.95); opacity: 0.8; }
    50% { transform: scale(1.15); opacity: 0.4; }
    100% { transform: scale(0.95); opacity: 0.8; }
}

@keyframes textShine {
    0% { background-position: 0% 50%; }
    100% { background-position: 100% 50%; }
}

/* Hero Banner Component */
.hero-banner {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 30px 36px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(16px);
    box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
}

.hero-banner::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 200%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.15), transparent);
    animation: textShine 6s infinite linear;
    pointer-events: none;
}

.hero-title {
    font-size: 34px;
    font-weight: 800;
    background: linear-gradient(120deg, #ffffff 0%, #cbd5e1 40%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}

.live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.4);
    padding: 4px 12px;
    border-radius: 30px;
    font-size: 11px;
    font-weight: 700;
    color: #34d399;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.live-dot {
    width: 8px;
    height: 8px;
    background: #34d399;
    border-radius: 50%;
    box-shadow: 0 0 10px #34d399;
    animation: radarPing 2s infinite ease-in-out;
}

/* Glassmorphic Cards */
.fintech-card {
    background: rgba(15, 23, 42, 0.72);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 20px;
    backdrop-filter: blur(14px);
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.fintech-card:hover {
    transform: translateY(-4px) scale(1.005);
    border-color: rgba(99, 102, 241, 0.4);
    box-shadow: 0 20px 40px -10px rgba(99, 102, 241, 0.25);
}

/* Interactive Metric Boxes */
.metric-tile {
    background: linear-gradient(145deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 16px;
    padding: 18px 20px;
    text-align: center;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}

.metric-tile:hover {
    transform: translateY(-3px);
    border-color: rgba(129, 140, 248, 0.5);
    box-shadow: 0 12px 28px -8px rgba(99, 102, 241, 0.3);
}

.metric-tile-value {
    font-family: 'Outfit', sans-serif;
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #ffffff;
}

.metric-tile-label {
    font-size: 11px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-top: 6px;
}

/* Animated Decision Badges */
.badge-sanction {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.35) 100%);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.5);
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
    padding: 8px 18px;
    border-radius: 30px;
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 14px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 1px;
}

.badge-decline {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.35) 100%);
    color: #f87171;
    border: 1px solid rgba(248, 113, 113, 0.5);
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
    padding: 8px 18px;
    border-radius: 30px;
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 14px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 1px;
}

.badge-refer {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(217, 119, 6, 0.35) 100%);
    color: #fbbf24;
    border: 1px solid rgba(251, 191, 36, 0.5);
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
    padding: 8px 18px;
    border-radius: 30px;
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 14px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 1px;
}

/* Agent Swarm Pipeline Visualizer */
.pipeline-flow {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    margin: 20px 0;
}

.pipeline-node {
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 14px;
    text-align: center;
    transition: all 0.3s ease;
    position: relative;
}

.pipeline-node.active-node {
    border-color: #818cf8;
    box-shadow: 0 0 25px rgba(99, 102, 241, 0.4);
    transform: translateY(-2px);
}

.node-icon {
    font-size: 24px;
    margin-bottom: 6px;
    display: block;
}

.node-name {
    font-size: 12px;
    font-weight: 700;
    color: #cbd5e1;
    margin: 0;
}

.node-status {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    margin-top: 6px;
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
}

/* Counter-Offer Spotlight Box */
.counter-spotlight {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.2) 100%);
    border: 1px solid rgba(167, 139, 250, 0.4);
    box-shadow: 0 10px 30px rgba(124, 58, 237, 0.25);
    border-radius: 18px;
    padding: 24px;
    margin-top: 16px;
    position: relative;
    overflow: hidden;
}

.counter-spotlight::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 150px; height: 150px;
    background: radial-gradient(circle, rgba(167, 139, 250, 0.3) 0%, transparent 70%);
    pointer-events: none;
}

/* Streamlit Native Widget Enhancements */
div[data-testid="stForm"] {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 28px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
}

.stButton>button {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 24px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 8px 20px -4px rgba(79, 70, 229, 0.5) !important;
}

.stButton>button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 28px -4px rgba(79, 70, 229, 0.7) !important;
}

code, pre {
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 10px !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Initialize Orchestration Manager
@st.cache_resource
def get_manager():
    return UnderwritingManager()


manager = get_manager()


def run_async(coro):
    """Run an async coroutine inside the Streamlit event loop."""
    return asyncio.run(coro)


# Helper: Render Circular Speedometer FOIR Gauge with Plotly
def render_foir_gauge(foir_val: float, max_foir: float = 40.0):
    val = min(max(foir_val, 0.0), 100.0) if foir_val is not None else 0.0

    bar_color = "#10b981" if val <= max_foir else ("#f59e0b" if val <= 50.0 else "#f43f5e")

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=val,
        number={"suffix": "%", "font": {"family": "Outfit", "size": 36, "color": "#ffffff"}},
        delta={"reference": max_foir, "increasing": {"color": "#f43f5e"}, "decreasing": {"color": "#10b981"}, "suffix": "% vs limit"},
        title={"text": f"<b>Fixed Obligation to Income Ratio (FOIR)</b><br><span style='font-size:12px;color:#94a3b8'>Institutional Limit: {max_foir}%</span>", "font": {"family": "Plus Jakarta Sans", "size": 14, "color": "#cbd5e1"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#475569"},
            "bar": {"color": bar_color, "thickness": 0.3},
            "bgcolor": "rgba(15, 23, 42, 0.5)",
            "borderwidth": 1,
            "bordercolor": "rgba(255, 255, 255, 0.1)",
            "steps": [
                {"range": [0, max_foir], "color": "rgba(16, 185, 129, 0.15)"},
                {"range": [max_foir, 50], "color": "rgba(245, 158, 11, 0.15)"},
                {"range": [50, 100], "color": "rgba(244, 63, 94, 0.15)"}
            ],
            "threshold": {
                "line": {"color": "#ef4444", "width": 3},
                "thickness": 0.85,
                "value": max_foir
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=50, b=20),
        height=240
    )
    return fig


# Helper: Render Donut Chart for Portfolio Decision Distribution
def render_decision_donut(sanctioned: int, declined: int, referred: int):
    labels = ["Sanctioned", "Declined", "Referred"]
    values = [sanctioned, declined, referred]
    colors = ["#10b981", "#f43f5e", "#f59e0b"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        marker=dict(colors=colors, line=dict(color="#0f172a", width=2)),
        textinfo="label+percent",
        textfont=dict(family="Plus Jakarta Sans", size=13, color="#ffffff"),
        hoverinfo="label+value+percent",
        showlegend=False
    )])

    total = sum(values)
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:12px;color:#94a3b8'>Total Apps</span>",
        x=0.5, y=0.5,
        font=dict(family="Outfit", size=24, color="#ffffff"),
        showarrow=False
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=260
    )
    return fig


# -------------------------------------------------------------------------------------------------
# SIDEBAR NAVIGATION & SYSTEM BADGE
# -------------------------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px 0 16px 0;">
        <span style="font-size: 38px;">⚡</span>
        <h2 class="brand-title" style="margin: 0; font-size: 24px; color: #ffffff;">FinCore AI</h2>
        <span style="font-size: 11px; color: #818cf8; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">
            Multi-Agent Swarm Underwriter
        </span>
    </div>
    """, unsafe_allow_html=True)

    menu_selection = st.radio(
        "Navigation",
        [
            "📊 Executive Dashboard",
            "📝 New Loan Intake",
            "🤖 Agent Monitoring",
            "🧮 EMI Amortization Tool",
            "📜 Underwriting Results",
            "🗄️ Application History",
            "🎬 Interactive Presentation Deck"
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("""
    <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px;">
        <div style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">SWARM ARCHITECTURE</div>
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.6;">
            • Framework: <b>Semantic Kernel</b><br>
            • Mode: <b>Manager-Worker Swarm</b><br>
            • Policy Ceiling: <b>FOIR &le; 40.0%</b><br>
            • Security: <b>Injection Sanitized</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⚡ Seed 5 Demo Personas", use_container_width=True, help="Populate verified institutional cases"):
        with st.spinner("Seeding institutional applications..."):
            from main import seed_demo_cases
            db = SessionLocal()
            try:
                res = run_async(seed_demo_cases(db))
                st.toast("✅ Successfully populated and evaluated 5 standard test cases!", icon="🎉")
                time.sleep(0.5)
                st.rerun()
            finally:
                db.close()


# -------------------------------------------------------------------------------------------------
# PAGE 1: EXECUTIVE DASHBOARD
# -------------------------------------------------------------------------------------------------
if menu_selection == "📊 Executive Dashboard":
    # Hero Banner
    st.markdown("""
    <div class="hero-banner">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 14px;">
            <div>
                <div class="live-indicator">
                    <span class="live-dot"></span> Autonomous Swarm Active
                </div>
                <h1 class="hero-title" style="margin-top: 10px;">Credit Underwriting Operations Center</h1>
                <p style="color: #94a3b8; font-size: 14px; margin: 6px 0 0 0;">
                    Real-time monitoring of institutional credit volume, automated risk scoring, and counter-offer restructuring.
                </p>
            </div>
            <div style="text-align: right;">
                <span style="font-family: 'JetBrains Mono'; font-size: 12px; color: #818cf8;">REGULATORY FOIR: 40.0%</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    db = SessionLocal()
    metrics = get_dashboard_metrics(db)
    apps = list_applications_records(db, limit=100)
    db.close()

    # Dynamic KPI Metrics Grid
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""
        <div class="metric-tile">
            <div class="metric-tile-value">{metrics['total_applications']}</div>
            <div class="metric-tile-label">Total Applications</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-tile" style="border-top: 2px solid #10b981;">
            <div class="metric-tile-value" style="color: #34d399;">{metrics['sanctioned_count']}</div>
            <div class="metric-tile-label">Sanctioned</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-tile" style="border-top: 2px solid #f43f5e;">
            <div class="metric-tile-value" style="color: #f87171;">{metrics['declined_count']}</div>
            <div class="metric-tile-label">Declined</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-tile" style="border-top: 2px solid #f59e0b;">
            <div class="metric-tile-value" style="color: #fbbf24;">{metrics['referred_count']}</div>
            <div class="metric-tile-label">Referred</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="metric-tile">
            <div class="metric-tile-value" style="font-size: 26px;">₹{metrics['average_loan_amount']:,.0f}</div>
            <div class="metric-tile-label">Average Loan Size</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="metric-tile" style="border-top: 2px solid #6366f1;">
            <div class="metric-tile-value" style="color: #818cf8;">{metrics['approval_rate']:.1f}%</div>
            <div class="metric-tile-label">Approval Ratio</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts & Interactive Breakdown Row
    col_chart, col_swarm = st.columns([1, 1])

    with col_chart:
        st.markdown("### Portfolio Decision Distribution")
        if metrics["total_applications"] > 0:
            donut_fig = render_decision_donut(
                sanctioned=metrics["sanctioned_count"],
                declined=metrics["declined_count"],
                referred=metrics["referred_count"]
            )
            st.plotly_chart(donut_fig, use_container_width=True)
        else:
            st.info("No applications evaluated yet. Click '⚡ Seed 5 Demo Personas' in sidebar.")

    with col_swarm:
        st.markdown("### Active Autonomous Agents")
        st.markdown("""
        <div class="fintech-card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <span style="font-weight: 700; color: #a5b4fc;">Manager-Worker Delegation Architecture</span>
                <span style="font-size: 11px; background: rgba(99, 102, 241, 0.2); padding: 3px 10px; border-radius: 12px; color: #818cf8;">6 Connected</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div style="background: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 10px;">
                    <span style="font-size: 13px; font-weight: 600; color: #ffffff;">📄 Document Agent</span>
                    <p style="margin: 2px 0 0 0; font-size: 11px; color: #94a3b8;">PDF parser & injection defense</p>
                </div>
                <div style="background: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 10px;">
                    <span style="font-size: 13px; font-weight: 600; color: #ffffff;">🧮 EMI Agent</span>
                    <p style="margin: 2px 0 0 0; font-size: 11px; color: #94a3b8;">Reducing-balance math</p>
                </div>
                <div style="background: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 10px;">
                    <span style="font-size: 13px; font-weight: 600; color: #ffffff;">⚖️ Affordability Agent</span>
                    <p style="margin: 2px 0 0 0; font-size: 11px; color: #94a3b8;">FOIR debt-to-income &le; 40%</p>
                </div>
                <div style="background: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 10px;">
                    <span style="font-size: 13px; font-weight: 600; color: #ffffff;">🏛️ Credit History Agent</span>
                    <p style="margin: 2px 0 0 0; font-size: 11px; color: #94a3b8;">Bureau default & fraud check</p>
                </div>
                <div style="background: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 10px;">
                    <span style="font-size: 13px; font-weight: 600; color: #ffffff;">💡 Counter-Offer Worker</span>
                    <p style="margin: 2px 0 0 0; font-size: 11px; color: #94a3b8;">Restructuring & tenure boost</p>
                </div>
                <div style="background: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 10px;">
                    <span style="font-size: 13px; font-weight: 600; color: #ffffff;">👔 Underwriting Manager</span>
                    <p style="margin: 2px 0 0 0; font-size: 11px; color: #94a3b8;">Policy arbiter & justification</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Recent Applications Table
    st.markdown("### Recent Portfolio Submissions")
    if apps:
        app_rows = []
        for a in apps[:10]:
            app_rows.append({
                "App ID": a.application_id,
                "Applicant": a.applicant_name,
                "Monthly Income": f"₹{a.monthly_income:,.0f}" if a.monthly_income is not None else "Missing",
                "Existing Debt": f"₹{a.existing_emis:,.0f}",
                "Requested": f"₹{a.requested_amount:,.0f}",
                "Tenure": f"{a.tenure_months}m",
                "Calculated EMI": f"₹{a.calculated_emi:,.0f}" if a.calculated_emi else "N/A",
                "FOIR": f"{a.foir:.1f}%" if a.foir is not None else "N/A",
                "Decision": a.final_decision,
                "Audit Summary": a.decision_reason[:75] + "..." if len(a.decision_reason) > 75 else a.decision_reason
            })
        st.dataframe(pd.DataFrame(app_rows), use_container_width=True, hide_index=True)


# -------------------------------------------------------------------------------------------------
# PAGE 2: NEW LOAN INTAKE & LIVE SIMULATION
# -------------------------------------------------------------------------------------------------
elif menu_selection == "📝 New Loan Intake":
    st.markdown("""
    <div class="hero-banner">
        <h1 class="hero-title">New Credit Application Intake</h1>
        <p style="color: #94a3b8; font-size: 14px; margin: 6px 0 0 0;">
            Submit applicant financials or test edge cases with instant multi-agent evaluation.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Quick Fill Profile Select
    preset_choice = st.selectbox(
        "⚡ Quick-Fill Institutional Demonstration Personas",
        [
            "Custom (Blank Proposal)",
            "Case 1: Rahul Sharma (Eligible -> SANCTION)",
            "Case 2: Priya Patel (High Debt Burden -> DECLINE with Counter-Offer)",
            "Case 3: Amit Kumar (Missing Income -> Immediate REFER)",
            "Case 4: Vikram Singh (Credit Default -> Hard DECLINE)",
            "Case 5: Sneha Rao (Affordability Failure -> Valid Counter-Offer)",
            "Adversarial: Prompt Injection Attack (Defense Neutralization)"
        ]
    )

    defaults = {
        "app_id": "APP" + str(np.random.randint(100, 999)),
        "name": "",
        "income": 60000.0,
        "existing_emis": 8000.0,
        "amount": 500000.0,
        "rate": 12.0,
        "tenure": 60,
        "has_income": True,
        "inject": False
    }

    if "Case 1" in preset_choice:
        defaults = {"app_id": "APP001", "name": "Rahul Sharma", "income": 60000.0, "existing_emis": 8000.0, "amount": 500000.0, "rate": 12.0, "tenure": 60, "has_income": True, "inject": False}
    elif "Case 2" in preset_choice:
        defaults = {"app_id": "APP002", "name": "Priya Patel", "income": 75000.0, "existing_emis": 24000.0, "amount": 700000.0, "rate": 12.0, "tenure": 36, "has_income": True, "inject": False}
    elif "Case 3" in preset_choice:
        defaults = {"app_id": "APP003", "name": "Amit Kumar", "income": 0.0, "existing_emis": 5000.0, "amount": 300000.0, "rate": 11.5, "tenure": 48, "has_income": False, "inject": False}
    elif "Case 4" in preset_choice:
        defaults = {"app_id": "APP004", "name": "Vikram Singh", "income": 90000.0, "existing_emis": 10000.0, "amount": 400000.0, "rate": 12.0, "tenure": 36, "has_income": True, "inject": False}
    elif "Case 5" in preset_choice:
        defaults = {"app_id": "APP005", "name": "Sneha Rao", "income": 50000.0, "existing_emis": 12000.0, "amount": 600000.0, "rate": 12.0, "tenure": 48, "has_income": True, "inject": False}
    elif "Adversarial" in preset_choice:
        defaults = {"app_id": "APP999", "name": "Eve Mallicious", "income": 80000.0, "existing_emis": 5000.0, "amount": 400000.0, "rate": 12.0, "tenure": 36, "has_income": True, "inject": True}

    with st.form("application_intake_form"):
        col1, col2 = st.columns(2)

        with col1:
            app_id = st.text_input("Application Identifier *", value=defaults["app_id"])
            applicant_name = st.text_input("Applicant Full Name *", value=defaults["name"])

            provide_income = st.checkbox("Declare Verified Monthly Income?", value=defaults["has_income"], help="Uncheck to test immediate referral policy for missing income.")
            monthly_income = None
            if provide_income:
                monthly_income = st.number_input(
                    "Net Monthly Income (₹) *",
                    min_value=1000.0,
                    max_value=10000000.0,
                    value=float(defaults["income"]) if defaults["income"] > 0 else 50000.0,
                    step=5000.0
                )
            else:
                st.warning("⚠️ Income omitted: Underwriting policy mandates an immediate halt and REFER.")

            existing_emis = st.number_input(
                "Existing Monthly EMI Obligations (₹)",
                min_value=0.0,
                max_value=5000000.0,
                value=float(defaults["existing_emis"]),
                step=1000.0
            )

        with col2:
            requested_amount = st.number_input(
                "Requested Principal Loan Amount (₹) *",
                min_value=10000.0,
                max_value=10000000.0,
                value=float(defaults["amount"]),
                step=25000.0
            )
            tenure_months = st.slider(
                "Requested Tenure (Months) *",
                min_value=6,
                max_value=84,
                value=int(defaults["tenure"]),
                step=6
            )
            interest_rate = st.number_input(
                "Annual Interest Rate (%) *",
                min_value=0.0,
                max_value=36.0,
                value=float(defaults["rate"]),
                step=0.25
            )

            # Real-time Reducing-Balance estimate
            if requested_amount > 0 and tenure_months > 0:
                est_emi = compute_emi(requested_amount, interest_rate, tenure_months).monthly_emi
                st.markdown(f"""
                <div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(129, 140, 248, 0.3); border-radius: 12px; padding: 12px; margin-top: 14px;">
                    <span style="font-size: 11px; color: #a5b4fc; font-weight: 700; text-transform: uppercase;">Estimated Reducing-Balance EMI</span>
                    <div style="font-family: 'Outfit'; font-size: 22px; font-weight: 800; color: #ffffff;">₹{est_emi:,.2f} <span style="font-size: 13px; color: #94a3b8;">/ mo</span></div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Upload Income & Verification Document")
        uploaded_pdf = st.file_uploader("Upload Salary Slip / Financial Proof (PDF format, max 5MB)", type=["pdf"])

        auto_generate_mock_pdf = st.checkbox(
            "Auto-generate verified payroll PDF document for this submission",
            value=True if uploaded_pdf is None else False,
            help="Generates an authentic PDF salary statement matching form figures"
        )

        submit_button = st.form_submit_button("🚀 Launch Multi-Agent Underwriting Swarm", use_container_width=True)

    if submit_button:
        if not app_id or not applicant_name:
            st.error("Please supply both Application ID and Applicant Name.")
        else:
            pdf_path_to_use = None

            if uploaded_pdf is not None:
                save_path = settings.uploads_dir / f"{app_id}_{uploaded_pdf.name}"
                with open(save_path, "wb") as f:
                    f.write(uploaded_pdf.read())
                pdf_path_to_use = str(save_path)
            elif auto_generate_mock_pdf:
                save_path = settings.uploads_dir / f"generated_{app_id}.pdf"
                generate_sample_application_pdf(
                    file_path=str(save_path),
                    applicant_name=applicant_name,
                    monthly_income=monthly_income,
                    existing_emis=existing_emis,
                    requested_amount=requested_amount,
                    tenure_months=tenure_months,
                    annual_interest_rate=interest_rate,
                    include_prompt_injection=defaults["inject"]
                )
                pdf_path_to_use = str(save_path)

            app_input = LoanApplicationInput(
                application_id=app_id,
                applicant_name=applicant_name,
                monthly_income=monthly_income,
                existing_emis=existing_emis,
                requested_amount=requested_amount,
                tenure_months=tenure_months,
                annual_interest_rate=interest_rate,
                uploaded_document_path=pdf_path_to_use
            )

            # Animated Sequential Execution Visualizer
            progress_placeholder = st.empty()
            with progress_placeholder.container():
                progress_bar = st.progress(0, text="Initializing Shared Applicant Memory...")
                time.sleep(0.15)
                progress_bar.progress(20, text="Agent 1 (Document Agent): Extracting PDF & checking prompt injection...")
                time.sleep(0.15)
                progress_bar.progress(40, text="Agent 2 (EMI Agent): Deterministically computing reducing-balance installment...")
                time.sleep(0.15)
                progress_bar.progress(60, text="Agent 3 (Affordability Agent): Evaluating FOIR against 40% ceiling...")
                time.sleep(0.15)
                progress_bar.progress(80, text="Agent 4 (Credit Agent): Querying bureau default & fraud database...")
                time.sleep(0.15)
                progress_bar.progress(95, text="Agent 6 (Underwriting Manager): Synthesizing credit appraisal & justification...")
                time.sleep(0.1)

            try:
                result = run_async(manager.process_application(app_input, persist_db=True))
                progress_placeholder.empty()

                st.session_state["latest_result"] = result.model_dump()
                st.session_state["latest_app_id"] = app_id

                # Celebratory animations on decision
                dec_val = result.decision.value
                if dec_val == "SANCTION":
                    st.balloons()
                    st.markdown(f"""
                    <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 16px; padding: 20px; text-align: center; margin-top: 14px;">
                        <span class="badge-sanction">🎉 SANCTION APPROVED</span>
                        <h3 style="color: #ffffff; margin: 10px 0 0 0;">Application {app_id} Approved</h3>
                        <p style="color: #a7f3d0; font-size: 14px; margin: 4px 0 0 0;">{result.reason}</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif dec_val == "DECLINE":
                    st.markdown(f"""
                    <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 16px; padding: 20px; text-align: center; margin-top: 14px;">
                        <span class="badge-decline">⛔ DECLINE</span>
                        <h3 style="color: #ffffff; margin: 10px 0 0 0;">Application {app_id} Declined</h3>
                        <p style="color: #fecaca; font-size: 14px; margin: 4px 0 0 0;">{result.reason}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 16px; padding: 20px; text-align: center; margin-top: 14px;">
                        <span class="badge-refer">⚠️ REFER FOR REVIEW</span>
                        <h3 style="color: #ffffff; margin: 10px 0 0 0;">Application {app_id} Referred</h3>
                        <p style="color: #fde68a; font-size: 14px; margin: 4px 0 0 0;">{result.reason}</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.info("Switch to **📜 Underwriting Results** or **🤖 Agent Monitoring** to inspect complete logs.")
            except Exception as ex:
                progress_placeholder.empty()
                st.error(f"Error during multi-agent underwriting: {ex}")


# -------------------------------------------------------------------------------------------------
# PAGE 3: AGENT MONITORING
# -------------------------------------------------------------------------------------------------
elif menu_selection == "🤖 Agent Monitoring":
    st.markdown("""
    <div class="hero-banner">
        <h1 class="hero-title">Multi-Agent Swarm Pipeline Observability</h1>
        <p style="color: #94a3b8; font-size: 14px; margin: 6px 0 0 0;">
            Inspect individual worker latency, state transitions, and immutable shared memory snapshots.
        </p>
    </div>
    """, unsafe_allow_html=True)

    db = SessionLocal()
    apps = list_applications_records(db, limit=50)
    db.close()

    if not apps:
        st.info("No applications evaluated yet. Please submit or seed applications first.")
    else:
        app_ids = [a.application_id for a in apps]
        selected_app_id = st.selectbox("Select Application Trace to Inspect:", app_ids)

        db = SessionLocal()
        selected_app = get_application(db, selected_app_id)
        audit_logs = get_audit_logs(db, selected_app_id)
        db.close()

        if selected_app:
            dec_val = selected_app.final_decision
            badge_class = "badge-sanction" if dec_val == "SANCTION" else ("badge-decline" if dec_val == "DECLINE" else "badge-refer")

            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div>
                    <h2 style="margin: 0; color: #ffffff;">{selected_app.applicant_name}</h2>
                    <span style="font-family: 'JetBrains Mono'; font-size: 13px; color: #94a3b8;">TRACE ID: {selected_app.application_id}</span>
                </div>
                <span class="{badge_class}">{dec_val}</span>
            </div>
            """, unsafe_allow_html=True)

            # Agent Swarm Flow Diagram
            st.markdown("#### Execution Sequence Graph")
            pipeline_cols = st.columns(6)
            agent_icons = {
                "DocumentAgent": "📄",
                "EMIAgent": "🧮",
                "AffordabilityAgent": "⚖️",
                "CreditHistoryAgent": "🏛️",
                "CounterOfferAgent": "💡",
                "UnderwritingManager": "👔"
            }

            nodes = [
                ("DocumentAgent", "Doc Agent"),
                ("EMIAgent", "EMI Agent"),
                ("AffordabilityAgent", "Affordability"),
                ("CreditHistoryAgent", "Bureau Agent"),
                ("CounterOfferAgent", "Counter-Offer"),
                ("UnderwritingManager", "Manager")
            ]

            log_dict = {l.agent_name: l for l in audit_logs}

            for idx, (agent_key, label) in enumerate(nodes):
                with pipeline_cols[idx]:
                    has_log = agent_key in log_dict
                    status_text = log_dict[agent_key].status if has_log else "SKIPPED"
                    status_bg = "#10b981" if status_text == "COMPLETED" else ("#f43f5e" if status_text == "FAILED" else ("#f59e0b" if status_text in ["FLAGGED", "HALTED"] else "#64748b"))

                    st.markdown(f"""
                    <div class="pipeline-node {'active-node' if has_log else ''}">
                        <span class="node-icon">{agent_icons.get(agent_key, '⚡')}</span>
                        <div class="node-name">{label}</div>
                        <span class="node-status" style="background: {status_bg}33; color: {status_bg}; border: 1px solid {status_bg};">
                            {status_text}
                        </span>
                        <div style="font-size: 10px; color: #94a3b8; margin-top: 4px;">
                            {f"{log_dict[agent_key].execution_time_ms:.2f}ms" if has_log else "—"}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Step-by-Step Detail Drawers
            st.markdown("#### Agent Execution Logs & JSON Payloads")
            for idx, log in enumerate(audit_logs):
                with st.expander(f"Step {idx+1}: {log.agent_name} — {log.status} ({log.execution_time_ms:.2f} ms)"):
                    st.markdown(f"**Task Description:** {log.task_description}")
                    st.markdown(f"**Started At:** `{log.started_at}` | **Completed At:** `{log.completed_at}`")
                    st.json(json.loads(log.output_summary_json) if log.output_summary_json else {})

            # Shared Memory Full Inspection
            with st.expander("📦 Complete Shared Applicant Memory Snapshot"):
                st.json(json.loads(selected_app.shared_memory_snapshot) if selected_app.shared_memory_snapshot else {})


# -------------------------------------------------------------------------------------------------
# PAGE 4: EMI AMORTIZATION TOOL
# -------------------------------------------------------------------------------------------------
elif menu_selection == "🧮 EMI Amortization Tool":
    st.markdown("""
    <div class="hero-banner">
        <h1 class="hero-title">Deterministic Reducing-Balance Amortization</h1>
        <p style="color: #94a3b8; font-size: 14px; margin: 6px 0 0 0;">
            Interactive financial simulator powered by pure deterministic reducing-balance algorithms.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Loan Inputs")
        p = st.number_input("Principal Loan Amount (₹)", min_value=1000.0, max_value=50000000.0, value=500000.0, step=25000.0)
        r = st.slider("Annual Interest Rate (%)", min_value=0.0, max_value=30.0, value=12.0, step=0.25)
        n = st.slider("Loan Tenure (Months)", min_value=1, max_value=360, value=60, step=1)

        emi_res = compute_emi(p, r, n)

    with col2:
        st.markdown("### Installment Summary")
        st.markdown(f"""
        <div class="fintech-card" style="border-left: 4px solid #6366f1;">
            <div style="font-size: 12px; color: #a5b4fc; text-transform: uppercase; font-weight: 700;">Monthly Installment</div>
            <h1 style="color: #ffffff; font-family: 'Outfit'; margin: 4px 0 16px 0; font-size: 42px;">
                ₹{emi_res.monthly_emi:,.2f} <span style="font-size: 16px; color: #94a3b8; font-weight: 400;">/ month</span>
            </h1>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 14px;">
                <div>
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Total Principal</span>
                    <div style="font-size: 18px; font-weight: 700; color: #ffffff;">₹{emi_res.principal:,.2f}</div>
                </div>
                <div>
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Total Interest Payable</span>
                    <div style="font-size: 18px; font-weight: 700; color: #818cf8;">₹{emi_res.total_interest:,.2f}</div>
                </div>
            </div>
            <div style="margin-top: 12px;">
                <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Total Repayment Obligation</span>
                <div style="font-size: 20px; font-weight: 800; color: #34d399;">₹{emi_res.total_repayment:,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Interactive Amortization Chart
    st.markdown("### Principal vs Total Interest Composition")
    pie_fig = go.Figure(data=[go.Pie(
        labels=["Principal Amount", "Total Interest Payable"],
        values=[emi_res.principal, emi_res.total_interest],
        hole=0.55,
        marker=dict(colors=["#6366f1", "#f59e0b"], line=dict(color="#0f172a", width=2)),
        textinfo="label+percent",
        textfont=dict(family="Plus Jakarta Sans", size=14, color="#ffffff")
    )])
    pie_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        height=280
    )
    st.plotly_chart(pie_fig, use_container_width=True)


# -------------------------------------------------------------------------------------------------
# PAGE 5: UNDERWRITING RESULTS & COUNTER-OFFER SHOWCASE
# -------------------------------------------------------------------------------------------------
elif menu_selection == "📜 Underwriting Results":
    st.markdown("""
    <div class="hero-banner">
        <h1 class="hero-title">Credit Appraisal & Risk Assessment</h1>
        <p style="color: #94a3b8; font-size: 14px; margin: 6px 0 0 0;">
            Detailed multi-agent evaluation verdict, FOIR speedometer, and automated loan counter-offers.
        </p>
    </div>
    """, unsafe_allow_html=True)

    db = SessionLocal()
    apps = list_applications_records(db, limit=50)
    db.close()

    if not apps:
        st.info("No applications evaluated yet. Please submit or seed applications first.")
    else:
        app_ids = [a.application_id for a in apps]
        default_index = 0
        if "latest_app_id" in st.session_state and st.session_state["latest_app_id"] in app_ids:
            default_index = app_ids.index(st.session_state["latest_app_id"])

        selected_id = st.selectbox("Select Application Assessment:", app_ids, index=default_index)

        db = SessionLocal()
        app = get_application(db, selected_id)
        db.close()

        if app:
            dec = app.final_decision
            badge_class = "badge-sanction" if dec == "SANCTION" else ("badge-decline" if dec == "DECLINE" else "badge-refer")

            # Decision Hero Header Card
            st.markdown(f"""
            <div class="fintech-card" style="border-top: 3px solid {'#10b981' if dec == 'SANCTION' else ('#f43f5e' if dec == 'DECLINE' else '#f59e0b')};">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                    <div>
                        <span style="font-size: 12px; font-weight: 700; color: #818cf8; letter-spacing: 1px;">CREDIT APPRAISAL RESULT</span>
                        <h2 style="margin: 4px 0 0 0; color: #ffffff; font-size: 32px;">{app.applicant_name}</h2>
                        <span style="font-family: 'JetBrains Mono'; font-size: 13px; color: #94a3b8;">APP REF: {app.application_id}</span>
                    </div>
                    <span class="{badge_class}" style="font-size: 18px; padding: 10px 24px;">{dec}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Key Financial Appraisal Parameters & Speedometer FOIR Gauge
            col_metrics, col_gauge = st.columns([1.2, 1])

            with col_metrics:
                st.markdown("#### Financial Appraisal Summary")
                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Requested Principal", f"₹{app.requested_amount:,.0f}", f"{app.tenure_months}m @ {app.annual_interest_rate}%")
                    emi_val = f"₹{app.calculated_emi:,.2f}" if app.calculated_emi else "N/A"
                    st.metric("Proposed EMI", emi_val)
                with m2:
                    inc_val = f"₹{app.monthly_income:,.0f}" if app.monthly_income is not None else "Missing"
                    st.metric("Net Monthly Income", inc_val, f"Existing Debt: ₹{app.existing_emis:,.0f}")
                    st.metric("Credit Bureau Standing", app.credit_verdict, f"Affordability: {app.affordability_verdict}")

            with col_gauge:
                foir_val = app.foir if app.foir is not None else 0.0
                st.plotly_chart(render_foir_gauge(foir_val, settings.max_foir_percent), use_container_width=True)

            # Executive Justification Synthesis
            st.markdown("### Executive Underwriting Justification")
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.7); border-left: 4px solid #818cf8; border-radius: 12px; padding: 18px; margin-bottom: 20px;">
                <p style="margin: 0; color: #f1f5f9; line-height: 1.7; font-size: 15px;">
                    {app.justification_paragraph}
                </p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"**Institutional Decision Rationale:** {app.decision_reason}")

            # Counter Offer Section
            if app.counter_offer_json:
                co = json.loads(app.counter_offer_json)
                if co.get("feasible"):
                    st.markdown("### 💡 Automated Loan Counter-Offer")
                    st.markdown(f"""
                    <div class="counter-spotlight">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <h3 style="margin: 0; color: #ffffff; font-family: 'Outfit';">Restructured Loan Terms</h3>
                            <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #34d399; padding: 4px 14px; border-radius: 20px; font-weight: 700; font-size: 12px;">
                                FOIR RECOVERED TO {co['revised_foir']:.2f}%
                            </span>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px;">
                            <div style="background: rgba(15, 23, 42, 0.7); padding: 14px; border-radius: 12px;">
                                <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">RECOMMENDED AMOUNT</span>
                                <div style="font-size: 22px; font-weight: 800; color: #ffffff;">₹{co['recommended_amount']:,.2f}</div>
                                <span style="font-size: 11px; color: #cbd5e1;">(Original: ₹{co['original_amount']:,.0f})</span>
                            </div>
                            <div style="background: rgba(15, 23, 42, 0.7); padding: 14px; border-radius: 12px;">
                                <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">RECOMMENDED TENURE</span>
                                <div style="font-size: 22px; font-weight: 800; color: #818cf8;">{co['recommended_tenure']} Months</div>
                                <span style="font-size: 11px; color: #cbd5e1;">(Extended from {co['original_tenure']}m)</span>
                            </div>
                            <div style="background: rgba(15, 23, 42, 0.7); padding: 14px; border-radius: 12px;">
                                <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">REVISED MONTHLY EMI</span>
                                <div style="font-size: 22px; font-weight: 800; color: #ffffff;">₹{co['recommended_emi']:,.2f}</div>
                                <span style="font-size: 11px; color: #cbd5e1;">(Down from ₹{co['original_emi']:,.0f})</span>
                            </div>
                            <div style="background: rgba(15, 23, 42, 0.7); padding: 14px; border-radius: 12px;">
                                <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">COMPLIANT FOIR</span>
                                <div style="font-size: 22px; font-weight: 800; color: #34d399;">{co['revised_foir']:.2f}%</div>
                                <span style="font-size: 11px; color: #34d399;">&le; 40.0% Ceiling Pass</span>
                            </div>
                        </div>
                        <p style="margin: 0; color: #e0e7ff; font-size: 14px;"><strong>Restructuring Rationale:</strong> {co['explanation']}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # Export Prompt Section 8 JSON
            with st.expander("📋 View Structured Response (Prompt Section 8 Format)"):
                structured_json = {
                    "application_id": app.application_id,
                    "decision": app.final_decision,
                    "requested_amount": app.requested_amount,
                    "emi": app.calculated_emi,
                    "existing_emi": app.existing_emis,
                    "monthly_income": app.monthly_income,
                    "foir": app.foir,
                    "affordability": app.affordability_verdict,
                    "credit_history": app.credit_verdict,
                    "counter_offer": json.loads(app.counter_offer_json) if app.counter_offer_json else None,
                    "reason": app.decision_reason
                }
                st.code(json.dumps(structured_json, indent=2), language="json")


# -------------------------------------------------------------------------------------------------
# PAGE 6: APPLICATION HISTORY
# -------------------------------------------------------------------------------------------------
elif menu_selection == "🗄️ Application History":
    st.markdown("""
    <div class="hero-banner">
        <h1 class="hero-title">Application History & Portfolio Audit</h1>
        <p style="color: #94a3b8; font-size: 14px; margin: 6px 0 0 0;">
            Search and filter past underwriting decisions, risk verdicts, and compliance audit logs.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        decision_filter = st.selectbox("Filter by Decision:", ["ALL", "SANCTION", "DECLINE", "REFER"])
    with col2:
        search_query = st.text_input("Search by Application ID or Applicant Name:")

    db = SessionLocal()
    records = list_applications_records(
        db=db,
        decision_filter=decision_filter,
        search_query=search_query,
        limit=100
    )
    db.close()

    if records:
        table_data = []
        for r in records:
            table_data.append({
                "App ID": r.application_id,
                "Applicant Name": r.applicant_name,
                "Monthly Income": f"₹{r.monthly_income:,.0f}" if r.monthly_income is not None else "Missing",
                "Existing Debt": f"₹{r.existing_emis:,.0f}",
                "Requested Principal": f"₹{r.requested_amount:,.0f}",
                "Calculated EMI": f"₹{r.calculated_emi:,.0f}" if r.calculated_emi else "N/A",
                "FOIR": f"{r.foir:.2f}%" if r.foir is not None else "N/A",
                "Affordability": r.affordability_verdict,
                "Credit Bureau": r.credit_verdict,
                "Decision": r.final_decision,
                "Submission Date": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""
            })

        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
    else:
        st.info("No matching records found in the underwriting database.")


# -------------------------------------------------------------------------------------------------
# PAGE 7: INTERACTIVE ANIMATED PRESENTATION DECK
# -------------------------------------------------------------------------------------------------
elif menu_selection == "🎬 Interactive Presentation Deck":
    import streamlit.components.v1 as components

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown("### 🎬 FinCore AI | Animated Presentation Deck")
        st.caption("Interactive full-screen presentation mode for faculty and academic evaluation.")
    with col_h2:
        presentation_file = BASE_DIR / "FinCore_Multi_Agent_Underwriting_Presentation.pptx"
        if presentation_file.exists():
            with open(presentation_file, "rb") as f:
                st.download_button(
                    label="📥 Download .PPTX File",
                    data=f.read(),
                    file_name="FinCore_Multi_Agent_Underwriting_Presentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )

    html_path = BASE_DIR / "frontend" / "presentation.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Render full embedded presentation with 850px height
        components.html(html_content, height=850, scrolling=False)
    else:
        st.warning("Presentation HTML file not found.")
