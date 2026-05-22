# Financial Analytics Portfolio

> Ingeniero Civil · MAF EAFIT · Ibagué, Colombia

Portafolio de modelos de análisis financiero y pipelines de datos automatizados,
construido con Python y Excel. Enfocado en mercados colombianos e internacionales.

---

## Proyectos

### 01 · Pipeline de Precios — Yahoo Finance → Excel
**Archivo:** `descarga_acciones.py`

Pipeline automatizado que descarga precios históricos diarios de activos
internacionales y los escribe directamente en Excel, eliminando cualquier
intervención manual.

**Activos:** S&P 500 · Apple · Coca-Cola · Ecopetrol · Nvidia · Amazon · Tesla  
**Período:** 2016 — presente · 2604 fechas · Moneda: USD  
**Features:**
- Limpieza automática: elimina filas con datos faltantes en cualquier activo
- Log auditable generado en cada ejecución
- Arquitectura modular: agregar activos nuevos requiere una línea de código

**Stack:** Python 3.13 · yfinance · pandas · openpyxl

---

## Stack Técnico

| Herramienta | Uso |
|---|---|
| Python 3.13 | Pipelines y automatización |
| pandas | Manipulación de datos |
| yfinance | Descarga de precios Yahoo Finance |
| Excel / openpyxl | Modelos de análisis y output |

---

## En construcción
- Análisis de FICs colombianos (datos.gov.co)
- Métricas de portafolio: Sharpe, VaR, CVaR
- Backtesting de estrategias cuantitativas
