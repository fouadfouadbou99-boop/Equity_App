import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

from utils import (
    load_data,
    calculate_metrics
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Portfolio Analytics",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Portfolio Analytics Dashboard")

st.markdown("""
Analyse de la Poche Actions
Comparaison avec le MASI RB
""")

# --------------------------------------------------
# UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Télécharger le fichier Excel",
    type=["xlsx"]
)

if uploaded_file is None:

    st.info(
        "Veuillez charger votre fichier Excel."
    )

    st.stop()

# --------------------------------------------------
# CHARGEMENT DATA
# --------------------------------------------------

try:

    df = load_data(uploaded_file)

except Exception as e:

    st.error(
        f"Erreur lors du chargement : {e}"
    )

    st.stop()

# --------------------------------------------------
# KPI
# --------------------------------------------------

metrics, active_return = calculate_metrics(df)

st.header("Indicateurs Clés")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric(
    "Performance Portefeuille",
    f"{metrics['Performance Portefeuille']:.2%}"
)

kpi2.metric(
    "Performance Indice",
    f"{metrics['Performance Indice']:.2%}"
)

kpi3.metric(
    "Alpha",
    f"{metrics['Alpha']:.2%}"
)

kpi4.metric(
    "Hit Ratio",
    f"{metrics['Hit Ratio']:.2%}"
)

kpi5, kpi6, kpi7, kpi8 = st.columns(4)

kpi5.metric(
    "Bêta",
    f"{metrics['Beta']:.2f}"
)

kpi6.metric(
    "Corrélation",
    f"{metrics['Corrélation']:.2f}"
)

kpi7.metric(
    "Tracking Error",
    f"{metrics['Tracking Error']:.2%}"
)

kpi8.metric(
    "Information Ratio",
    f"{metrics['Information Ratio']:.2f}"
)

# --------------------------------------------------
# TABLEAU KPI
# --------------------------------------------------

st.header("Tableau des indicateurs")

kpi_df = pd.DataFrame(
    metrics.items(),
    columns=["Indicateur", "Valeur"]
)

st.dataframe(
    kpi_df,
    use_container_width=True
)

# --------------------------------------------------
# COURBE BASE 100
# --------------------------------------------------

st.header("Evolution Base 100")

