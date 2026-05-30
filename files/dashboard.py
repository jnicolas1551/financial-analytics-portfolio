# =============================================================================
# DASHBOARD.PY — INTERFAZ INTERACTIVA EN STREAMLIT
# Portfolio Analyzer · Versión 1.0
# =============================================================================
#
# CÓMO CORRER:
#   py -m streamlit run dashboard.py
#
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from io import BytesIO

from config import (
    APP_TITULO, APP_SUBTITULO, PERIODOS_DISPONIBLES,
    DIAS_ANIO_DEFAULT, RF_DEFAULT, EXCEL_EXPORT_NOMBRE
)
from datos import combinar_activos, calcular_rendimientos
from calculos import (
    precios_base100, retorno_nominal, retorno_ea,
    volatilidad_diaria, volatilidad_anual, sharpe_ratio,
    analisis_percentiles, rango_percentil_actual,
    matriz_correlacion, covarianza_diaria, covarianza_anual,
    montecarlo_iteraciones, tabla_activos, tabla_portafolio
)
from optimizacion import optimizar_todos, frontera_eficiente


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Portfolio Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title(APP_TITULO)
st.caption(APP_SUBTITULO)

# -----------------------------------------------------------------------------
# SIDEBAR — INPUTS DEL USUARIO
# -----------------------------------------------------------------------------

st.sidebar.header("⚙️ Configuración")

# ACTIVOS
st.sidebar.subheader("Activos")
tickers_yahoo_input = st.sidebar.text_input(
    "Tickers Yahoo Finance (último = benchmark)",
    value="AAPL, NVDA, KO, ^GSPC",
    help="Separa con comas. El último ticker será el benchmark."
)

tickers_fics_input = st.sidebar.text_input(
    "FICs Colombia (palabras clave)",
    value="",
    help="Opcional. Separa con comas. Ej: RENTAFACIL, UNIVERSITAS"
)

# PERÍODO
st.sidebar.subheader("Período de análisis")

fecha_especifica = st.sidebar.date_input(
    "Fecha inicio específica (opcional)",
    value=None,
    help="Si se completa, se usa como fecha de inicio en lugar del período máximo."
)

periodos_seleccionados = st.sidebar.multiselect(
    "Períodos a analizar",
    options=list(PERIODOS_DISPONIBLES.keys()),
    default=["1 año", "2 años", "3 años"],
    help="Selecciona hasta 3 períodos."
)

# PARÁMETROS
st.sidebar.subheader("Parámetros")

dias_anio = st.sidebar.number_input(
    "Días hábiles por año",
    min_value=252,
    max_value=365,
    value=DIAS_ANIO_DEFAULT,
    step=1
)

rf_pct = st.sidebar.number_input(
    "Tasa libre de riesgo RF (%)",
    min_value=0.0,
    max_value=20.0,
    value=RF_DEFAULT,
    step=0.1,
    format="%.2f"
)
rf = rf_pct / 100

# BOTÓN DE EJECUCIÓN
ejecutar = st.sidebar.button("▶ Ejecutar análisis", type="primary", use_container_width=True)

# -----------------------------------------------------------------------------
# LÓGICA PRINCIPAL
# -----------------------------------------------------------------------------

