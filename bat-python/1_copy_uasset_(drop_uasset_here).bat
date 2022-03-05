@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
python src\main.py "%~1" --mode=copy_uasset
@popd

pause

:skip