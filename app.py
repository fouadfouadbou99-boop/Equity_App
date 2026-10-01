import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


# ==========================================================
# DETECTION AUTOMATIQUE DE LA FREQUENCE
# ==========================================================

def detect_frequency_factor(dates):
    dates = pd.to_datetime(dates, errors="coerce").dropna().sort_values()

    if len(dates) < 2:
        return 252, "Quotidien"

    gap = dates.diff().dt.days.median()

    if gap <= 3:
        return 252, "Quotidien"
    if gap <= 10:
        return 52, "Hebdomadaire"
    if gap <= 40:
        return 12, "Mensuel"
    if gap <= 120:
        return 4, "Trimestriel"
    return 1, "Annuel"


# ==========================================================
# NORMALISATION DES RENDEMENTS
# ==========================================================

def normalize_returns(series):
    """Convertit une série de rendements en décimales."""
    series = pd.to_numeric(series, errors="coerce")
    valid = series.dropna()

    if valid.empty:
        return series

    max_abs = valid.abs().max()
    if pd.isna(max_abs):
        return series

    # Si les valeurs sont exprimées en %, ex: 5 ou 42 -> 0.05 / 0.42
    if max_abs > 1:
        return series / 100.0

    return series


def finite_pair(port, bench):
    pair = pd.DataFrame({"port": port, "bench": bench}).replace([np.inf, -np.inf], np.nan).dropna()
    if pair.empty:
        return np.array([]), np.array([])
    return pair["port"].to_numpy(dtype=float), pair["bench"].to_numpy(dtype=float)


# ==========================================================
# RATIOS FINANCIERS
# ==========================================================

def calculate_beta(port, bench):
    port, bench = finite_pair(port, bench)
    if len(port) < 2:
        return np.nan

    var_bench = np.var(bench, ddof=1)
    if np.isclose(var_bench, 0):
        return np.nan

    return np.cov(port, bench, ddof=1)[0, 1] / var_bench


def calculate_tracking_error(port, bench, annual_factor):
    port, bench = finite_pair(port, bench)
    if len(port) < 2:
        return np.nan

    active = port - bench
    return np.std(active, ddof=1) * np.sqrt(annual_factor)


def calculate_information_ratio(port, bench, annual_factor):
    port, bench = finite_pair(port, bench)
    if len(port) < 2:
        return np.nan

    active = port - bench
    te = np.std(active, ddof=1) * np.sqrt(annual_factor)
    if np.isclose(te, 0):
        return np.nan

    active_annualized = np.mean(active) * annual_factor
    return active_annualized / te


def period_rf_from_annual(annual_rf, annual_factor):
    if annual_rf <= -1:
        return np.nan
    return (1 + annual_rf) ** (1 / annual_factor) - 1


def calculate_sharpe(returns, annual_factor, rf=0):
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2:
        return np.nan

    rf_period = period_rf_from_annual(rf, annual_factor)
    if not np.isfinite(rf_period):
        return np.nan

    excess = returns - rf_period
    vol = np.std(excess, ddof=1)
    if np.isclose(vol, 0):
        return np.nan

    return (np.mean(excess) * annual_factor) / (np.std(returns, ddof=1) * np.sqrt(annual_factor))


def calculate_sortino(returns, annual_factor, rf=0):
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2:
        return np.nan

    rf_period = period_rf_from_annual(rf, annual_factor)
    if not np.isfinite(rf_period):
        return np.nan

    excess = returns - rf_period
    downside = excess[excess < 0]
    if len(downside) == 0:
        return np.nan

    downside_vol = np.std(downside, ddof=1)
    if np.isclose(downside_vol, 0):
        return np.nan

    annual_return = np.mean(excess) * annual_factor
    annual_downside = downside_vol * np.sqrt(annual_factor)
    return annual_return / annual_downside


def calculate_correlation(port, bench):
    port, bench = finite_pair(port, bench)
    if len(port) < 2:
        return np.nan
    return np.corrcoef(port, bench)[0, 1]


