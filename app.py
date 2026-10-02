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

    var_bench = np.var(
        bench,
        ddof=1
    )

    if np.isclose(var_bench, 0):
        return np.nan

    covariance = np.cov(
        port,
        bench,
        ddof=1
    )[0, 1]

    return covariance / var_bench


def calculate_tracking_error(
    port,
    bench,
    annual_factor
):

    port, bench = finite_pair(
        port,
        bench
    )

    if len(port) < 2:
        return np.nan

    active = port - bench

    return (
        np.std(
            active,
            ddof=1
        )
        * np.sqrt(annual_factor)
    )


def calculate_information_ratio(
    annual_return_pf,
    annual_return_bm,
    te
):

    if (
        pd.isna(te)
        or te <= 0
    ):
        return np.nan

    return (
        annual_return_pf
        - annual_return_bm
    ) / te


def period_rf_from_annual(
    annual_rf,
    annual_factor
):

    if annual_rf <= -1:
        return np.nan

    return (
        (1 + annual_rf)
        ** (1 / annual_factor)
        - 1
    )


def calculate_sharpe(
    returns,
    annual_factor,
    rf=0
):

    returns = np.asarray(
        returns,
        dtype=float
    )

    returns = returns[
        np.isfinite(returns)
    ]

    if len(returns) < 2:
        return np.nan

    annual_return = (
        np.prod(1 + returns)
        ** (
            annual_factor
            / len(returns)
        )
        - 1
    )

    annual_vol = (
        np.std(
            returns,
            ddof=1
        )
        * np.sqrt(
            annual_factor
        )
    )

    if annual_vol == 0:
        return np.nan

    return (
        annual_return
        / annual_vol
    )


def calculate_sortino(
    returns,
    annual_factor,
    rf=0
):

    returns = np.asarray(
        returns,
        dtype=float
    )

    returns = returns[
        np.isfinite(returns)
    ]

    if len(returns) < 2:
        return np.nan

    annual_return = (
        np.prod(1 + returns)
        ** (
            annual_factor
            / len(returns)
        )
        - 1
    )

    downside = np.minimum(
        returns,
        0
    )

    downside_deviation = np.sqrt(
        np.mean(
            downside ** 2
        )
    )

    annual_downside = (
        downside_deviation
        * np.sqrt(
            annual_factor
        )
    )

    if annual_downside == 0:
        return np.nan

    return (
        annual_return
        / annual_downside
    )


def calculate_correlation(
    port,
    bench
):

    port, bench = finite_pair(
        port,
        bench
    )

    if len(port) < 2:
        return np.nan

    return np.corrcoef(
        port,
        bench
    )[0, 1]


def calculate_var(
    returns,
    confidence=0.95
):

    returns = np.asarray(
        returns,
        dtype=float
    )

    returns = returns[
        np.isfinite(returns)
    ]

    if len(returns) == 0:
        return np.nan

    return np.quantile(
        returns,
        1 - confidence
    )


def calculate_cvar(
    returns,
    confidence=0.95
):

    returns = np.asarray(
        returns,
        dtype=float
    )

    returns = returns[
        np.isfinite(returns)
    ]

    if len(returns) == 0:
        return np.nan

    var95 = np.quantile(
        returns,
        1 - confidence
    )

    return np.mean(
        returns[
            returns <= var95
        ]
    )


def calculate_max_drawdown(
    nav_series
):

    nav_series = (
        pd.to_numeric(
            nav_series,
            errors="coerce"
        )
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .dropna()
    )

    if nav_series.empty:
        return (
            np.nan,
            pd.Series(dtype=float)
        )

    running_max = nav_series.cummax()

    drawdown = (
        nav_series
        / running_max
        - 1
    )

    return (
        drawdown.min(),
        drawdown
    )


def format_value(
    value,
    fmt
):

    if pd.isna(value):
        return "N/D"

    return format(
        value,
        fmt
    )


def annualized_return(
    total_return,
    periods
):

    if (
        pd.isna(total_return)
        or periods <= 0
    ):
        return np.nan

    return (
        (1 + total_return)
        ** (1 / periods)
        - 1
    )

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
# SELECTION INTELLIGENTE DES COLONNES
# ==========================================================

base100_cols = [
    c for c in df.columns
    if "Base 100" in str(c)
]

perf_cols = [
    c for c in df.columns
    if "Perf" in str(c)
]

