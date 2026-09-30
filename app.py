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
# CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Dashboard Gestion Actions",
    layout="wide"
)

st.title("📈 Dashboard Universel de Performance Financière")


# ==========================================================
# FONCTIONS KPI
# ==========================================================

def calculate_beta(port, bench):

    covariance = np.cov(port, bench)[0, 1]

    variance = np.var(bench)

    return covariance / variance


def calculate_tracking_error(port, bench):

    diff = port - bench

    return diff.std() * np.sqrt(52)


def calculate_information_ratio(port, bench):

    active = port - bench

    alpha = active.mean() * 52

    te = active.std() * np.sqrt(52)

    if te == 0:
        return np.nan

    return alpha / te


def calculate_sharpe(returns, rf=0):

    vol = returns.std() * np.sqrt(52)

    ret = returns.mean() * 52

    if vol == 0:
        return np.nan

    return (ret - rf) / vol


def calculate_sortino(returns, rf=0):

    downside = returns[returns < 0]

    downside_std = downside.std() * np.sqrt(52)

    annual_return = returns.mean() * 52

    if downside_std == 0:
        return np.nan

    return (annual_return - rf) / downside_std


def calculate_max_drawdown(series):

    roll_max = series.cummax()

    drawdown = series / roll_max - 1.0

    return drawdown.min(), drawdown


def calculate_var(returns, confidence=0.95):

    return np.percentile(
        returns,
        (1 - confidence) * 100
    )


def calculate_cvar(returns, confidence=0.95):

    var = calculate_var(returns, confidence)

    return returns[returns <= var].mean()

# ==========================================================
# EXPORT EXCEL
# ==========================================================

