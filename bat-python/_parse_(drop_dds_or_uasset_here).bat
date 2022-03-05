@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
python src\main.py "%~1"
@popd

pause

:skip