@echo off
setlocal

:: Caminho absoluto do projeto
set TARGET_DIR=C:\gpt-executor

:: Força o script a entrar no diretório do projeto
cd /d "%TARGET_DIR%"

echo [+] Diretório atual: %CD%
echo [+] Aplicando permissões de escrita...

icacls "%TARGET_DIR%\backend" /grant *S-1-1-0:(OI)(CI)F /T
icacls "%TARGET_DIR%\workspace" /grant *S-1-1-0:(OI)(CI)F /T

echo [+] Permissões aplicadas com sucesso.
pause
