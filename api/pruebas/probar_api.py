"""Prueba automática de la API de Aguja Fina (repositorio agujafinadb).

Requisitos: la API encendida (python app.py) y la base afdb cargada con
logical_model.sql y catalog.sql. No depende de los ids del seed: crea sus propios
clientes y pedidos y toma los ids de las respuestas.

Uso, desde la carpeta API:
    python pruebas\\probar_api.py
    python pruebas\\probar_api.py http://localhost:5000
"""
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

import requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000").rstrip("/")
FUTURO = (date.today() + timedelta(days=7)).isoformat()
resultados = []


def tel():
    return "09" + "".join(random.choices("0123456789", k=8))


def probar(codigo, descripcion, metodo, ruta, esperado, json=None, verificar=None):
    """Hace una petición, compara el código HTTP y, opcionalmente, el contenido."""
    try:
        r = requests.request(metodo, BASE + ruta, json=json, timeout=10)
    except requests.ConnectionError:
        print(f"\nNo hay conexión con {BASE}. ¿Está encendida la API (python app.py)?")
        sys.exit(1)
    try:
        cuerpo = r.json()
    except ValueError:
        cuerpo = r.text
    ok = r.status_code == esperado
    nota = ""
    if ok and verificar:
        try:
            nota = verificar(cuerpo) or ""
        except AssertionError as e:
            ok, nota = False, str(e)
    estado = "OK   " if ok else "FALLA"
    print(f"[{estado}] {codigo:<6} {descripcion}")
    print(f"         {metodo} {ruta} -> {r.status_code} (esperado {esperado}) {nota}")
    if not ok:
        print(f"         respuesta: {str(cuerpo)[:300]}")
    resultados.append(ok)
    return cuerpo


def exigir(condicion, mensaje):
    """Falla la verificación con un mensaje si la condición no se cumple."""
    if not condicion:
        raise AssertionError(mensaje)


def igual(valor, esperado, nombre):
    assert Decimal(str(valor)) == Decimal(esperado), f"{nombre} = {valor}, se esperaba {esperado}"


def seccion(titulo):
    print(f"\n=== {titulo} ===")


print(f"Probando la API en {BASE}")

# ------------------------------------------------------------------
seccion("Catálogo y cascada (FR-05, FR-16)")
prendas = probar("TC-10", "Listar prendas (nivel 1 de la cascada)", "GET", "/prendas", 200)
probar("404", "Prenda inexistente", "GET", "/prendas/999999", 404)
pantalon = next(p for p in prendas if p["tipo_prenda"].startswith("Pantal"))
servicios = probar("TC-10", "Servicios del pantalón (nivel 2)", "GET",
                   f"/prendas/{pantalon['id_prenda']}/servicios", 200)
bastas = next(s for s in servicios if "bastas" in s["nombre_servicio"].lower())
cambio = next(s for s in servicios if s["nombre_servicio"] == "Cambio")
desc = probar("TC-10", "Descripciones con mínimo y máximo (nivel 3)", "GET",
              f"/prendas/{pantalon['id_prenda']}/servicios/{bastas['id_servicio']}/descripciones", 200,
              verificar=lambda b: f"({len(b)} descripciones)")
p_basta = next(d for d in desc if d["descripcion_arreglo"] == "20-24")      # rango 5.00 a 7.00
p_cierre = next(d for d in probar("TC-10", "Descripciones de Cambio", "GET",
                f"/prendas/{pantalon['id_prenda']}/servicios/{cambio['id_servicio']}/descripciones", 200)
                if d["descripcion_arreglo"] == "Cierre")                    # rango 6.00 a 8.00
probar("TC-25", "Prenda duplicada", "POST", "/prendas", 409, json={"tipo_prenda": pantalon["tipo_prenda"]})

