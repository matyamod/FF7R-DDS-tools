@echo off

@if "%~1"=="" goto skip

@pushd %~dp0
FF7R-DDS-tools.exe "%~1" --save_folder=removed --mode=remove_mipmaps
@popd

pause

:skip