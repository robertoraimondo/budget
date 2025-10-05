@echo off
echo Money Tracker Application
echo ========================
echo.
if exist budget.db (
    echo Database: Found existing database
) else (
    echo Database: Will create new database
)
echo.
echo Starting application...
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
C:/Python313/python.exe app.py