def generate_excel(df, kpis):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Data",
            index=False
        )

        pd.DataFrame(
            kpis.items(),
            columns=["Indicateur", "Valeur"]
        ).to_excel(
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

    elems.append(
        Paragraph(
            "Rapport de Performance",
            styles["Title"]
        )
    )

    elems.append(
        Spacer(1, 12)
    )

    for k, v in kpis.items():

        elems.append(
            Paragraph(
                f"{k}: {v}",
                styles["BodyText"]
            )
        )

    doc.build(elems)

    buffer.seek(0)

    return buffer

# ==========================================================
# CHARGEMENT FICHIER
# ==========================================================

file = st.file_uploader(
    "Importer le fichier Excel",
    type=["xlsx"]
)

if file:

    df = pd.read_excel(file)

    date_col = df.columns[0]

    df[date_col] = pd.to_datetime(
        df[date_col]
    )

    # ==========================================================
    # DETECTION AUTOMATIQUE DES COLONNES
    # ==========================================================

    cols = list(df.columns)

    base100_cols = [
        c for c in cols
        if "base" in c.lower()
    ]

    perf_cols = [
        c for c in cols
        if "perf" in c.lower()
    ]

    if len(base100_cols) < 2:
        st.error(
            "Le fichier doit contenir au moins deux colonnes Base 100."
        )
        st.write(df.columns.tolist())
        st.stop()

    if len(perf_cols) < 2:
        st.error(
            "Le fichier doit contenir au moins deux colonnes de performance."
        )
        st.write(df.columns.tolist())
        st.stop()

    st.subheader("Paramétrage de l'analyse")

    col1, col2 = st.columns(2)

    with col1:
        portfolio_nav = st.selectbox(
            "Valeur / Portefeuille",
            base100_cols,
            index=0
        )

    with col2:
        benchmark_nav = st.selectbox(
            "Benchmark",
            base100_cols,
            index=min(1, len(base100_cols) - 1)
        )

    col3, col4 = st.columns(2)

    with col3:
        portfolio_ret = st.selectbox(
            "Performance Valeur / Portefeuille",
            perf_cols,
            index=0
        )

    with col4:
        benchmark_ret = st.selectbox(
            "Performance Benchmark",
            perf_cols,
            index=min(1, len(perf_cols) - 1)
        )

    returns_pf = df[portfolio_ret].dropna()
    returns_bm = df[benchmark_ret].dropna()

    perf_pf = (
        df[portfolio_nav].iloc[-1]
        /
        df[portfolio_nav].iloc[0]
    ) - 1

    perf_bm = (
        df[benchmark_nav].iloc[-1]
        /
        df[benchmark_nav].iloc[0]
    ) - 1


    perf_pf = (
        df[portfolio_nav].iloc[-1]
        /
        df[portfolio_nav].iloc[0]
    ) - 1

    perf_bm = (
        df[benchmark_nav].iloc[-1]
        /
        df[benchmark_nav].iloc[0]
    ) - 1

    alpha = perf_pf - perf_bm

    beta = calculate_beta(
        returns_pf,
        returns_bm
    )

    volatility_pf = (
        returns_pf.std()
        * np.sqrt(52)
    )

    volatility_bm = (
        returns_bm.std()
        * np.sqrt(52)
    )

    te = calculate_tracking_error(
        returns_pf,
        returns_bm
    )

    ir = calculate_information_ratio(
        returns_pf,
        returns_bm
    )

    sharpe = calculate_sharpe(
        returns_pf
    )

    sortino = calculate_sortino(
        returns_pf
    )

    corr = returns_pf.corr(
        returns_bm
    )

    var95 = calculate_var(
        returns_pf
    )

    cvar95 = calculate_cvar(
        returns_pf
    )

    max_dd, dd_curve = \
        calculate_max_drawdown(
            df[portfolio_nav]
        )

    hit_ratio = (
        (
            returns_pf >
            returns_bm
        )
    ).mean()

    nom_pf = portfolio_nav.replace("Base 100", "").strip()
    nom_bm = benchmark_nav.replace("Base 100", "").strip()

    kpis = {
    f"Performance {nom_pf}": f"{perf_pf:.2%}",
    f"Performance {nom_bm}": f"{perf_bm:.2%}",
    f"Alpha {nom_pf}": f"{alpha:.2%}",
    "Beta": f"{beta:.2f}",
    f"Volatilité {nom_pf}": f"{volatility_pf:.2%}",
    "Tracking Error": f"{te:.2%}",
    "Information Ratio": f"{ir:.2f}",
    f"Sharpe {nom_pf}": f"{sharpe:.2f}",
    f"Sortino {nom_pf}": f"{sortino:.2f}",
    "Corrélation": f"{corr:.2f}",
    "VaR 95%": f"{var95:.2%}",
    "CVaR 95%": f"{cvar95:.2%}",
    "Max Drawdown": f"{max_dd:.2%}",
    "Hit Ratio": f"{hit_ratio:.2%}"
}

    # ======================================================
    # TABLEAU KPI
    # ======================================================

    st.header("Indicateurs Clés")

    metrics = st.columns(4)

    compteur = 0

    for k, v in kpis.items():

        metrics[
            compteur % 4
        ].metric(
            k,
            v
        )

        compteur += 1

    # ======================================================
    # TABLEAU KPI DETAILLE
    # ======================================================

    st.header("Tableau des Indicateurs")

    st.dataframe(
        pd.DataFrame(
            kpis.items(),
            columns=[
                "Indicateur",
                "Valeur"
            ]
        ),
        use_container_width=True
    )

    # ======================================================
    # GRAPHIQUE BASE 100
    # ======================================================

    st.header("Evolution Base 100")

    fig = px.line(
        df,
        x=date_col,
        y=[
            portfolio_nav,
            benchmark_nav
        ]
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ======================================================
    # PERFORMANCE HEBDOMADAIRE
    # ======================================================

    st.header(
        "Performances Hebdomadaires"
    )

    fig2 = px.bar(
        df,
        x=date_col,
        y=[
            portfolio_ret,
            benchmark_ret
        ]
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # ======================================================
    # DRAWDOWN
    # ======================================================

    st.header(
        "Drawdown"
    )

    fig_dd = go.Figure()

    fig_dd.add_trace(

        go.Scatter(

            x=df[date_col],

            y=dd_curve,

            fill='tozeroy',

            name="Drawdown"
        )
    )

    st.plotly_chart(
        fig_dd,
        use_container_width=True
    )

    # ======================================================
    # DISTRIBUTION
    # ======================================================

    st.header(
        "Distribution des Rendements"
    )

    fig_hist = px.histogram(
        returns_pf,
        nbins=20
    )

    st.plotly_chart(
        fig_hist,
        use_container_width=True
    )

    # ======================================================
    # COMMENTAIRES IA
    # ======================================================

    st.header(
        "Commentaires Automatiques"
    )

commentaire = f"""
    {nom_pf} affiche une performance cumulée de {perf_pf:.2%}
    contre {perf_bm:.2%} pour {nom_bm}.

    L'alpha observé est de {alpha:.2%}.

    Le bêta ressort à {beta:.2f}.

    La volatilité annualisée de {nom_pf}
    est de {volatility_pf:.2%}.

    Le tracking error ressort à {te:.2%}.

    Le ratio de Sharpe est de {sharpe:.2f}.

    Le drawdown maximal observé est de {max_dd:.2%}.
"""

    st.info(commentaire)

    # ======================================================
    # CONCLUSION
    # ======================================================

    st.header(
        "Conclusion Exécutive"
    )

    if alpha > 0:

        conclusion = """
        Le portefeuille surperforme
        son benchmark tout en
        maintenant un niveau de
        risque maîtrisé.
        """

    else:

        conclusion = """
        Le portefeuille sous-performe
        le benchmark et nécessite
        une analyse approfondie
        d'attribution de performance.
        """

    st.success(
        conclusion
    )

    # ======================================================
    # EXPORTS
    # ======================================================

    st.header("Exports")

    excel_file = generate_excel(
        df,
        kpis
    )

    pdf_file = generate_pdf(
        kpis
    )

    st.download_button(
        "Télécharger Excel",
        excel_file,
        file_name=
        "reporting_actions.xlsx"
    )

    st.download_button(
        "Télécharger PDF",
        pdf_file,
        file_name=
        "reporting_actions.pdf"
    )

    st.download_button(
        "Télécharger CSV",
        df.to_csv(
            index=False
        ),
        file_name=
        "reporting_actions.csv"
    )

    st.download_button(
        "Télécharger JSON",
        df.to_json(
            orient="records"
        ),
        file_name=
        "reporting_actions.json"
    )

    # ======================================================
    # DATA POWER BI
    # ======================================================

    st.header(
        "Connexion Power BI"
    )

    st.code(
"""
# api_powerbi.py

from fastapi import FastAPI
import pandas as pd

app = FastAPI()

@app.get('/portfolio')

def portfolio():

    df = pd.read_excel(
        'data.xlsx'
    )

    return (
        df.to_dict(
            orient='records'
        )
    )
"""
    )

    st.info(
    """
    Power BI :

    Get Data
    -> Web

    http://localhost:8000/portfolio
    """
    )
