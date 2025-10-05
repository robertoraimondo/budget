@echo off
REM Production run script for Flask app using Waitress (Windows WSGI server)
REM Ensure you have installed waitress: pip install waitress


set FLASK_ENV=production
set FLASK_APP=app:app

REM Run the app with Waitress on localhost (127.0.0.1) port 8000
waitress-serve --host=127.0.0.1 --port=8000 app:app
