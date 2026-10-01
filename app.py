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
# NORMALISATION ET NETTOYAGE DES RENDEMENTS
# ==========================================================

def normalize_returns(series):
    """Convertit une série de rendements en décimales."""
    series = pd.to_numeric(series, errors="coerce")
    valid = series.dropna()

    if valid.empty:
        return series

    # 5 signifie 5 %, alors que 0.05 signifie déjà 5 %.
    if valid.abs().max() > 1:
        return series / 100
    return series


def finite_pair(port, bench):
    """Retourne deux tableaux alignés, sans NaN ni valeur infinie."""
    pair = pd.DataFrame({"port": port, "bench": bench}).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    return pair["port"].to_numpy(dtype=float), pair["bench"].to_numpy(dtype=float)


# ==========================================================
# CALCUL DES RATIOS
# ==========================================================

def calculate_beta(port, bench):
    port, bench = finite_pair(port, bench)
    if len(port) < 2:
        return np.nan

    benchmark_variance = np.var(bench, ddof=1)
    if np.isclose(benchmark_variance, 0):
        return np.nan

    # Même convention ddof=1 au numérateur et au dénominateur.
    return np.cov(port, bench, ddof=1)[0, 1] / benchmark_variance


def calculate_tracking_error(port, bench, annual_factor):
    port, bench = finite_pair(port, bench)
    if len(port) < 2:
        return np.nan

    active_returns = port - bench
    return np.std(active_returns, ddof=1) * np.sqrt(annual_factor)


def calculate_information_ratio(port, bench, annual_factor):
    """IR = rendement actif annualisé / tracking error annualisé."""
    port, bench = finite_pair(port, bench)
    if len(port) < 2:
        return np.nan

    active_returns = port - bench
    tracking_error = np.std(active_returns, ddof=1) * np.sqrt(annual_factor)
    if np.isclose(tracking_error, 0):
        return np.nan

    annual_active_return = np.mean(active_returns) * annual_factor
    return annual_active_return / tracking_error


def periodic_risk_free_rate(annual_rf, annual_factor):
    """Convertit un taux sans risque annuel en taux par période."""
    if annual_rf <= -1:
        return np.nan
    return (1 + annual_rf) ** (1 / annual_factor) - 1


def calculate_sharpe(returns, annual_factor, rf=0):
    """Sharpe annualisé avec excès de rendement par période."""
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2:
        return np.nan

    periodic_rf = periodic_risk_free_rate(rf, annual_factor)
    if not np.isfinite(periodic_rf):
        return np.nan

    excess_returns = returns - periodic_rf
    volatility = np.std(excess_returns, ddof=1)
    if np.isclose(volatility, 0):
        return np.nan

    return np.mean(excess_returns) * np.sqrt(annual_factor) / volatility


def calculate_sortino(returns, annual_factor, rf=0):
    """Sortino annualisé avec downside deviation (pas l'écart-type des pertes)."""
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2:
        return np.nan

    periodic_rf = periodic_risk_free_rate(rf, annual_factor)
    if not np.isfinite(periodic_rf):
        return np.nan

    excess_returns = returns - periodic_rf
    downside_deviation = np.sqrt(np.mean(np.minimum(excess_returns, 0) ** 2))
    if np.isclose(downside_deviation, 0):
        return np.nan

    annual_excess_return = np.mean(excess_returns) * annual_factor
    annual_downside_deviation = downside_deviation * np.sqrt(annual_factor)
    return annual_excess_return / annual_downside_deviation


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

    var = calculate_var(returns, confidence)
    tail = returns[returns <= var]
    return np.mean(tail) if len(tail) else np.nan


def calculate_max_drawdown(nav_series):
    nav_series = pd.to_numeric(nav_series, errors="coerce")
    nav_series = nav_series.replace([np.inf, -np.inf], np.nan).dropna()
    if nav_series.empty:
        return np.nan, pd.Series(dtype=float)

    cumulative_max = nav_series.cummax()
    drawdown = nav_series / cumulative_max - 1
    return drawdown.min(), drawdown


def format_value(value, fmt):
    return "N/D" if pd.isna(value) else format(value, fmt)


# ==========================================================
# EXPORTS
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
        elems.extend([
            Paragraph(f"<b>{key}</b>: {value}", styles["BodyText"]),
            Spacer(1, 6),
        ])

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
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
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
# EXTRACTION ET ALIGNEMENT DES DONNEES
# ==========================================================

