# Dashboard Institutionnel de Gestion d'Actifs

## Description

Application Streamlit dédiée au pilotage d'un portefeuille actions avec comparaison au benchmark MASI RB.

L'application fournit :

- KPI de performance
- KPI de risque
- Gestion active
- Analyse benchmark
- Analyse drawdown
- Analyse VaR
- Attribution de performance
- Dashboard exécutif
- Commentaires automatiques
- Export Excel
- Export PDF
- Export PowerPoint
- API Power BI

---

## Fonctionnalités

### Performance

- Performance cumulée
- Performance annualisée
- WTD
- MTD
- QTD
- YTD
- 1M
- 3M
- 6M
- 12M

### Gestion active

- Alpha
- Alpha annualisé
- Bêta
- Corrélation
- Tracking Error
- Information Ratio
- Hit Ratio

### Risque

- Volatilité
- Downside Volatility
- VaR 95%
- VaR 99%
- CVaR 95%
- CVaR 99%

### Ratios

- Sharpe
- Sortino
- Treynor
- Omega
- Calmar
- Sterling

### Drawdown

- Drawdown courant
- Maximum Drawdown
- Recovery Time

### Rolling Analysis

- Rolling Volatility
- Rolling Alpha
- Rolling Beta
- Rolling Sharpe
- Rolling Tracking Error

---

## Installation

Créer un environnement virtuel :

```bash
python -m venv venv
```

Activation :

```bash
source venv/bin/activate
```

ou sous Windows :

```bash
venv\Scripts\activate
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

---

## Exécution

```bash
streamlit run app.py
```

---

## Données requises

Le fichier Excel doit contenir les colonnes suivantes :

```text
Date
VL_portefeuille_actions
VL_portefeuille_actions base_100
Perf Hebdo Portefeuille_actions
MASI_RB
MASI_RB_ base_100
Perf Hebdo MASI_RB
```

---

## Exports

### Excel

Contient :

- Historique
- KPI
- Risque
- Performance
- Tracking Error
- Attribution

### PDF

Rapport automatique comprenant :

- Synthèse exécutive
- KPI
- Graphiques
- Conclusion

### PowerPoint

Présentation prête pour :

- Comité d'investissement
- Conseil d'administration
- Comité risques

### CSV

Export des historiques.

### JSON

Interopérabilité BI et API.

---

## Power BI

L'application expose une API REST.

### KPI

```text
http://localhost:8000/kpis
```

### Historique

```text
http://localhost:8000/history
```

Power BI peut se connecter directement à ces endpoints.

---

## KPI produits

La solution restitue plus de 40 indicateurs.

### Performance

- Perf Absolue
- Perf Relative
- Alpha

### Risque

- Volatilité
- VaR
- CVaR

### Gestion active

- Bêta
- Tracking Error
- Information Ratio

### Ratios

- Sharpe
- Sortino
- Treynor
- Calmar

### Drawdown

- Maximum Drawdown
- Time under water

---

## Architecture

```text
project/
│
├── app.py
├── requirements.txt
├── README.md
│
├── data/
├── exports/
├── reports/
├── assets/
└── api/
```

---

## Déploiement

Compatible :

- Azure App Service
- Azure Container Apps
- Docker
- Kubernetes
- Streamlit Community

---

## Auteur

Dashboard institutionnel destiné à l'analyse de portefeuille et au reporting d'investissement.
