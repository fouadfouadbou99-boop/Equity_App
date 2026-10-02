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
# COMMENTAIRE DE GESTION
# ==========================================================
def generate_commentary(
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

    perf_text = ""
    if pd.notna(annual_return_pf) and pd.notna(annual_return_bm):

        ecart = annual_return_pf - annual_return_bm

        if ecart > 0:
            perf_text = (
                f"Le portefeuille affiche une performance annualisée de "
                f"{annual_return_pf:.2%} contre {annual_return_bm:.2%} "
                f"pour son benchmark, soit une surperformance de "
                f"{ecart:.2%}."
            )
        else:
            perf_text = (
                f"Le portefeuille affiche une performance annualisée de "
                f"{annual_return_pf:.2%} contre {annual_return_bm:.2%} "
                f"pour son benchmark, soit une sous-performance de "
                f"{abs(ecart):.2%}."
            )

    beta_comment = ""

    if pd.notna(beta):
        if beta > 1.1:
            beta_comment = "sensibilité supérieure au marché"
        elif beta < 0.9:
            beta_comment = "profil défensif"
        else:
            beta_comment = "sensibilité proche du marché"

    vol_comment = ""

    if pd.notna(volatility_pf) and pd.notna(volatility_bm):
        if volatility_pf > volatility_bm:
            vol_comment = "une volatilité supérieure à celle du benchmark"
        else:
            vol_comment = "une volatilité inférieure à celle du benchmark"

    risk_text = (
        f"Le portefeuille présente {vol_comment}. "
        f"Son bêta de {beta:.2f} traduit une {beta_comment}. "
        f"Le drawdown maximal ressort à {max_dd:.2%}."
    )

    alpha_text = ""
    if pd.notna(alpha):
        if alpha > 0:
            alpha_text = (
                f"L'alpha positif de {alpha:.2%} témoigne d'une création de valeur."
            )
        else:
            alpha_text = (
                f"L'alpha de {alpha:.2%} traduit une création de valeur insuffisante."
            )

    ir_text = ""
    if pd.notna(ir):
        ir_text = (
            f"L'Information Ratio s'établit à {ir:.2f}."
        )

    hit_text = ""
    if pd.notna(hit_ratio):
        hit_text = (
            f"Le portefeuille surperforme son benchmark dans "
            f"{hit_ratio:.2%} des observations."
        )

    active_text = (
        f"{alpha_text} {ir_text} {hit_text}"
    )

    score = 0

    if pd.notna(alpha) and alpha > 0:
        score += 1

    if pd.notna(ir) and ir > 0:
        score += 1

    if pd.notna(sharpe) and sharpe > 1:
        score += 1

    if pd.notna(hit_ratio) and hit_ratio > 0.5:
        score += 1

    if score >= 3:
        conclusion = (
            "Dans l'ensemble, les indicateurs mettent en évidence "
            "une gestion performante, créatrice de valeur et bien "
            "rémunérée au regard du risque supporté."
        )
    elif score >= 2:
        conclusion = (
            "Les indicateurs ressortent globalement satisfaisants "
            "avec une création de valeur partielle et un profil "
            "de risque maîtrisé."
        )
    else:
        conclusion = (
            "Les indicateurs suggèrent une performance insuffisante "
            "au regard des risques encourus et nécessitent une "
            "vigilance accrue."
        )

    return {
        "Performance": perf_text,
        "Risque": risk_text,
        "Gestion Active": active_text,
        "Conclusion": conclusion,
    }
# ==========================================================
# COMMENTAIRE AUTOMATIQUE
# ==========================================================
def generate_commentary(
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
    comments = []

    # Performance
    if pd.notna(annual_return_pf) and pd.notna(annual_return_bm):
        if annual_return_pf > annual_return_bm:
            comments.append(
                f"Le portefeuille surperforme son benchmark avec une performance annualisée de {annual_return_pf:.2%} contre {annual_return_bm:.2%}."
            )
        else:
            comments.append(
                f"Le portefeuille sous-performe son benchmark avec une performance annualisée de {annual_return_pf:.2%} contre {annual_return_bm:.2%}."
            )

    # Alpha
    if pd.notna(alpha):
        if alpha > 0:
            comments.append(
                f"L'alpha positif de {alpha:.2%} traduit une création de valeur par rapport au benchmark."
            )
        else:
            comments.append(
                f"L'alpha de {alpha:.2%} indique une destruction de valeur relativement au benchmark."
            )

    # Beta
    if pd.notna(beta):
        if beta > 1.2:
            comments.append(
                f"Le bêta de {beta:.2f} révèle une sensibilité supérieure au marché."
            )
        elif beta < 0.8:
            comments.append(
                f"Le bêta de {beta:.2f} indique un profil défensif."
            )
        else:
            comments.append(
                f"Le bêta de {beta:.2f} traduit une exposition proche de celle du marché."
            )

    # Sharpe
    if pd.notna(sharpe):
        if sharpe > 1:
            comments.append(
                f"Le ratio de Sharpe ({sharpe:.2f}) reflète une bonne rémunération du risque."
            )
        elif sharpe > 0:
            comments.append(
                f"Le ratio de Sharpe ({sharpe:.2f}) reste positif mais perfectible."
            )
        else:
            comments.append(
                f"Le ratio de Sharpe ({sharpe:.2f}) suggère une rémunération insuffisante du risque."
            )

    # Sortino
    if pd.notna(sortino):
        if sortino > 1:
            comments.append(
                f"Le ratio de Sortino ({sortino:.2f}) confirme une maîtrise satisfaisante du risque baissier."
            )

    # Information Ratio
    if pd.notna(ir):
        if ir > 0.5:
            comments.append(
                f"L'Information Ratio ({ir:.2f}) traduit une génération régulière d'alpha."
            )
        elif ir < 0:
            comments.append(
                f"L'Information Ratio ({ir:.2f}) traduit une sous-performance ajustée du risque actif."
            )

    # Volatilité
    if pd.notna(volatility_pf) and pd.notna(volatility_bm):
        if volatility_pf > volatility_bm:
            comments.append(
                "La volatilité du portefeuille est supérieure à celle du benchmark."
            )
        else:
            comments.append(
                "La volatilité du portefeuille est inférieure ou équivalente à celle du benchmark."
            )

    # Drawdown
    if pd.notna(max_dd):
        comments.append(
            f"Le drawdown maximum observé est de {max_dd:.2%}."
        )

    # Hit Ratio
    if pd.notna(hit_ratio):
        comments.append(
            f"Le portefeuille surperforme le benchmark lors de {hit_ratio:.2%} des périodes observées."
        )

    # Capture
    if pd.notna(up_capture):
        if up_capture > 1:
            comments.append(
                "Le portefeuille capte plus de hausse que le benchmark dans les marchés haussiers."
            )

    if pd.notna(down_capture):
        if down_capture < 1:
            comments.append(
                "Le portefeuille protège mieux le capital lors des marchés baissiers."
            )

    return " ".join(comments)
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
commentaire = generate_commentary(
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
commentaires = generate_commentary(
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

    st.subheader("1️⃣ Performance")
    st.write(commentaires["Performance"])

    st.subheader("2️⃣ Risque")
    st.write(commentaires["Risque"])

    st.subheader("3️⃣ Gestion Active")
    st.write(commentaires["Gestion Active"])

    st.subheader("4️⃣ Conclusion")
    st.success(commentaires["Conclusion"])

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

    fig_dd.update_layout(
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
        title="Distribution"
    )

    st.plotly_chart(
        fig_hist,
        use_container_width=True
    )

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