fig = px.line(
    df,
    x="Date",
    y=[
        "Base100_Portefeuille",
        "Base100_MASI"
    ],
    labels={
        "value": "Base 100",
        "variable": "Portefeuille / MASI"
    }
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# --------------------------------------------------
# PERFORMANCES HEBDO
# --------------------------------------------------

st.header("Rendements Hebdomadaires")

fig_perf = go.Figure()

fig_perf.add_trace(

    go.Bar(
        x=df["Date"],
        y=df["Perf_Portefeuille"],
        name="Portefeuille"
    )

)

fig_perf.add_trace(

    go.Bar(
        x=df["Date"],
        y=df["Perf_MASI"],
        name="Indice"
    )

)

st.plotly_chart(
    fig_perf,
    use_container_width=True
)

# --------------------------------------------------
# ACTIVE RETURN
# --------------------------------------------------

st.header("Active Return")

active_df = pd.DataFrame({

    "Date": df["Date"].iloc[1:],

    "Active Return": active_return.values

})

fig_active = px.area(
    active_df,
    x="Date",
    y="Active Return"
)

st.plotly_chart(
    fig_active,
    use_container_width=True
)

# --------------------------------------------------
# HISTOGRAMME
# --------------------------------------------------

st.header("Distribution des Rendements")

fig_hist = px.histogram(
    df,
    x="Perf_Portefeuille",
    nbins=30
)

st.plotly_chart(
    fig_hist,
    use_container_width=True
)

# --------------------------------------------------
# BETA
# --------------------------------------------------

st.header("Analyse du Bêta")

scatter_df = pd.DataFrame({

    "Indice":
        df["Perf_MASI"],

    "Portefeuille":
        df["Perf_Portefeuille"]

}).dropna()

fig_beta = px.scatter(
    scatter_df,
    x="Indice",
    y="Portefeuille",
    trendline="ols"
)

st.plotly_chart(
    fig_beta,
    use_container_width=True
)

# --------------------------------------------------
# COMMENTAIRE
# --------------------------------------------------

st.header("Analyse Automatique")

alpha = metrics["Alpha"]

if alpha > 0:

    st.success(
        f"""
        Le portefeuille surperforme
        son benchmark.

        Alpha observé :
        {alpha:.2%}
        """
    )

else:

    st.error(
        f"""
        Le portefeuille sous-performe
        son benchmark.

        Alpha observé :
        {alpha:.2%}
        """
    )

tracking_error = metrics["Tracking Error"]

if tracking_error < 0.05:

    st.info(
        "Le niveau de risque actif reste modéré."
    )

else:

    st.warning(
        "Le risque actif est relativement élevé."
    )

# --------------------------------------------------
# SYNTHÈSE
# --------------------------------------------------

st.header("Résumé Exécutif")

resume = f"""

Nombre de points d'observation :
{metrics["Nombre de points d'observation"]}

Performance du portefeuille :
{metrics["Performance Portefeuille"]:.2%}

Performance du benchmark :
{metrics["Performance Indice"]:.2%}

Alpha :
{metrics["Alpha"]:.2%}

Volatilité portefeuille :
{metrics["Volatilité Portefeuille"]:.2%}

Volatilité benchmark :
{metrics["Volatilité Indice"]:.2%}

Bêta :
{metrics["Beta"]:.2f}

Corrélation :
{metrics["Corrélation"]:.2f}

Tracking Error :
{metrics["Tracking Error"]:.2%}

Information Ratio :
{metrics["Information Ratio"]:.2f}

Sharpe Portefeuille :
{metrics["Sharpe Portefeuille"]:.2f}

Sharpe Indice :
{metrics["Sharpe Indice"]:.2f}

Hit Ratio :
{metrics["Hit Ratio"]:.2%}
"""

st.text_area(
    "Conclusion",
    resume,
    height=350
)

# --------------------------------------------------
# DONNÉES SOURCE
# --------------------------------------------------

st.header("Données Sources")

st.dataframe(
    df,
    use_container_width=True
)

# --------------------------------------------------
# EXPORT EXCEL
# --------------------------------------------------

st.header("Exports")

excel_buffer = BytesIO()

with pd.ExcelWriter(
    excel_buffer,
    engine="xlsxwriter"
) as writer:

    df.to_excel(
        writer,
        sheet_name="Donnees",
        index=False
    )

    kpi_df.to_excel(
        writer,
        sheet_name="KPI",
        index=False
    )

st.download_button(

    label="📥 Télécharger Excel",

    data=excel_buffer.getvalue(),

    file_name="Portfolio_Analytics.xlsx",

    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --------------------------------------------------
# EXPORT CSV KPI
# --------------------------------------------------

csv = kpi_df.to_csv(
    index=False
)

st.download_button(
    "📥 Télécharger KPI CSV",
    csv,
    file_name="KPI.csv",
    mime="text/csv"
)

# --------------------------------------------------
# EXPORT POWER BI
# --------------------------------------------------

powerbi_df = pd.DataFrame({

    "Date":
        df["Date"],

    "VL_Portefeuille":
        df["VL_Portefeuille"],

    "MASI_RB":
        df["MASI_RB"],

    "Perf_Portefeuille":
        df["Perf_Portefeuille"],

    "Perf_MASI":
        df["Perf_MASI"]

})

powerbi_csv = powerbi_df.to_csv(
    index=False
)

st.download_button(
    "📊 Télécharger Dataset Power BI",
    powerbi_csv,
    file_name="powerbi_dataset.csv",
    mime="text/csv"
)

# --------------------------------------------------
# PIED DE PAGE
# --------------------------------------------------

st.success(
    "Analyse terminée avec succès."
)
