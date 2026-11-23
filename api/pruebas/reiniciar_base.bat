@echo off
REM Recarga la base afdb desde cero: esquema, catalogo y datos de prueba.
REM Uso: doble clic, o desde cmd:  API\pruebas\reiniciar_base.bat
REM Ajusta estas dos lineas a tu contenedor:
set CONTENEDOR=mysqlcontainer8
set CLAVE=none

cd /d "%~dp0..\.."
echo Recargando afdb en el contenedor %CONTENEDOR% ...
docker exec -i -e MYSQL_PWD=%CLAVE% %CONTENEDOR% mysql -u root < INIT\logical_model.sql || goto error
docker exec -i -e MYSQL_PWD=%CLAVE% %CONTENEDOR% mysql -u root < INIT\catalog.sql || goto error
docker exec -i -e MYSQL_PWD=%CLAVE% %CONTENEDOR% mysql -u root < INIT\seed.sql || goto error
echo Listo: base afdb recargada (7 clientes, 6 pedidos, 26 precios).
pause
exit /b 0

:error
echo ERROR al recargar. Revisa que Docker este encendido y el nombre y la clave del contenedor.
pause
exit /b 1
