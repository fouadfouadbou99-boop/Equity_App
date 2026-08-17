import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
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

        # st.subheader("Vérification des colonnes nécessaires")
        # required_cols = ['Date', 'Prix_Portefeuille', 'Prix_MASI'] # Exemple, ajustez au besoin
        # for col in required_cols:
        #     if col not in df.columns:
        #         st.error(f"La colonne '{col}' est manquante dans votre fichier. Veuillez vérifier le format.")
        #         st.stop()

        # st.subheader("Traitement et calcul des métriques")
        # df_processed, kpis = utils.process_and_calculate_metrics(df) # Utiliser vos fonctions de utils.py

        # Dummy data for demonstration since utils.py is not provided
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df['Prix_Portefeuille'] = df['Prix_Portefeuille'].astype(float)
        df['Prix_MASI'] = df['Prix_MASI'].astype(float)

        # Calcul des rendements quotidiens
        df['Rendement_Portefeuille'] = df['Prix_Portefeuille'].pct_change()
        df['Rendement_MASI'] = df['Prix_MASI'].pct_change()

        # Calcul de la performance base 100
        df['Perf_Portefeuille'] = (1 + df['Rendement_Portefeuille']).cumprod() * 100
        df['Perf_MASI'] = (1 + df['Rendement_MASI']).cumprod() * 100
        
        # Drop first row with NaN values from pct_change
        df = df.dropna()
        
        # For Beta calculation, ensure we have daily returns
        # If not already calculated, you would do it here
        df['Perf_Portefeuille_Daily'] = df['Prix_Portefeuille'].pct_change()
        df['Perf_MASI_Daily'] = df['Prix_MASI'].pct_change()

        # Calcul des rendements hebdomadaires (exemple)
        df_weekly = df.resample('W').last()
        df_weekly['Rendement_Portefeuille_Hebdo'] = df_weekly['Prix_Portefeuille'].pct_change()
        df_weekly['Rendement_MASI_Hebdo'] = df_weekly['Prix_MASI'].pct_change()

        # Exemple de calcul de KPI (simulé)
        kpis = {
            "Performance Portefeuille (Total)": "25.00%",
            "Performance Indice (Total)": "18.00%",
            "Volatilité Portefeuille": "12.00%",
            "Volatilité Indice": "10.00%",
            "Ratio de Sharpe": "1.50",
            "Bêta": "1.20",
            "Tracking Error": "3.00%",
            "Information Ratio": "0.80"
        }

        # Affichage des KPIs
        st.sidebar.header("2. Indicateurs Clés de Performance")
        cols = st.sidebar.columns(2)
        for i, (kpi_name, kpi_value) in enumerate(kpis.items()):
            with cols[i % 2]:
                st.metric(label=kpi_name, value=kpi_value)

        st.sidebar.markdown("---")
        
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
        df['Active_Return'] = df['Rendement_Portefeuille'] - df['Rendement_MASI']
        fig_active_return = px.line(df['Active_Return'].dropna(), 
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
        st.header("Analyse du Bêta") # Restored st.header

        # Create a DataFrame for scatter plot, dropping rows with any missing values.
        # Using the daily returns for beta calculation.
        scatter_df_for_plot = df[['Rendement_MASI_Daily', 'Rendement_Portefeuille_Daily']].dropna().copy()
        scatter_df_for_plot.rename(columns={
            'Rendement_MASI_Daily': 'Rendement de l\'Indice',
            'Rendement_Portefeuille_Daily': 'Rendement du Portefeuille'
        }, inplace=True)

        fig_beta = px.scatter(
            scatter_df_for_plot,
            x='Rendement de l\'Indice',
            y='Rendement du Portefeuille',
            trendline="ols",
            title="Analyse du Bêta: Rendement du Portefeuille vs Rendement de l'Indice", # Added plot title
            labels={ # Explicitly set axis labels
                'Rendement de l\'Indice': 'Rendement de l\'Indice',
                'Rendement du Portefeuille': 'Rendement du Portefeuille'
            }
        )
        st.plotly_chart(fig_beta, use_container_width=True) # Restored st.plotly_chart
        
        # --- Commentaire automatique et résumé exécutif ---
        st.subheader("Commentaire Automatique et Résumé Exécutif")
        st.write("Générez ici des commentaires automatisés basés sur les KPIs et l'analyse. (À implémenter)")
        # Exemple de commentaire simple
        st.markdown("Le portefeuille a surperformé l'indice de référence, avec un rendement total de X% contre Y% pour l'indice.")

        # --- Affichage des données source ---
        st.subheader("Données Source (Nettoyées et Traitées)")
        st.dataframe(df)

        # --- Options d'Export ---
        st.sidebar.header("3. Options d'Export")
        col1_exp, col2_exp, col3_exp = st.sidebar.columns(3)

        with col1_exp:
            st.download_button(
                label="Exporter Excel",
                data=df.to_excel("portfolio_analytics.xlsx", index=False).encode('utf-8'),
                file_name="portfolio_analytics.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Exporter les données traitées en fichier Excel."
            )
        with col2_exp:
            st.download_button(
                label="Exporter KPIs (CSV)",
                data=pd.DataFrame(list(kpis.items()), columns=['KPI', 'Valeur']).to_csv(index=False).encode('utf-8'),
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

    except Exception as e:
        st.error(f"Une erreur est survenue lors du traitement du fichier : {e}")
        st.info("Veuillez vérifier que votre fichier Excel est correctement formaté.")
else:
    st.info("Veuillez téléverser un fichier Excel pour commencer l'analyse.")

