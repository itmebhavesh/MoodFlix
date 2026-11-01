@echo off
cd /d "%~dp0"
echo === MoodFlix starting ===
if not exist venv (
  echo Creating virtual environment - first time only...
  python -m venv venv || py -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
start "" http://127.0.0.1:5000
python run.py
pause
