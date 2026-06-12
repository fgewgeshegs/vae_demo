Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\jay_demo\backend"
WshShell.Run "cmd /c D:\jay_demo\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 > startup.log 2>&1", 0, False
