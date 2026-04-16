@echo off
setlocal enabledelayedexpansion

:: ---------------------------------------------------------------------------
:: build_library.bat
:: Compile the mymath library manually with MSVC 2019 (outside of Conan).
:: Run this script BEFORE running "conan export-pkg".
:: ---------------------------------------------------------------------------

set "SCRIPT_DIR=%~dp0"

:: Create lib directory if needed
if not exist "%SCRIPT_DIR%lib" mkdir "%SCRIPT_DIR%lib"

:: Locate Visual Studio 2019 using vswhere (ships with VS installer)
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
    echo ERROR: vswhere.exe not found.
    echo        Please install Visual Studio 2019 ^(any edition^).
    exit /b 1
)

for /f "usebackq tokens=*" %%i in (
    `"%VSWHERE%" -version "[16.0,17.0)" -latest -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`
) do set "VS_PATH=%%i"

if not defined VS_PATH (
    echo ERROR: Visual Studio 2019 with C++ tools not found.
    echo        Make sure "Desktop development with C++" is installed.
    exit /b 1
)

set "VCVARS=%VS_PATH%\VC\Auxiliary\Build\vcvarsall.bat"
if not exist "%VCVARS%" (
    echo ERROR: vcvarsall.bat not found at: %VCVARS%
    exit /b 1
)

echo [mymath] Setting up MSVC 2019 environment ^(x64^)...
call "%VCVARS%" x64
if errorlevel 1 (
    echo ERROR: Failed to initialise MSVC environment.
    exit /b 1
)

echo [mymath] Compiling source...
cl.exe /std:c++17 /O2 /EHsc /nologo ^
    /I "%SCRIPT_DIR%include" ^
    /c "%SCRIPT_DIR%src\mymath.cpp" ^
    /Fo"%SCRIPT_DIR%mymath.obj"
if errorlevel 1 (
    echo ERROR: Compilation failed.
    exit /b 1
)

echo [mymath] Creating static library...
lib.exe /nologo /OUT:"%SCRIPT_DIR%lib\mymath.lib" "%SCRIPT_DIR%mymath.obj"
if errorlevel 1 (
    echo ERROR: lib.exe failed.
    del "%SCRIPT_DIR%mymath.obj" 2>nul
    exit /b 1
)

del "%SCRIPT_DIR%mymath.obj" 2>nul

echo [mymath] Done. Library is at: %SCRIPT_DIR%lib\mymath.lib
