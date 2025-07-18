@echo off

:: Nome: restart_env.bat
:: Função: Reinicializa o ambiente GPT Executor com Docker + ngrok

cd /d %~dp0

:: Parar os containers se estiverem ativos
echo Parando containers existentes...
docker-compose down --volumes --remove-orphans

:: Atualizar imagens (opcional)
echo Verificando por atualizações...
docker builder prune -af

:: Reconstruir e subir ambiente
echo Reconstruindo e iniciando containers...
docker-compose up --build

:: Aguardar e exibir status final
echo Aguarde alguns segundos para estabilização...
timeout /t 5 > nul
echo --- STATUS DO AMBIENTE ---
docker ps

echo Ambiente reiniciado com sucesso.
pause