# ------------------------------------------------------------------
seccion("Clientes (FR-01, FR-02)")
t1 = tel()
cli = probar("TC-01", "Registrar persona con apellido", "POST", "/clientes", 201,
             json={"tipo_cliente": "persona", "nombre": "Prueba", "apellido": "API", "telefono": t1})
probar("TC-01b", "Persona sin apellido (regla del repositorio)", "POST", "/clientes", 409,
       json={"tipo_cliente": "persona", "nombre": "Sin Apellido", "telefono": tel()})
probar("TC-02", "Cliente sin teléfono", "POST", "/clientes", 400,
       json={"tipo_cliente": "persona", "nombre": "X", "apellido": "Y"})
probar("TC-02b", "Nombre hecho solo de espacios", "POST", "/clientes", 400,
       json={"tipo_cliente": "persona", "nombre": "   ", "apellido": "Y", "telefono": tel()})
probar("TC-02c", "Tipo de cliente no permitido", "POST", "/clientes", 400,
       json={"tipo_cliente": "otro", "nombre": "X", "telefono": tel()})
probar("TC-03", "Otra persona con el mismo teléfono", "POST", "/clientes", 409,
       json={"tipo_cliente": "persona", "nombre": "Otra", "apellido": "Z", "telefono": t1})
probar("TC-04", "Empresa con el mismo teléfono", "POST", "/clientes", 201,
       json={"tipo_cliente": "empresa", "nombre": "Empresa Prueba", "telefono": t1})
probar("TC-05", "Número de identificación sin tipo", "POST", "/clientes", 409,
       json={"tipo_cliente": "persona", "nombre": "X", "apellido": "Y", "telefono": tel(),
             "numero_identificacion": "1234567890"})
probar("TC-05b", "Empresa con cédula", "POST", "/clientes", 409,
       json={"tipo_cliente": "empresa", "nombre": "E", "telefono": tel(),
             "tipo_identificacion": "cedula", "numero_identificacion": "1234567890"})
probar("TC-05c", "Dirección sin ciudad", "POST", "/clientes", 409,
       json={"tipo_cliente": "persona", "nombre": "X", "apellido": "Y", "telefono": tel(),
             "direccion": "Calle 1"})
probar("TC-06", "Buscar por teléfono lista persona y empresa", "GET", f"/clientes/buscar?q={t1}", 200,
       verificar=lambda b: exigir(len(b) == 2, f"{len(b)} resultados") or "(2 resultados)")

id_cli = cli["id_cliente"]

# ------------------------------------------------------------------
seccion("Pedidos (FR-04, FR-07, FR-08, FR-09)")


def pedido(**extra):
    datos = {"id_cliente": id_cli, "descuento_porcentaje": 5, "detalles": [
        {"id_precio": p_basta["id_precio"], "precio_acordado": 6, "fecha_entrega_estimada": FUTURO,
         "notas": "azul"},
        {"id_precio": p_cierre["id_precio"], "precio_acordado": 7, "fecha_entrega_estimada": FUTURO,
         "usa_repuesto": True}]}
    datos.update(extra)
    return datos


probar("TC-04b", "Pedido sin líneas", "POST", "/pedidos", 400, json=pedido(detalles=[]))
probar("TC-09", "Pedido de un cliente inexistente", "POST", "/pedidos", 409, json=pedido(id_cliente=999999))
malo = pedido()
malo["detalles"][0]["precio_acordado"] = 50
probar("TC-14", "Precio acordado fuera de rango", "POST", "/pedidos", 400, json=malo)
malo = pedido()
malo["detalles"][0]["fecha_entrega_estimada"] = "2020-01-01"
probar("TC-13", "Fecha estimada anterior a la recepción", "POST", "/pedidos", 400, json=malo)
probar("TC-16", "Descuento de 3 %", "POST", "/pedidos", 409, json=pedido(descuento_porcentaje=3))
probar("TC-16b", "Descuento de 12 %", "POST", "/pedidos", 409, json=pedido(descuento_porcentaje=12))
creado = probar("TC-08", "Pedido válido con 2 líneas y 5 % de descuento", "POST", "/pedidos", 201,
                json=pedido(), verificar=lambda b: f"(pedido {b['pedido']['id_pedido']})")