if ejecutar:

    # Parsear tickers
    tickers_yahoo = [t.strip().upper() for t in tickers_yahoo_input.split(',') if t.strip()]
    tickers_fics = [t.strip() for t in tickers_fics_input.split(',') if t.strip()]

    if len(tickers_yahoo) < 2:
        st.error("Necesitas al menos 2 tickers en Yahoo Finance (activos + benchmark).")
        st.stop()

    benchmark = tickers_yahoo[-1]
    activos_yahoo = tickers_yahoo[:-1]

    # Fecha de inicio
    if fecha_especifica:
        fecha_inicio = fecha_especifica.strftime('%Y-%m-%d')
    else:
        años_max = max([PERIODOS_DISPONIBLES[p] for p in periodos_seleccionados]) if periodos_seleccionados else 3
        fecha_inicio = (datetime.today() - timedelta(days=int(años_max * 365) + 30)).strftime('%Y-%m-%d')

    # Períodos seleccionados
    periodos = {k: v for k, v in PERIODOS_DISPONIBLES.items() if k in periodos_seleccionados}
    if not periodos:
        st.error("Selecciona al menos un período de análisis.")
        st.stop()

    # DESCARGA DE DATOS
    with st.spinner("Descargando datos..."):
        try:
            df_precios, benchmark_nombre = combinar_activos(
                tickers_yahoo, tickers_fics, benchmark, fecha_inicio
            )
        except Exception as e:
            st.error(f"Error descargando datos: {e}")
            st.stop()

    cols_activos = [c for c in df_precios.columns if c != benchmark]

    # Pesos iniciales iguales
    n_activos = len(cols_activos)
    pesos = {c: 1/n_activos for c in cols_activos}

    # CÁLCULOS
    with st.spinner("Calculando métricas..."):

        df_rend = calcular_rendimientos(df_precios, pesos)
        df_base100 = precios_base100(df_precios)
        df_nom = retorno_nominal(df_precios, periodos)
        df_ea = retorno_ea(df_nom, periodos, dias_anio)
        df_vol_d = volatilidad_diaria(df_rend, periodos)
        df_vol_a = volatilidad_anual(df_vol_d, dias_anio)
        df_sharpe = sharpe_ratio(df_ea, df_vol_a, rf)
        df_percentiles = analisis_percentiles(df_rend)
        df_rango = rango_percentil_actual(df_rend)
        df_corr = matriz_correlacion(df_rend)
        df_cov_d = covarianza_diaria(df_rend)
        df_cov_a = covarianza_anual(df_cov_d, dias_anio)
        retornos_mc = montecarlo_iteraciones(df_rend, dias_anio=dias_anio)
        tablas_act = tabla_activos(df_rend, df_cov_a, pesos, rf, benchmark, retornos_mc, dias_anio)
        tablas_port = tabla_portafolio(tablas_act, pesos, cols_activos)

    # OPTIMIZACIÓN
    with st.spinner("Optimizando portafolios..."):
        df_opt = optimizar_todos(tablas_act, df_cov_a, rf)

    # -------------------------------------------------------------------------
    # SECCIÓN 1: RESUMEN RÁPIDO
    # -------------------------------------------------------------------------
    st.header("📈 Resumen del Portafolio")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Activos analizados", len(cols_activos))
    col2.metric("Benchmark", benchmark)
    col3.metric("Fechas disponibles", len(df_precios))
    col4.metric("RF utilizada", f"{rf_pct:.2f}%")

    # -------------------------------------------------------------------------
    # SECCIÓN 2: TABLA DE PESOS ÓPTIMOS (PRINCIPAL)
    # -------------------------------------------------------------------------
    st.header("🎯 Portafolios Óptimos")
    st.caption("9 portafolios: 3 métodos × 3 objetivos. Pesos en % por activo.")

    if not df_opt.empty:
        # Mostrar pesos formateados como porcentaje
        cols_pesos = [c for c in df_opt.columns if c in cols_activos]
        cols_metricas = ['Retorno', 'Volatilidad', 'Sharpe']

        df_display = df_opt[cols_pesos + cols_metricas].copy()
        for col in cols_pesos:
            df_display[col] = df_display[col].map(lambda x: f"{x:.1%}")
        for col in cols_metricas:
            df_display[col] = df_display[col].map(lambda x: f"{x:.2%}" if col != 'Sharpe' else f"{x:.3f}")

        st.dataframe(df_display, use_container_width=True)

    # -------------------------------------------------------------------------
    # SECCIÓN 3: TABLAS DE ANÁLISIS (DESPLEGABLES)
    # -------------------------------------------------------------------------
    st.header("📊 Análisis Detallado")

    with st.expander("Retorno Nominal por Período"):
        st.dataframe(df_nom.style.format("{:.2%}"), use_container_width=True)

    with st.expander("Retorno Efectivo Anual (EA)"):
        st.dataframe(df_ea.style.format("{:.2%}"), use_container_width=True)

    with st.expander("Volatilidad Diaria"):
        st.dataframe(df_vol_d.style.format("{:.4%}"), use_container_width=True)

    with st.expander("Volatilidad Anual"):
        st.dataframe(df_vol_a.style.format("{:.2%}"), use_container_width=True)

    with st.expander("Sharpe Ratio"):
        st.dataframe(df_sharpe.style.format("{:.3f}"), use_container_width=True)

    with st.expander("Análisis de Percentiles (rendimientos diarios)"):
        st.dataframe(df_percentiles.style.format("{:.4%}"), use_container_width=True)

    with st.expander("Rango Percentil Actual"):
        st.dataframe(df_rango.to_frame().T.style.format("{:.2%}"), use_container_width=True)

    with st.expander("Matriz de Correlación"):
        fig_corr = px.imshow(
            df_corr, text_auto=".2f",
            color_continuous_scale='RdBu_r',
            zmin=-1, zmax=1,
            title="Correlación de Rendimientos"
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    with st.expander("Covarianza Diaria"):
        st.dataframe(df_cov_d.style.format("{:.8f}"), use_container_width=True)

    with st.expander("Covarianza Anual"):
        st.dataframe(df_cov_a.style.format("{:.6f}"), use_container_width=True)

    with st.expander("Tabla por Activo — Markowitz"):
        st.dataframe(tablas_act['markowitz'].style.format("{:.4f}"), use_container_width=True)

    with st.expander("Tabla por Activo — CAPM"):
        st.dataframe(tablas_act['capm'].style.format("{:.4f}"), use_container_width=True)

    with st.expander("Tabla por Activo — Montecarlo"):
        st.dataframe(tablas_act['montecarlo'].style.format("{:.4f}"), use_container_width=True)

    with st.expander("Verificación del Portafolio"):
        col1, col2, col3 = st.columns(3)
        for i, (metodo, df_p) in enumerate(tablas_port.items()):
            [col1, col2, col3][i].subheader(metodo.capitalize())
            [col1, col2, col3][i].dataframe(df_p.style.format("{:.4f}"))

    # -------------------------------------------------------------------------
    # SECCIÓN 4: GRÁFICOS DE FRONTERA EFICIENTE
    # -------------------------------------------------------------------------
    st.header("📉 Frontera Eficiente")

    fig = go.Figure()

    colores = {'markowitz': 'blue', 'capm': 'green', 'montecarlo': 'red'}

    for metodo in ['markowitz', 'capm', 'montecarlo']:
        if metodo not in tablas_act:
            continue
        retornos_metodo = tablas_act[metodo].loc['Retorno']
        cov_activos = df_cov_a.loc[cols_activos, cols_activos]

        df_frontera = frontera_eficiente(retornos_metodo, cov_activos, rf)

        if not df_frontera.empty:
            fig.add_trace(go.Scatter(
                x=df_frontera['Volatilidad'],
                y=df_frontera['Retorno'],
                mode='lines',
                name=f'Frontera {metodo.capitalize()}',
                line=dict(color=colores[metodo], width=2)
            ))

    # Agregar puntos de portafolios óptimos
    if not df_opt.empty:
        fig.add_trace(go.Scatter(
            x=df_opt['Volatilidad'],
            y=df_opt['Retorno'],
            mode='markers+text',
            name='Portafolios Óptimos',
            text=df_opt.index.get_level_values('Objetivo'),
            textposition='top center',
            marker=dict(size=10, color='black', symbol='star')
        ))

    fig.update_layout(
        title="Frontera Eficiente — 3 Métodos",
        xaxis_title="Volatilidad Anual",
        yaxis_title="Retorno Esperado",
        xaxis=dict(tickformat='.1%'),
        yaxis=dict(tickformat='.1%'),
        height=500,
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Gráfico de precios base 100
    with st.expander("Ver evolución de precios (Base 100)"):
        fig2 = px.line(
            df_base100,
            title="Evolución de Precios — Base 100",
            labels={'value': 'Precio Normalizado', 'fecha': 'Fecha'}
        )
        st.plotly_chart(fig2, use_container_width=True)

    # -------------------------------------------------------------------------
    # SECCIÓN 5: EXPORTAR A EXCEL
    # -------------------------------------------------------------------------
    st.header("💾 Exportar")

    def generar_excel():
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_precios.to_excel(writer, sheet_name='Precios')
            df_rend.to_excel(writer, sheet_name='Rendimientos')
            df_base100.to_excel(writer, sheet_name='Precios Base 100')
            df_nom.to_excel(writer, sheet_name='Retorno Nominal')
            df_ea.to_excel(writer, sheet_name='Retorno EA')
            df_vol_d.to_excel(writer, sheet_name='Volatilidad Diaria')
            df_vol_a.to_excel(writer, sheet_name='Volatilidad Anual')
            df_sharpe.to_excel(writer, sheet_name='Sharpe Ratio')
            df_percentiles.to_excel(writer, sheet_name='Percentiles')
            df_rango.to_frame().to_excel(writer, sheet_name='Rango Percentil')
            df_corr.to_excel(writer, sheet_name='Correlacion')
            df_cov_d.to_excel(writer, sheet_name='Covarianza Diaria')
            df_cov_a.to_excel(writer, sheet_name='Covarianza Anual')
            for metodo, df_t in tablas_act.items():
                df_t.to_excel(writer, sheet_name=f'Tabla Activos {metodo[:4].title()}')
            if not df_opt.empty:
                df_opt.to_excel(writer, sheet_name='Portafolios Optimos')
        buffer.seek(0)
        return buffer

    st.download_button(
        label="📥 Descargar análisis completo en Excel",
        data=generar_excel(),
        file_name=EXCEL_EXPORT_NOMBRE,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

else:
    st.info("👈 Configura los parámetros en el panel izquierdo y presiona **Ejecutar análisis**.")
    st.markdown("""
    ### ¿Qué hace este sistema?
    1. **Descarga** precios históricos de Yahoo Finance y FICs colombianos
    2. **Calcula** 14 tablas de análisis financiero
    3. **Optimiza** 9 portafolios: 3 métodos × 3 objetivos
    4. **Visualiza** la frontera eficiente interactiva
    5. **Exporta** todos los resultados a Excel
    """)
