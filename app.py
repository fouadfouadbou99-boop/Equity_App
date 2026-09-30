import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from io import BytesIO
from scipy.stats import norm
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
    dates = pd.to_datetime(
        dates,
        errors="coerce"
    ).dropna().sort_values()

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
    Normalise les rendements.
    Si max > 1, suppose que c'est des pourcentages (100 = 100%)
    Si max <= 1, suppose que ce sont des décimales (0.5 = 50%)
    """
    max_val = series.abs().max()
    
    if max_val > 1:
        # Probablement des pourcentages, diviser par 100
        return series / 100
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
    diff = port - bench

    if len(diff) < 2:
        return np.nan

    return diff.std(ddof=1) * np.sqrt(annual_factor)


def calculate_information_ratio(port, bench, annual_factor):
    active = port - bench

    if len(active) < 2:
        return np.nan

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

    if len(downside) < 2:
        return np.nan

    downside_vol = downside.std(ddof=1) * np.sqrt(annual_factor)
    annual_return = returns.mean() * annual_factor

    if downside_vol == 0:
        return np.nan

    return (annual_return - rf) / downside_vol


def calculate_max_drawdown(series):
    if len(series) == 0:
        return np.nan, pd.Series(dtype=float)

    roll_max = series.cummax()
    drawdown = (series / roll_max) - 1

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
        pd.DataFrame(kpis.items(), columns=["Indicateur", "Valeur"]).to_excel(
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
    help="Format requis: Date + 2 colonnes Base 100 + 2 colonnes Performance"
)

if file is None:
    st.info("👉 Veuillez importer un fichier Excel pour lancer l'analyse.")
    st.stop()

if file:
    try:
        df = pd.read_excel(file)
    except Exception as e:
        st.error(f"❌ Erreur de lecture du fichier: {str(e)}")
        st.stop()

    if df.empty:
        st.error("❌ Le fichier Excel est vide.")
        st.stop()

    if df.columns.empty:
        st.error("❌ Le fichier Excel ne contient aucune colonne.")
        st.stop()

    date_col = df.columns[0]

    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    except Exception as e:
        st.error(f"❌ Erreur de conversion des dates: {str(e)}")
        st.stop()

    df = df.dropna(subset=[date_col]).reset_index(drop=True)

    if df.empty:
        st.error("❌ La colonne de dates est vide ou invalide.")
        st.stop()

    ANNUAL_FACTOR, FREQUENCE = detect_frequency_factor(df[date_col])

    st.success(f"✅ Fréquence détectée : **{FREQUENCE}** | Annualisation : **{ANNUAL_FACTOR}**")

    # ==========================================================
    # DETECTION AUTOMATIQUE DES COLONNES
    # ==========================================================

    cols = list(df.columns)
    available_cols = [c for c in cols if c != date_col]

    if len(available_cols) < 4:
        st.error("❌ Le fichier doit contenir au moins 4 colonnes (Date + 2 séries Base 100 + 2 Performance).")
        st.info(f"Colonnes détectées: {available_cols}")
        st.stop()

    st.subheader("⚙️ Paramétrage de l'analyse")

    col1, col2 = st.columns(2)

    with col1:
        portfolio_nav = st.selectbox(
            "📊 Valeur / Portefeuille (Base 100)",
            available_cols,
            index=0
        )

    with col2:
        benchmark_candidates = [c for c in available_cols if c != portfolio_nav]
        benchmark_nav = st.selectbox(
            "📈 Benchmark (Base 100)",
            benchmark_candidates,
            index=0 if len(benchmark_candidates) > 0 else None
        )

    remaining_perf = [
        c for c in available_cols
        if c not in [portfolio_nav, benchmark_nav]
    ]

    if len(remaining_perf) < 2:
        st.error("❌ Le fichier doit contenir au moins deux colonnes de performance distinctes.")
        st.stop()

    col3, col4 = st.columns(2)

    with col3:
        portfolio_ret = st.selectbox(
            "📉 Performance Portefeuille",
            remaining_perf,
            index=0
        )

    with col4:
        benchmark_ret_candidates = [c for c in remaining_perf if c != portfolio_ret]
        benchmark_ret = st.selectbox(
            "📈 Performance Benchmark",
            benchmark_ret_candidates,
            index=0 if len(benchmark_ret_candidates) > 0 else None
        )

    if portfolio_nav == benchmark_nav:
        st.warning("⚠️ Le portefeuille et le benchmark sont identiques.")
        st.stop()

    if portfolio_ret == benchmark_ret:
        st.warning("⚠️ Les performances sont identiques.")
        st.stop()

    # ==========================================================
    # ALIGNEMENT ET NORMALISATION DES SERIES
    # ==========================================================

    perf_df = df[[portfolio_ret, benchmark_ret]].apply(
        pd.to_numeric,
        errors="coerce"
    ).dropna()

    if perf_df.empty or len(perf_df) < 2:
        st.error("❌ Pas assez de données numériques valides.")
        st.stop()

    returns_pf = perf_df[portfolio_ret].values
    returns_bm = perf_df[benchmark_ret].values

    # Normalisation automatique
    returns_pf_norm = normalize_returns(pd.Series(returns_pf)).values
    returns_bm_norm = normalize_returns(pd.Series(returns_bm)).values

    # Calcul de la performance globale avec les colonnes Base 100
    nav_pf = pd.to_numeric(df[portfolio_nav], errors="coerce").dropna()
    nav_bm = pd.to_numeric(df[benchmark_nav], errors="coerce").dropna()

    if len(nav_pf) > 1 and len(nav_bm) > 1:
        perf_pf = (nav_pf.iloc[-1] / nav_pf.iloc[0]) - 1
        perf_bm = (nav_bm.iloc[-1] / nav_bm.iloc[0]) - 1
    else:
        perf_pf = np.nan
        perf_bm = np.nan

    alpha = perf_pf - perf_bm

    # ==========================================================
    # CALCULS DES KPI
    # ==========================================================

    beta = calculate_beta(returns_pf_norm, returns_bm_norm)

    volatility_pf = returns_pf_norm.std(ddof=1) * np.sqrt(ANNUAL_FACTOR)
    volatility_bm = returns_bm_norm.std(ddof=1) * np.sqrt(ANNUAL_FACTOR)

    te = calculate_tracking_error(returns_pf_norm, returns_bm_norm, ANNUAL_FACTOR)
    ir = calculate_information_ratio(returns_pf_norm, returns_bm_norm, ANNUAL_FACTOR)

    sharpe = calculate_sharpe(returns_pf_norm, ANNUAL_FACTOR)
    sortino = calculate_sortino(returns_pf_norm, ANNUAL_FACTOR)

    corr = np.corrcoef(returns_pf_norm, returns_bm_norm)[0, 1]

    var95 = calculate_var(returns_pf_norm)
    cvar95 = calculate_cvar(returns_pf_norm)

    max_dd, dd_curve = calculate_max_drawdown(nav_pf)

    hit_ratio = (returns_pf_norm > returns_bm_norm).mean()

    nom_pf = str(portfolio_nav).strip()
    nom_bm = str(benchmark_nav).strip()

    # ==========================================================
    # CONSTRUCTION DU DICTIONNAIRE KPI
    # ==========================================================

    kpis = {
        "📅 Fréquence": FREQUENCE,
        "📊 Annualisation": ANNUAL_FACTOR,
        f"📈 Performance {nom_pf}": f"{perf_pf:.2%}",
        f"📈 Performance {nom_bm}": f"{perf_bm:.2%}",
        f"🎯 Alpha": f"{alpha:.2%}",
        f"📉 Beta": f"{beta:.2f}",
        f"📊 Volatilité {nom_pf}": f"{volatility_pf:.2%}",
        f"📊 Volatilité {nom_bm}": f"{volatility_bm:.2%}",
        "🔍 Tracking Error": f"{te:.2%}",
        "💡 Information Ratio": f"{ir:.2f}",
        f"📉 Sharpe {nom_pf}": f"{sharpe:.2f}",
        f"📉 Sortino {nom_pf}": f"{sortino:.2f}",
        "🔗 Corrélation": f"{corr:.2f}",
        "⚠️ VaR 95%": f"{var95:.2%}",
        "⚠️ CVaR 95%": f"{cvar95:.2%}",
        "📉 Max Drawdown": f"{max_dd:.2%}",
        "🎯 Hit Ratio": f"{hit_ratio:.2%}"
    }

    # ==========================================================
    # AFFICHAGE DES KPI
    # ==========================================================

    st.header("📊 Indicateurs Clés de Performance")

    metrics = st.columns(4)
    compteur = 0

    for k, v in kpis.items():
        metrics[compteur % 4].metric(k, v)
        compteur += 1

    # ==========================================================
    # TABLEAU DETAILLE
    # ==========================================================

    st.header("📋 Tableau des Indicateurs")
    kpi_df = pd.DataFrame(list(kpis.items()), columns=["Indicateur", "Valeur"])
    st.dataframe(kpi_df, use_container_width=True, hide_index=True)

    # ==========================================================
    # GRAPHIQUES
    # ==========================================================

    st.header("📈 Visualisations")

    col_graph1, col_graph2 = st.columns(2)

    with col_graph1:
        st.subheader("Évolution Base 100")
        fig = px.line(
            df,
            x=date_col,
            y=[portfolio_nav, benchmark_nav],
            title=f"{nom_pf} vs {nom_bm}",
            labels={date_col: "Date", "value": "Valeur", "variable": "Série"}
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with col_graph2:
        st.subheader("Performances Périodiques")
        fig2 = px.bar(
            df,
            x=date_col,
            y=[portfolio_ret, benchmark_ret],
            title="Comparaison Rendements",
            labels={date_col: "Date", "value": "Rendement", "variable": "Série"},
            barmode="group"
        )
        st.plotly_chart(fig2, use_container_width=True)

    col_graph3, col_graph4 = st.columns(2)

    with col_graph3:
        st.subheader("Drawdown")
        fig_dd = go.Figure()
        fig_dd.add_trace(
            go.Scatter(
                x=df[date_col],
                y=dd_curve * 100,
                fill='tozeroy',
                name="Drawdown (%)",
                line=dict(color='red')
            )
        )
        fig_dd.update_layout(title="Évolution du Drawdown", xaxis_title="Date", yaxis_title="Drawdown (%)")
        st.plotly_chart(fig_dd, use_container_width=True)

    with col_graph4:
        st.subheader("Distribution des Rendements")
        fig_hist = px.histogram(
            returns_pf_norm * 100,
            nbins=30,
            title="Distribution Rendements Portefeuille",
            labels={"value": "Rendement (%)", "count": "Fréquence"}
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # ==========================================================
    # ANALYSE NARRATIVE
    # ==========================================================

    st.header("💬 Analyse Exécutive")

    if alpha > 0:
        perf_text = f"**surperforme** de **{alpha:.2%}**"
        sentiment = "✅ Positif"
    else:
        perf_text = f"**sous-performe** de **{abs(alpha):.2%}**"
        sentiment = "⚠️ À investiguer"

    analysis = f"""
    **Résumé de la performance:**
    
    - Le portefeuille {perf_text} son benchmark.
    - **Beta: {beta:.2f}** (systématique du portefeuille)
    - **Sharpe: {sharpe:.2f}** (rendement ajusté au risque)
    - **Sortino: {sortino:.2f}** (rendement ajusté au risque baissier)
    - **Volatilité:** {volatility_pf:.2%} vs {volatility_bm:.2%} (benchmark)
    - **Drawdown Maximum:** {max_dd:.2%}
    
    **Verdict:** {sentiment}
    """

    st.markdown(analysis)

    # ==========================================================
    # EXPORTS
    # ==========================================================

    st.header("📥 Télécharger les Rapports")

    col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)

    excel_file = generate_excel(df, kpis)
    pdf_file = generate_pdf(kpis)

    with col_exp1:
        st.download_button(
            "📊 Excel",
            excel_file,
            file_name="reporting_actions.xlsx"
        )

    with col_exp2:
        st.download_button(
            "📄 PDF",
            pdf_file,
            file_name="reporting_actions.pdf"
        )

    with col_exp3:
        st.download_button(
            "📋 CSV",
            df.to_csv(index=False),
            file_name="reporting_actions.csv"
        )

    with col_exp4:
        st.download_button(
            "📦 JSON",
            df.to_json(orient="records"),
            file_name="reporting_actions.json"
        )

    st.markdown("---")
    st.caption("📌 Dashboard créé avec Streamlit | Données actualisées automatiquement")
