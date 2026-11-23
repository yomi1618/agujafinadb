# Aguja Fina: sistema de gestión

Aguja Fina reemplaza los cuadernos de una sastrería de arreglos de ropa por una base de datos
relacional y una API. Registra clientes, pedidos con varias prendas, precios negociados dentro de un
rango, adelantos, entregas parciales y deudas, y calcula al instante cuánto debe cada cliente.

Todo corre en un solo computador: MySQL 8.0.33 en Docker y una API en Flask.

**Autores:** Hilary Chaglla y Yomi Caizaluisa.

## Contenido del repositorio

```
agujafinadb/
├── README.md
├── requirements.txt          dependencias de Python
├── .gitignore
├── INIT/
│   ├── logical_model.sql     crea la base afdb: 9 tablas, índices, FK, CHECK y 2 vistas
│   ├── catalog.sql           catálogo: 3 prendas, 6 servicios, 26 precios
│   └── seed.sql              datos de prueba: 7 clientes, 6 pedidos, entregas y pagos
└── API/
    ├── app.py                la API (Flask + SQLAlchemy + Marshmallow)
    ├── .env.example          plantilla de configuración (copiar como .env)
    ├── test_curls.txt        66 pruebas con curl (bash)
    ├── correr_test_curls.py  ejecuta test_curls.txt sin bash, desde el cmd de Windows
    └── pruebas/
        ├── probar_api.py     prueba automática del flujo completo (48 casos)
        ├── api.http          pruebas manuales desde VS Code (extensión REST Client)
        ├── demo.sh           demostración guiada, paso a paso
        ├── reiniciar_base.bat  recarga la base desde cero (Windows)
        └── json/             cuerpos JSON para probar con curl -d @archivo
```

## Cómo funciona el negocio

1. **Recepción.** El cajero busca o registra al cliente. Si tiene deuda, la API lo indica con
   `alerta_deuda`, pero no bloquea el pedido. Cada línea del pedido se elige en cascada:
   **Prenda → Servicio → Descripción**, y esa combinación trae el precio mínimo y máximo. El precio
   acordado debe quedar dentro del rango. El pedido admite un descuento de 0 % o entre 5 % y 10 %,
   y adelantos.
2. **Entrega.** El cliente puede llevarse todas las prendas o solo algunas. Si se lleva prendas que no
   pagó, la entrega exige un motivo de deuda.

## Instalación

### 1. MySQL en Docker

Si todavía no tienes un contenedor de MySQL, créalo así. El puerto queda publicado solo en este
computador (`127.0.0.1`):

```
docker run --name afdb-mysql -e MYSQL_ROOT_PASSWORD=tu_clave_root -p 127.0.0.1:3306:3306 -d mysql:8.0.33
```

Si ya tienes uno, usa su nombre y su puerto (columna PORTS de `docker ps`) en los pasos siguientes.

### 2. Cargar la base

Desde la carpeta raíz del repositorio, ejecuta los scripts **en este orden**: `seed.sql` necesita el
catálogo.

```
docker exec -i afdb-mysql mysql -u root -ptu_clave_root < INIT/logical_model.sql
docker exec -i afdb-mysql mysql -u root -ptu_clave_root < INIT/catalog.sql
docker exec -i afdb-mysql mysql -u root -ptu_clave_root < INIT/seed.sql
```

