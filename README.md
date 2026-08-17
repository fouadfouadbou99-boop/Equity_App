# Portfolio Analytics Streamlit App

This Streamlit application provides a comprehensive analysis of a financial portfolio against a benchmark index (e.g., MASI). Users can upload their portfolio data in Excel format, and the app will display key performance indicators (KPIs), various interactive charts, and provide data export options.

## Features

-   **Data Upload**: Easily upload your portfolio and benchmark data via an Excel file (`.xlsx`).
-   **Key Performance Indicators (KPIs)**: View essential metrics such as total performance, volatility, Sharpe Ratio, Beta, Tracking Error, and Information Ratio.
-   **Interactive Visualizations**:
    -   **Evolution Base 100**: Compare the growth of your portfolio against the benchmark, normalized to a base of 100.
    -   **Weekly Returns**: Analyze weekly performance trends for both your portfolio and the benchmark.
    -   **Active Return**: Track the difference in returns between your portfolio and the benchmark.
    -   **Returns Distribution**: Visualize the frequency distribution of daily returns for both.
    -   **Beta Analysis**: A scatter plot showing portfolio returns vs. benchmark returns, with an OLS trendline to estimate the Beta coefficient.
-   **Automated Commentary**: A section for automated insights and executive summaries based on the analysis.
-   **Source Data Display**: Review the cleaned and processed underlying data.
-   **Export Options**: Download processed data and KPIs in various formats:
    -   Excel (`.xlsx`)
    -   KPIs CSV (`.csv`)
    -   Power BI CSV (`.csv`) for easy integration into reporting tools.
    -   PDF (`.pdf`) for a basic data table export.

## How to Run

1.  **Install Dependencies**: Make sure you have Python installed. Then, install the required libraries using `pip`:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Save the App**: Save the `app.py` file in a directory.
3.  **Run Streamlit**: Open your terminal or command prompt, navigate to the directory where `app.py` is saved, and run the command:
    ```bash
    streamlit run app.py
    ```
    This will open the application in your web browser.

## Data Format

Your Excel file should contain at least the following columns:
-   `Date`: (Date format) The date of the data point.
-   `Prix_Portefeuille`: (Numeric) The price or value of your portfolio.
-   `Prix_MASI`: (Numeric) The price or value of the benchmark index (e.g., MASI).

## Contribution

Feel free to contribute by adding more features, improving existing analyses, or refining the UI.