id_ped = creado["pedido"]["id_pedido"]
linea_basta, linea_cierre = (d["id_detalle"] for d in creado["detalles"])


def resumen_inicial(b):
    igual(b["subtotal"], "13.00", "subtotal")
    igual(b["descuento_monto"], "0.65", "descuento")
    igual(b["total_neto"], "12.35", "total")
    assert b["estado"] == "activo", f"estado = {b['estado']}"
    return "(subtotal 13.00, descuento 0.65, total 12.35)"


probar("TC-20", "Resumen del pedido", "GET", f"/pedidos/{id_ped}/resumen", 200, verificar=resumen_inicial)
probar("TC-11", "Líneas con notas y repuesto", "GET", f"/pedidos/{id_ped}/lineas", 200,
       verificar=lambda b: exigir(b[1]["usa_repuesto"] is True and b[0]["notas"] == "azul",
                              "notas o repuesto no guardados") or "(notas y repuesto guardados)")

# ------------------------------------------------------------------
seccion("Pagos (FR-10)")
probar("TC-18", "Adelanto de 5.00", "POST", "/pagos", 201,
       json={"id_pedido": id_ped, "monto": 5, "tipo_pago": "adelanto", "metodo_pago": "efectivo"})
probar("TC-19", "Pago que supera el total", "POST", "/pagos", 400,
       json={"id_pedido": id_ped, "monto": 50, "tipo_pago": "adelanto", "metodo_pago": "efectivo"})
probar("TC-19b", "Método de pago no permitido", "POST", "/pagos", 400,
       json={"id_pedido": id_ped, "monto": 1, "tipo_pago": "adelanto", "metodo_pago": "tarjeta"})
probar("TC-07", "Pedido activo sin entregar: todavía no es deuda", "GET", f"/clientes/{id_cli}/deuda", 200,
       verificar=lambda b: igual(b["saldo_pendiente"], "0.00", "deuda") or "(deuda 0.00)")

# ------------------------------------------------------------------
seccion("Entregas (FR-13, FR-14)")
probar("TC-23", "Entrega con deuda y sin motivo", "POST", f"/pedidos/{id_ped}/entregas", 400,
       json={"lineas": [linea_cierre]})
probar("TC-24", "Entrega parcial con motivo", "POST", f"/pedidos/{id_ped}/entregas", 201,
       json={"lineas": [linea_cierre], "motivo_deuda": "Paga el lunes"})
probar("TC-07b", "Deuda exigible tras la entrega parcial", "GET", f"/clientes/{id_cli}/deuda", 200,
       verificar=lambda b: igual(b["saldo_pendiente"], "1.65", "deuda") or "(deuda 1.65)")
probar("TC-03b", "Buscar al cliente muestra la alerta", "GET", f"/clientes/buscar?q={t1}", 200,
       verificar=lambda b: exigir(any(c["alerta_deuda"] for c in b), "sin alerta") or "(alerta_deuda true)")
probar("NFR-04", "Entregar dos veces la misma línea", "POST", f"/pedidos/{id_ped}/entregas", 409,
       json={"lineas": [linea_cierre], "motivo_deuda": "x"})
otro = probar("TC-08b", "Segundo pedido del mismo cliente", "POST", "/pedidos", 201, json=pedido())
probar("NFR-04b", "Entregar una línea de otro pedido", "POST", f"/pedidos/{id_ped}/entregas", 409,
       json={"lineas": [otro["detalles"][0]["id_detalle"]], "motivo_deuda": "x"})
probar("TC-21", "Pedidos activos del cliente", "GET", f"/clientes/{id_cli}/pedidos?estado=activo", 200,
       verificar=lambda b: f"({len(b)} activos)")

