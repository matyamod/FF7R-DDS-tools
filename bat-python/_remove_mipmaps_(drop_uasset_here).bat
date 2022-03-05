@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
python src\main.py "%~1" --save_folder=removed --mode=remove_mipmaps
@popd

pause

:skip