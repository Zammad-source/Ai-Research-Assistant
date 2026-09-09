@echo off
set KMP_DUPLICATE_LIB_OK=TRUE
set PYTHONDONTWRITEBYTECODE=1
call venv\Scripts\activate
uvicorn app.main:app --reload --reload-dir app