# ------------------------------------------------------------------
seccion("Cobrar la deuda y cerrar (FR-13, FR-19)")
probar("TC-22", "Pago final de 7.35", "POST", "/pagos", 201,
       json={"id_pedido": id_ped, "monto": 7.35, "tipo_pago": "saldo_final", "metodo_pago": "efectivo"})
probar("TC-22b", "Entregar la última línea ya pagada (sin motivo)", "POST", f"/pedidos/{id_ped}/entregas", 201,
       json={"lineas": [linea_basta]})
probar("TC-22c", "El pedido queda entregado y sin saldo", "GET", f"/pedidos/{id_ped}/resumen", 200,
       verificar=lambda b: exigir(b["estado"] == "entregado", f"estado = {b['estado']}")
       or igual(b["saldo_total_pendiente"], "0.00", "saldo") or "(entregado, saldo 0.00)")
probar("TC-28", "Reporte de deudores no incluye al cliente", "GET", "/clientes/con-deuda", 200,
       verificar=lambda b: exigir(all(c["id_cliente"] != id_cli for c in b), "sigue en el reporte")
       or "(no aparece)")

# ------------------------------------------------------------------
seccion("Reglas al modificar o borrar (corregidas)")
probar("REG-1", "Subir el descuento de un pedido ya pagado", "PUT", f"/pedidos/{id_ped}", 400,
       json={"descuento_porcentaje": 10})
probar("REG-2", "Modificar una línea ya entregada", "PUT", f"/detalles-pedido/{linea_cierre}", 400,
       json={"notas": "cambio"})
pagos = probar("REG-3", "Pagos del pedido entregado", "GET", f"/pagos?id_pedido={id_ped}", 200)
probar("REG-4", "Borrar un pago de un pedido con entregas", "DELETE", f"/pagos/{pagos[0]['id_pago']}", 400)
probar("REG-5", "Modificar un pago de un pedido con entregas", "PUT", f"/pagos/{pagos[0]['id_pago']}", 400,
       json={"monto": 1})
id_otro = otro["pedido"]["id_pedido"]
probar("REG-6", "Descuento en un pedido sin pagos: sí se permite", "PUT", f"/pedidos/{id_otro}", 200,
       json={"descuento_porcentaje": 10})
probar("REG-7", "Precio de una línea sin entregar, dentro del rango", "PUT",
       f"/detalles-pedido/{otro['detalles'][0]['id_detalle']}", 200, json={"precio_acordado": 5.5})
probar("REG-8", "Ruta inexistente responde JSON", "GET", "/ruta-que-no-existe", 404,
       verificar=lambda b: exigir(isinstance(b, dict) and "error" in b, "no es JSON") or "(JSON)")
probar("GUI", "La GUI se sirve en la raíz", "GET", "/", 200)

# ------------------------------------------------------------------
seccion("Integridad y CRUD (NFR-04, FR-17)")
probar("TC-32", "Borrar un cliente con pedidos", "DELETE", f"/clientes/{id_cli}", 409)
probar("TC-26", "Modificar el email del cliente (PUT parcial)", "PUT", f"/clientes/{id_cli}", 200,
       json={"email": f"prueba{id_cli}@ejemplo.com"})
probar("TC-26b", "Leer el cliente modificado", "GET", f"/clientes/{id_cli}", 200,
       verificar=lambda b: b["email"] and "(email guardado)")
serv = probar("TC-26c", "Crear un servicio", "POST", "/servicios", 201,
              json={"nombre_servicio": f"Servicio prueba {tel()}"})
probar("TC-26d", "Borrar ese servicio", "DELETE", f"/servicios/{serv['id_servicio']}", 200)
probar("TC-26e", "Ya no existe", "GET", f"/servicios/{serv['id_servicio']}", 404)

# ------------------------------------------------------------------
total, bien = len(resultados), sum(resultados)
print(f"\nResultado: {bien} de {total} pruebas pasaron.")
sys.exit(0 if bien == total else 1)
