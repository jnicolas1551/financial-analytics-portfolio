# Quant Dashboard — Análisis Técnico y Estadístico de Portafolio

Dashboard interactivo en Streamlit para análisis cuantitativo de portafolios con valoración estadística (regresión lineal + percentiles) y análisis técnico (MM, MACD, RSI, Fibonacci).

---

## 📁 Estructura de archivos

Ubicación del proyecto:
```
D:\Datos Usuario\Documents\PROYECTO APRENDIZAJE IA\3. ANALISIS TECNICO ESTADISTICO PORTAFOLIO\
│
├── dashboard_quant.py     ← código principal de la app
├── requirements.txt       ← librerías necesarias
└── README.md              ← este archivo
```

---

## ⚙️ Requisitos

- **Python 3.13 o superior** instalado (con PATH configurado)
- **Git Bash** instalado
- Conexión a internet (para descargar datos de Yahoo Finance)

---

## 🚀 Paso a paso para correr la app

### Primera vez (instalación de librerías)

Abre **CMD** y ejecuta:

```cmd
D:
```

```cmd
cd "Datos Usuario\Documents\PROYECTO APRENDIZAJE IA\3. ANALISIS TECNICO ESTADISTICO PORTAFOLIO"
```

```cmd
python -m pip install -r requirements.txt
```

Espera a que termine la descarga e instalación.

---

### Correr la app (cada vez que la uses)

Abre **Git Bash** (desde cualquier ubicación) y ejecuta estos 2 comandos:

```bash
cd "/d/Datos Usuario/Documents/PROYECTO APRENDIZAJE IA/3. ANALISIS TECNICO ESTADISTICO PORTAFOLIO"
```

```bash
python -m streamlit run dashboard_quant.py
```

La app se abre automáticamente en tu navegador en:
```
http://localhost:8501
```

**Para detener la app:** en Git Bash presiona `Ctrl + C`.

---

> 💡 **Atajo alternativo:** abre directamente la carpeta del proyecto en el explorador de Windows, haz **clic derecho dentro de la carpeta → "Open Git Bash here"**. Esto te abre Git Bash ya posicionado en la ruta y solo tienes que ejecutar:
> ```bash
> python -m streamlit run dashboard_quant.py
> ```

---

## 📊 Funcionalidades

### Entrada de datos
- **Yahoo Finance:** ingresa tickers separados por coma (el último es el benchmark)
- **Excel:** sube un archivo con filas=fechas, columnas=activos, última columna=benchmark

### Configuración
- Selecciona uno o varios períodos: 1 mes, 3 meses, 6 meses, 1 año, 2, 3, 5, 10 años, o máximo
- Ajusta pesos entre bloque técnico y estadístico
- Ajusta pesos dentro del estadístico (regresión vs percentil 50)
- Ajusta pesos dentro del técnico (MM, RSI, MACD, Fibonacci)

### Análisis Estadístico
- Gráfico Base 100
- Matriz de correlaciones vs benchmark
- Alpha, Beta, R², coeficiente de correlación
- Valoración estadística + potencial de valoración
- Desviación estándar, media y CV de últimos 20 días
- Percentiles (0%, 1%, 5%, 15%, 25%, 50%, 75%, 95%, 99%, 100%)
- Precio valorado ponderado

### Análisis Técnico
- **Medias Móviles** (5, 20, 100, 200) con detección de cruces y golden/death cross
- **MACD** (12, 26, 9) con histograma
- **RSI** (14) con zonas de sobrecompra/sobreventa
- **Fibonacci** (retrocesos 23.6%, 38.2%, 50%, 61.8%)
- Tabla consolidada de señales por indicador
- Consenso técnico por votación

### Exportación
- Descarga el análisis completo en Excel con múltiples hojas por período

---

## 🛠 Notas técnicas

- Los datos se cargan al **máximo histórico disponible** y se filtran por período
- La fecha de inicio se **unifica** al primer día en que todos los activos tienen datos (corte automático por el activo con menor histórico)
- Los gaps puntuales se rellenan con forward fill para mercados con festivos diferentes
- El análisis técnico usa el histórico completo para calcular correctamente las medias largas (MM100, MM200)

---

## ⚠️ Solución de problemas comunes

**Error: "python: command not found"**
→ Cierra Git Bash y ábrelo de nuevo. Si persiste, verifica que Python esté en el PATH del sistema.

**Error: "ModuleNotFoundError"**
→ Vuelve a correr `python -m pip install -r requirements.txt` desde CMD.

**Warning: "tickers no devolvieron datos"**
→ Verifica que el ticker exista en Yahoo Finance (yahoo.com/finance). Algunos tickers requieren sufijo (ej: ECOPETROL.CL para BVC).

**La app no abre el navegador:**
→ Abre manualmente `http://localhost:8501`

**El comando `cd` falla en Git Bash:**
→ Recuerda que Git Bash usa formato Linux: `/d/` en lugar de `D:\` y `/` en lugar de `\`.
