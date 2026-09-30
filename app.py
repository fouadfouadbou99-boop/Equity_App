import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from io import BytesIO
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

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
    elif gap <= 10:
        return 52, "Hebdomadaire"
    elif gap <= 40:
        return 12, "Mensuel"
    elif gap <= 120:
        return 4, "Trimestriel"
    else:
        return 1, "Annuel"

# ==========================================================
# NORMALISATION DES RENDEMENTS
# ==========================================================

def normalize_returns(series):
    """
    Normalise les rendements en décimales.
    Détecte si c'est des %ages (max > 1) ou des décimales (max <= 1)
    """
    series = pd.to_numeric(series, errors="coerce").dropna()
    if len(series) == 0:
        return series
    
    max_val = series.abs().max()
    
    # Si max > 10, probablement en pourcentages (ex: 50 pour 50%)
    if max_val > 10:
        return series / 100
    # Si entre 1 et 10, probablement aussi en pourcentages (ex: 5 pour 5%)
    elif max_val > 1:
        return series / 100
    # Sinon, déjà en décimales (ex: 0.05 pour 5%)
    else:
        return series

# ==========================================================
# CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Dashboard Gestion Actions",
    layout="wide"
)

st.title("📈 Dashboard Universel de Performance Financière")
st.markdown("---")

# ==========================================================
# FONCTIONS KPI
# ==========================================================

def calculate_beta(port, bench):
    if len(port) < 2 or len(bench) < 2:
        return np.nan

    covariance = np.cov(port, bench)[0, 1]
    variance = np.var(bench, ddof=1)

    if variance == 0:
        return np.nan

    return covariance / variance


def calculate_tracking_error(port, bench, annual_factor):
    if len(port) < 2 or len(bench) < 2:
        return np.nan
    
    diff = port - bench
    return diff.std(ddof=1) * np.sqrt(annual_factor)


def calculate_information_ratio(port, bench, annual_factor):
    if len(port) < 2 or len(bench) < 2:
        return np.nan
    
    active = port - bench
    alpha = active.mean() * annual_factor
    te = active.std(ddof=1) * np.sqrt(annual_factor)

    if te == 0:
        return np.nan

    return alpha / te


def calculate_sharpe(returns, annual_factor, rf=0):
    if len(returns) < 2:
        return np.nan

    annual_return = returns.mean() * annual_factor
    annual_vol = returns.std(ddof=1) * np.sqrt(annual_factor)

    if annual_vol == 0:
        return np.nan

    return (annual_return - rf) / annual_vol


def calculate_sortino(returns, annual_factor, rf=0):
    if len(returns) < 2:
        return np.nan

    downside = returns[returns < 0]

    if len(downside) < 1:
        return np.nan

    downside_vol = downside.std(ddof=1) * np.sqrt(annual_factor) if len(downside) > 1 else 0
    annual_return = returns.mean() * annual_factor

    if downside_vol == 0:
        return np.nan

    return (annual_return - rf) / downside_vol


def calculate_max_drawdown(nav_series):
    if len(nav_series) < 2:
        return np.nan, pd.Series(dtype=float)

    nav_series = pd.to_numeric(nav_series, errors="coerce").dropna()
    if len(nav_series) < 2:
        return np.nan, pd.Series(dtype=float)
    
    roll_max = nav_series.cummax()
    drawdown = (nav_series / roll_max) - 1

    return drawdown.min(), drawdown


def calculate_var(returns, confidence=0.95):
    if len(returns) == 0:
        return np.nan
    return np.percentile(returns, (1 - confidence) * 100)


def calculate_cvar(returns, confidence=0.95):
    if len(returns) == 0:
        return np.nan
    var = calculate_var(returns, confidence)
    return returns[returns <= var].mean()

# ==========================================================
# EXPORT EXCEL
# ==========================================================

def generate_excel(df, kpis):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)
        pd.DataFrame(list(kpis.items()), columns=["Indicateur", "Valeur"]).to_excel(
            writer,
            sheet_name="KPI",
            index=False
        )

    output.seek(0)
    return output


# ==========================================================
# EXPORT PDF
# ==========================================================