for column in [portfolio_nav, benchmark_nav, portfolio_ret, benchmark_ret]:
    df[column] = pd.to_numeric(df[column], errors="coerce")

nav_df = df[[date_col, portfolio_nav, benchmark_nav]].dropna().reset_index(drop=True)
if len(nav_df) < 2:
    st.error("❌ Pas assez de données Base 100 valides.")
    st.stop()

returns_pf_series = normalize_returns(df[portfolio_ret])
returns_bm_series = normalize_returns(df[benchmark_ret])
perf_df = pd.DataFrame({"pf": returns_pf_series, "bm": returns_bm_series}).replace(
    [np.inf, -np.inf], np.nan
).dropna()

if len(perf_df) < 2:
    st.error("❌ Pas assez de données de rendements alignées.")
    st.stop()

returns_pf = perf_df["pf"].to_numpy(dtype=float)
returns_bm = perf_df["bm"].to_numpy(dtype=float)
active_returns = returns_pf - returns_bm

# ==========================================================
# CALCUL KPI
# ==========================================================

perf_pf_total = nav_df[portfolio_nav].iloc[-1] / nav_df[portfolio_nav].iloc[0] - 1
perf_bm_total = nav_df[benchmark_nav].iloc[-1] / nav_df[benchmark_nav].iloc[0] - 1
alpha = perf_pf_total - perf_bm_total

beta = calculate_beta(returns_pf, returns_bm)
volatility_pf = np.std(returns_pf, ddof=1) * np.sqrt(annual_factor)
volatility_bm = np.std(returns_bm, ddof=1) * np.sqrt(annual_factor)
te = calculate_tracking_error(returns_pf, returns_bm, annual_factor)
ir = calculate_information_ratio(returns_pf, returns_bm, annual_factor)
sharpe = calculate_sharpe(returns_pf, annual_factor)
sortino = calculate_sortino(returns_pf, annual_factor)
corr = calculate_correlation(returns_pf, returns_bm)
var95 = calculate_var(returns_pf)
cvar95 = calculate_cvar(returns_pf)
max_dd, dd_curve = calculate_max_drawdown(nav_df[portfolio_nav])
hit_ratio = (active_returns > 0).mean()

# ==========================================================
# CONSTRUCTION KPI
# ==========================================================

kpis = {
    "📅 Fréquence": frequency,
    "📊 Annualisation": annual_factor,
    f"📈 Perf {portfolio_nav}": format_value(perf_pf_total, ".2%"),
    f"📈 Perf {benchmark_nav}": format_value(perf_bm_total, ".2%"),
    "🎯 Alpha (total)": format_value(alpha, ".2%"),
    "📉 Beta": format_value(beta, ".2f"),
    f"📊 Vol {portfolio_nav}": format_value(volatility_pf, ".2%"),
    f"📊 Vol {benchmark_nav}": format_value(volatility_bm, ".2%"),
    "🔍 Tracking Error": format_value(te, ".2%"),
    "💡 Information Ratio": format_value(ir, ".2f"),
    "📉 Sharpe": format_value(sharpe, ".2f"),
    "📉 Sortino": format_value(sortino, ".2f"),
    "🔗 Corrélation": format_value(corr, ".2f"),
    "⚠️ VaR 95%": format_value(var95, ".2%"),
    "⚠️ CVaR 95%": format_value(cvar95, ".2%"),
    "📉 Max Drawdown": format_value(max_dd, ".2%"),
    "🎯 Hit Ratio": format_value(hit_ratio, ".2%"),
}

# ==========================================================
# AFFICHAGE
# ==========================================================

st.header("📊 Indicateurs Clés de Performance")
metrics = st.columns(4)
for counter, (key, value) in enumerate(kpis.items()):
    metrics[counter % 4].metric(key, value)

st.header("📋 Tableau Détaillé")
kpi_df = pd.DataFrame(list(kpis.items()), columns=["Indicateur", "Valeur"])
st.dataframe(kpi_df, use_container_width=True, hide_index=True)

st.header("📈 Visualisations")
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Évolution Base 100")
    fig = px.line(nav_df, x=date_col, y=[portfolio_nav, benchmark_nav])
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
    fig_dd.add_trace(go.Scatter(
        x=nav_df[date_col],
        y=dd_curve.to_numpy() * 100,
        fill="tozeroy",
        line=dict(color="red"),
    ))
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