def calculate_var(returns, confidence=0.95):
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) == 0:
        return np.nan
    return np.percentile(returns, (1 - confidence) * 100)


def calculate_cvar(returns, confidence=0.95):
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) == 0:
        return np.nan

    var_value = calculate_var(returns, confidence)
    tail = returns[returns <= var_value]
    if len(tail) == 0:
        return np.nan
    return np.mean(tail)


def calculate_max_drawdown(nav_series):
    nav_series = pd.to_numeric(nav_series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if nav_series.empty:
        return np.nan, pd.Series(dtype=float)

    running_max = nav_series.cummax()
    drawdown = nav_series / running_max - 1
    return drawdown.min(), drawdown


def format_value(value, fmt):
    if pd.isna(value):
        return "N/D"
    return format(value, fmt)


# ==========================================================
# EXPORT EXCEL / PDF
# ==========================================================

def generate_excel(df, kpis):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)
        pd.DataFrame(list(kpis.items()), columns=["Indicateur", "Valeur"]).to_excel(
            writer, sheet_name="KPI", index=False
        )
    output.seek(0)
    return output


def generate_pdf(kpis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elems = [Paragraph("Rapport de Performance Financière", styles["Title"]), Spacer(1, 12)]

    for key, value in kpis.items():
        elems.append(Paragraph(f"<b>{key}</b>: {value}", styles["BodyText"]))
        elems.append(Spacer(1, 6))

    doc.build(elems)
    buffer.seek(0)
    return buffer


# ==========================================================
# CONFIGURATION ET CHARGEMENT
# ==========================================================

st.set_page_config(page_title="Dashboard Gestion Actions", layout="wide")
st.title("📈 Dashboard Universel de Performance Financière")
st.markdown("---")

file = st.file_uploader(
    "📁 Importer votre fichier Excel",
    type=["xlsx"],
    help="Format: Date + 2 colonnes Base 100 + 2 colonnes Performance",
)

if file is None:
    st.info("👉 Veuillez importer un fichier Excel pour lancer l'analyse.")
    st.stop()

try:
    df = pd.read_excel(file)
except Exception as exc:
    st.error(f"❌ Erreur de lecture: {exc}")
    st.stop()

if df.empty or df.columns.empty:
    st.error("❌ Le fichier est vide ou ne contient pas de colonnes.")
    st.stop()

date_col = df.columns[0]
try:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
except Exception as exc:
    st.error(f"❌ Erreur de conversion dates: {exc}")
    st.stop()

df = df.dropna(subset=[date_col]).sort_values(date_col).reset_index(drop=True)
if df.empty:
    st.error("❌ Pas de dates valides.")
    st.stop()

annual_factor, frequency = detect_frequency_factor(df[date_col])
st.success(f"✅ Fréquence: **{frequency}** | Annualisation: **{annual_factor}**")

# ==========================================================
# SELECTION DES COLONNES
# ==========================================================

available_cols = [column for column in df.columns if column != date_col]
if len(available_cols) < 4:
    st.error("❌ Besoin de 4 colonnes minimum (Date + 2 Base 100 + 2 Performance).")
    st.stop()

st.subheader("⚙️ Paramétrage")
col1, col2, col3, col4 = st.columns(4)

with col1:
    portfolio_nav = st.selectbox("📊 Portefeuille Base 100", available_cols, index=0)

with col2:
    benchmark_candidates = [c for c in available_cols if c != portfolio_nav]
    benchmark_nav = st.selectbox("📈 Benchmark Base 100", benchmark_candidates, index=0)

remaining_perf = [c for c in available_cols if c not in [portfolio_nav, benchmark_nav]]
if len(remaining_perf) < 2:
    st.error("❌ Besoin de 2 colonnes de performance.")
    st.stop()

with col3:
    portfolio_ret = st.selectbox("📉 Performance Portefeuille", remaining_perf, index=0)

with col4:
    benchmark_ret_candidates = [c for c in remaining_perf if c != portfolio_ret]
    benchmark_ret = st.selectbox("📈 Performance Benchmark", benchmark_ret_candidates, index=0)

if portfolio_nav == benchmark_nav or portfolio_ret == benchmark_ret:
    st.warning("⚠️ Colonnes identiques sélectionnées.")
    st.stop()

# ==========================================================
# DONNEES ET NORMALISATION
# ==========================================================

for column in [portfolio_nav, benchmark_nav, portfolio_ret, benchmark_ret]:
    df[column] = pd.to_numeric(df[column], errors="coerce")

def safe_total_return(series):
    series = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(series) < 2:
        return np.nan
    return series.iloc[-1] / series.iloc[0] - 1

nav_pf = df[portfolio_nav].replace([np.inf, -np.inf], np.nan).dropna()
nav_bm = df[benchmark_nav].replace([np.inf, -np.inf], np.nan).dropna()

perf_pf_total = safe_total_return(nav_pf)
perf_bm_total = safe_total_return(nav_bm)

returns_pf_raw = normalize_returns(df[portfolio_ret])
returns_bm_raw = normalize_returns(df[benchmark_ret])

perf_df = pd.DataFrame({"pf": returns_pf_raw, "bm": returns_bm_raw}).replace([np.inf, -np.inf], np.nan).dropna()
if len(perf_df) < 2:
    st.error("❌ Pas assez de données de rendement alignées.")
    st.stop()

returns_pf = perf_df["pf"].to_numpy(dtype=float)
returns_bm = perf_df["bm"].to_numpy(dtype=float)
active_returns = returns_pf - returns_bm

# ==========================================================
# KPI
# ==========================================================

# Nettoyage final des rendements
returns_pf = returns_pf[np.isfinite(returns_pf)]
returns_bm = returns_bm[np.isfinite(returns_bm)]

returns_pf = returns_pf[returns_pf > -0.9999]
returns_bm = returns_bm[returns_bm > -0.9999]

# ==========================================================
# PERFORMANCE TOTALE
# ==========================================================

perf_pf_total = (
    nav_pf.iloc[-1] / nav_pf.iloc[0]
) - 1

perf_bm_total = (
    nav_bm.iloc[-1] / nav_bm.iloc[0]
) - 1

# ==========================================================
# PERFORMANCE ANNUALISEE
# ==========================================================

nb_obs_pf = len(nav_pf)
nb_obs_bm = len(nav_bm)

annual_return_pf = (
    nav_pf.iloc[-1] / nav_pf.iloc[0]
) ** (
    annual_factor / nb_obs_pf
) - 1

annual_return_bm = (
    nav_bm.iloc[-1] / nav_bm.iloc[0]
) ** (
    annual_factor / nb_obs_bm
) - 1

# ==========================================================
# ALPHA
# ==========================================================

alpha = annual_return_pf - annual_return_bm

# ==========================================================
# BETA
# ==========================================================

beta = calculate_beta(
    returns_pf,
    returns_bm
)

# ==========================================================
# VOLATILITE
# ==========================================================

volatility_pf = (
    np.std(
        returns_pf,
        ddof=1
    )
    * np.sqrt(annual_factor)
)

volatility_bm = (
    np.std(
        returns_bm,
        ddof=1
    )
    * np.sqrt(annual_factor)
)

# ==========================================================
# TRACKING ERROR
# ==========================================================

active_returns = (
    returns_pf
    - returns_bm
)

te = (
    np.std(
        active_returns,
        ddof=1
    )
    * np.sqrt(annual_factor)
)

# ==========================================================
# INFORMATION RATIO
# ==========================================================

if te > 0:
    ir = (
        annual_return_pf
        - annual_return_bm
    ) / te
else:
    ir = np.nan

# ==========================================================
# SHARPE
# ==========================================================

if volatility_pf > 0:
    sharpe = (
        annual_return_pf
        / volatility_pf
    )
else:
    sharpe = np.nan

# ==========================================================
# SORTINO
# ==========================================================

downside_returns = (
    returns_pf[
        returns_pf < 0
    ]
)

if len(downside_returns) > 1:

    downside_vol = (
        np.std(
            downside_returns,
            ddof=1
        )
        * np.sqrt(annual_factor)
    )

    if downside_vol > 0:
        sortino = (
            annual_return_pf
            / downside_vol
        )
    else:
        sortino = np.nan

else:
    sortino = np.nan

# ==========================================================
# CORRELATION
# ==========================================================

corr = calculate_correlation(
    returns_pf,
    returns_bm
)

# ==========================================================
# VAR & CVAR
# ==========================================================

var95 = np.quantile(
    returns_pf,
    0.05
)

cvar95 = np.mean(
    returns_pf[
        returns_pf <= var95
    ]
)

# ==========================================================
# DRAWDOWN
# ==========================================================

max_dd, dd_curve = calculate_max_drawdown(
    df[portfolio_nav]
)

# ==========================================================
# HIT RATIO
# ==========================================================

hit_ratio = (
    active_returns > 0
).mean()

# ==========================================================
# UP CAPTURE
# ==========================================================

up_mask = (
    returns_bm > 0
)

if up_mask.sum() > 0:

    up_capture = (
        np.mean(
            returns_pf[up_mask]
        )
        /
        np.mean(
            returns_bm[up_mask]
        )
    )

else:

    up_capture = np.nan

# ==========================================================
# DOWN CAPTURE
# ==========================================================

down_mask = (
    returns_bm < 0
)

if down_mask.sum() > 0:

    down_capture = (
        np.mean(
            returns_pf[down_mask]
        )
        /
        np.mean(
            returns_bm[down_mask]
        )
    )

else:

    down_capture = np.nan

# ==========================================================
# BATTING AVERAGE
# ==========================================================

batting_average = (
    active_returns > 0
).sum() / len(active_returns)

# ==========================================================
# KPI DICTIONARY
# ==========================================================

kpis = {

    "📅 Fréquence":
        frequency,

    "📊 Annualisation":
        annual_factor,

    f"📈 Perf Totale {portfolio_nav}":
        format_value(
            perf_pf_total,
            ".2%"
        ),

    f"📈 Perf Totale {benchmark_nav}":
        format_value(
            perf_bm_total,
            ".2%"
        ),

    "📈 Perf Annualisée PF":
        format_value(
            annual_return_pf,
            ".2%"
        ),

    "📈 Perf Annualisée BM":
        format_value(
            annual_return_bm,
            ".2%"
        ),

    "🎯 Alpha":
        format_value(
            alpha,
            ".2%"
        ),

    "📉 Beta":
        format_value(
            beta,
            ".2f"
        ),

    f"📊 Vol {portfolio_nav}":
        format_value(
            volatility_pf,
            ".2%"
        ),

    f"📊 Vol {benchmark_nav}":
        format_value(
            volatility_bm,
            ".2%"
        ),

    "🔍 Tracking Error":
        format_value(
            te,
            ".2%"
        ),

    "💡 Information Ratio":
        format_value(
            ir,
            ".2f"
        ),

    "📉 Sharpe":
        format_value(
            sharpe,
            ".2f"
        ),

    "📉 Sortino":
        format_value(
            sortino,
            ".2f"
        ),

    "🔗 Corrélation":
        format_value(
            corr,
            ".2f"
        ),

    "⚠️ VaR 95%":
        format_value(
            var95,
            ".2%"
        ),

    "⚠️ CVaR 95%":
        format_value(
            cvar95,
            ".2%"
        ),

    "📉 Max Drawdown":
        format_value(
            max_dd,
            ".2%"
        ),

    "🎯 Hit Ratio":
        format_value(
            hit_ratio,
            ".2%"
        ),

    "📈 Up Capture":
        format_value(
            up_capture,
            ".2f"
        ),

    "📉 Down Capture":
        format_value(
            down_capture,
            ".2f"
        ),

    "🎯 Batting Average":
        format_value(
            batting_average,
            ".2%"
        )
}
# ==========================================================
# DICTIONNAIRE KPI
# ==========================================================

kpis = {

    "📅 Fréquence":
        frequency,

    "📊 Annualisation":
        annual_factor,

    f"📈 Perf Totale {portfolio_nav}":
        format_value(
            perf_pf_total,
            ".2%"
        ),

    f"📈 Perf Totale {benchmark_nav}":
        format_value(
            perf_bm_total,
            ".2%"
        ),

    "📈 Perf Annualisée PF":
        format_value(
            annual_return_pf,
            ".2%"
        ),

    "📈 Perf Annualisée BM":
        format_value(
            annual_return_bm,
            ".2%"
        ),

    "🎯 Alpha":
        format_value(
            alpha,
            ".2%"
        ),

    "📉 Beta":
        format_value(
            beta,
            ".2f"
        ),

    f"📊 Vol {portfolio_nav}":
        format_value(
            volatility_pf,
            ".2%"
        ),

    f"📊 Vol {benchmark_nav}":
        format_value(
            volatility_bm,
            ".2%"
        ),

    "🔍 Tracking Error":
        format_value(
            te,
            ".2%"
        ),

    "💡 Information Ratio":
        format_value(
            ir,
            ".2f"
        ),

    "📉 Sharpe":
        format_value(
            sharpe,
            ".2f"
        ),

    "📉 Sortino":
        format_value(
            sortino,
            ".2f"
        ),

    "🔗 Corrélation":
        format_value(
            corr,
            ".2f"
        ),

    "⚠️ VaR 95%":
        format_value(
            var95,
            ".2%"
        ),

    "⚠️ CVaR 95%":
        format_value(
            cvar95,
            ".2%"
        ),

    "📉 Max Drawdown":
        format_value(
            max_dd,
            ".2%"
        ),

    "🎯 Hit Ratio":
        format_value(
            hit_ratio,
            ".2%"
        ),

    "📈 Up Capture":
        format_value(
            up_capture,
            ".2f"
        ),

    "📉 Down Capture":
        format_value(
            down_capture,
            ".2f"
        ),

    "🎯 Batting Average":
        format_value(
            batting_average,
            ".2%"
        ),
}
# ==========================================================
# AFFICHAGE
# ==========================================================

st.header("📊 Indicateurs Clés de Performance")
metrics = st.columns(4)
for i, (key, value) in enumerate(kpis.items()):
    metrics[i % 4].metric(key, value)

st.header("📋 Tableau Détaillé")
kpi_df = pd.DataFrame(list(kpis.items()), columns=["Indicateur", "Valeur"])
st.dataframe(kpi_df, use_container_width=True, hide_index=True)

# ==========================================================
# GRAPHIQUES
# ==========================================================

st.header("📈 Visualisations")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Évolution Base 100")
    fig = px.line(df, x=date_col, y=[portfolio_nav, benchmark_nav])
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Rendements Périodiques")
    fig2 = px.bar(df, x=date_col, y=[portfolio_ret, benchmark_ret], barmode="group")
    st.plotly_chart(fig2, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader("Drawdown")
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=df[date_col], y=dd_curve.to_numpy() * 100, fill="tozeroy", line=dict(color="red")))
    fig_dd.update_layout(title="Drawdown (%)", xaxis_title="Date", yaxis_title="Drawdown (%)")
    st.plotly_chart(fig_dd, use_container_width=True)

with col4:
    st.subheader("Distribution Rendements")
    fig_hist = px.histogram(returns_pf * 100, nbins=30, title="Distribution")
    st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================================
# TELECHARGEMENTS
# ==========================================================

st.header("📥 Téléchargements")
col_e1, col_e2, col_e3, col_e4 = st.columns(4)
excel_file = generate_excel(df, kpis)
pdf_file = generate_pdf(kpis)

with col_e1:
    st.download_button("📊 Excel", excel_file, file_name="reporting.xlsx")
with col_e2:
    st.download_button("📄 PDF", pdf_file, file_name="reporting.pdf")
with col_e3:
    st.download_button("📋 CSV", df.to_csv(index=False), file_name="reporting.csv")
with col_e4:
    st.download_button("📦 JSON", df.to_json(orient="records"), file_name="reporting.json")

st.markdown("---")
st.caption("📌 Dashboard Streamlit | Données actualisées en temps réel")
