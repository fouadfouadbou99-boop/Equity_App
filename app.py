
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from fpdf2 import FPDF # Changed from 'from fpdf import FPDF' to explicitly use fpdf2

# import utils # Assurez-vous que utils.py est dans le même répertoire

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Portfolio Analytics App",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Titre de l'application
st.title("📈 Portfolio Analytics App")

# Sidebar pour le téléversement de fichier
st.sidebar.header("1. Télécharger vos données")
uploaded_file = st.sidebar.file_uploader(
    "Veuillez télécharger votre fichier Excel (.xlsx)",
    type=["xlsx"],
    help="Le fichier Excel doit contenir les données de performance de votre portefeuille et de l'indice de référence."
)

# Initialiser un DataFrame vide pour le cas où aucun fichier n'est téléversé
df = pd.DataFrame()

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.sidebar.success("Fichier chargé avec succès !")

        # Afficher les premières lignes du dataframe pour vérification
        st.subheader("Aperçu des données chargées")
        st.dataframe(df.head())

        # --- Traitement et calcul des métriques --- #
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)

        # Utiliser les noms de colonnes réels du fichier de l'utilisateur
        df['Prix_Portefeuille'] = df['VL_ portefeuille_actions'].astype(float)
        df['Prix_MASI'] = df['MAISI_RB'].astype(float)

        # Calcul des rendements quotidiens
        df['Rendement_Portefeuille'] = df['Prix_Portefeuille'].pct_change()
        df['Rendement_MASI'] = df['Prix_MASI'].pct_change()

        # Drop first row with NaN values from pct_change to avoid issues with cumulative products
        df = df.dropna()

        # Calcul de la performance base 100
        df['Perf_Portefeuille'] = (1 + df['Rendement_Portefeuille']).cumprod() * 100
        df['Perf_MASI'] = (1 + df['Rendement_MASI']).cumprod() * 100

        # Calcul des rendements hebdomadaires
        df_weekly = df.resample('W').last()
        df_weekly['Rendement_Portefeuille_Hebdo'] = df_weekly['Prix_Portefeuille'].pct_change()
        df_weekly['Rendement_MASI_Hebdo'] = df_weekly['Prix_MASI'].pct_change()

        # --- CALCUL DES KPIS RÉELS --- #
        # Rendements moyens
        avg_port_return = df['Rendement_Portefeuille'].mean() * 252 # Annualisé
        avg_masi_return = df['Rendement_MASI'].mean() * 252 # Annualisé

        # Volatilité (écart-type annualisé)
        vol_port = df['Rendement_Portefeuille'].std() * np.sqrt(252)
        vol_masi = df['Rendement_MASI'].std() * np.sqrt(252)

        # Bêta (nécessite une régression linéaire)
        # Assurez-vous qu'il n'y a pas de zéros ou de NaN qui peuvent causer des problèmes
        # On va utiliser numpy pour la covariance et variance
        if df['Rendement_MASI'].std() != 0:
            beta = df['Rendement_Portefeuille'].cov(df['Rendement_MASI']) / df['Rendement_MASI'].var()
        else:
            beta = 0.0 # Gérer le cas où la variance de l'indice est nulle

        # Ratio de Sharpe (taux sans risque = 0 pour simplification)
        # Normalement (Rendement du Portefeuille - Taux Sans Risque) / Volatilité du Portefeuille
        sharpe_ratio = avg_port_return / vol_port if vol_port != 0 else 0.0

        # Tracking Error
        active_return = df['Rendement_Portefeuille'] - df['Rendement_MASI']
        tracking_error = active_return.std() * np.sqrt(252)

        # Information Ratio (si Tracking Error != 0)
        information_ratio = active_return.mean() * 252 / tracking_error if tracking_error != 0 else 0.0

        kpis_calculated = {
            "Performance Portefeuille (Ann.)": f"{avg_port_return:.2%}",
            "Performance Indice (Ann.)": f"{avg_masi_return:.2%}",
            "Volatilité Portefeuille (Ann.)": f"{vol_port:.2%}",
            "Volatilité Indice (Ann.)": f"{vol_masi:.2%}",
            "Ratio de Sharpe": f"{sharpe_ratio:.2f}",
            "Bêta": f"{beta:.2f}",
            "Tracking Error (Ann.)": f"{tracking_error:.2%}",
            "Information Ratio": f"{information_ratio:.2f}"
        }

        # Affichage des KPIs
        st.sidebar.header("2. Indicateurs Clés de Performance")
        cols = st.sidebar.columns(2)
        kpi_items = list(kpis_calculated.items())
        for i, (kpi_name, kpi_value) in enumerate(kpi_items):
            with cols[i % 2]:
                st.metric(label=kpi_name, value=kpi_value)
        st.sidebar.markdown("---")

        st.subheader("Tableau Récapitulatif des KPIs")
        st.dataframe(pd.DataFrame(kpi_items, columns=['KPI', 'Valeur']).set_index('KPI'))
        st.markdown("---")

        st.header("Visualisations")

        # --- Évolution Base 100 ---
        st.subheader("Évolution Base 100")
        fig_base100 = px.line(df[['Perf_Portefeuille', 'Perf_MASI']],
                              title='Évolution Base 100 du Portefeuille et du MASI',
                              labels={'value': 'Performance (Base 100)', 'Date': 'Date'})
        st.plotly_chart(fig_base100, use_container_width=True)

        # --- Rendements Hebdomadaires ---
        st.subheader("Rendements Hebdomadaires")
        fig_rendements_hebdo = px.line(df_weekly[['Rendement_Portefeuille_Hebdo', 'Rendement_MASI_Hebdo']].dropna(),
                                         title='Rendements Hebdomadaires du Portefeuille et du MASI',
                                         labels={'value': 'Rendement Hebdomadaire', 'Date': 'Date'})
        st.plotly_chart(fig_rendements_hebdo, use_container_width=True)

        # --- Active Return ---
        st.subheader("Active Return")
        df['Active_Return_Daily'] = df['Rendement_Portefeuille'] - df['Rendement_MASI'] # Daily active return
        fig_active_return = px.line(df['Active_Return_Daily'].dropna(),
                                     title='Active Return (Rendement Portefeuille - Rendement Indice)',
                                     labels={'value': 'Active Return', 'Date': 'Date'})
        st.plotly_chart(fig_active_return, use_container_width=True)

        # --- Distribution des Rendements ---
        st.subheader("Distribution des Rendements")
        fig_dist_rendements = px.histogram(df[['Rendement_Portefeuille', 'Rendement_MASI']].melt(),
                                            x="value", color="variable",
                                            nbins=50, title='Distribution des Rendements',
                                            labels={'value': 'Rendement', 'variable': 'Type de Rendement'})
        st.plotly_chart(fig_dist_rendements, use_container_width=True)

        # --- Analyse du Bêta ---
        st.header("Analyse du Bêta")

        scatter_df_for_plot = df[['Rendement_MASI', 'Rendement_Portefeuille']].dropna().copy()
        scatter_df_for_plot.rename(columns={
            'Rendement_MASI': 'Rendement de l\'Indice',
            'Rendement_Portefeuille': 'Rendement du Portefeuille'
        }, inplace=True)

        fig_beta = px.scatter(
            scatter_df_for_plot,
            x='Rendement de l\'Indice',
            y='Rendement du Portefeuille',
            trendline="ols",
            title="Analyse du Bêta: Rendement du Portefeuille vs Rendement de l'Indice",
            labels={
                'Rendement de l\'Indice': 'Rendement de l\'Indice',
                'Rendement du Portefeuille': 'Rendement du Portefeuille'
            }
        )
        st.plotly_chart(fig_beta, use_container_width=True)

        # --- Commentaire automatique et résumé exécutif ---
        st.subheader("Commentaire Automatique et Résumé Exécutif")
        commentary = ""

        if avg_port_return > avg_masi_return:
            commentary += f"Le portefeuille a **surpassé** l'indice de référence MASI, avec une performance annualisée de {kpis_calculated['Performance Portefeuille (Ann.)']} contre {kpis_calculated['Performance Indice (Ann.)']} pour l'indice. "
        else:
            commentary += f"Le portefeuille a **sous-performé** l'indice de référence MASI, avec une performance annualisée de {kpis_calculated['Performance Portefeuille (Ann.)']} contre {kpis_calculated['Performance Indice (Ann.)']} pour l'indice. "

        commentary += f"La volatilité du portefeuille est de {kpis_calculated['Volatilité Portefeuille (Ann.)']}, ce qui est {'plus élevé' if vol_port > vol_masi else 'plus bas'} que celle de l'indice ({kpis_calculated['Volatilité Indice (Ann.)']}). "
        commentary += f"Le Bêta du portefeuille est de {kpis_calculated['Bêta']}, indiquant sa sensibilité aux mouvements du marché. "
        commentary += f"Le Ratio de Sharpe de {kpis_calculated['Ratio de Sharpe']} suggère la performance ajustée au risque du portefeuille. "
        commentary += f"Enfin, la Tracking Error est de {kpis_calculated['Tracking Error (Ann.)']}, et le Ratio d'Information de {kpis_calculated['Information Ratio']} mesure la capacité du gérant à générer de l'alpha par rapport à la volatilité de l'excès de rendement. "

        st.markdown(commentary)

        # --- Affichage des données source ---
        st.subheader("Données Source (Nettoyées et Traitées)")
        st.dataframe(df)

        # --- Options d'Export ---
        st.sidebar.header("3. Options d'Export")
        col1_exp, col2_exp, col3_exp, col4_exp = st.sidebar.columns(4) # Added a column for PDF

        with col1_exp:
            # Need to use BytesIO for to_excel with download_button
            import io
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            st.download_button(
                label="Exporter Excel",
                data=excel_buffer.getvalue(),
                file_name="portfolio_analytics.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Exporter les données traitées en fichier Excel."
            )
        with col2_exp:
            st.download_button(
                label="Exporter KPIs (CSV)",
                data=pd.DataFrame(kpi_items, columns=['KPI', 'Valeur']).to_csv(index=False).encode('utf-8'),
                file_name="kpis.csv",
                mime="text/csv",
                help="Exporter les KPIs en fichier CSV."
            )
        with col3_exp:
            st.download_button(
                label="Exporter Power BI (CSV)",
                data=df.to_csv(index=False).encode('utf-8'), # Ajuster selon le format Power BI attendu
                file_name="powerbi_data.csv",
                mime="text/csv",
                help="Exporter les données pour Power BI en CSV."
            )

        with col4_exp:
            # PDF Export
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Rapport d'Analyse de Portefeuille", ln=True, align='C')
            pdf.ln(10)

            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 5, commentary)
            pdf.ln(10)

            pdf.set_font("Arial", 'B', size=10)
            pdf.cell(0, 10, txt="Indicateurs Clés de Performance", ln=True)
            pdf.ln(5)

            # Table headers
            col_width = pdf.w / 2.5 # distribute width for 2 columns
            row_height = 8
            pdf.set_font("Arial", 'B', size=9)
            pdf.cell(col_width, row_height, "KPI", border=1)
            pdf.cell(col_width, row_height, "Valeur", border=1)
            pdf.ln(row_height)

            # Table data
            pdf.set_font("Arial", size=9)
            for kpi_name, kpi_value in kpi_items:
                pdf.cell(col_width, row_height, str(kpi_name), border=1)
                pdf.cell(col_width, row_height, str(kpi_value), border=1)
                pdf.ln(row_height)

            pdf_output = pdf.output(dest='S').encode('latin-1') # Use latin-1 for FPDF simple encoding

            st.download_button(
                label="Exporter PDF",
                data=pdf_output,
                file_name="portfolio_report.pdf",
                mime="application/pdf",
                help="Exporter les KPIs et le résumé en PDF."
            )

    except Exception as e:
        st.error(f"Une erreur est survenue lors du traitement du fichier : {e}")
        st.info("Veuillez vérifier que votre fichier Excel est correctement formaté et qu'il contient les colonnes 'Date', 'VL_ portefeuille_actions' et 'MAISI_RB'.")
else:
    st.info("Veuillez téléverser un fichier Excel pour commencer l'analyse.")

