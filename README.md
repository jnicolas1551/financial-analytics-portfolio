# Financial Analytics Portfolio

> Ingeniero Civil · MAF EAFIT · Ibagué, Colombia
>
> Portafolio de modelos de análisis financiero y pipelines de datos automatizados,
>
> construido con Python. Enfocado en mercados colombianos e internacionales.
>
> ---
>
> ## Proyectos
>
> ### 01 · Portfolio Analyzer — Sistema de Análisis Cuantitativo
>
> Archivos: dashboard.py · calculos.py · optimizacion.py · datos.py · config.py
>
> Sistema completo de análisis y optimización de portafolios de inversión con interfaz
>
> web interactiva construida en Streamlit.
>
> Modelos implementados: Markowitz · CAPM · Montecarlo
> Métricas: Retorno nominal · EA · Volatilidad · Sharpe Ratio · Information Ratio · Percentiles · Correlación · Covarianza
> Optimización: 9 portafolios óptimos (3 métodos × 3 objetivos) + portafolio combinado ponderado por Sharpe o IR
> Fuentes de datos: Yahoo Finance · datos.gov.co (FICs colombianos) · Excel propio
> Output: Dashboard interactivo + exportación completa a Excel
>
> Stack: Python 3.13 · Streamlit · pandas · numpy · scipy · plotly · yfinance
>
> ---
>
> ### 02 · Pipeline de Precios — Yahoo Finance → Excel
>
> Archivo: descarga_acciones.py
>
> Pipeline automatizado que descarga precios históricos diarios de activos
>
> internacionales y los escribe directamente en Excel.
>
> Activos: S&P 500 · Apple · Coca-Cola · Ecopetrol · Nvidia · Amazon · Tesla
> Período: 2020 — presente · Moneda: USD
> Features: Limpieza automática · Log auditable · Arquitectura modular
>
> Stack: Python 3.13 · yfinance · pandas · openpyxl
>
> ---
>
> ## Stack Técnico
>
> | Herramienta | Uso |
> |---|---|
> | Python 3.13 | Pipelines y modelos cuantitativos |
> | Streamlit | Dashboard interactivo |
> | pandas / numpy | Manipulación y cálculo vectorizado |
> | scipy | Optimización de portafolio (SLSQP) |
> | plotly | Visualización interactiva |
> | yfinance | Descarga de precios Yahoo Finance |
> | sqlite3 | Base de datos de precios |
> | openpyxl | Exportación a Excel |
>
> ---
>
> ## Cómo correr el Portfolio Analyzer
>
> ```bash
> pip install streamlit yfinance pandas numpy scipy plotly openpyxl
>
> streamlit run dashboard.py
> ```
>
> ---
>
> ## En construcción
>
> - Backtesting de estrategias
> - - VaR · CVaR · Drawdown máximo
>   - - Integración FICs colombianos en tiempo real
>     - - Trading algorítmico con broker API
