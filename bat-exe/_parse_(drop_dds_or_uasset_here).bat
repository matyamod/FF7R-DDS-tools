@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
FF7R-DDS-tools.exe "%~1"
@popd

pause

:skip