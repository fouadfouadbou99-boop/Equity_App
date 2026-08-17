import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Dashboard Actions",
    layout="wide"
)

st.title("📈 Dashboard Poche Actions")

uploaded_file = st.file_uploader(
    "Importer le fichier Excel",
    type=["xlsx"]
)

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    df["Date"] = pd.to_datetime(df["Date"])

    perf_pf = (
        df["VL_portefeuille_actions base_100"].iloc[-1]
        / df["VL_portefeuille_actions base_100"].iloc[0]
    ) - 1

    perf_idx = (
        df["MASI_RB_ base_100"].iloc[-1]
        / df["MASI_RB_ base_100"].iloc[0]
    ) - 1

    alpha = perf_pf - perf_idx

    vol_pf = (
        df["Perf Hebdo Portefeuille_actions"]
        .std()
        * np.sqrt(52)
    )

    vol_idx = (
        df["Perf Hebdo MASI_RB"]
        .std()
        * np.sqrt(52)
    )

    beta = (
        np.cov(
            df["Perf Hebdo Portefeuille_actions"].dropna(),
            df["Perf Hebdo MASI_RB"].dropna()
        )[0,1]
        /
        np.var(
            df["Perf Hebdo MASI_RB"].dropna()
        )
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Performance Portefeuille",
        f"{perf_pf:.2%}"
    )

    col2.metric(
        "Performance Benchmark",
        f"{perf_idx:.2%}"
    )

    col3.metric(
        "Alpha",
        f"{alpha:.2%}"
    )

    col4.metric(
        "Beta",
        round(beta,2)
    )

    st.subheader("Evolution Base 100")

    fig = px.line(
        df,
        x="Date",
        y=[
            "VL_portefeuille_actions base_100",
            "MASI_RB_ base_100"
        ]
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("Performance Hebdomadaire")

    fig2 = px.bar(
        df,
        x="Date",
        y=[
            "Perf Hebdo Portefeuille_actions",
            "Perf Hebdo MASI_RB"
        ]
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    st.subheader("Analyse automatique")

    if alpha > 0:
        commentaire = """
        Surperformance du portefeuille
        par rapport au benchmark.
        """
    else:
        commentaire = """
        Sous-performance du portefeuille
        par rapport au benchmark.
        """

    st.info(commentaire)

    st.subheader("Conclusion")

    st.success(
        f"""
        Performance portefeuille : {perf_pf:.2%}

        Performance benchmark : {perf_idx:.2%}

        Alpha : {alpha:.2%}

        Volatilité portefeuille :
        {vol_pf:.2%}

        Volatilité benchmark :
        {vol_idx:.2%}
        """
    )
