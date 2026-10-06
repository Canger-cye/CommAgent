@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [CommAgent] 启动中...
python run.py --llm mock --port 8787
pause
