import pandas as pd
import numpy as np


# --------------------------------------------------
# CHARGEMENT DES DONNÉES
# --------------------------------------------------

def load_data(file):

    df = pd.read_excel(file)

    df = df.iloc[:, 0:7]

    df.columns = [
        "Date",
        "VL_Portefeuille",
        "Base100_Portefeuille",
        "Perf_Portefeuille",
        "MASI_RB",
        "Base100_MASI",
        "Perf_MASI"
    ]

    df["Date"] = pd.to_datetime(df["Date"])

    return df


# --------------------------------------------------
# CALCUL DES INDICATEURS
# --------------------------------------------------

def calculate_metrics(df):

    portfolio = (
        df["Perf_Portefeuille"]
        .dropna()
        .astype(float)
    )

    benchmark = (
        df["Perf_MASI"]
        .dropna()
        .astype(float)
    )

    active_return = portfolio - benchmark

    nb_obs = len(df)

    perf_portefeuille = (

        df["VL_Portefeuille"].iloc[-1]

        /

        df["VL_Portefeuille"].iloc[0]

        - 1
    )

    perf_indice = (

        df["MASI_RB"].iloc[-1]

        /

        df["MASI_RB"].iloc[0]

        - 1
    )

    alpha = (

        perf_portefeuille

        -

        perf_indice
    )

    alpha_annualise = (

        (1 + alpha)

        **

        (52 / nb_obs)

        - 1
    )

    vol_port = portfolio.std()

    vol_indice = benchmark.std()

    vol_ann_port = (
        vol_port * np.sqrt(52)
    )

    vol_ann_indice = (
        vol_indice * np.sqrt(52)
    )

    covariance = np.cov(
        portfolio,
        benchmark
    )[0, 1]

    variance_benchmark = np.var(
        benchmark
    )

    beta = (

        covariance

        /

        variance_benchmark

        if variance_benchmark != 0

        else 0
    )

    correlation = portfolio.corr(
        benchmark
    )

    tracking_error = active_return.std()

    tracking_error_ann = (
        tracking_error * np.sqrt(52)
    )

    information_ratio = (

        alpha_annualise

        /

        tracking_error_ann

        if tracking_error_ann != 0

        else 0
    )

    mean_port = portfolio.mean()

    mean_indice = benchmark.mean()

    sharpe_port = (

        mean_port

        /

        vol_port

        if vol_port != 0

        else 0
    )

    sharpe_indice = (

        mean_indice

        /

        vol_indice

        if vol_indice != 0

        else 0
    )

    hit_ratio = (

        (active_return > 0).sum()

        /

        len(active_return)

        if len(active_return) > 0

        else 0
    )

    metrics = {

        "Nombre de points d'observation":
            nb_obs,

        "Performance Portefeuille":
            perf_portefeuille,

        "Performance Indice":
            perf_indice,

        "Alpha":
            alpha,

        "Alpha Annualisé":
            alpha_annualise,

        "Volatilité Portefeuille":
            vol_ann_port,

        "Volatilité Indice":
            vol_ann_indice,

        "Beta":
            beta,

        "Corrélation":
            correlation,

        "Tracking Error":
            tracking_error_ann,

        "Information Ratio":
            information_ratio,

        "Sharpe Portefeuille":
            sharpe_port,

        "Sharpe Indice":
            sharpe_indice,

        "Hit Ratio":
            hit_ratio
    }

    return metrics, active_return


# --------------------------------------------------
# COMMENTAIRE AUTOMATIQUE
# --------------------------------------------------

def generate_commentary(metrics):

    alpha = metrics["Alpha"]

    beta = metrics["Beta"]

    hit_ratio = metrics["Hit Ratio"]

    texte = ""

    if alpha > 0:

        texte += (
            "Le portefeuille "
            "surperforme son benchmark. "
        )

    else:

        texte += (
            "Le portefeuille "
            "sous-performe son benchmark. "
        )

    if beta > 1:

        texte += (
            "Le portefeuille est "
            "plus risqué que le marché. "
        )

    else:

        texte += (
            "Le niveau de risque "
            "reste inférieur ou proche "
            "du marché. "
        )

    if hit_ratio > 0.50:

        texte += (
            "Le hit ratio est favorable."
        )

    else:

        texte += (
            "Le hit ratio doit être amélioré."
        )

    return texte


# --------------------------------------------------
# RESUME EXECUTIF
# --------------------------------------------------

def executive_summary(metrics):

    resume = f"""

Performance Portefeuille :
{metrics['Performance Portefeuille']:.2%}

Performance Indice :
{metrics['Performance Indice']:.2%}

Alpha :
{metrics['Alpha']:.2%}

Volatilité Portefeuille :
{metrics['Volatilité Portefeuille']:.2%}

Volatilité Indice :
{metrics['Volatilité Indice']:.2%}

Beta :
{metrics['Beta']:.2f}

Tracking Error :
{metrics['Tracking Error']:.2%}

Information Ratio :
{metrics['Information Ratio']:.2f}

Hit Ratio :
{metrics['Hit Ratio']:.2%}
"""

    return resume