if len(base100_cols) < 2:
    st.error(
        "❌ Deux colonnes Base 100 sont requises."
    )
    st.stop()

if len(perf_cols) < 2:
    st.error(
        "❌ Deux colonnes Performance sont requises."
    )
    st.stop()

st.subheader("⚙️ Paramétrage")

col1, col2, col3, col4 = st.columns(4)

with col1:
    portfolio_nav = st.selectbox(
        "📊 Portefeuille Base 100",
        base100_cols,
        index=0
    )

with col2:
    benchmark_nav = st.selectbox(
        "📈 Benchmark Base 100",
        [c for c in base100_cols if c != portfolio_nav],
        index=0
    )

with col3:
    portfolio_ret = st.selectbox(
        "📉 Performance Portefeuille",
        perf_cols,
        index=0
    )

with col4:
    benchmark_ret = st.selectbox(
        "📈 Performance Benchmark",
        [c for c in perf_cols if c != portfolio_ret],
        index=0
    )

# ==========================================================
# DONNEES ET NORMALISATION
# ==========================================================

for column in [
    portfolio_nav,
    benchmark_nav,
    portfolio_ret,
    benchmark_ret
]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


def safe_total_return(series):

    series = (
        pd.to_numeric(
            series,
            errors="coerce"
        )
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .dropna()
    )

    if len(series) < 2:
        return np.nan

    return (
        series.iloc[-1]
        / series.iloc[0]
        - 1
    )
nav_pf = (
    df[portfolio_nav]
    .replace([np.inf, -np.inf], np.nan)
    .dropna()
)

nav_bm = (
    df[benchmark_nav]
    .replace([np.inf, -np.inf], np.nan)
    .dropna()
)
nav_bm = (
    df[benchmark_nav]
    .replace([np.inf, -np.inf], np.nan)
    .dropna()
)
# ==========================================================
# NAV
# ==========================================================

nav_pf = (
    df[portfolio_nav]
    .replace([np.inf, -np.inf], np.nan)
    .dropna()
)

nav_bm = (
    df[benchmark_nav]
    .replace([np.inf, -np.inf], np.nan)
    .dropna()
)

# ==========================================================
# PERFORMANCE TOTALE
# ==========================================================

perf_pf_total = safe_total_return(nav_pf)
perf_bm_total = safe_total_return(nav_bm)

# ==========================================================
# RENDEMENTS
# ==========================================================

returns_pf_raw = normalize_returns(
    df[portfolio_ret]
)

returns_bm_raw = normalize_returns(
    df[benchmark_ret]
)

perf_df = pd.DataFrame({
    "pf": returns_pf_raw,
    "bm": returns_bm_raw
})

perf_df = (
    perf_df
    .replace([np.inf, -np.inf], np.nan)
    .dropna()
)

if len(perf_df) < 2:

    st.error(
        "❌ Pas assez de données de rendement alignées."
    )

    st.stop()

returns_pf = perf_df["pf"].to_numpy(dtype=float)
returns_bm = perf_df["bm"].to_numpy(dtype=float)

active_returns = (
    returns_pf
    - returns_bm
)

# ==========================================================
# PERFORMANCE ANNUALISEE
# ==========================================================

years = len(df) / annual_factor

if years > 0:

    annual_return_pf = (
        (1 + perf_pf_total)
        ** (1 / years)
    ) - 1

    annual_return_bm = (
        (1 + perf_bm_total)
        ** (1 / years)
    ) - 1

else:

    annual_return_pf = np.nan
    annual_return_bm = np.nan

# ==========================================================
# RISQUES
# ==========================================================

beta = calculate_beta(
    returns_pf,
    returns_bm
)

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

te = calculate_tracking_error(
    returns_pf,
    returns_bm,
    annual_factor
)

corr = calculate_correlation(
    returns_pf,
    returns_bm
)

var95 = calculate_var(
    returns_pf,
    confidence=0.95
)

def calculate_cvar(
    returns,
    confidence=0.95
):

    returns = np.asarray(
        returns,
        dtype=float
    )

    returns = returns[
        np.isfinite(returns)
    ]

    if len(returns) == 0:
        return np.nan

    var95 = np.quantile(
        returns,
        1 - confidence
    )

    return np.mean(
        returns[
            returns <= var95
        ]
    )