En el cmd de Windows usa `INIT\` en lugar de `INIT/`. `logical_model.sql` empieza con
`DROP DATABASE afdb`: cada vez que lo ejecutas, la base vuelve a su estado inicial. En Windows también
puedes recargarla con `API\pruebas\reiniciar_base.bat` (ajusta el contenedor y la clave al inicio del
archivo).

Comprobación: solo Carlos Andrés debe tener deuda, de 20.00.

```
docker exec afdb-mysql mysql -u root -ptu_clave_root afdb -e "SELECT nombre, saldo_pendiente FROM v_cliente_deuda;"
```

### 3. Usuario para la API

La API no usa root, sino un usuario con permisos solo sobre `afdb`:

```
docker exec -i afdb-mysql mysql -u root -ptu_clave_root -e "CREATE USER 'af_user'@'%' IDENTIFIED BY 'tu_clave_api'; GRANT ALL PRIVILEGES ON afdb.* TO 'af_user'@'%';"
```

### 4. Entorno de Python

Con conda:

```
conda create -n apidb python=3.11
conda activate apidb
pip install -r requirements.txt
```

En Ubuntu o WSL, usa un entorno virtual (Ubuntu 24 no permite `pip install` en el sistema):

```bash
python3 -m venv ~/venv-afdb
source ~/venv-afdb/bin/activate
pip install -r requirements.txt
```

### 5. Configuración

Copia la plantilla y escribe tus valores:

```
copy API\.env.example API\.env
```

```
DB_USER=af_user
DB_PASSWORD=tu_clave_api
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=afdb
PORT=5000
```

El archivo `.env` está en `.gitignore`: las credenciales nunca se suben al repositorio.

### 6. Encender la API

```
cd API
python app.py
```

La API queda en `http://localhost:5000`. Para comprobarla: `curl http://localhost:5000/prendas`.

## Pruebas

Hay cuatro formas de probar la API. En todas conviene recargar la base antes (paso 2).

| Forma | Comando | Dónde |
| --- | --- | --- |
| Las 66 pruebas de `test_curls.txt` | `bash test_curls.txt` | Ubuntu, WSL o Git Bash, desde `API` |
| Las mismas, sin bash | `python correr_test_curls.py` | cmd de Windows, desde `API` |
| Flujo completo con verificación automática | `python pruebas/probar_api.py` | Cualquier terminal, desde `API` |
| Pruebas manuales con botón «Send Request» | Abrir `pruebas/api.http` | VS Code con la extensión REST Client |
| Demostración guiada, un paso por Enter | `bash pruebas/demo.sh` | Ubuntu, WSL o Git Bash, desde `API` |

Resultado esperado de `test_curls.txt` con la base recién cargada: 45 respuestas 200, 3 con 201,
5 con 400, 8 con 404 y 5 con 409. `probar_api.py` debe terminar con «48 de 48 pruebas pasaron», y
`demo.sh` con «19 de 19 pasos dieron el código esperado».

## Modelo de datos

La base `afdb` tiene 9 tablas en tercera forma normal, en tres grupos:

| Grupo | Tabla | Qué guarda |
| --- | --- | --- |
| Catálogo | `prenda` | Tipos de prenda |
| | `servicio` | Tipos de trabajo |
| | `precio_servicio` | Prenda + servicio + descripción, con precio mínimo y máximo |
| Operación | `cliente` | Persona o empresa |
| | `pedido` | Cabecera: cliente, fecha de recepción, descuento |
| | `detalle_pedido` | Cada prenda del pedido: precio acordado, fecha estimada, repuesto, notas |
| Salida | `entrega` | Cada retiro de prendas, con el motivo si queda deuda |
| | `detalle_entrega` | Qué prendas salieron en cada entrega |
| | `pago` | Adelantos y pagos finales |

Ninguna tabla guarda totales, saldos ni estados: los calculan dos vistas.

- **`v_pedido_resumen`**: por pedido, subtotal, descuento, total, pagado, estado (`activo` o
  `entregado`), saldo pendiente y deuda exigible.
- **`v_cliente_deuda`**: por cliente, la suma de su deuda exigible.

La **deuda exigible** es el valor de las prendas ya entregadas menos lo pagado. Una prenda que sigue en
el taller es saldo pendiente, pero no deuda.

**Reglas que garantiza la base:**
- 13 restricciones CHECK: tipos permitidos, descuento de 0 o entre 5 y 10, cédula de 10 dígitos y RUC
  de 13, montos positivos, ciudad obligatoria si hay dirección, entre otras.
- 7 índices UNIQUE, por ejemplo un solo cliente por tipo y teléfono.
- Llaves foráneas con `ON DELETE RESTRICT`: no se puede borrar un registro que tiene hijos.
- `detalle_entrega` usa dos llaves foráneas compuestas, `(id_entrega, id_pedido)` y
  `(id_detalle, id_pedido)`, para que una entrega solo pueda incluir prendas de su propio pedido. Su
  llave primaria, `id_detalle`, impide entregar dos veces la misma prenda.

