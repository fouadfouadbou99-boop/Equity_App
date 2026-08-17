# Portfolio Analytics

Application Streamlit permettant :

- Analyse de la poche actions
- Comparaison au MASI RB
- Alpha
- Bêta
- Corrélation
- Volatilité
- Tracking Error
- Information Ratio
- Sharpe Ratio
- Hit Ratio
- Visualisations interactives
- Export Excel
- Export PDF
- Intégration Power BI

---

## Installation

```bash
git clone https://github.com/votre-compte/portfolio-analytics.git

cd portfolio-analytics

pip install -r requirements.txt
```

---

## Lancement

```bash
streamlit run app.py
```

---

## Données attendues

Colonnes :

Date

VL_Portefeuille

Base100_Portefeuille

Perf_Portefeuille

MASI_RB

Base100_MASI

Perf_MASI

---

## Déploiement

Compatible :

- GitHub
- Streamlit Community Cloud
- Azure App Service
- Docker
- Power BI

---

## Power BI

Power BI pourra :

- Consommer directement le fichier Excel exporté
- Consommer une base SQL Azure
- Consommer un Dataflow

La solution recommandée est :

Excel → Streamlit → Azure SQL → Power BI
