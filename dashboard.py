from pathlib import Path
from io import BytesIO
from datetime import datetime, date, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as ReportImage
)

# WattWise Advanced Modular Components
from modules.db import (
    init_db,
    add_saving_action,
    get_all_saving_actions,
    update_saving_action,
    delete_saving_action,
    run_readonly_query,
)
from modules.auth import (
    authenticate_user,
    register_user,
    provision_initial_admin,
    count_admins,
    count_users,
    get_all_users,
    update_user_status,
    update_user_role,
    validate_username,
    validate_password,
)
from modules.dataset_manager import (
    detect_candidate_columns,
    validate_and_transform_uploaded_csv,
)
from modules.savings_tracker import (
    ACTION_PRESETS,
    evaluate_action_impact,
)
from modules.profiling import (
    extract_behavioural_features,
    run_kmeans_clustering,
    FEATURE_DESCRIPTIONS,
)
from modules.changepoint import (
    detect_cusum_changepoints,
    detect_binary_segmentation_changepoints,
    summarize_changepoints,
    generate_synthetic_validation_series,
)
from modules.carbon import (
    PRESET_EMISSION_FACTORS,
    CEA_NATIONAL_GRID_FACTOR,
    calculate_emissions,
    compute_daily_emissions,
    compute_monthly_emissions,
    find_highest_emission_days,
)
from modules.insights_engine import (
    generate_intelligent_insights,
    InsightCard,
)

