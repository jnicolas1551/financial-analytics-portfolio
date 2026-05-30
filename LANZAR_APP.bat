@echo off
cd /d "D:\Datos Usuario\Documents\PROYECTOS_CLAUDE\ANALISIS_INSTITUCIONAL"
echo.
echo  Iniciando Dashboard de Analisis Fundamental...
echo  Abre tu navegador en: http://localhost:8501
echo.
python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
pause