cvar95 = calculate_cvar(
    returns_pf,
    confidence=0.95
)
max_dd, dd_curve = calculate_max_drawdown(
    df[portfolio_nav]
)

# ==========================================================
# ALPHA
# ==========================================================

if np.isfinite(beta):

    alpha = (
        annual_return_pf
        - (
            beta * annual_return_bm
        )
    )

else:

    alpha = np.nan


# ==========================================================
# INFORMATION RATIO
# ==========================================================

ir = calculate_information_ratio(
    annual_return_pf,
    annual_return_bm,
    te
)


# ==========================================================
# SHARPE
# ==========================================================

sharpe = calculate_sharpe(
    returns_pf,
    annual_factor,
    rf=0
)


# ==========================================================
# SORTINO
# ==========================================================

sortino = calculate_sortino(
    returns_pf,
    annual_factor,
    rf=0
)


# ==========================================================
# HIT RATIO
# ==========================================================

hit_ratio = np.mean(
    returns_pf > returns_bm
)


# ==========================================================
# UP CAPTURE
# ==========================================================

up_capture = np.nan

up_mask = (
    returns_bm > 0
)

if (
    np.any(up_mask)
    and np.mean(
        returns_bm[up_mask]
    ) != 0
):

    up_capture = (
        np.mean(
            returns_pf[up_mask]
        )
        /
        np.mean(
            returns_bm[up_mask]
        )
    )


# ==========================================================
# DOWN CAPTURE
# ==========================================================

down_capture = np.nan

down_mask = (
    returns_bm < 0
)

if (
    np.any(down_mask)
    and np.mean(
        returns_bm[down_mask]
    ) != 0
):

    down_capture = (
        np.mean(
            returns_pf[down_mask]
        )
        /
        np.mean(
            returns_bm[down_mask]
        )
    )


# ==========================================================
# BATTING AVERAGE
# ==========================================================

batting_average = np.mean(
    returns_pf > returns_bm
)
# ==========================================================
# DETECTION DU TYPE D'ANALYSE
# ==========================================================
def detect_analysis_subject(name):

    if pd.isna(name):
        return {
            "subject": "l'actif analysé",
            "category": "asset"
        }

    text = str(name).lower()

    portfolio_keywords = [
        "portefeuille",
        "portfolio",
        "opcvm",
        "fonds",
        "fund",
        "sicav",
        "fcp"
    ]

    if any(word in text for word in portfolio_keywords):
        return {
            "subject": "le portefeuille",
            "category": "portfolio"
        }

    return {
        "subject": "l'actif analysé",
        "category": "asset"
    }