# ---------------------------------------------------------
# CONFIG + VISUAL THEME
# ---------------------------------------------------------
st.set_page_config(
    page_title="WattWise | Electricity Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = Path("sample_electricity_data.csv")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --bg:#080d18; --panel:#111a2b; --panel2:#151f33; --line:#26344c; --text:#edf4ff; --muted:#94a6c4; --cyan:#35d8f2; --blue:#6388ff; --violet:#a78bfa; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background: radial-gradient(ellipse at 10% 0%, #142747 0%, #080d18 42%, #080d18 100%); color:var(--text); }
[data-testid="stHeader"] { background:rgba(8,13,24,.75); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#101a2c 0%,#0b1220 100%); border-right:1px solid #26344c; }
[data-testid="stSidebar"] * { color:#e7efff; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.035em; }
h1 { font-size:2.15rem !important; }
h2 { font-size:1.45rem !important; }
p, label, .stCaption { color:#b9c7dd; }
div[data-testid="stMetric"] { background:linear-gradient(145deg,rgba(21,32,53,.96),rgba(14,23,39,.96)); border:1px solid #2a3b57; padding:18px 20px; border-radius:17px; box-shadow:0 12px 30px rgba(0,0,0,.16); transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease; }
div[data-testid="stMetric"]:hover { transform:translateY(-4px); border-color:#35d8f2; box-shadow:0 14px 32px rgba(53,216,242,.12); }
div[data-testid="stMetricLabel"] { color:#9eb2d0 !important; }
div[data-testid="stMetricValue"] { color:#f5f9ff !important; font-family:'Space Grotesk',sans-serif; }
div[data-testid="stMetricDelta"] { color:#35d8f2 !important; }
.stButton > button, .stDownloadButton > button { border:1px solid #35d8f2; color:#07111d !important; background:linear-gradient(100deg,#35d8f2,#75a4ff); border-radius:11px; font-weight:800; transition:all .22s ease; }
.stButton > button *, .stDownloadButton > button * { color:#07111d !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { font-size:1rem; }
[data-testid="stSidebar"] [role="radiogroup"] label p { font-size:1.02rem !important; font-weight:600; }
.stButton > button:hover, .stDownloadButton > button:hover { transform:translateY(-2px); box-shadow:0 8px 22px rgba(53,216,242,.24); border-color:#b4f4ff; }
div[data-testid="stDataFrame"], div[data-testid="stTable"] { border:1px solid #26344c; border-radius:12px; overflow:hidden; }
hr { border-color:#26344c !important; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color:#26344c !important; border-radius:16px; }
section[data-testid="stFileUploaderDropzone"] { background:#111a2b; }
[data-testid="stSelectbox"], [data-testid="stDateInput"] { border-radius:10px; }
div[data-testid="stAlert"] { border-radius:12px; }
.watt-hero { padding:26px 28px; border:1px solid #2c4564; border-radius:22px; background:linear-gradient(115deg,rgba(20,43,72,.95),rgba(17,26,43,.93) 55%,rgba(42,34,79,.72)); margin-bottom:18px; box-shadow:0 18px 50px rgba(0,0,0,.18); }
.watt-kicker { text-transform:uppercase; letter-spacing:.17em; font-size:.72rem; color:#35d8f2; font-weight:700; }
.watt-title { font-family:'Space Grotesk',sans-serif; font-size:2.1rem; line-height:1.15; color:#f5f8ff; font-weight:700; margin:.35rem 0 .55rem; }
.watt-sub { color:#aabbd5; max-width:850px; font-size:.97rem; }
.section-label { color:#35d8f2; font-size:.78rem; text-transform:uppercase; letter-spacing:.14em; font-weight:700; margin-bottom:3px; }
.small-card { border:1px solid #26344c; background:rgba(17,26,43,.88); border-radius:14px; padding:16px 18px; height:100%; }
.small-card h4 { margin:0 0 8px; color:#eaf3ff; font-family:'Space Grotesk',sans-serif; }
.small-card p { margin:0; color:#a8bad3; font-size:.9rem; }
.finding-metric { min-width:0; min-height:116px; padding:16px 18px; border:1px solid #2a3b57; border-radius:17px; background:linear-gradient(145deg,rgba(21,32,53,.96),rgba(14,23,39,.96)); display:flex; flex-direction:column; justify-content:center; overflow:hidden; }
.finding-metric-label { color:#9eb2d0; font-size:.82rem; margin-bottom:7px; }
.finding-metric-value { color:#f5f9ff; font-family:'Space Grotesk',sans-serif; font-size:clamp(1.45rem, 2vw, 2rem); line-height:1.15; white-space:nowrap; letter-spacing:-.04em; }
.finding-total-value { font-size:clamp(1.25rem, 1.65vw, 1.8rem); letter-spacing:-.045em; }
.finding-metric-unit { color:#b9c7dd; font-size:.8rem; margin-top:5px; }
.footer-note { color:#7588a7; font-size:.78rem; padding-top:12px; }

/* Custom Badge Styles */
.badge-high { display:inline-block; background:rgba(34,197,94,0.18); color:#4ade80; border:1px solid #22c55e; padding:3px 10px; border-radius:999px; font-weight:700; font-size:0.75rem; letter-spacing:0.04em; }
.badge-moderate { display:inline-block; background:rgba(234,179,8,0.18); color:#facc15; border:1px solid #eab308; padding:3px 10px; border-radius:999px; font-weight:700; font-size:0.75rem; letter-spacing:0.04em; }
.badge-low { display:inline-block; background:rgba(239,68,68,0.18); color:#f87171; border:1px solid #ef4444; padding:3px 10px; border-radius:999px; font-weight:700; font-size:0.75rem; letter-spacing:0.04em; }
.source-pill-default { display:inline-block; background:rgba(53,216,242,0.14); color:#35d8f2; border:1px solid #35d8f2; padding:3px 10px; border-radius:12px; font-size:0.8rem; font-weight:600; }
.source-pill-upload { display:inline-block; background:rgba(167,139,250,0.18); color:#c4b5fd; border:1px solid #a78bfa; padding:3px 10px; border-radius:12px; font-size:0.8rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# DATA
# ---------------------------------------------------------
NUMERIC_COLUMNS = [
    "Global_active_power", "Global_reactive_power", "Voltage",
    "Global_intensity", "Sub_metering_1", "Sub_metering_2", "Sub_metering_3",
]
REQUIRED_COLUMNS = set(NUMERIC_COLUMNS)


def prepare_data(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize a WattWise dataset and validate the columns used by the dashboard."""
    data = data.copy()
    data.columns = data.columns.astype(str).str.strip()

    if "DateTime" not in data.columns:
        if "Datetime" in data.columns:
            data["DateTime"] = pd.to_datetime(data["Datetime"], errors="coerce")
        elif "Date" in data.columns and "Time" in data.columns:
            data["DateTime"] = pd.to_datetime(
                data["Date"].astype(str) + " " + data["Time"].astype(str),
                dayfirst=True, errors="coerce"
            )
        else:
            raise ValueError("Add a `DateTime` column or both `Date` and `Time` columns.")
    else:
        data["DateTime"] = pd.to_datetime(data["DateTime"], dayfirst=True, errors="coerce")

    missing = sorted(REQUIRED_COLUMNS.difference(data.columns))
    if missing:
        # Gracefully fill optional sub-metering or electrical measurements with 0 if missing
        for col in missing:
            data[col] = 0.0

    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)

    data = data.dropna(subset=["DateTime", "Global_active_power"])
    if data.empty:
        raise ValueError("No usable rows remain. Check the date/time and Global_active_power values.")
    return data.sort_values("DateTime").reset_index(drop=True)


@st.cache_data(show_spinner="Loading and preparing electricity data…")
def load_data(file_path: str) -> pd.DataFrame:
    return prepare_data(pd.read_csv(file_path))


# Initialize SQLite database tables
init_db()

if not DATA_FILE.exists():
    st.error(f"Dataset not found: `{DATA_FILE.name}`. Place it beside this Python file.")
    st.stop()

try:
    default_df = load_data(str(DATA_FILE))
except Exception as exc:
    st.error(f"Unable to load the default dataset: {exc}")
    st.stop()

# Safe session state dataset management
if "wattwise_active_df" not in st.session_state:
    st.session_state["wattwise_active_df"] = default_df
    st.session_state["wattwise_data_source"] = DATA_FILE.name
    st.session_state["wattwise_is_custom"] = False

if "wattwise_upload_version" not in st.session_state:
    st.session_state["wattwise_upload_version"] = 0

df = st.session_state["wattwise_active_df"]
data_source = st.session_state.get("wattwise_data_source", DATA_FILE.name)
is_custom_dataset = st.session_state.get("wattwise_is_custom", False)

if df.empty:
    st.error("The active dataset has no usable records.")
    st.stop()

# Resample to daily consumption in kWh
daily = (df.set_index("DateTime")["Global_active_power"].resample("D").sum().div(60)
         .rename("Consumption (kWh)").dropna())
total_kwh = float(daily.sum())
average_daily_kwh = float(daily.mean()) if not daily.empty else 0.0
peak_date = daily.idxmax() if not daily.empty else None
peak_kwh = float(daily.max()) if not daily.empty else 0.0
start_date, end_date = df["DateTime"].min(), df["DateTime"].max()
min_date, max_date = start_date.date(), end_date.date()
monthly = daily.resample("MS").sum().dropna()

# Common chart style
CHART_TEMPLATE = "plotly_dark"
CHART_COLORS = ["#35d8f2", "#6388ff", "#a78bfa", "#42d392", "#ffb86b", "#ff719a"]

def polish(fig, height=360, show_legend=None):
    layout_update = dict(
        template=CHART_TEMPLATE, height=height, margin=dict(l=10, r=10, t=36, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#dce8fa"),
        hoverlabel=dict(bgcolor="#111a2b", bordercolor="#35d8f2", font_color="#f1f6ff"),
    )
    if show_legend is not None:
        layout_update["showlegend"] = show_legend
    elif getattr(fig.layout, "showlegend", None) is not None:
        layout_update["showlegend"] = fig.layout.showlegend
    else:
        layout_update["showlegend"] = True

    if layout_update.get("showlegend", True):
        layout_update["legend"] = dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        )

    fig.update_layout(**layout_update)

    # Eliminate unassigned or blank figure titles to prevent Plotly.js / Streamlit from rendering 'undefined'
    if hasattr(fig.layout, "title") and fig.layout.title is not None:
        t_text = getattr(fig.layout.title, "text", None)
        if not t_text or not str(t_text).strip():
            fig.layout.title = None
        else:
            fig.layout.title.font = dict(family="DM Sans, sans-serif", size=15, color="#f1f6ff")

    # Clean up empty/unassigned legend titles so Plotly.js does not render literal "undefined"
    if hasattr(fig.layout, "legend") and fig.layout.legend is not None:
        if hasattr(fig.layout.legend, "title") and fig.layout.legend.title is not None:
            t_val = getattr(fig.layout.legend.title, "text", None)
            if not t_val or not str(t_val).strip():
                fig.layout.legend.title = None

    fig.update_xaxes(showgrid=False, linecolor="#2a3b57")
    fig.update_yaxes(gridcolor="rgba(148,166,196,.13)", zerolinecolor="#2a3b57")
    return fig

def section_heading(icon, title, subtitle=None):
    st.markdown(f'<div class="section-label">{icon} &nbsp; ANALYTICS</div>', unsafe_allow_html=True)
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)

def kpi(label, value, help_text=None):
    st.metric(label, value, help=help_text)

def make_excel_bytes(frame: pd.DataFrame, date_columns=None) -> bytes:
    """Create a readable Excel workbook with styled headers and sensible column widths."""
    date_columns = set(date_columns or [])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl", datetime_format="DD-MM-YYYY") as writer:
        frame.to_excel(writer, index=False, sheet_name="Data")
        ws = writer.sheets["Data"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="13243B")
            cell.alignment = Alignment(vertical="center")
        for col_idx, column in enumerate(frame.columns, start=1):
            letter = get_column_letter(col_idx)
            values = [str(column)] + [str(v) for v in frame[column].head(500).fillna("").tolist()]
            width = min(max(max((len(v) for v in values), default=10) + 2, 12), 28)
            ws.column_dimensions[letter].width = width
            if column in date_columns:
                for cell in ws[letter][1:]:
                    cell.number_format = "DD-MM-YYYY"
        ws.row_dimensions[1].height = 24
    return output.getvalue()

# ---------------------------------------------------------
# AUTHENTICATION & ACCESS CONTROL GATE
# ---------------------------------------------------------
if "wattwise_user" not in st.session_state or not st.session_state["wattwise_user"]:
    auth_col1, auth_col2, auth_col3 = st.columns([1, 2.2, 1])
    with auth_col2:
        st.markdown("""
        <div style="text-align:center; padding: 26px 20px 14px;">
          <div style="font-size:12px; letter-spacing:3px; color:#35d8f2; font-weight:700">WATTWISE / SECURITY PROTOCOL</div>
          <div style="font-family:'Space Grotesk',sans-serif; font-size:28px; font-weight:700; color:#f1f6ff; margin-top:4px">
            Energy Protocol Access
          </div>
          <p style="color:#94a6c4; font-size:14px; margin-top:6px;">
            Secure Role-Based Authentication & Environmental Intelligence Portal
          </p>
        </div>
        """, unsafe_allow_html=True)

        existing_admins = count_admins()

        if existing_admins == 0:
            st.info("👑 **Initial Setup Required**: No administrator account has been provisioned yet. Set up the initial administrator to secure this WattWise deployment.")
            auth_tabs = st.tabs(["👑 Master Admin Setup", "🔑 Sign In", "📝 Create Account"])

            with auth_tabs[0]:
                with st.form("provision_admin_form"):
                    st.markdown("#### Setup Initial Administrator")
                    adm_u = st.text_input("Administrator Username", key="p_adm_u").strip()
                    adm_p = st.text_input("Administrator Password", type="password", key="p_adm_p", help="Must be at least 8 characters and contain both letters and numbers.")
                    adm_pc = st.text_input("Confirm Password", type="password", key="p_adm_pc")
                    btn_adm = st.form_submit_button("Provision Administrator Account", use_container_width=True)
                    if btn_adm:
                        if adm_p != adm_pc:
                            st.error("Passwords do not match.")
                        else:
                            ok, msg = provision_initial_admin(adm_u, adm_p)
                            if ok:
                                st.success("Master administrator account initialized! Please sign in with your new credentials.")
                                st.rerun()
                            else:
                                st.error(msg)

            login_tab = auth_tabs[1]
            register_tab = auth_tabs[2]
        else:
            auth_tabs = st.tabs(["🔑 Sign In", "📝 Create Account"])
            login_tab = auth_tabs[0]
            register_tab = auth_tabs[1]

        with login_tab:
            with st.form("login_form"):
                st.markdown("#### Sign In to Your Account")
                l_user = st.text_input("Username", key="l_user").strip()
                l_pass = st.text_input("Password", type="password", key="l_pass")
                btn_login = st.form_submit_button("Sign In to WattWise", use_container_width=True)
                if btn_login:
                    ok, msg, uinfo = authenticate_user(l_user, l_pass)
                    if ok:
                        st.session_state["wattwise_user"] = uinfo
                        st.success(f"Welcome back, {uinfo['username']}!")
                        st.rerun()
                    else:
                        st.error(msg)

        with register_tab:
            with st.form("register_form"):
                st.markdown("#### Register New Account")
                r_user = st.text_input("Choose Username", key="r_user").strip()
                r_pass = st.text_input("Choose Password", type="password", key="r_pass", help="Minimum 8 characters with at least one letter and one number.")
                r_pass_conf = st.text_input("Confirm Password", type="password", key="r_pass_conf")
                btn_reg = st.form_submit_button("Register Account", use_container_width=True)
                if btn_reg:
                    if r_pass != r_pass_conf:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg, _ = register_user(r_user, r_pass, role="user")
                        if ok:
                            st.success(msg + " You can now sign in using the 'Sign In' tab.")
                        else:
                            st.error(msg)

    st.stop()

current_user = st.session_state.get("wattwise_user", {"id": 1, "username": "guest", "role": "user"})

# ---------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------
st.sidebar.markdown("""
<div style="padding:8px 4px 18px">
  <div style="font-size:12px;letter-spacing:3px;color:#35d8f2;font-weight:700">WATTWISE / ANALYTICS</div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:24px;font-weight:700;margin-top:6px">Energy Protocol</div>
  <div style="font-size:12px;color:#94a6c4;margin-top:4px">Advanced Household Intelligence</div>
</div>
""", unsafe_allow_html=True)

# User session indicator in sidebar
is_admin = (current_user.get("role") == "admin")
badge_class = "badge-high" if is_admin else "badge-moderate"
role_display = "🛡️ ADMIN" if is_admin else "👤 USER"

st.sidebar.markdown(f"""
<div style="padding:10px 14px; background:linear-gradient(135deg,rgba(20,43,72,0.7),rgba(17,26,43,0.7)); border:1px solid #2a3b57; border-radius:14px; margin-bottom:12px">
  <div style="font-size:10px; text-transform:uppercase; color:#94a6c4; letter-spacing:1.5px; font-weight:700">AUTHENTICATED AS</div>
  <div style="font-size:16px; font-weight:700; color:#f5f9ff; margin-top:2px">{current_user['username']}</div>
  <div style="margin-top:6px">
    <span class="{badge_class}">{role_display}</span>
  </div>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state.pop("wattwise_user", None)
    st.rerun()

pages = {
    "◈  Overview": "overview",
    "⌁  Consumption analysis": "consumption",
    "△  Anomaly detection": "anomaly",
    "⎇  Change-Point Detection": "changepoint",
    "☵  Consumption Behaviour Profiling": "profiling",
    "⚡ Smart Energy Savings Tracker": "savings",
    "🌱 Carbon Footprint Intelligence": "carbon",
    "✧  Energy efficiency": "efficiency",
    "◎  Intelligent Insights & Report": "insights",
    "📁 Custom Dataset Upload": "upload",
    "▤  SQL analytics": "sql",
}

if is_admin:
    pages["🛡️  Admin Console"] = "admin_console"

selected_label = st.sidebar.radio("WORKSPACE", list(pages.keys()), label_visibility="visible")
page = pages[selected_label]

st.sidebar.markdown("---")
st.sidebar.markdown("**ACTIVE DATASET**")
if is_custom_dataset:
    st.sidebar.markdown(f'<span class="source-pill-upload">Custom: {data_source}</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown(f'<span class="source-pill-default">Default: {DATA_FILE.name}</span>', unsafe_allow_html=True)

st.sidebar.caption("● Loaded successfully")
st.sidebar.write(f"**Records** `{len(df):,}`")
st.sidebar.write(f"**Coverage** `{start_date:%d %b %Y} — {end_date:%d %b %Y}`")

if is_custom_dataset:
    if st.sidebar.button("↺ Restore default dataset", use_container_width=True):
        st.session_state["wattwise_active_df"] = default_df
        st.session_state["wattwise_data_source"] = DATA_FILE.name
        st.session_state["wattwise_is_custom"] = False
        st.session_state["wattwise_upload_version"] += 1
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit · Pandas · Plotly · Scikit-Learn")
st.sidebar.caption("Persistence: SQLite · Reporting: ReportLab")

# ---------------------------------------------------------
# PDF REPORT ENGINE
# ---------------------------------------------------------
def make_pdf_report(data: pd.DataFrame, daily_series: pd.Series, source_name: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm, title="Electricity Consumption Analysis Report"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=24, leading=29, textColor=colors.HexColor("#12233f"),
                              alignment=TA_CENTER, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubTitleCustom", parent=styles["Normal"], fontSize=10,
                              leading=15, textColor=colors.HexColor("#53657f"), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="SectionCustom", parent=styles["Heading2"], fontSize=13,
                              leading=17, textColor=colors.HexColor("#087f9c"), spaceBefore=11, spaceAfter=6))
    styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=8.5,
                              leading=12, textColor=colors.HexColor("#26344a"), spaceAfter=5))
    story = []
    story += [Spacer(1, 25*mm), Paragraph("ELECTRICITY CONSUMPTION", styles["CoverTitle"]),
              Paragraph("ANALYSIS & CARBON INTELLIGENCE REPORT", styles["CoverTitle"]),
              Spacer(1, 4*mm),
              Paragraph("Household energy usage · Exploratory analysis · Emissions & savings audit", styles["SubTitleCustom"]),
              Spacer(1, 10*mm)]
    cover_data = [
        ["Report generated", datetime.now().strftime("%d %B %Y, %H:%M")],
        ["Active source file", source_name],
        ["Usable records", f"{len(data):,}"],
        ["Coverage period", f"{data['DateTime'].min():%d %b %Y} – {data['DateTime'].max():%d %b %Y}"],
        ["Daily observations", f"{len(daily_series):,}"],
    ]
    table = Table(cover_data, colWidths=[48*mm, 95*mm], hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#eaf4fa")),
        ("TEXTCOLOR", (0,0), (-1,-1), colors.HexColor("#20324c")),
        ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#d3deea")),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story += [table, Spacer(1, 15*mm),
              Paragraph("Prepared from household electricity measurements. Consumption is derived from active-power readings at minute resolution.", styles["SubTitleCustom"]),
              PageBreak()]

    # 1. Executive summary
    story.append(Paragraph("1. Executive summary", styles["SectionCustom"]))
    summary_text = (
        f"The dataset contains {len(data):,} usable records from {data['DateTime'].min():%d %B %Y} "
        f"to {data['DateTime'].max():%d %B %Y}. Total estimated observed consumption is "
        f"{daily_series.sum():,.2f} kWh across {len(daily_series):,} days, with a daily mean of "
        f"{daily_series.mean():,.2f} kWh/day. Peak consumption was recorded on "
        f"{daily_series.idxmax():%d %B %Y} ({daily_series.max():,.2f} kWh)."
        if not daily_series.empty else "No daily consumption observations were available."
    )
    story.append(Paragraph(summary_text, styles["BodyCustom"]))

    # 2. Dataset overview
    story.append(Paragraph("2. Dataset overview", styles["SectionCustom"]))
    overview = [
        ["Item", "Value"],
        ["Source file", source_name],
        ["Rows analyzed", f"{len(data):,}"],
        ["Columns available", f"{len(data.columns):,}"],
        ["Date range", f"{data['DateTime'].min():%Y-%m-%d} to {data['DateTime'].max():%Y-%m-%d}"],
        ["Numeric fields", ", ".join(data.select_dtypes(include="number").columns)],
    ]
    t = Table(overview, colWidths=[48*mm, 120*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#142b49")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#d5deea")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f7fb")]),
        ("FONTSIZE",(0,0),(-1,-1),8), ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(t)

    # 3. Daily statistics
    story.append(Paragraph("3. Daily consumption statistics", styles["SectionCustom"]))
    stats = daily_series.describe(percentiles=[.25,.5,.75])
    stat_rows = [["Statistic", "Observed value"]]
    for label, value in [
        ("Number of daily observations", len(daily_series)),
        ("Total observed consumption (kWh)", daily_series.sum()),
        ("Mean (kWh/day)", stats.get("mean", float("nan"))),
        ("Median (kWh/day)", stats.get("50%", float("nan"))),
        ("Standard deviation (kWh/day)", stats.get("std", float("nan"))),
        ("Minimum (kWh/day)", stats.get("min", float("nan"))),
        ("25th percentile (kWh/day)", stats.get("25%", float("nan"))),
        ("75th percentile (kWh/day)", stats.get("75%", float("nan"))),
        ("Maximum (kWh/day)", stats.get("max", float("nan"))),
    ]:
        stat_rows.append([str(label), f"{value:,.2f}" if isinstance(value, (int,float)) else str(value)])
    t_stat = Table(stat_rows, colWidths=[90*mm, 65*mm], repeatRows=1)
    t_stat.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#142b49")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#d5deea")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f7fb")]),
        ("FONTSIZE",(0,0),(-1,-1),8), ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(t_stat)

    # 4. Carbon Footprint Intelligence
    story.append(Paragraph("4. Carbon footprint intelligence", styles["SectionCustom"]))
    tot_kwh = float(daily_series.sum())
    carb_est = calculate_emissions(tot_kwh, CEA_NATIONAL_GRID_FACTOR)
    carb_rows = [
        ["Emissions Parameter", "Value"],
        ["Total Observed Electricity", f"{tot_kwh:,.2f} kWh"],
        ["Emissions Factor Applied", f"{CEA_NATIONAL_GRID_FACTOR:.3f} kg CO2e/kWh"],
        ["Benchmark Standard", "Central Electricity Authority (CEA) of India, CO2 Baseline Database (Ver 19.0)"],
        ["Estimated Emissions (kg CO2e)", f"{carb_est['emissions_kg']:,.2f} kg CO2e"],
        ["Estimated Emissions (Tonnes CO2e)", f"{carb_est['emissions_tonnes']:,.4f} Tonnes CO2e"],
        ["Average Daily Emissions", f"{carb_est['emissions_kg']/max(1, len(daily_series)):,.2f} kg CO2e/day"],
    ]
    t_carb = Table(carb_rows, colWidths=[65*mm, 100*mm], repeatRows=1)
    t_carb.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#142b49")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#d5deea")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f7fb")]),
        ("FONTSIZE",(0,0),(-1,-1),8), ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(t_carb)

    # 5. Sub-meter summary
    story.append(Paragraph("5. Sub-meter summary", styles["SectionCustom"]))
    sub_cols = [c for c in ["Sub_metering_1","Sub_metering_2","Sub_metering_3"] if c in data.columns]
    if sub_cols:
        sub_rows = [["Sub-meter", "Observed total (kWh)", "Mean per record"]]
        labels = {"Sub_metering_1":"Kitchen appliances", "Sub_metering_2":"Laundry appliances", "Sub_metering_3":"Water heater / AC"}
        for col in sub_cols:
            sub_rows.append([labels.get(col,col), f"{data[col].sum()/1000:,.2f}", f"{data[col].mean():,.3f}"])
        t_sub = Table(sub_rows, colWidths=[65*mm, 55*mm, 45*mm], repeatRows=1)
        t_sub.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#142b49")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#d5deea")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f7fb")]),
            ("FONTSIZE",(0,0),(-1,-1),8), ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ]))
        story.append(t_sub)
    else:
        story.append(Paragraph("Sub-metering columns were not present in the loaded dataset.", styles["BodyCustom"]))

    # 6. Limitations & Assumptions
    story.append(Paragraph("6. Limitations & scientific assumptions", styles["SectionCustom"]))
    limitations = [
        "Daily kWh is estimated by summing active-power readings and dividing by 60, assuming readings are approximately one minute apart.",
        "Rows missing DateTime or Global_active_power are excluded. Missing readings can cause observed totals to be underestimated.",
        "Emissions are estimated using the static Indian National Grid weighted average factor (0.716 kg CO2e/kWh) and do not account for time-of-day marginal grid emission swings.",
        "Observed reductions following energy-saving interventions indicate statistical shifts, not guaranteed causal savings.",
    ]
    for item in limitations:
        story.append(Paragraph("• " + item, styles["BodyCustom"]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d5deea"))
        canvas.line(18*mm, 14*mm, A4[0]-18*mm, 14*mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#63748c"))
        canvas.drawString(18*mm, 9*mm, "WattWise Electricity Protocol · Household Energy Intelligence Report")
        canvas.drawRightString(A4[0]-18*mm, 9*mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()

# ---------------------------------------------------------
# PAGE ROUTING
# ---------------------------------------------------------

# =========================================================
# 1. OVERVIEW
# =========================================================
if page == "overview":
    st.markdown(f"""
    <div class="watt-hero">
      <div class="watt-kicker">◈ ENERGY INTELLIGENCE / OVERVIEW</div>
      <div class="watt-title">Electricity Consumption<br>Analysis Dashboard</div>
      <div class="watt-sub">Explore household electricity patterns, compare consumption over time, and turn measured readings into actionable energy intelligence.</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"Data coverage: {start_date:%d %B %Y} — {end_date:%d %B %Y}  ·  {len(df):,} usable records  ·  Source: {data_source}")

    a,b,c,d = st.columns(4)
    with a: kpi("Total observed consumption", f"{total_kwh:,.2f} kWh", "Estimated from available minute-level active-power readings.")
    with b: kpi("Average daily consumption", f"{average_daily_kwh:,.2f} kWh/day")
    with c: kpi("Peak daily consumption", f"{peak_kwh:,.2f} kWh")
    with d: kpi("Usable records", f"{len(df):,}")

    st.markdown("---")
    left, right = st.columns([1.65, 1])
    with left:
        section_heading("⌁", "Daily consumption trend", "Estimated daily kWh based on available active-power readings.")
        fig = px.area(daily.rename_axis("Date").reset_index(), x="Date", y="Consumption (kWh)",
                      color_discrete_sequence=[CHART_COLORS[0]])
        fig.update_traces(line=dict(width=2), fillcolor="rgba(53,216,242,.12)")
        st.plotly_chart(polish(fig, 370), use_container_width=True)
    with right:
        section_heading("▥", "Monthly overview", "Total observed consumption by month.")
        if not monthly.empty:
            mdf = monthly.rename_axis("Month").reset_index()
            mdf["Month"] = mdf["Month"].dt.strftime("%b %Y")
            fig = px.bar(mdf, x="Month", y="Consumption (kWh)", color_discrete_sequence=[CHART_COLORS[1]])
            fig.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(polish(fig, 370), use_container_width=True)
        else:
            st.info("Monthly data is not available.")

    st.markdown("---")
    section_heading("▤", "Dataset preview", "First ten rows from the active dataset.")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)
    st.info("Interpretation note: removed or missing readings may cause observed consumption totals to be underestimated. Electricity cost and formal efficiency scores are not estimated without a tariff and validated scoring method.")

# =========================================================
# 2. CONSUMPTION ANALYSIS
# =========================================================
elif page == "consumption":
    st.markdown('<div class="watt-kicker">⌁ CONSUMPTION / EXPLORE</div>', unsafe_allow_html=True)
    st.title("Consumption analysis")
    st.write("Choose a date window and aggregation level to explore observed household electricity usage.")

    min_date, max_date = df["DateTime"].min().date(), df["DateTime"].max().date()
    f1, f2, f3 = st.columns([1,1,1])
    with f1: from_date = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
    with f2: to_date = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)
    with f3: period = st.selectbox("Trend granularity", ["Daily", "Weekly", "Monthly"])

    if from_date > to_date:
        st.warning("Start date must be on or before end date.")
        st.stop()

    filtered = df[(df["DateTime"].dt.date >= from_date) & (df["DateTime"].dt.date <= to_date)].copy()
    if filtered.empty:
        st.warning("No records found for the selected date range.")
        st.stop()

    selected_daily = filtered.set_index("DateTime")["Global_active_power"].resample("D").sum().div(60).rename("Consumption (kWh)").dropna()

    if period == "Daily":
        chart_series = selected_daily
        average_label, peak_label, unit_label = "Average per day", "Highest-consumption day", "kWh/day"
        peak_period = chart_series.idxmax() if not chart_series.empty else None
        peak_value = float(chart_series.max()) if not chart_series.empty else 0.0
        peak_display = f"{peak_value:,.2f} kWh"
    elif period == "Weekly":
        chart_series = selected_daily.resample("W-SUN").sum().dropna()
        average_label, peak_label, unit_label = "Average per week", "Highest-consumption week", "kWh/week"
        peak_period = chart_series.idxmax() if not chart_series.empty else None
        peak_value = float(chart_series.max()) if not chart_series.empty else 0.0
        peak_display = f"{peak_value:,.2f} kWh"
    else:
        chart_series = selected_daily.resample("MS").sum().dropna()
        average_label, peak_label, unit_label = "Average per month", "Highest-consumption month", "kWh/month"
        peak_period = chart_series.idxmax() if not chart_series.empty else None
        peak_value = float(chart_series.max()) if not chart_series.empty else 0.0
        peak_display = f"{peak_value:,.2f} kWh"

    c1,c2,c3 = st.columns(3)
    with c1: kpi("Selected-range total", f"{chart_series.sum():,.2f} kWh")
    with c2: kpi(average_label, f"{chart_series.mean():,.2f} {unit_label}" if not chart_series.empty else "N/A")
    with c3: kpi(peak_label, peak_display if not chart_series.empty else "N/A")

    if peak_period is not None:
        if period == "Daily":
            peak_period_label = f"Peak date: {peak_period:%d %B %Y}"
        elif period == "Weekly":
            peak_period_label = f"Peak week ending: {peak_period:%d %B %Y}"
        else:
            peak_period_label = f"Peak month: {peak_period:%B %Y}"
        st.info(peak_period_label)

    chart_frame = chart_series.rename_axis("Date").rename("Consumption (kWh)").reset_index()
    fig = px.line(chart_frame, x="Date", y="Consumption (kWh)",
                  markers=(period=="Daily"), color_discrete_sequence=[CHART_COLORS[0]])
    fig.update_layout(title=f"{period} electricity consumption")
    fig.update_traces(line=dict(width=2.5), name=f"{period} consumption", showlegend=False)
    st.plotly_chart(polish(fig, 390), use_container_width=True)

    st.markdown("---")
    section_heading("▥", "Sub-metering comparison", "Observed sub-meter values converted to kWh using interval interpretation.")
    sub_cols = [c for c in ["Sub_metering_1","Sub_metering_2","Sub_metering_3"] if c in filtered.columns]
    if sub_cols:
        totals = filtered[sub_cols].sum()/1000
        labels = {"Sub_metering_1":"Kitchen appliances","Sub_metering_2":"Laundry appliances","Sub_metering_3":"Water heater / AC"}
        sub_df = pd.DataFrame({"Category":[labels.get(c,c) for c in sub_cols],"Observed energy (kWh)":totals.values})
        x,y = st.columns([1.2,1])
        with x:
            fig = px.bar(sub_df, x="Category", y="Observed energy (kWh)", color="Category", color_discrete_sequence=CHART_COLORS)
            fig.update_layout(showlegend=False)
            st.plotly_chart(polish(fig, 330), use_container_width=True)
        with y:
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Sub-metering columns were not found in the active dataset.")

# =========================================================
# 3. ANOMALY DETECTION (IQR OUTLIERS)
# =========================================================
elif page == "anomaly":
    st.markdown('<div class="watt-kicker">△ OUTLIER REVIEW / IQR</div>', unsafe_allow_html=True)
    st.title("Anomaly detection")
    st.write("Flags unusually high daily consumption using the interquartile range (IQR). A flagged day is a statistical outlier, not automatically an error or fault.")

    q1, q3 = daily.quantile(.25), daily.quantile(.75)
    iqr = q3 - q1
    lower_limit, upper_limit = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    unusual_days = daily[daily > upper_limit].sort_values(ascending=False)

    a,b,c = st.columns(3)
    with a: kpi("High-consumption days", f"{len(unusual_days):,}")
    with b: kpi("Upper IQR threshold", f"{upper_limit:.2f} kWh/day")
    with c: kpi("Highest flagged day", f"{unusual_days.max():.2f} kWh" if not unusual_days.empty else "None")

    plot_df = daily.rename("Daily consumption (kWh)").to_frame()
    plot_df["Upper IQR threshold"] = upper_limit

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["Daily consumption (kWh)"], name="Daily consumption", line=dict(color=CHART_COLORS[0], width=2)))
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["Upper IQR threshold"], name="Upper IQR threshold", line=dict(color=CHART_COLORS[4], width=2, dash="dash")))
    fig.update_layout(
        showlegend=True,
        margin=dict(l=10, r=10, t=20, b=55),
    )
    section_heading("△", "Daily consumption vs. anomaly threshold", "The dashed line marks the IQR threshold used to flag unusually high days.")
    st.plotly_chart(polish(fig, 390), use_container_width=True)

    section_heading("△", "Flagged dates", "Sorted from highest to lowest observed consumption.")
    if unusual_days.empty:
        st.success("No days exceeded the current upper IQR threshold.")
    else:
        outlier_table = unusual_days.rename("Consumption (kWh)").rename_axis("Date").reset_index()
        display_table = outlier_table.copy()
        display_table["Date"] = pd.to_datetime(display_table["Date"]).dt.strftime("%d-%m-%Y")
        st.dataframe(display_table, use_container_width=True, hide_index=True)
        st.download_button(
            "↓ Export flagged days (Excel)",
            make_excel_bytes(outlier_table, ["Date"]),
            "high_consumption_days.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    st.caption(f"IQR lower limit: {lower_limit:.2f} kWh/day · Upper limit: {upper_limit:.2f} kWh/day. This view flags high values only.")

# =========================================================
# FEATURE 3: CHANGE-POINT DETECTION
# =========================================================
elif page == "changepoint":
    st.markdown('<div class="watt-kicker">⎇ STRUCTURAL SHIFTS / REGIME DETECTION</div>', unsafe_allow_html=True)
    st.title("Electricity Consumption Change-Point Detection")
    st.write(
        "Detects sustained structural shifts in consumption patterns over time. "
        "Unlike Point Anomaly Detection (which flags individual outlier days), Change-Point Detection "
        "identifies persistent level shifts (step increases or decreases) in baseline electricity usage."
    )

    c1, c2, c3, c4 = st.columns([1, 1.2, 1, 1])
    with c1:
        cp_granularity = st.selectbox("Aggregation interval", ["Daily", "Weekly"], index=0)
    with c2:
        cp_method = st.selectbox("Detection method", ["Offline CUSUM (Taylor)", "Binary Segmentation (Welch t-test)"])
    with c3:
        cp_threshold = st.slider("Sensitivity threshold", min_value=0.8, max_value=2.5, value=1.25, step=0.05,
                                 help="Lower threshold increases sensitivity (more points); higher threshold requires stronger statistical evidence.")
    with c4:
        cp_min_segment = st.slider("Min segment length", min_value=7, max_value=45, value=14, step=1,
                                   help="Minimum number of observations required between consecutive change points.")

    # Prepare series
    analysis_series = daily if cp_granularity == "Daily" else daily.resample("W-SUN").sum().dropna()

    if len(analysis_series) < 2 * cp_min_segment:
        st.warning(f"Not enough observations ({len(analysis_series)}) for the selected minimum segment length ({cp_min_segment}).")
        st.stop()

    if "CUSUM" in cp_method:
        detected_indices, diag_df = detect_cusum_changepoints(
            analysis_series, threshold=cp_threshold, min_segment_length=cp_min_segment
        )
    else:
        sig_alpha = 0.05 if cp_threshold <= 1.2 else 0.01
        detected_indices = detect_binary_segmentation_changepoints(
            analysis_series, min_segment_length=cp_min_segment, significance_alpha=sig_alpha
        )

    summary_df = summarize_changepoints(analysis_series, detected_indices, window_days=cp_min_segment * 2)

    k1, k2, k3 = st.columns(3)
    with k1: kpi("Detected Change-Points", f"{len(detected_indices):,}")
    with k2: kpi("Mean Series Consumption", f"{analysis_series.mean():,.2f} kWh/{'day' if cp_granularity=='Daily' else 'wk'}")
    with k3: kpi("Analysis Observations", f"{len(analysis_series):,} {cp_granularity.lower()} intervals")

    # Time series visualization with change points
    fig_cp = go.Figure()
    fig_cp.add_trace(go.Scatter(
        x=analysis_series.index, y=analysis_series.values,
        name=f"Observed {cp_granularity} Consumption",
        line=dict(color=CHART_COLORS[0], width=1.8),
    ))

    # Mark detected points and segment horizontal means
    boundary_points = [0] + detected_indices + [len(analysis_series)]
    for i in range(len(boundary_points) - 1):
        s_idx, e_idx = boundary_points[i], boundary_points[i + 1]
        seg_vals = analysis_series.iloc[s_idx:e_idx]
        seg_mean = float(seg_vals.mean())
        seg_x = analysis_series.index[s_idx:e_idx]
        fig_cp.add_trace(go.Scatter(
            x=seg_x, y=[seg_mean] * len(seg_x),
            mode="lines",
            name="Regime Baseline Mean",
            showlegend=(i == 0),
            line=dict(color="#ffb86b", width=2.2, dash="dash"),
            hoverinfo="y+name",
        ))

    # Clean vertical dashed lines for detected change points (without cluttered overlapping text)
    for idx in detected_indices:
        cp_d = analysis_series.index[idx]
        fig_cp.add_vline(
            x=cp_d, line_width=1.5, line_dash="dash", line_color="#ff719a",
        )

    fig_cp.update_layout(
        title=None,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        ),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    section_heading("⎇", "Interactive Consumption Regimes", "Vertical pink dashed lines mark detected change points; orange dashed lines show regime averages.")
    st.plotly_chart(polish(fig_cp, 390, show_legend=True), use_container_width=True)

    section_heading("▤", "Structural Shift Summary", "Comparison of consumption stats before and after each detected change-point.")
    if summary_df.empty:
        st.info("No statistically significant persistent change points were detected at the current sensitivity setting.")
    else:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        st.download_button(
            "↓ Export change-points (Excel)",
            make_excel_bytes(summary_df),
            "consumption_changepoints.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Synthetic Benchmark Validation Bench (Strictly isolated from dashboard data)
    with st.expander("🧪 Statistically Validate Algorithm on Synthetic Benchmark (Ground Truth)"):
        st.write(
            "This interactive test generates a controlled synthetic time series with a known, injected step jump "
            "to demonstrate algorithm detection sensitivity without altering the dashboard dataset."
        )
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1: syn_base = st.number_input("Synthetic Base Mean (kWh)", value=15.0, step=1.0)
        with s_col2: syn_shift = st.number_input("Injected Step Jump (kWh)", value=12.0, step=1.0)
        with s_col3: syn_day = st.slider("Injected Change Day", min_value=20, max_value=80, value=50)

        synth_series, true_cp = generate_synthetic_validation_series(
            n_days=100, base_mean=syn_base, shift_size=syn_shift, noise_std=2.0, changepoint_day=syn_day, seed=42
        )
        synth_detected, _ = detect_cusum_changepoints(synth_series, threshold=1.2, min_segment_length=10)

        fig_syn = go.Figure()
        fig_syn.add_trace(go.Scatter(x=list(range(len(synth_series))), y=synth_series.values, name="Synthetic Series (Labeled)", line=dict(color="#6388ff")))
        fig_syn.add_vline(x=true_cp, line_color="#42d392", line_width=2, annotation_text=f"True Jump Day: {true_cp}", annotation_position="top left")
        for d in synth_detected:
            fig_syn.add_vline(x=d, line_color="#ff719a", line_dash="dash", annotation_text=f"Detected: Day {d}", annotation_position="bottom right")
        fig_syn.update_layout(title="Synthetic Validation Test Bench (Known Ground Truth vs Detection)")
        st.plotly_chart(polish(fig_syn, 320), use_container_width=True)

        if synth_detected:
            diff_days = abs(synth_detected[0] - true_cp)
            st.success(f"Algorithm successfully detected the synthetic step shift within {diff_days} day(s) of the ground truth (True Day {true_cp} vs Detected Day {synth_detected[0]}).")

# =========================================================
# FEATURE 2: CONSUMPTION BEHAVIOUR PROFILING (K-MEANS)
# =========================================================
elif page == "profiling":
    st.markdown('<div class="watt-kicker">☵ MACHINE LEARNING / K-MEANS PROFILING</div>', unsafe_allow_html=True)
    st.title("Consumption Behaviour Profiling")
    st.write(
        "Groups days or weeks into distinct behavioural profiles using K-Means clustering. "
        "Engineers multi-dimensional consumption features (total energy, peak power, daytime vs overnight baseload, evening load, and weekend dynamics)."
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        prof_granularity = st.selectbox("Profiling resolution", ["Daily", "Weekly"], index=0)
    with c2:
        n_clusters = st.slider("Number of clusters (k)", min_value=2, max_value=6, value=3, step=1)
    with c3:
        seed = st.number_input("Reproducible random seed", value=42, step=1)

    with st.spinner("Extracting behavioural features and fitting K-Means…"):
        feat_df = extract_behavioural_features(df, granularity=prof_granularity)
        if len(feat_df) < n_clusters:
            st.error(f"Dataset has only {len(feat_df)} observations; at least {n_clusters} are required.")
            st.stop()
        clustered_df, ctx = run_kmeans_clustering(feat_df, n_clusters=n_clusters, random_state=int(seed))

    sil_score = ctx.get("silhouette_score")
    var_ratio = ctx.get("pca_variance_ratio", [0, 0])

    m1, m2, m3, m4 = st.columns(4)
    with m1: kpi("Total Observations", f"{len(clustered_df):,} {prof_granularity.lower()} periods")
    with m2: kpi("Clusters Formed", f"{n_clusters}")
    with m3:
        sil_label = f"{sil_score:.3f}" if sil_score is not None else "N/A"
        kpi("Silhouette Score", sil_label, "Measures cluster separation (-1 to +1). Values > 0.35 indicate distinct clusters.")
    with m4:
        pca_tot = sum(var_ratio) * 100.0
        kpi("2D PCA Explained Variance", f"{pca_tot:.1f}%", "Proportion of multi-dimensional feature variance captured by the 2D projection.")

    st.markdown("---")
    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        section_heading("☵", "2D PCA Cluster Projection", f"PC1 ({var_ratio[0]*100:.1f}%) and PC2 ({var_ratio[1]*100:.1f}%) capture key behavioral axes.")
        fig_pca = px.scatter(
            clustered_df, x="pca1", y="pca2", color="cluster_label",
            labels={"cluster_label": "Cluster Profile"},
            hover_data=["period_str", "total_kwh", "peak_power_kw", "evening_kwh"],
            color_discrete_sequence=CHART_COLORS,
        )
        fig_pca.update_traces(marker=dict(size=7, opacity=0.85))
        fig_pca.update_layout(
            xaxis_title="Principal Component 1", yaxis_title="Principal Component 2",
        )
        st.plotly_chart(polish(fig_pca, 390, show_legend=True), use_container_width=True)

    with right_col:
        section_heading("▥", "Cluster Characteristics Comparison", "Average daily consumption across discovered profiles.")
        prof_summary = []
        for c_id, prof in ctx["cluster_profiles"].items():
            prof_summary.append({
                "Cluster": f"Cluster {c_id + 1}",
                "Profile": prof["name"],
                "Count": prof["count"],
                "Share (%)": f"{prof['percentage']:.1f}%",
                "Mean kWh": round(prof["mean_kwh"], 2),
                "Peak kW": round(prof["peak_kw"], 2),
                "Evening kWh": round(prof["evening_kwh"], 2),
                "Overnight kWh": round(prof["overnight_kwh"], 2),
            })
        prof_df = pd.DataFrame(prof_summary)
        fig_bar = px.bar(
            prof_df, x="Cluster", y="Mean kWh", color="Cluster",
            hover_data=["Profile", "Peak kW", "Share (%)"],
            color_discrete_sequence=CHART_COLORS, text="Mean kWh"
        )
        fig_bar.update_traces(texttemplate="%{text:.1f} kWh", textposition="outside")
        fig_bar.update_layout(
            showlegend=False,
            xaxis=dict(tickangle=0, title="Cluster"),
            yaxis=dict(title="Mean Daily Consumption (kWh)"),
        )
        st.plotly_chart(polish(fig_bar, 390, show_legend=False), use_container_width=True)

    section_heading("▤", "Discovered Behavioural Profiles Table", "Detailed statistical summary of each cluster.")
    st.dataframe(prof_df, use_container_width=True, hide_index=True)

    section_heading("🔍", "Cluster Data Explorer", "Filter and explore specific dates or weeks assigned to each cluster.")
    selected_cluster_label = st.selectbox("Select cluster to inspect", list(ctx["cluster_labels_map"].values()))
    subset_cluster = clustered_df[clustered_df["cluster_label"] == selected_cluster_label][
        ["period_str", "total_kwh", "peak_power_kw", "std_power_kw", "evening_kwh", "overnight_kwh", "peak_to_avg_ratio"]
    ].rename(columns={
        "period_str": "Date / Period", "total_kwh": "Total kWh", "peak_power_kw": "Peak kW",
        "std_power_kw": "Variability (kW)", "evening_kwh": "Evening kWh", "overnight_kwh": "Overnight kWh",
        "peak_to_avg_ratio": "Peak/Avg Ratio"
    })
    st.dataframe(subset_cluster.head(100), use_container_width=True, hide_index=True)

# =========================================================
# FEATURE 1: SMART ENERGY SAVINGS TRACKER
# =========================================================
elif page == "savings":
    st.markdown('<div class="watt-kicker">⚡ INTERVENTION TRACKER / SQLITE PERSISTENCE</div>', unsafe_allow_html=True)
    st.title("Smart Energy Savings Tracker")
    st.write(
        "Record household energy-saving actions (e.g. LED retrofits, thermostat adjustments, appliance upgrades) "
        "and empirically evaluate consumption changes between equivalent baseline and follow-up periods using SQLite."
    )

    if current_user.get("role") == "admin":
        st.caption("🛡️ **Administrator Mode**: Viewing and managing all recorded interventions across the system.")
    else:
        st.caption(f"👤 **User Workspace**: Displaying records associated with your account (**{current_user['username']}**).")

    all_actions = get_all_saving_actions(user_id=current_user["id"], role=current_user["role"])

    # Headline summary metrics
    s1, s2, s3 = st.columns(3)
    with s1: kpi("Recorded Interventions", f"{len(all_actions):,}")
    with s2:
        evaluated_count = 0
        total_daily_saved = 0.0
        for _, act in all_actions.iterrows():
            ev = evaluate_action_impact(
                daily, pd.to_datetime(act["action_date"]).date(),
                baseline_days=int(act["baseline_days"]), followup_days=int(act["followup_days"]),
                tariff_inr=float(act["tariff_inr"])
            )
            if ev.get("status") == "success":
                evaluated_count += 1
                total_daily_saved += ev.get("estimated_daily_cost_diff", 0.0)
        kpi("Evaluated Actions", f"{evaluated_count:,}")
    with s3:
        kpi("Observed Cost Difference", f"₹{total_daily_saved:,.2f}/day", "Sum of estimated daily cost differences across all evaluated actions.")

    st.markdown("---")
    tab_new, tab_manage = st.tabs(["⚡ Log New Energy-Saving Action", "📋 Manage & Evaluate Recorded Actions"])

    with tab_new:
        with st.form("new_action_form", clear_on_submit=True):
            st.markdown("#### Enter Intervention Details")
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                action_name = st.text_input("Action Name / Description", placeholder="e.g. Replaced incandescent bulbs with LEDs")
                action_preset = st.selectbox("Action Category", ACTION_PRESETS)
                action_date_val = st.date_input(
                    "Intervention Date",
                    value=min(max_date, max(min_date, min_date + timedelta(days=60))),
                    min_value=min_date, max_value=max_date,
                    help="Date on which the energy-saving action took place."
                )
            with f_col2:
                tariff_val = st.number_input("Electricity Tariff (₹/kWh)", value=7.50, min_value=0.0, step=0.25)
                w_col1, w_col2 = st.columns(2)
                with w_col1:
                    base_days = st.selectbox("Baseline window (days)", [7, 14, 21, 30], index=1)
                with w_col2:
                    follow_days = st.selectbox("Follow-up window (days)", [7, 14, 21, 30], index=1)
                notes_val = st.text_area("Optional Notes", placeholder="e.g. 5x 60W bulbs replaced in living room and kitchen.")

            submit_action = st.form_submit_button("Save Action to Database", use_container_width=True)
            if submit_action:
                if not action_name.strip():
                    st.error("Please provide an action name.")
                else:
                    new_id = add_saving_action(
                        action_name=action_name,
                        action_category=action_preset,
                        action_date=str(action_date_val),
                        baseline_days=base_days,
                        followup_days=follow_days,
                        tariff_inr=tariff_val,
                        notes=notes_val,
                        user_id=current_user["id"],
                        username=current_user["username"],
                    )
                    st.success(f"Action '{action_name}' logged successfully with ID #{new_id} in SQLite database!")
                    st.rerun()

    with tab_manage:
        if all_actions.empty:
            st.info("No energy-saving actions recorded yet. Use the 'Log New Energy-Saving Action' tab above to record your first action.")
        else:
            st.dataframe(all_actions, use_container_width=True, hide_index=True)

            selected_act_id = st.selectbox(
                "Select action to evaluate or manage",
                options=all_actions["id"].tolist(),
                format_func=lambda x: f"#{x} - {all_actions.loc[all_actions['id']==x, 'action_name'].values[0]} ({all_actions.loc[all_actions['id']==x, 'action_date'].values[0]})"
            )

            chosen_record = all_actions[all_actions["id"] == selected_act_id].iloc[0]
            act_date = pd.to_datetime(chosen_record["action_date"]).date()

            eval_res = evaluate_action_impact(
                daily_series=daily,
                action_date=act_date,
                baseline_days=int(chosen_record["baseline_days"]),
                followup_days=int(chosen_record["followup_days"]),
                tariff_inr=float(chosen_record["tariff_inr"]),
            )

            if eval_res["status"] == "success":
                e1, e2, e3, e4 = st.columns(4)
                with e1: kpi("Baseline Mean", f"{eval_res['baseline_mean_kwh']:.2f} kWh/day", f"{eval_res['baseline_days_evaluated']} days analyzed")
                with e2: kpi("Follow-Up Mean", f"{eval_res['followup_mean_kwh']:.2f} kWh/day", f"{eval_res['followup_days_evaluated']} days analyzed")
                with e3:
                    diff_sym = "▼" if eval_res['absolute_daily_diff_kwh'] >= 0 else "▲"
                    kpi("Observed Daily Diff", f"{diff_sym} {abs(eval_res['absolute_daily_diff_kwh']):.2f} kWh/day", f"{eval_res['percentage_change']:+.1f}% shift")
                with e4:
                    kpi("Est. Period Cost Diff", f"₹{eval_res['estimated_period_cost_diff']:,.2f}", f"Over {eval_res['followup_days_evaluated']} follow-up days @ ₹{chosen_record['tariff_inr']}/kWh")

                # Before vs After Timeline Chart
                b_series = eval_res["baseline_data"]
                f_series = eval_res["followup_data"]
                combined_window = pd.concat([b_series, f_series]).sort_index()

                fig_act = go.Figure()
                fig_act.add_trace(go.Scatter(x=combined_window.index, y=combined_window.values, name="Daily Consumption", line=dict(color=CHART_COLORS[0], width=2)))
                fig_act.add_vline(x=str(act_date), line_color="#ff719a", line_dash="dash", line_width=2,
                                  annotation_text=f"Action: {chosen_record['action_name']}", annotation_position="top left")
                # Baseline mean line
                fig_act.add_trace(go.Scatter(
                    x=b_series.index, y=[eval_res['baseline_mean_kwh']] * len(b_series),
                    name="Baseline Mean", line=dict(color="#ffb86b", width=2, dash="dot")
                ))
                # Followup mean line
                fig_act.add_trace(go.Scatter(
                    x=f_series.index, y=[eval_res['followup_mean_kwh']] * len(f_series),
                    name="Follow-Up Mean", line=dict(color="#42d392", width=2, dash="dot")
                ))
                fig_act.update_layout(title="Empirical Before-and-After Comparison Window")
                st.plotly_chart(polish(fig_act, 350), use_container_width=True)

                st.caption("Scientific integrity notice: Observed consumption change does not prove direct causation. Weather, seasonal transitions, appliance usage cycles, and occupancy variations may also contribute.")
            else:
                st.warning(eval_res.get("message", "Unable to evaluate action impact."))

            # Update or Delete Record
            st.markdown("---")
            u_col1, u_col2 = st.columns(2)
            with u_col1:
                with st.expander("✏️ Edit Action Record"):
                    with st.form("edit_action_form"):
                        up_name = st.text_input("Name", value=chosen_record["action_name"])
                        up_cat = st.selectbox("Category", ACTION_PRESETS, index=ACTION_PRESETS.index(chosen_record["action_category"]) if chosen_record["action_category"] in ACTION_PRESETS else 0)
                        up_date = st.date_input("Date", value=act_date, min_value=min_date, max_value=max_date)
                        up_b_days = st.number_input("Baseline Days", value=int(chosen_record["baseline_days"]), min_value=3, max_value=60)
                        up_f_days = st.number_input("Follow-up Days", value=int(chosen_record["followup_days"]), min_value=3, max_value=60)
                        up_tariff = st.number_input("Tariff (₹/kWh)", value=float(chosen_record["tariff_inr"]), min_value=0.0)
                        up_notes = st.text_area("Notes", value=chosen_record["notes"] or "")
                        if st.form_submit_button("Update Action"):
                            ok_up = update_saving_action(
                                action_id=selected_act_id, action_name=up_name, action_category=up_cat,
                                action_date=str(up_date), baseline_days=int(up_b_days),
                                followup_days=int(up_f_days), tariff_inr=up_tariff, notes=up_notes,
                                user_id=current_user["id"], role=current_user["role"]
                            )
                            if ok_up:
                                st.success("Action updated successfully!")
                                st.rerun()
                            else:
                                st.error("Permission denied: You cannot edit an action belonging to another user.")

            with u_col2:
                with st.expander("🗑️ Delete Action Record"):
                    st.write(f"Are you sure you want to delete action **#{selected_act_id}** (`{chosen_record['action_name']}`)?")
                    confirm_del = st.checkbox("I confirm deletion of this persistent database record", key=f"del_chk_{selected_act_id}")
                    if st.button("Delete Action", type="primary", disabled=not confirm_del):
                        ok_del = delete_saving_action(
                            action_id=selected_act_id,
                            user_id=current_user["id"],
                            role=current_user["role"]
                        )
                        if ok_del:
                            st.success(f"Action #{selected_act_id} deleted from database.")
                            st.rerun()
                        else:
                            st.error("Permission denied: You cannot delete an action belonging to another user.")

# =========================================================
# FEATURE 4: CARBON FOOTPRINT INTELLIGENCE
# =========================================================
elif page == "carbon":
    st.markdown('<div class="watt-kicker">🌱 ENVIRONMENTAL METRICS / GHG EMISSIONS</div>', unsafe_allow_html=True)
    st.title("Carbon Footprint Intelligence")
    st.write(
        "Estimate greenhouse gas emissions associated with electricity consumption using verified, "
        "transparent emissions factors from the Central Electricity Authority (CEA), Government of India."
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        c_from = st.date_input("Emissions start date", value=min_date, min_value=min_date, max_value=max_date)
    with c2:
        c_to = st.date_input("Emissions end date", value=max_date, min_value=min_date, max_value=max_date)
    with c3:
        factor_choice = st.selectbox("Grid emissions factor preset", list(PRESET_EMISSION_FACTORS.keys()) + ["Custom Factor"])

    if factor_choice == "Custom Factor":
        active_factor = st.number_input("Custom Emission Factor (kg CO₂e/kWh)", value=0.716, min_value=0.05, max_value=2.0, step=0.01)
        factor_source = "User-configured custom factor"
        factor_scope = "User-defined scope"
    else:
        preset_info = PRESET_EMISSION_FACTORS[factor_choice]
        active_factor = preset_info["factor"]
        factor_source = preset_info["source"]
        factor_scope = preset_info["scope"]

    st.caption(f"**Active Emission Factor:** `{active_factor:.3f} kg CO₂e/kWh`  ·  **Source:** {factor_source}  ·  **Scope:** {factor_scope}")

    filtered_carbon_daily = daily[(daily.index.date >= c_from) & (daily.index.date <= c_to)]
    if filtered_carbon_daily.empty:
        st.warning("No consumption records found for the selected date range.")
        st.stop()

    carbon_tot_kwh = float(filtered_carbon_daily.sum())
    carbon_res = calculate_emissions(carbon_tot_kwh, active_factor)
    daily_em_df = compute_daily_emissions(filtered_carbon_daily, active_factor)
    monthly_em_df = compute_monthly_emissions(filtered_carbon_daily, active_factor)

    m1, m2, m3, m4 = st.columns(4)
    with m1: kpi("Total Consumption", f"{carbon_tot_kwh:,.2f} kWh")
    with m2: kpi("Estimated Emissions", f"{carbon_res['emissions_kg']:,.2f} kg CO₂e")
    with m3: kpi("Estimated Carbon", f"{carbon_res['emissions_tonnes']:,.4f} Tonnes CO₂e")
    with m4:
        avg_daily_em = carbon_res["emissions_kg"] / max(1, len(filtered_carbon_daily))
        kpi("Daily Emissions Rate", f"{avg_daily_em:,.2f} kg/day")

    st.markdown("---")
    left_c, right_c = st.columns([1.5, 1])

    with left_c:
        section_heading("🌱", "Daily Carbon Emissions Trend", "Daily greenhouse gas emissions computed from active power readings.")
        fig_carb_daily = px.area(daily_em_df, x="Date", y="Emissions (kg CO2e)", color_discrete_sequence=["#42d392"])
        fig_carb_daily.update_traces(line=dict(width=1.5), fillcolor="rgba(66,211,146,.12)")
        st.plotly_chart(polish(fig_carb_daily, 370), use_container_width=True)

    with right_c:
        section_heading("▥", "Monthly Carbon Footprint", "Monthly total emissions in kilograms of CO₂e.")
        if not monthly_em_df.empty:
            fig_carb_mon = px.bar(monthly_em_df, x="Month_Label", y="Emissions (kg CO2e)", color_discrete_sequence=["#35d8f2"])
            fig_carb_mon.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(polish(fig_carb_mon, 370), use_container_width=True)
        else:
            st.info("Monthly carbon totals not available.")

    section_heading("▲", "Highest-Emission Days", "Top 10 highest carbon emitting days in the selected date range.")
    top_carbon_days = find_highest_emission_days(filtered_carbon_daily, active_factor, top_n=10)
    st.dataframe(top_carbon_days, use_container_width=True, hide_index=True)

    st.info(
        "Methodology & Limitations: Carbon emissions are estimated using the static Indian National Grid weighted average factor (CEA Database Ver 19). "
        "Actual emissions depend on real-time dispatch curves and regional generation sources. Reductions in electricity use translate directly to avoidance of grid marginal emissions."
    )

# =========================================================
# 5. ENERGY USAGE REVIEW (PRESERVED)
# =========================================================
elif page == "efficiency":
    st.markdown('<div class="watt-kicker">✧ USAGE REVIEW / OPPORTUNITIES</div>', unsafe_allow_html=True)
    st.title("Energy usage review")
    st.write("Use observed patterns to identify days and categories worth investigating. This page does not assign an unsupported official efficiency score.")

    a,b,c = st.columns(3)
    with a: kpi("Average daily consumption", f"{average_daily_kwh:.2f} kWh")
    with b: kpi("Peak day", f"{peak_kwh:.2f} kWh · {peak_date:%d %b %Y}" if peak_date is not None else "N/A")
    with c: kpi("Peak vs. average", f"{peak_kwh/average_daily_kwh:.1f}×" if average_daily_kwh > 0 else "N/A")

    histogram_data = daily.rename_axis("Date").rename("Consumption (kWh)").reset_index()
    section_heading("▥", "Distribution of daily consumption", "Shows how frequently daily totals fall into different consumption ranges.")
    fig = px.histogram(histogram_data, x="Consumption (kWh)", nbins=35, color_discrete_sequence=[CHART_COLORS[2]])
    fig.update_layout(showlegend=False, title=None, margin=dict(l=10, r=10, t=24, b=10),
                      xaxis_title="Daily consumption (kWh)", yaxis_title="Number of days")
    st.plotly_chart(polish(fig, 360), use_container_width=True)

    st.markdown("### Recommendations based on consumption")
    recommendation_items = []
    if average_daily_kwh > 0 and peak_kwh >= 1.5 * average_daily_kwh and peak_date is not None:
        recommendation_items.append((
            "Investigate the peak-use day",
            f"Consumption reached {peak_kwh:.2f} kWh on {peak_date:%d %B %Y}, about {peak_kwh / average_daily_kwh:.1f}× the overall daily average. Check which appliances were used that day."
        ))
    else:
        recommendation_items.append((
            "Review high-use days",
            "Sort daily totals from highest to lowest and compare the largest values with normal household activity before treating them as avoidable waste."
        ))

    if not monthly.empty and len(monthly) >= 2:
        high_month = monthly.idxmax()
        low_month = monthly.idxmin()
        recommendation_items.append((
            "Compare high- and low-use months",
            f"Observed monthly use was highest in {high_month:%B %Y} ({monthly.max():,.2f} kWh) and lowest in {low_month:%B %Y} ({monthly.min():,.2f} kWh). Compare seasonal routines."
        ))

    sub_cols = [c for c in ["Sub_metering_1", "Sub_metering_2", "Sub_metering_3"] if c in df.columns]
    if sub_cols:
        sub_totals = (df[sub_cols].sum() / 1000).sort_values(ascending=False)
        sub_names = {"Sub_metering_1": "kitchen appliances", "Sub_metering_2": "laundry appliances", "Sub_metering_3": "water heater / AC"}
        largest_sub = sub_totals.index[0]
        recommendation_items.append((
            "Start with the largest measured sub-meter",
            f"Among the recorded sub-meter categories, {sub_names.get(largest_sub, largest_sub)} has the largest observed total ({sub_totals.iloc[0]:,.2f} kWh). Review usage patterns in that category first."
        ))

    recommendation_items.append((
        "Try practical, low-cost changes",
        "Switch off devices when not needed, avoid leaving high-power appliances running unnecessarily, and use efficient settings for heating, cooling, and laundry where applicable."
    ))

    for row_start in range(0, len(recommendation_items), 2):
        cols = st.columns(2)
        for col, item in zip(cols, recommendation_items[row_start:row_start + 2]):
            title, detail = item
            with col:
                st.markdown(f'<div class="small-card"><h4>{title}</h4><p>{detail}</p></div>', unsafe_allow_html=True)
        if row_start + 2 < len(recommendation_items):
            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

# =========================================================
# FEATURE 6: INTELLIGENT INSIGHTS & REPORT
# =========================================================
elif page == "insights":
    st.markdown('<div class="watt-kicker">◎ STATISTICAL RIGOR / EVIDENCE-GRADED INSIGHTS</div>', unsafe_allow_html=True)
    st.title("Intelligent Insights & Findings")
    st.write("Confidence-aware, statistically grounded analytical findings derived directly from the active dataset.")

    highest_month = monthly.idxmax() if not monthly.empty else None
    lowest_month = monthly.idxmin() if not monthly.empty else None

    # Summary metrics cards
    row1_left, row1_right = st.columns(2, gap="large")
    with row1_left:
        with st.container(border=True):
            st.markdown("#### ◈ Dataset coverage")
            st.metric("Usable records", f"{len(df):,}")
            st.caption(f"{start_date:%d %b %Y} — {end_date:%d %b %Y}")
    with row1_right:
        with st.container(border=True):
            st.markdown("#### △ Peak consumption")
            st.metric("Highest daily total", f"{peak_kwh:,.2f} kWh")
            if peak_date is not None:
                st.caption(f"Recorded on {peak_date:%d %B %Y}")

    row2_left, row2_right = st.columns(2, gap="large")
    with row2_left:
        with st.container(border=True):
            st.markdown("#### ⌁ Daily consumption")
            metric_left, metric_right = st.columns([1, 1], gap="small")
            with metric_left:
                st.markdown(
                    f'<div class="finding-metric"><div class="finding-metric-label">Daily average</div>'
                    f'<div class="finding-metric-value">{average_daily_kwh:,.2f}</div>'
                    '<div class="finding-metric-unit">kWh/day</div></div>',
                    unsafe_allow_html=True,
                )
            with metric_right:
                st.markdown(
                    f'<div class="finding-metric"><div class="finding-metric-label">Total observed</div>'
                    f'<div class="finding-metric-value finding-total-value">{total_kwh:,.2f}</div>'
                    '<div class="finding-metric-unit">kWh</div></div>',
                    unsafe_allow_html=True,
                )
            st.caption("Estimated from available minute-level active-power readings.")
    with row2_right:
        with st.container(border=True):
            st.markdown("#### ▥ Monthly extremes")
            if highest_month is not None and lowest_month is not None:
                month_left, month_right = st.columns([1, 1], gap="small")
                with month_left:
                    st.markdown(
                        f'<div class="finding-metric"><div class="finding-metric-label">Highest month</div>'
                        f'<div class="finding-metric-value finding-month-value">{highest_month:%b %Y}</div>'
                        f'<div class="finding-metric-unit">{monthly.max():,.2f} kWh</div></div>',
                        unsafe_allow_html=True,
                    )
                with month_right:
                    st.markdown(
                        f'<div class="finding-metric"><div class="finding-metric-label">Lowest month</div>'
                        f'<div class="finding-metric-value finding-month-value">{lowest_month:%b %Y}</div>'
                        f'<div class="finding-metric-unit">{monthly.min():,.2f} kWh</div></div>',
                        unsafe_allow_html=True,
                    )
                st.write("")
                st.write("")
            else:
                st.caption("Monthly totals are not available for this dataset.")

    st.markdown("---")
    section_heading("💡", "Confidence-Aware Intelligent Insights", "Evidence-graded findings based on statistical tests (two-sample t-tests, IQR, quantile filtering).")

    insights_list = generate_intelligent_insights(df, daily)
    badge_classes = {
        "HIGH": "badge-high",
        "MODERATE": "badge-moderate",
        "LOW": "badge-low",
    }

    for ins in insights_list:
        with st.container(border=True):
            head_col, badge_col = st.columns([3, 1])
            with head_col:
                st.markdown(f"### {ins.title}")
                st.caption(f"Category: **{ins.category}** · Date Range: {ins.date_range}")
            with badge_col:
                b_cls = badge_classes.get(ins.confidence_level, "badge-moderate")
                st.markdown(f'<div style="text-align:right;"><span class="{b_cls}">● {ins.confidence_level} EVIDENCE</span></div>', unsafe_allow_html=True)
                st.caption(f"<div style='text-align:right;'>{ins.confidence_rationale}</div>", unsafe_allow_html=True)

            st.write(f"**Observation:** {ins.observation}")

            stat_items = [f"**{k}**: `{v}`" for k, v in ins.supporting_stats.items()]
            st.markdown(" · ".join(stat_items))

            st.markdown(f"**Methodology:** *{ins.rule_or_method}*")
            st.markdown(f"**Explanation:** {ins.explanation}")
            st.info(f"💡 **Practical Recommendation:** {ins.recommendation}")

            with st.expander("Analytical Limitations & Scientific Caveats"):
                for lim in ins.limitations:
                    st.markdown(f"- {lim}")

    st.markdown("---")
    st.markdown("### Export comprehensive report")
    st.caption("Generate a detailed formal PDF report including executive summaries, emissions audits, and sub-meter statistics.")
    try:
        pdf_bytes = make_pdf_report(df, daily, data_source)
        st.download_button("↓ Download Detailed PDF Report", data=pdf_bytes,
                           file_name="electricity_consumption_analysis_report.pdf",
                           mime="application/pdf", type="primary", use_container_width=False)
    except Exception as exc:
        st.error(f"Could not generate PDF report: {exc}")

    csv_summary = pd.DataFrame({
        "Metric":["Usable records","Start date","End date","Total observed consumption (kWh)","Average daily consumption (kWh/day)","Peak daily consumption (kWh)","Peak date"],
        "Value":[len(df), str(start_date), str(end_date), round(total_kwh,2), round(average_daily_kwh,2), round(peak_kwh,2), str(peak_date)]
    })
    csv_summary["Value"] = csv_summary["Value"].astype(str)
    csv_summary.loc[csv_summary["Metric"].isin(["Start date", "End date", "Peak date"]), "Value"] = [
        pd.to_datetime(v, errors="coerce").strftime("%d-%m-%Y") if pd.notna(pd.to_datetime(v, errors="coerce")) else "N/A"
        for v in csv_summary.loc[csv_summary["Metric"].isin(["Start date", "End date", "Peak date"]), "Value"]
    ]
    st.download_button(
        "↓ Download key metrics (Excel)",
        make_excel_bytes(csv_summary),
        "electricity_key_metrics.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# =========================================================
# FEATURE 5: CUSTOM DATASET UPLOAD
# =========================================================
elif page == "upload":
    st.markdown('<div class="watt-kicker">📁 CUSTOM DATA / SAFE AUDIT & MAPPING</div>', unsafe_allow_html=True)
    st.title("Custom Dataset Upload")
    st.write(
        "Analyze your own household electricity CSV files without altering the original dataset or database. "
        "Uploaded files are validated, audited for quality, and kept temporarily in memory for the active browser session only."
    )

    st.markdown("""
    > [!IMPORTANT]
    > **Data Safety Guarantee:** Uploaded datasets are processed in memory and never overwrite `cleaned_electricity_data.csv` or alter the SQLite database.
    """)

    u_file = st.file_uploader("Select electricity consumption CSV file", type=["csv"], key=f"uploader_{st.session_state['wattwise_upload_version']}")

    if u_file is not None:
        file_bytes = u_file.getvalue()
        try:
            raw_preview = pd.read_csv(BytesIO(file_bytes), nrows=10)
            raw_columns = list(raw_preview.columns)
            cand_map = detect_candidate_columns(raw_columns)

            st.success(f"File `{u_file.name}` parsed ({len(file_bytes)/1024/1024:.2f} MB). Detected {len(raw_columns)} columns.")

            st.markdown("### 1. Column Mapping Configuration")
            st.caption("Verify or adjust auto-detected column roles:")

            m_c1, m_c2 = st.columns(2)
            with m_c1:
                col_options_with_none = ["-- Select --"] + raw_columns
                dt_def = cand_map["datetime"] if cand_map["datetime"] in raw_columns else "-- Select --"
                date_def = cand_map["date"] if cand_map["date"] in raw_columns else "-- Select --"
                time_def = cand_map["time"] if cand_map["time"] in raw_columns else "-- Select --"

                chosen_dt = st.selectbox("Combined DateTime Column", col_options_with_none, index=col_options_with_none.index(dt_def))
                chosen_date = st.selectbox("Or Separate Date Column", col_options_with_none, index=col_options_with_none.index(date_def))
                chosen_time = st.selectbox("Separate Time Column", col_options_with_none, index=col_options_with_none.index(time_def))

            with m_c2:
                power_def = cand_map["power"] if cand_map["power"] in raw_columns else raw_columns[0]
                chosen_power = st.selectbox("Electricity Power / Consumption Column", raw_columns, index=raw_columns.index(power_def))
                power_unit_val = st.selectbox("Measurement Unit", [
                    "kW (approx. 1-minute interval)",
                    "Watts (W)",
                    "Daily kWh (pre-aggregated)"
                ])

            with st.expander("Optional: Sub-Metering Column Mapping"):
                s_c1, s_c2, s_c3 = st.columns(3)
                sub1_def = cand_map["sub1"] if cand_map["sub1"] in raw_columns else "-- None --"
                sub2_def = cand_map["sub2"] if cand_map["sub2"] in raw_columns else "-- None --"
                sub3_def = cand_map["sub3"] if cand_map["sub3"] in raw_columns else "-- None --"
                with s_c1: sel_sub1 = st.selectbox("Sub 1 (Kitchen)", ["-- None --"] + raw_columns, index=(["-- None --"] + raw_columns).index(sub1_def))
                with s_c2: sel_sub2 = st.selectbox("Sub 2 (Laundry)", ["-- None --"] + raw_columns, index=(["-- None --"] + raw_columns).index(sub2_def))
                with s_c3: sel_sub3 = st.selectbox("Sub 3 (Water Heater / AC)", ["-- None --"] + raw_columns, index=(["-- None --"] + raw_columns).index(sub3_def))

            # Run validation
            cleaned_custom, report, issues = validate_and_transform_uploaded_csv(
                file_bytes=file_bytes,
                datetime_col=chosen_dt if chosen_dt != "-- Select --" else None,
                date_col=chosen_date if chosen_date != "-- Select --" else None,
                time_col=chosen_time if chosen_time != "-- Select --" else None,
                power_col=chosen_power,
                power_unit=power_unit_val,
                sub1_col=sel_sub1 if sel_sub1 != "-- None --" else None,
                sub2_col=sel_sub2 if sel_sub2 != "-- None --" else None,
                sub3_col=sel_sub3 if sel_sub3 != "-- None --" else None,
            )

            st.markdown("### 2. Data Quality Audit Report")
            if issues:
                with st.expander("⚠️ Data Preprocessing Warnings & Corrections", expanded=True):
                    for issue in issues:
                        st.markdown(f"- {issue}")

            if cleaned_custom is not None:
                q1, q2, q3, q4 = st.columns(4)
                with q1: kpi("Raw Uploaded Rows", f"{report.get('total_rows', 0):,}")
                with q2: kpi("Usable Clean Rows", f"{report.get('usable_rows', 0):,}")
                with q3: kpi("Mean Active Power", f"{report.get('mean_power', 0.0):.2f} kW")
                with q4: kpi("Date Span", f"{report.get('start_date', 'N/A')[:10]} to {report.get('end_date', 'N/A')[:10]}")

                st.dataframe(cleaned_custom.head(8), use_container_width=True, hide_index=True)

                st.markdown("### 3. Confirmation")
                if st.button("✓ Apply Uploaded Dataset to Active Dashboard Session", type="primary", use_container_width=True):
                    st.session_state["wattwise_active_df"] = cleaned_custom
                    st.session_state["wattwise_data_source"] = u_file.name
                    st.session_state["wattwise_is_custom"] = True
                    st.success(f"Dashboard switched to uploaded dataset: '{u_file.name}'!")
                    st.rerun()
            else:
                st.error("Cannot apply this dataset until column mapping issues are resolved.")

        except Exception as exc:
            st.error(f"Error inspecting uploaded CSV: {exc}")

    st.markdown("---")
    st.markdown("### Active Session Management")
    if is_custom_dataset:
        st.write(f"Active Session is currently analyzing: **{data_source}**")
        if st.button("↺ Restore Project Default Dataset", use_container_width=True):
            st.session_state["wattwise_active_df"] = default_df
            st.session_state["wattwise_data_source"] = DATA_FILE.name
            st.session_state["wattwise_is_custom"] = False
            st.session_state["wattwise_upload_version"] += 1
            st.success("Default project dataset restored!")
            st.rerun()
    else:
        st.info(f"Active Session is using the default project dataset: **{DATA_FILE.name}** ({len(df):,} records).")

# =========================================================
# 7. SQL ANALYTICS (CONNECTED TO SQLITE)
# =========================================================
elif page == "sql":
    st.markdown('<div class="watt-kicker">▤ DATA STRUCTURE / LIVE SQL QUERY ENGINE</div>', unsafe_allow_html=True)
    st.title("SQL Analytics")
    st.write(
        "Execute live, read-only SQL queries directly against the `electricity.db` SQLite database "
        "(containing 2,049,280 electricity records and persistent energy-saving action logs)."
    )

    query_templates = {
        "Monthly Consumption & Peak Power": """SELECT strftime('%Y-%m', Datetime) AS month,
       ROUND(SUM(Global_active_power) / 60, 2) AS total_kwh,
       ROUND(AVG(Global_active_power), 3) AS avg_power_kw,
       ROUND(MAX(Global_active_power), 3) AS peak_power_kw,
       COUNT(*) AS reading_count
FROM electricity_data
GROUP BY strftime('%Y-%m', Datetime)
ORDER BY month DESC;""",

        "Top 10 Peak Consumption Hours": """SELECT Date, Hour,
       ROUND(SUM(Global_active_power) / 60, 2) AS hour_kwh,
       ROUND(MAX(Global_active_power), 2) AS max_kw
FROM electricity_data
GROUP BY Date, Hour
ORDER BY hour_kwh DESC
LIMIT 10;""",

        "Sub-metering Energy Breakdown": """SELECT ROUND(SUM(Sub_metering_1) / 1000, 2) AS kitchen_kwh,
       ROUND(SUM(Sub_metering_2) / 1000, 2) AS laundry_kwh,
       ROUND(SUM(Sub_metering_3) / 1000, 2) AS climate_water_kwh,
       ROUND(SUM(Global_active_power) / 60, 2) AS total_kwh
FROM electricity_data;""",

        "Energy-Saving Actions Log": """SELECT id, action_name, action_category, action_date,
       baseline_days, followup_days, tariff_inr, created_at
FROM energy_saving_actions
ORDER BY id DESC;""",

        "Custom Query": "SELECT * FROM electricity_data LIMIT 25;",
    }

    selected_template = st.selectbox("Select SQL Query Template", list(query_templates.keys()))
    sql_text = st.text_area("SQL Statement (Read-only SELECT queries)", value=query_templates[selected_template], height=160)

    if st.button("Execute SQL Query", type="primary"):
        try:
            with st.spinner("Executing query against SQLite database…"):
                result_df = run_readonly_query(sql_text)
            st.success(f"Query returned {len(result_df):,} row(s) successfully.")
            st.dataframe(result_df, use_container_width=True, hide_index=True)
            st.download_button(
                "↓ Export SQL Result (Excel)",
                make_excel_bytes(result_df),
                "sql_query_result.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as exc:
            st.error(f"SQL execution error: {exc}")

# =========================================================
# 8. ADMIN CONSOLE (AUTHENTICATION & RBAC MANAGEMENT)
# =========================================================
elif page == "admin_console":
    st.markdown('<div class="watt-kicker">🛡️ SYSTEM ADMINISTRATION / RBAC ACCESS CONTROL</div>', unsafe_allow_html=True)
    st.title("Admin Console")
    st.write(
        "Manage user accounts, enforce role-based access control, audit account activity, and maintain system security policies. "
        "All administrative actions are verified server-side with strict integrity enforcement."
    )

    if current_user.get("role") != "admin":
        st.error("Access Denied: Administrator privileges are required to view this page.")
        st.stop()

    all_users = get_all_users()
    total_users_count = len(all_users)
    active_users_count = sum(1 for u in all_users if u["is_active"] == 1)
    admin_users_count = sum(1 for u in all_users if u["role"] == "admin" and u["is_active"] == 1)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Total Accounts", f"{total_users_count:,}")
    with c2: kpi("Active Accounts", f"{active_users_count:,}")
    with c3: kpi("Active Admins", f"{admin_users_count:,}")
    with c4: kpi("Security Standard", "PBKDF2-SHA256", "600,000 iterations & 16-byte cryptographic salt")

    st.markdown("---")
    tab_overview, tab_manage, tab_provision = st.tabs([
        "📋 Registered User Accounts",
        "⚙️ Account Permissions & Status",
        "➕ Provision New User / Admin"
    ])

    with tab_overview:
        st.markdown("#### User Registry")
        if not all_users:
            st.info("No registered accounts found in database.")
        else:
            display_users = []
            for u in all_users:
                display_users.append({
                    "User ID": u["id"],
                    "Username": u["username"],
                    "Role": u["role"].upper(),
                    "Status": "Active" if u["is_active"] == 1 else "Deactivated",
                    "Created At": u["created_at"],
                    "Last Login": u["last_login"] or "Never",
                })
            registry_df = pd.DataFrame(display_users)
            st.dataframe(registry_df, use_container_width=True, hide_index=True)

            st.download_button(
                "↓ Export User Registry (Excel)",
                make_excel_bytes(registry_df),
                "wattwise_user_registry.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    with tab_manage:
        st.markdown("#### Manage Account Status & Roles")
        if not all_users:
            st.info("No user accounts available to manage.")
        else:
            user_dict = {
                u["id"]: f"#{u['id']} - {u['username']} ({u['role'].upper()}, {'Active' if u['is_active'] == 1 else 'Deactivated'})"
                for u in all_users
            }
            selected_uid = st.selectbox(
                "Select account to manage",
                options=list(user_dict.keys()),
                format_func=lambda x: user_dict[x]
            )
            target = next(u for u in all_users if u["id"] == selected_uid)

            m_col1, m_col2 = st.columns(2)
            with m_col1:
                with st.container(border=True):
                    st.markdown("##### Account Status (Enable / Deactivate)")
                    st.write(f"Account: **{target['username']}** (ID #{target['id']})")
                    st.write(f"Current Status: `{'Active' if target['is_active'] == 1 else 'Deactivated'}`")

                    is_self = (target["id"] == current_user["id"])
                    if is_self:
                        st.caption("⚠️ Security restriction: You cannot deactivate your own administrative account.")

                    new_status_bool = st.selectbox(
                        "Target Status",
                        options=[True, False],
                        index=0 if target["is_active"] == 1 else 1,
                        format_func=lambda x: "Active (Enabled)" if x else "Deactivated (Disabled)",
                        disabled=is_self,
                        key=f"status_select_{selected_uid}"
                    )

                    if st.button("Apply Status Change", disabled=is_self, key=f"btn_apply_status_{selected_uid}"):
                        ok, msg = update_user_status(
                            target_user_id=selected_uid,
                            new_is_active=new_status_bool,
                            caller_role=current_user["role"],
                            caller_id=current_user["id"],
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            with m_col2:
                with st.container(border=True):
                    st.markdown("##### Role Assignment")
                    st.write(f"Account: **{target['username']}** (ID #{target['id']})")
                    st.write(f"Current Role: `{target['role'].upper()}`")

                    new_role_val = st.selectbox(
                        "Target Role",
                        options=["user", "admin"],
                        index=0 if target["role"] == "user" else 1,
                        format_func=lambda x: x.upper(),
                        key=f"role_select_{selected_uid}"
                    )

                    if st.button("Apply Role Change", key=f"btn_apply_role_{selected_uid}"):
                        ok, msg = update_user_role(
                            target_user_id=selected_uid,
                            new_role=new_role_val,
                            caller_role=current_user["role"],
                            caller_id=current_user["id"],
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    with tab_provision:
        st.markdown("#### Provision New Account Directly")
        with st.form("admin_provision_form", clear_on_submit=True):
            new_u = st.text_input("Username", placeholder="e.g. analyst_user").strip()
            new_p = st.text_input("Password", type="password", help="Must be at least 8 characters with letters and numbers.")
            new_r = st.selectbox("Assign Role", ["user", "admin"], format_func=lambda x: x.upper())
            submit_prov = st.form_submit_button("Create Account", use_container_width=True)
            if submit_prov:
                ok, msg, _ = register_user(new_u, new_p, role=new_r)
                if ok:
                    st.success(f"Account '{new_u}' successfully provisioned with role '{new_r.upper()}'.")
                    st.rerun()
                else:
                    st.error(msg)

st.markdown('<div class="footer-note">WattWise · Electricity Consumption Analysis & Environmental Intelligence · Estimates based on empirical readings and stated assumptions.</div>', unsafe_allow_html=True)
