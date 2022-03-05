@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
FF7R-DDS-tools.exe "%~1" --save_folder=exported --mode=export
@popd

pause

:skip