$Python = "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

Set-Location $PSScriptRoot

& $Python -m uvicorn app.api:app --reload --reload-dir $PSScriptRoot --host 127.0.0.1 --port 8000