**Reglas que garantiza la API**, porque cruzan tablas: el precio acordado dentro del rango, la fecha
estimada no anterior a la recepción, al menos una línea por pedido, la suma de pagos no mayor al total y
el motivo obligatorio cuando una entrega deja deuda.

## Endpoints

Cada recurso tiene CRUD: `GET /recurso` (acepta filtros por columna, por ejemplo
`/clientes?ciudad=Ibarra`), `GET /recurso/<id>`, `POST /recurso`, `PUT /recurso/<id>` y
`DELETE /recurso/<id>`.

| Recurso | Observación |
| --- | --- |
| `/prendas`, `/servicios`, `/precios-servicio`, `/clientes` | CRUD completo |
| `/pedidos` | Se crea con `POST /pedidos`, junto con sus líneas |
| `/detalles-pedido` | Valida rango y fecha; no deja borrar la última línea |
| `/entregas`, `/detalles-entrega` | Se crean con `POST /pedidos/<id>/entregas` |
| `/pagos` | Valida que la suma de pagos no supere el total |

| Ruta especial | Qué hace |
| --- | --- |
| `POST /pedidos` | Crea el pedido y sus líneas en una sola transacción |
| `POST /pedidos/<id>/entregas` | Entrega total o parcial; acepta `pago` y exige `motivo_deuda` si queda deuda |
| `GET /pedidos/<id>/resumen` | Totales, estado y saldos del pedido |
| `GET /pedidos/<id>/lineas` | Líneas con prenda, servicio, rango y si ya se entregaron |
| `GET /clientes/buscar?q=` | Busca por nombre, apellido o teléfono; incluye `alerta_deuda` |
| `GET /clientes/<id>/deuda` | Deuda exigible del cliente |
| `GET /clientes/con-deuda` | Reporte de clientes con deuda |
| `GET /clientes/<id>/pedidos?estado=` | Pedidos del cliente, `activo` o `entregado` |
| `GET /prendas/<id>/servicios` | Cascada, nivel 2 |
| `GET /prendas/<p>/servicios/<s>/descripciones` | Cascada, nivel 3, con `id_precio` y rango |

Ejemplo de creación de un pedido:

```json
POST /pedidos
{
  "id_cliente": 5,
  "descuento_porcentaje": 5,
  "detalles": [
    {"id_precio": 1, "precio_acordado": 6, "fecha_entrega_estimada": "2026-12-01"},
    {"id_precio": 9, "precio_acordado": 7, "fecha_entrega_estimada": "2026-12-03", "usa_repuesto": true}
  ]
}
```

### Códigos de respuesta

| Código | Significado |
| --- | --- |
| 200 / 201 | Operación correcta / registro creado |
| 400 | Datos inválidos (Marshmallow) o una regla de la API incumplida |
| 404 | El registro no existe |
| 409 | MySQL rechazó la operación: CHECK (3819), duplicado (1062) o llave foránea (1451, 1452) |
| 500 | Otro error de base de datos, por ejemplo sin conexión |

## Respaldo y restauración

```
docker exec -e MYSQL_PWD=tu_clave_root afdb-mysql mysqldump -u root --single-transaction --databases afdb > respaldo.sql
docker exec -i -e MYSQL_PWD=tu_clave_root afdb-mysql mysql -u root < respaldo.sql
```

`--single-transaction` toma una copia consistente sin bloquear las tablas, y `--databases` incluye la
creación de la base, así que la restauración funciona aunque `afdb` se haya borrado.

## Limitaciones conocidas

- `PUT /pedidos/<id>` permite subir el descuento después de los pagos, y el saldo puede quedar negativo.
- `DELETE /pagos/<id>` permite borrar pagos de un pedido ya entregado, lo que crea deuda sin motivo.
- `PUT /detalles-pedido/<id>` permite cambiar el precio de una línea ya entregada.
- Varias líneas de `seed.sql` tienen precios fuera del rango del catálogo: se cargan directo en MySQL,
  sin pasar por la validación de la API.
- La búsqueda usa `LIKE '%texto%'`, que no aprovecha índices; es suficiente para el volumen de una
  sastrería.
- Todavía no hay interfaz gráfica: la API se usa con curl, REST Client o los scripts de prueba.
