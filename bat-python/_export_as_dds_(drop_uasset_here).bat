@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
python src\main.py "%~1" --save_folder=exported --mode=export
@popd

pause

:skip