# ==========================================================
# MOTEUR EXPERT D'ANALYSE FINANCIERE
# ==========================================================
def generate_commentary(
    asset_name,
    annual_return_pf,
    annual_return_bm,
    alpha,
    beta,
    sharpe,
    sortino,
    ir,
    volatility_pf,
    volatility_bm,
    max_dd,
    hit_ratio,
    up_capture,
    down_capture,
):

    subject = "l'actif analysé"

    # ======================================================
    # SCORING
    # ======================================================

    score = 0

    forces = []
    vigilances = []

    # Alpha

    if pd.notna(alpha):

        if alpha > 0:

            score += 20

            forces.append(
                f"Alpha positif ({alpha:.2%}) traduisant une création de valeur."
            )

        else:

            vigilances.append(
                f"Alpha négatif ({alpha:.2%})."
            )

    # Information Ratio

    if pd.notna(ir):

        if ir >= 1:

            score += 20

            forces.append(
                f"Information Ratio excellent ({ir:.2f})."
            )

        elif ir >= 0.5:

            score += 10

        else:

            vigilances.append(
                f"Information Ratio faible ({ir:.2f})."
            )

    # Sharpe

    if pd.notna(sharpe):

        if sharpe >= 2:

            score += 20

            forces.append(
                f"Ratio de Sharpe élevé ({sharpe:.2f})."
            )

        elif sharpe >= 1:

            score += 10

        else:

            vigilances.append(
                f"Ratio de Sharpe modeste ({sharpe:.2f})."
            )

    # Sortino

    if pd.notna(sortino):

        if sortino >= 2:

            score += 15

            forces.append(
                f"Excellente maîtrise du risque baissier (Sortino {sortino:.2f})."
            )

        elif sortino >= 1:

            score += 8

    # Drawdown

    if pd.notna(max_dd):

        if max_dd > -0.15:

            score += 10

        elif max_dd < -0.30:

            vigilances.append(
                f"Drawdown significatif ({max_dd:.2%})."
            )

    # Hit Ratio

    if pd.notna(hit_ratio):

        if hit_ratio > 0.50:

            score += 10

            forces.append(
                f"Surperformance plus fréquente que la sous-performance (Hit Ratio {hit_ratio:.2%})."
            )

    # Down Capture

    if pd.notna(down_capture):

        if down_capture < 1:

            score += 15

            forces.append(
                f"Bonne résistance dans les marchés baissiers (Down Capture {down_capture:.2f})."
            )

        else:

            vigilances.append(
                f"Sensibilité élevée aux phases baissières (Down Capture {down_capture:.2f})."
            )

    # ======================================================
    # DIAGNOSTIC
    # ======================================================

    if score >= 85:

        rating = "🟢 EXCELLENT"

    elif score >= 70:

        rating = "🟢 BON"

    elif score >= 55:

        rating = "🟡 SATISFAISANT"

    elif score >= 40:

        rating = "🟠 MOYEN"

    else:

        rating = "🔴 FAIBLE"

    # ======================================================
    # PERFORMANCE
    # ======================================================

    ecart_perf = annual_return_pf - annual_return_bm

    if ecart_perf > 0:

        perf_text = (
            f"{subject.capitalize()} affiche une performance annualisée de "
            f"{annual_return_pf:.2%}, supérieure à celle du benchmark "
            f"({annual_return_bm:.2%}). "

            f"La surperformance atteint {ecart_perf:.2%}, ce qui traduit "
            f"une dynamique particulièrement favorable sur la période étudiée. "

            f"Cette évolution met en évidence une capacité à générer une "
            f"valorisation significativement supérieure à celle de son "
            f"indice de référence."
        )

    else:

        perf_text = (
            f"{subject.capitalize()} affiche une performance annualisée de "
            f"{annual_return_pf:.2%} contre {annual_return_bm:.2%} pour le benchmark. "

            f"La sous-performance observée de {abs(ecart_perf):.2%} traduit "
            f"une évolution moins favorable que celle du marché de référence."
        )

    # ======================================================
    # RISQUE
    # ======================================================

    risk_text = (
        f"La volatilité annualisée ressort à {volatility_pf:.2%}, "
        f"contre {volatility_bm:.2%} pour le benchmark. "
        f"Le bêta de {beta:.2f} mesure la sensibilité de l'actif aux "
        f"mouvements du marché. "
        f"Le drawdown maximal atteint {max_dd:.2%}, représentant "
        f"la baisse la plus importante observée entre un point haut "
        f"et un point bas sur la période analysée."
    )

    # ======================================================
    # ANALYSE RELATIVE
    # ======================================================

    active_text = (
        f"L'alpha ressort à {alpha:.2%}. Cet indicateur mesure la performance "
        f"excédentaire par rapport à celle expliquée par le risque de marché. "

        f"L'Information Ratio s'établit à {ir:.2f} et permet d'évaluer "
        f"la régularité de la surperformance relative au benchmark. "

        f"Le ratio de Sharpe ({sharpe:.2f}) mesure le rendement obtenu "
        f"pour chaque unité de risque total supportée tandis que le ratio "
        f"de Sortino ({sortino:.2f}) se concentre spécifiquement sur "
        f"le risque baissier. "

        f"Le Hit Ratio de {hit_ratio:.2%} indique la proportion de périodes "
        f"durant lesquelles l'actif a surperformé son benchmark. "

        f"L'Up Capture ({up_capture:.2f}) mesure la participation aux phases "
        f"haussières du marché alors que le Down Capture ({down_capture:.2f}) "
        f"évalue le comportement lors des phases de correction."
    )

    # ======================================================
    # SYNTHESE
    # ======================================================

    if score >= 85:

        conclusion = (
            "L'ensemble des indicateurs convergent vers un diagnostic très favorable. "
            "La performance observée est élevée, la création de valeur apparaît "
            "importante et les ratios ajustés du risque ressortent à des niveaux "
            "particulièrement robustes. Le profil rendement-risque constitue "
            "l'un des principaux points forts de l'actif analysé."
        )

    elif score >= 70:

        conclusion = (
            "L'actif présente un profil globalement solide. La majorité des "
            "indicateurs sont orientés positivement et témoignent d'une "
            "bonne qualité de performance relativement au risque assumé."
        )

    elif score >= 55:

        conclusion = (
            "Les indicateurs apparaissent globalement satisfaisants, même si "
            "certains points de vigilance nécessitent un suivi particulier."
        )

    else:

        conclusion = (
            "Le profil ressort plus contrasté. Les performances observées "
            "ne compensent pas pleinement les risques supportés sur la période."
        )

    return {
        "Diagnostic": rating,
        "Score": score,
        "Forces": forces,
        "Vigilances": vigilances,
        "Performance": perf_text,
        "Risque": risk_text,
        "Analyse Relative": active_text,
        "Synthèse": conclusion,
    }
