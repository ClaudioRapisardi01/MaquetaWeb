@echo off
echo ================================================
echo  AVVIO WEB APP DISCOGRAFICA
echo ================================================
echo.

echo [1/3] Attivazione virtual environment...
call venv\Scripts\activate.bat

echo.
echo [2/3] Verifica database...
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); print('Database OK!')" 2>nul
if errorlevel 1 (
    echo ATTENZIONE: Database non inizializzato!
    echo Esegui prima: python init_db.py
    pause
    exit /b 1
)

echo.
echo [3/3] Avvio applicazione...
echo.
echo ================================================
echo  APP DISPONIBILE SU: http://localhost:6000
echo ================================================
echo.
echo Premi CTRL+C per fermare il server
echo.

python run.py

pause
