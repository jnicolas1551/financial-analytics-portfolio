# =============================================================================
# CALCULOS.PY — MOTOR DE CÁLCULO FINANCIERO
# Tablas 1-14 del modelo de análisis de portafolio
# =============================================================================
#
# ESTRUCTURA:
#   - precios_base100()      : Tabla 3 · precios normalizados a base 100
#   - retorno_nominal()      : Tabla 1 · retorno nominal por período
#   - retorno_ea()           : Tabla 2 · retorno efectivo anual
#   - volatilidad_diaria()   : Tabla 3 · desviación estándar por período
#   - volatilidad_anual()    : Tabla 4 · vol diaria × √días
#   - sharpe_ratio()         : Tabla 5 · retorno EA / vol anual
#   - percentiles()          : Tabla 6 · percentiles 0-100 cada 10%
#   - rango_percentil()      : Tabla 7 · percentil del último rendimiento
#   - correlacion()          : Tabla 8 · matriz de correlación
#   - covarianza_diaria()    : Tabla 9 · matriz de covarianza diaria
#   - covarianza_anual()     : Tabla 10 · covarianza × días año
#   - montecarlo_muestra()   : Tabla 11 · muestra aleatoria de 365 días
#   - montecarlo_iter()      : Tabla 12 · 1000 iteraciones Montecarlo
#   - tabla_activos()        : Tabla 13 · métricas por activo y método
#   - tabla_portafolio()     : Tabla 14 · métricas del portafolio total
#
# =============================================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import (
    DIAS_ANIO_DEFAULT, PERCENTILES_ANALISIS,
    MONTECARLO_ITERACIONES, MONTECARLO_PERCENTIL
)


# -----------------------------------------------------------------------------
# UTILIDAD: FILTRAR POR PERÍODO
# -----------------------------------------------------------------------------

def filtrar_periodo(df: pd.DataFrame, años) -> pd.DataFrame:
    """Filtra el DataFrame al período solicitado desde la última fecha."""
    if años is None:
        return df  # Retorna todo el histórico disponible
    fecha_fin = df.index.max()
    fecha_inicio = fecha_fin - timedelta(days=int(años * 365))
    return df[df.index >= fecha_inicio]

# -----------------------------------------------------------------------------
# TABLA 3: PRECIOS BASE 100
# -----------------------------------------------------------------------------

