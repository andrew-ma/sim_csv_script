@echo off
:: Setting Environment Variables
set MY_PYTHON=python
set SKIP_GENERATE_AUTHORS=1
set SKIP_WRITE_GIT_CHANGELOG=1

:: Delete folders
call :delete_folders build dist venv .eggs

:: Create new virtual environment
call :new_venv

:: :: Upgrade Pip version
:: %MY_PYTHON% -m pip install --upgrade pip

:: :: Installing Build Dependencies
:: %MY_PYTHON% -m pip install wheel setuptools

:: :: Installing Dependencies from requirements.txt
:: %MY_PYTHON% -m pip install -r requirements.txt

:: Generate Source Distribution ("".tar.gz")
@echo on
%MY_PYTHON% setup.py sdist
@echo off

:: Delete folders except for dist
call :delete_folders build .eggs

echo Done!

:: Deactivate the venv
deactivate

EXIT /B %ERRORLEVEL%

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:delete_folders
echo Deleting folders: %*
rmdir /s /q %* >nul 2>&1
EXIT /B 0

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:new_venv
echo Creating new venv
%MY_PYTHON% -m venv venv
call venv\Scripts\activate
EXIT /B 0
