import streamlit as st
import pandas as pd
import numpy as np

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
    layout="wide"
)

st.title("📊 Analyse de la Poche Actions")

st.markdown(
"""
Suivi de performance du portefeuille
comparé au MASI RB
"""
)

# --------------------------------------------------
# CHARGEMENT
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Charger le fichier Excel",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Veuillez charger un fichier Excel.")
    st.stop()

# --------------------------------------------------
# LECTURE
# --------------------------------------------------

try:

    df = load_data(uploaded_file)

except Exception as e:

    st.error(
        f"Erreur de lecture du fichier : {e}"
    )

    st.stop()

# --------------------------------------------------
# CALCULS
# --------------------------------------------------

metrics, active_return = calculate_metrics(df)

# --------------------------------------------------
# KPI
# --------------------------------------------------

st.header("Indicateurs Clés")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Performance Portefeuille",
    f"{metrics['Performance Portefeuille']:.2%}"
)

c2.metric(
    "Performance Indice",
    f"{metrics['Performance Indice']:.2%}"
)

c3.metric(
    "Alpha",
    f"{metrics['Alpha']:.2%}"
)

c4.metric(
    "Hit Ratio",
    f"{metrics['Hit Ratio']:.2%}"
)

c5, c6, c7, c8 = st.columns(4)

c5.metric(
    "Bêta",
    f"{metrics['Beta']:.2f}"
)

c6.metric(
    "Corrélation",
    f"{metrics['Corrélation']:.2f}"
)

c7.metric(
    "Tracking Error",
    f"{metrics['Tracking Error']:.2%}"
)

c8.metric(
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
# EVOLUTION BASE 100
# --------------------------------------------------

st.header("Evolution Base 100")

fig_base100 = px.line(
    df,
    x="Date",
    y=[
        "Base100_Portefeuille",
        "Base100_MASI"
    ],
    labels={
        "value": "Base 100",
        "variable": "Série"
    }
)

st.plotly_chart(
    fig_base100,
    use_container_width=True
)

# --------------------------------------------------
# PERFORMANCE HEBDO
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
    nbins=25
)

st.plotly_chart(
    fig_hist,
    use_container_width=True
)

# --------------------------------------------------
# SCATTER BETA
# --------------------------------------------------

st.header("Analyse Bêta")

scatter_df = pd.DataFrame({

    "Portefeuille":
    df["Perf_Portefeuille"],

    "Indice":
    df["Perf_MASI"]

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
# ANALYSE AUTOMATIQUE
# --------------------------------------------------

st.header("Commentaire Automatique")

alpha = metrics["Alpha"]

tracking_error = metrics["Tracking Error"]

hit_ratio = metrics["Hit Ratio"]

if alpha > 0:

    st.success(
        f"""
        Le portefeuille surperforme
        son benchmark avec un alpha
        de {alpha:.2%}.
        """
    )

else:

    st.error(
        f"""
        Le portefeuille sous-performe
        son benchmark avec un alpha
        de {alpha:.2%}.
        """
    )

if tracking_error < 0.05:

    st.info(
        "Le niveau de risque actif reste maîtrisé."
    )

else:

    st.warning(
        "Le risque actif est relativement élevé."
    )

if hit_ratio > 0.50:

    st.success(
        f"Hit Ratio favorable : {hit_ratio:.2%}"
    )

else:

    st.warning(
        f"Hit Ratio faible : {hit_ratio:.2%}"
    )

# --------------------------------------------------
# SYNTHÈSE EXÉCUTIVE
# --------------------------------------------------

st.header("Résumé Exécutif")

resume = f"""

Performance du portefeuille :
{metrics['Performance Portefeuille']:.2%}

Performance du benchmark :
{metrics['Performance Indice']:.2%}

Alpha :
{metrics['Alpha']:.2%}

Volatilité annualisée :
{metrics['Volatilité Portefeuille']:.2%}

Bêta :
{metrics['Beta']:.2f}

Tracking Error :
{metrics['Tracking Error']:.2%}

Information Ratio :
{metrics['Information Ratio']:.2f}

Hit Ratio :
{metrics['Hit Ratio']:.2%}
"""

st.text_area(
    "Conclusion",
    resume,
    height=250
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
        sheet_name="Data",
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

    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    )
)

# --------------------------------------------------
# EXPORT CSV
# --------------------------------------------------

csv = kpi_df.to_csv(
    index=False
).encode("utf-8")

st.download_button(

    label="📥 Télécharger CSV",

    data=csv,

    file_name="KPI.csv",

    mime="text/csv"
)

# --------------------------------------------------
# POWER BI
# --------------------------------------------------

st.header("Power BI")

st.info(
"""
Power BI peut être connecté :

1. Au fichier Excel exporté
2. A une base Azure SQL
3. A un Dataflow Power BI

Architecture recommandée :

Excel
→ Streamlit
→ Azure SQL
→ Power BI
"""
)

# --------------------------------------------------
# FIN
# --------------------------------------------------

st.success(
    "Analyse terminée avec succès."
)