# ==========================================================
# DICTIONNAIRE KPI
# ==========================================================

kpis = {

    "📅 Fréquence":
        str(frequency),

    "📊 Annualisation":
        str(annual_factor),

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
commentaires = generate_commentary(
    portfolio_nav,
    annual_return_pf,
    annual_return_bm,
    alpha,
    beta,
    sharpe,
    sortino,
    ir,
    volatility_pf,
    volatility_bm,
    max_dd,
    hit_ratio,
    up_capture,
    down_capture,
)
# ==========================================================
# AFFICHAGE
# ==========================================================

st.header("📝 Commentaire Automatique")

with st.expander(
    "Voir l'analyse détaillée",
    expanded=True
):

    st.subheader("🎯 Diagnostic Global")

    st.success(
        f"{commentaires['Diagnostic']} | "
        f"Score : {commentaires['Score']}/100"
    )

    st.subheader("✅ Forces")

    if len(commentaires["Forces"]) > 0:

        for item in commentaires["Forces"\]:
            st.write(f"• {item}")

    else:

        st.write(
            "Aucun point fort significatif identifié."
        )

    st.subheader("⚠️ Points de vigilance")

    if len(commentaires["Vigilances"]) > 0:

        for item in commentaires["Vigilances"\]:
            st.write(f"• {item}")

    else:

        st.write(
            "Aucun point de vigilance majeur détecté."
        )

    st.subheader("1️⃣ Performance")
    st.write(commentaires["Performance"])

    st.subheader("2️⃣ Risque")
    st.write(commentaires["Risque"])

    st.subheader("3️⃣ Analyse Relative")
    st.write(commentaires["Analyse Relative"])

    st.subheader("4️⃣ Synthèse")
    st.success(commentaires["Synthèse"])

st.markdown("---")
# ==========================================================
# KPI
# ==========================================================

st.header("📊 Indicateurs Clés de Performance")

metrics = st.columns(4)

for i, (key, value) in enumerate(kpis.items()):
    metrics[i % 4].metric(key, value)

# ==========================================================
# TABLEAU DETAILLE
# ==========================================================

st.header("📋 Tableau Détaillé")

kpi_df = pd.DataFrame({
    "Indicateur": [str(k) for k in kpis.keys()],
    "Valeur": [str(v) for v in kpis.values()]
})

st.dataframe(
    kpi_df,
    use_container_width=True,
    hide_index=True
)

# ==========================================================
# VISUALISATIONS
# ==========================================================

st.header("📈 Visualisations")

col1, col2 = st.columns(2)

with col1:

    st.subheader("Évolution Base 100")

    fig = px.line(
        df,
        x=date_col,
        y=[portfolio_nav, benchmark_nav]
    )

    fig.update_layout(
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with col2:

    st.subheader("Rendements Périodiques")

    fig2 = px.bar(
        df,
        x=date_col,
        y=[portfolio_ret, benchmark_ret],
        barmode="group"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

col3, col4 = st.columns(2)

with col3:

    st.subheader("Drawdown")

    fig_dd = go.Figure()

    fig_dd.add_trace(
        go.Scatter(
            x=df[date_col],
            y=dd_curve.to_numpy() * 100,
            fill="tozeroy",
            line=dict(color="red")
        )
    )

    g_dd.update_layout(
        title="Drawdown (%)",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)"
    )

    st.plotly_chart(
        fig_dd,
        use_container_width=True
    )

with col4:

    st.subheader("Distribution Rendements")

    fig_hist = px.histogram(
        returns_pf * 100,
        nbins=30,
        title="Distribution des rendements"
    )

    st.plotly_chart(
        fig_hist,
        use_container_width=True
    )

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