def generate_pdf(kpis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elems = []

    elems.append(Paragraph("Rapport de Performance Financière", styles["Title"]))
    elems.append(Spacer(1, 12))

    for k, v in kpis.items():
        elems.append(Paragraph(f"<b>{k}</b>: {v}", styles["BodyText"]))
        elems.append(Spacer(1, 6))

    doc.build(elems)
    buffer.seek(0)
    return buffer


# ==========================================================
# CHARGEMENT FICHIER
# ==========================================================

file = st.file_uploader(
    "📁 Importer votre fichier Excel",
    type=["xlsx"],
    help="Format: Date + 2 colonnes Base 100 + 2 colonnes Performance"
)

if file is None:
    st.info("👉 Veuillez importer un fichier Excel pour lancer l'analyse.")
    st.stop()

try:
    df = pd.read_excel(file)
except Exception as e:
    st.error(f"❌ Erreur de lecture: {str(e)}")
    st.stop()

if df.empty:
    st.error("❌ Le fichier est vide.")
    st.stop()

if df.columns.empty:
    st.error("❌ Pas de colonnes détectées.")
    st.stop()

date_col = df.columns[0]

try:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
except Exception as e:
    st.error(f"❌ Erreur conversion dates: {str(e)}")
    st.stop()

df = df.dropna(subset=[date_col]).reset_index(drop=True)

if df.empty:
    st.error("❌ Pas de dates valides.")
    st.stop()

ANNUAL_FACTOR, FREQUENCE = detect_frequency_factor(df[date_col])

st.success(f"✅ Fréquence: **{FREQUENCE}** | Annualisation: **{ANNUAL_FACTOR}**")

# ==========================================================
# SELECTION DES COLONNES
# ==========================================================

cols = list(df.columns)
available_cols = [c for c in cols if c != date_col]

if len(available_cols) < 4:
    st.error("❌ Besoin de 4 colonnes minimum (Date + 2 Base 100 + 2 Performance)")
    st.stop()

st.subheader("⚙️ Paramétrage")

col1, col2, col3, col4 = st.columns(4)

with col1:
    portfolio_nav = st.selectbox("📊 Portefeuille Base 100", available_cols, index=0)

with col2:
    benchmark_candidates = [c for c in available_cols if c != portfolio_nav]
    benchmark_nav = st.selectbox("📈 Benchmark Base 100", benchmark_candidates, index=0 if len(benchmark_candidates) > 0 else None)

remaining_perf = [c for c in available_cols if c not in [portfolio_nav, benchmark_nav]]

if len(remaining_perf) < 2:
    st.error("❌ Besoin de 2 colonnes de performance.")
    st.stop()

with col3:
    portfolio_ret = st.selectbox("📉 Performance Portefeuille", remaining_perf, index=0)

with col4:
    benchmark_ret_candidates = [c for c in remaining_perf if c != portfolio_ret]
    benchmark_ret = st.selectbox("📈 Performance Benchmark", benchmark_ret_candidates, index=0 if len(benchmark_ret_candidates) > 0 else None)

if portfolio_nav == benchmark_nav or portfolio_ret == benchmark_ret:
    st.warning("⚠️ Colonnes identiques sélectionnées.")
    st.stop()

# ==========================================================
# EXTRACTION ET NORMALISATION DES DONNEES
# ==========================================================

# Colonnes NAV (Base 100) - pour calcul performance globale et drawdown
nav_pf = pd.to_numeric(df[portfolio_nav], errors="coerce")
nav_bm = pd.to_numeric(df[benchmark_nav], errors="coerce")

# Colonnes Performance - pour calcul volatilité, Sharpe, etc.
returns_pf_raw = pd.to_numeric(df[portfolio_ret], errors="coerce")
returns_bm_raw = pd.to_numeric(df[benchmark_ret], errors="coerce")

# Normaliser les rendements
returns_pf = normalize_returns(returns_pf_raw)
returns_bm = normalize_returns(returns_bm_raw)

# Aligner les deux séries
perf_df = pd.DataFrame({
    'pf': returns_pf,
    'bm': returns_bm
}).dropna()

if len(perf_df) < 2:
    st.error("❌ Pas assez de données alignées.")
    st.stop()

returns_pf = perf_df['pf'].values
returns_bm = perf_df['bm'].values

# ==========================================================
# CALCULS DES KPI
# ==========================================================

# Performance globale (NAV)
if len(nav_pf) > 1 and len(nav_bm) > 1:
    perf_pf_total = (nav_pf.iloc[-1] / nav_pf.iloc[0]) - 1
    perf_bm_total = (nav_bm.iloc[-1] / nav_bm.iloc[0]) - 1
else:
    perf_pf_total = np.nan
    perf_bm_total = np.nan

alpha = perf_pf_total - perf_bm_total

# KPI basés sur les rendements normalisés
beta = calculate_beta(returns_pf, returns_bm)
volatility_pf = returns_pf.std(ddof=1) * np.sqrt(ANNUAL_FACTOR)
volatility_bm = returns_bm.std(ddof=1) * np.sqrt(ANNUAL_FACTOR)
te = calculate_tracking_error(returns_pf, returns_bm, ANNUAL_FACTOR)
ir = calculate_information_ratio(returns_pf, returns_bm, ANNUAL_FACTOR)
sharpe = calculate_sharpe(returns_pf, ANNUAL_FACTOR)
sortino = calculate_sortino(returns_pf, ANNUAL_FACTOR)
corr = np.corrcoef(returns_pf, returns_bm)[0, 1]
var95 = calculate_var(returns_pf)
cvar95 = calculate_cvar(returns_pf)

# Drawdown (NAV)
max_dd, dd_curve = calculate_max_drawdown(nav_pf)

# Hit ratio
hit_ratio = (returns_pf > returns_bm).mean()

nom_pf = str(portfolio_nav).strip()
nom_bm = str(benchmark_nav).strip()

# ==========================================================
# CONSTRUCTION KPI
# ==========================================================

kpis = {
    "📅 Fréquence": FREQUENCE,
    "📊 Annualisation": ANNUAL_FACTOR,
    f"📈 Perf {nom_pf}": f"{perf_pf_total:.2%}",
    f"📈 Perf {nom_bm}": f"{perf_bm_total:.2%}",
    f"🎯 Alpha": f"{alpha:.2%}",
    f"📉 Beta": f"{beta:.2f}",
    f"📊 Vol {nom_pf}": f"{volatility_pf:.2%}",
    f"📊 Vol {nom_bm}": f"{volatility_bm:.2%}",
    "🔍 Tracking Error": f"{te:.2%}",
    "💡 Info Ratio": f"{ir:.2f}",
    f"📉 Sharpe": f"{sharpe:.2f}",
    f"📉 Sortino": f"{sortino:.2f}",
    "🔗 Corrélation": f"{corr:.2f}",
    "⚠️ VaR 95%": f"{var95:.2%}",
    "⚠️ CVaR 95%": f"{cvar95:.2%}",
    "📉 Max Drawdown": f"{max_dd:.2%}",
    "🎯 Hit Ratio": f"{hit_ratio:.2%}"
}

# ==========================================================
# AFFICHAGE
# ==========================================================

st.header("📊 Indicateurs Clés de Performance")

metrics = st.columns(4)
compteur = 0

for k, v in kpis.items():
    metrics[compteur % 4].metric(k, v)
    compteur += 1

st.header("📋 Tableau Détaillé")
kpi_df = pd.DataFrame(list(kpis.items()), columns=["Indicateur", "Valeur"])
st.dataframe(kpi_df, use_container_width=True, hide_index=True)

# ==========================================================
# GRAPHIQUES
# ==========================================================

st.header("📈 Visualisations")

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Évolution Base 100")
    fig = px.line(df, x=date_col, y=[portfolio_nav, benchmark_nav])
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

with col_g2:
    st.subheader("Rendements Périodiques")
    fig2 = px.bar(df, x=date_col, y=[portfolio_ret, benchmark_ret], barmode="group")
    st.plotly_chart(fig2, use_container_width=True)

col_g3, col_g4 = st.columns(2)

with col_g3:
    st.subheader("Drawdown")
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=df[date_col], y=dd_curve * 100, fill='tozeroy', line=dict(color='red')))
    fig_dd.update_layout(title="Drawdown (%)", xaxis_title="Date", yaxis_title="Drawdown (%)")
    st.plotly_chart(fig_dd, use_container_width=True)

with col_g4:
    st.subheader("Distribution Rendements")
    fig_hist = px.histogram(returns_pf * 100, nbins=30, title="Distribution")
    st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================================
# EXPORTS
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