def precios_base100(df_precios: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza precios a base 100 desde la primera fecha disponible.
    Fórmula: precio_t / precio_0 × 100
    """
    return (df_precios / df_precios.iloc[0]) * 100


# -----------------------------------------------------------------------------
# TABLA 1: RETORNO NOMINAL
# -----------------------------------------------------------------------------

def retorno_nominal(df_precios: pd.DataFrame, periodos: dict) -> pd.DataFrame:
    """
    Calcula retorno nominal para cada período.
    Fórmula: (precio_final / precio_inicial) - 1

    Parámetros:
        df_precios: DataFrame de precios
        periodos  : dict {nombre: años} ej: {'1 año': 1.0, '2 años': 2.0}

    Retorna:
        DataFrame con períodos como índice y activos como columnas
    """
    resultados = {}
    fecha_fin = df_precios.index.max()

    for nombre, años in periodos.items():
        df_periodo = filtrar_periodo(df_precios, años)
        if len(df_periodo) < 2:
            continue
        precio_inicio = df_periodo.iloc[0]
        precio_fin = df_periodo.iloc[-1]
        resultados[nombre] = (precio_fin / precio_inicio) - 1

    return pd.DataFrame(resultados).T


# -----------------------------------------------------------------------------
# TABLA 2: RETORNO EFECTIVO ANUAL (EA)
# -----------------------------------------------------------------------------

def retorno_ea(df_nominal: pd.DataFrame, periodos: dict, dias_anio: int = DIAS_ANIO_DEFAULT) -> pd.DataFrame:
    """
    Convierte retorno nominal a efectivo anual.
    Fórmula: (1 + nominal)^(días_año / días_período) - 1
    """
    resultados = {}

    for nombre, años in periodos.items():
        if nombre not in df_nominal.index:
            continue
        nominal = df_nominal.loc[nombre]
        dias_periodo = int(años * dias_anio)
        ea = (1 + nominal) ** (dias_anio / dias_periodo) - 1
        resultados[nombre] = ea

    return pd.DataFrame(resultados).T


# -----------------------------------------------------------------------------
# TABLA 3: VOLATILIDAD DIARIA
# -----------------------------------------------------------------------------

def volatilidad_diaria(df_rendimientos: pd.DataFrame, periodos: dict) -> pd.DataFrame:
    """
    Calcula desviación estándar de rendimientos diarios por período.
    Excluye la columna PORTAFOLIO si existe.
    """
    resultados = {}
    cols = [c for c in df_rendimientos.columns if c != 'PORTAFOLIO']

    for nombre, años in periodos.items():
        df_periodo = filtrar_periodo(df_rendimientos[cols], años)
        if len(df_periodo) < 2:
            continue
        resultados[nombre] = df_periodo.std()

    return pd.DataFrame(resultados).T


# -----------------------------------------------------------------------------
# TABLA 4: VOLATILIDAD ANUAL
# -----------------------------------------------------------------------------

def volatilidad_anual(df_vol_diaria: pd.DataFrame, dias_anio: int = DIAS_ANIO_DEFAULT) -> pd.DataFrame:
    """
    Anualiza la volatilidad diaria.
    Fórmula: vol_diaria × √días_año
    """
    return df_vol_diaria * np.sqrt(dias_anio)


# -----------------------------------------------------------------------------
# TABLA 5: SHARPE RATIO
# -----------------------------------------------------------------------------

def sharpe_ratio(df_ea: pd.DataFrame, df_vol_anual: pd.DataFrame, rf: float) -> pd.DataFrame:
    """
    Calcula Sharpe Ratio por período y activo.
    Fórmula: (retorno_EA - RF) / volatilidad_anual

    Parámetros:
        rf: tasa libre de riesgo en decimal (ej: 0.045 para 4.5%)
    """
    return (df_ea - rf) / df_vol_anual


# -----------------------------------------------------------------------------
# TABLA 6: ANÁLISIS DE PERCENTILES
# -----------------------------------------------------------------------------

def analisis_percentiles(df_rendimientos: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula percentiles 0-100 cada 10% sobre rendimientos diarios.
    """
    cols = [c for c in df_rendimientos.columns if c != 'PORTAFOLIO']
    percentiles = [p/100 for p in PERCENTILES_ANALISIS]

    resultado = df_rendimientos[cols].quantile(percentiles)
    resultado.index = [f"{int(p*100)}%" for p in percentiles]
    return resultado


# -----------------------------------------------------------------------------
# TABLA 7: RANGO PERCENTIL ACTUAL
# -----------------------------------------------------------------------------

def rango_percentil_actual(df_rendimientos: pd.DataFrame) -> pd.Series:
    """
    Calcula en qué percentil se encuentra el último rendimiento
    de cada activo respecto a toda su historia.
    """
    cols = [c for c in df_rendimientos.columns if c != 'PORTAFOLIO']
    ultimo_rendimiento = df_rendimientos[cols].iloc[-1]

    resultado = {}
    for col in cols:
        serie = df_rendimientos[col].dropna()
        percentil = (serie < ultimo_rendimiento[col]).mean()
        resultado[col] = percentil

    return pd.Series(resultado, name='Rango Percentil Actual')


# -----------------------------------------------------------------------------
# TABLA 8: CORRELACIÓN
# -----------------------------------------------------------------------------

def matriz_correlacion(df_rendimientos: pd.DataFrame) -> pd.DataFrame:
    """Matriz de correlación de rendimientos diarios."""
    cols = [c for c in df_rendimientos.columns if c != 'PORTAFOLIO']
    return df_rendimientos[cols].corr()


# -----------------------------------------------------------------------------
# TABLA 9: COVARIANZA DIARIA
# -----------------------------------------------------------------------------

def covarianza_diaria(df_rendimientos: pd.DataFrame) -> pd.DataFrame:
    """Matriz de covarianza de rendimientos diarios."""
    cols = [c for c in df_rendimientos.columns if c != 'PORTAFOLIO']
    return df_rendimientos[cols].cov()


# -----------------------------------------------------------------------------
# TABLA 10: COVARIANZA ANUAL
# -----------------------------------------------------------------------------

def covarianza_anual(df_cov_diaria: pd.DataFrame, dias_anio: int = DIAS_ANIO_DEFAULT) -> pd.DataFrame:
    """
    Anualiza la matriz de covarianza.
    Fórmula: covarianza_diaria × días_año
    """
    return df_cov_diaria * dias_anio


# -----------------------------------------------------------------------------
# TABLA 11: MUESTRA MONTECARLO (1 iteración)
# -----------------------------------------------------------------------------

def montecarlo_muestra(df_rendimientos: pd.DataFrame, dias_anio: int = DIAS_ANIO_DEFAULT) -> pd.Series:
    """
    Selecciona un número aleatorio entre 1 y (n_fechas - días_año).
    Toma 365 días consecutivos desde esa fecha.
    Retorna el promedio de rendimientos de esos 365 días por activo.
    """
    cols = [c for c in df_rendimientos.columns if c != 'PORTAFOLIO']
    n = len(df_rendimientos)

    if n <= dias_anio:
        return df_rendimientos[cols].mean()

    idx_random = np.random.randint(0, n - dias_anio)
    muestra = df_rendimientos[cols].iloc[idx_random: idx_random + dias_anio]
    return muestra.mean()


# -----------------------------------------------------------------------------
# TABLA 12: MONTECARLO 1000 ITERACIONES
# -----------------------------------------------------------------------------

def montecarlo_iteraciones(
    df_rendimientos: pd.DataFrame,
    n_iter: int = MONTECARLO_ITERACIONES,
    percentil: int = MONTECARLO_PERCENTIL,
    dias_anio: int = DIAS_ANIO_DEFAULT
) -> pd.Series:
    """
    Itera 1000 veces montecarlo_muestra y retorna el percentil 50
    de los resultados como retorno representativo por activo.

    Vectorizado con numpy para máxima velocidad.
    """
    cols = [c for c in df_rendimientos.columns if c != 'PORTAFOLIO']
    n = len(df_rendimientos)
    arr = df_rendimientos[cols].values

    if n <= dias_anio:
        return pd.Series(arr.mean(axis=0), index=cols)

    # Generar todos los índices aleatorios de una vez (vectorizado)
    indices = np.random.randint(0, n - dias_anio, size=n_iter)

    # Calcular promedios para cada iteración
    promedios = np.array([
        arr[idx: idx + dias_anio].mean(axis=0)
        for idx in indices
    ])

    # Retornar percentil 50
    resultado = np.percentile(promedios, percentil, axis=0)
    return pd.Series(resultado, index=cols)


# -----------------------------------------------------------------------------
# TABLA 13: MÉTRICAS POR ACTIVO Y MÉTODO
# -----------------------------------------------------------------------------

def tabla_activos(
    df_rendimientos: pd.DataFrame,
    df_cov_anual: pd.DataFrame,
    pesos: dict,
    rf: float,
    benchmark: str,
    retornos_montecarlo: pd.Series,
    dias_anio: int = DIAS_ANIO_DEFAULT
) -> dict:
    """
    Calcula la tabla 13 para los tres métodos: Markowitz, CAPM, Montecarlo.

    Retorna dict con tres DataFrames, uno por método.
    Filas: métricas · Columnas: activos (sin benchmark)
    """
    cols_activos = [c for c in df_rendimientos.columns
                    if c != 'PORTAFOLIO' and c != benchmark]

    # Pesos como Series alineada
    pesos_serie = pd.Series(pesos).reindex(cols_activos).fillna(1/len(cols_activos))

    # Volatilidad anual por activo (período completo)
    vol_diaria = df_rendimientos[cols_activos].std()
    vol_anual_serie = vol_diaria * np.sqrt(dias_anio)

    # Beta: pendiente de regresión rendimiento_activo ~ rendimiento_benchmark
    rend_bench = df_rendimientos[benchmark]
    betas = {}
    for col in cols_activos:
        rend_activo = df_rendimientos[col]
        datos_validos = pd.concat([rend_activo, rend_bench], axis=1).dropna()
        if len(datos_validos) > 1:
            covarianza = datos_validos.cov().iloc[0, 1]
            varianza_bench = datos_validos.iloc[:, 1].var()
            betas[col] = covarianza / varianza_bench if varianza_bench != 0 else 0
        else:
            betas[col] = 0
    beta_serie = pd.Series(betas)

    # RM: promedio de rendimientos del benchmark anualizado
    rm_diario = df_rendimientos[benchmark].mean()
    rm_anual = (1 + rm_diario) ** dias_anio - 1

    # Varianza/Volatilidad del portafolio por activo:
    # w_i × Σ_j(w_j × cov_anual_ij)
    cov_activos = df_cov_anual.loc[cols_activos, cols_activos]
    var_port_por_activo = pesos_serie * cov_activos.dot(pesos_serie)

    resultados = {}

    for metodo in ['markowitz', 'capm', 'montecarlo']:

        if metodo == 'markowitz':
            # Promedio simple de rendimientos diarios anualizado
            rend_diario = df_rendimientos[cols_activos].mean()
            retornos = (1 + rend_diario) ** dias_anio - 1

        elif metodo == 'capm':
            # RF + Beta × (RM - RF)
            retornos = rf + beta_serie * (rm_anual - rf)

        elif metodo == 'montecarlo':
            # Percentil 50 de Montecarlo anualizado
            rend_mc = retornos_montecarlo.reindex(cols_activos)
            retornos = (1 + rend_mc) ** dias_anio - 1

        sharpe = (retornos - rf) / vol_anual_serie

        df_tabla = pd.DataFrame({
            'Peso (w)':              pesos_serie,
            'Retorno':               retornos,
            'Volatilidad Anual':     vol_anual_serie,
            'Var/Vol Portafolio':    var_port_por_activo,
            'Sharpe Ratio':          sharpe,
            'Beta':                  beta_serie,
        }).T

        resultados[metodo] = df_tabla

    return resultados


# -----------------------------------------------------------------------------
# TABLA 14: MÉTRICAS DEL PORTAFOLIO TOTAL
# -----------------------------------------------------------------------------

def tabla_portafolio(tablas_activos: dict, pesos: dict, cols_activos: list) -> dict:
    """
    Calcula la tabla 14 para cada método.
    Verifica el portafolio con los pesos definidos.

    Retorna dict con DataFrame por método.
    """
    pesos_serie = pd.Series(pesos).reindex(cols_activos).fillna(0)
    suma_pesos = pesos_serie.sum()

    resultados = {}

    for metodo, df_tabla in tablas_activos.items():
        retornos = df_tabla.loc['Retorno']
        vol_anual = df_tabla.loc['Volatilidad Anual']
        sharpe = df_tabla.loc['Sharpe Ratio']
        var_vol = df_tabla.loc['Var/Vol Portafolio']

        retorno_port = (pesos_serie * retornos).sum()
        vol_port = np.sqrt(var_vol.sum())
        sharpe_pond = (pesos_serie * sharpe).sum()
        sharpe_calc = retorno_port / vol_port if vol_port != 0 else 0

        df_port = pd.DataFrame({
            'Portafolio': {
                'Suma Pesos (w)':     suma_pesos,
                'Retorno':            retorno_port,
                'Volatilidad':        vol_port,
                'Sharpe Ponderado':   sharpe_pond,
                'Sharpe Calculado':   sharpe_calc,
            }
        })

        resultados[metodo] = df_port

    return resultados
