#!/usr/bin/env bash
# =====================================================================
# Aguja Fina - demostración en vivo de la API, paso a paso.
#
# Uso (terminal de Ubuntu o Git Bash, desde la carpeta API):
#     bash pruebas/demo.sh            pausa antes de cada paso (para presentar)
#     bash pruebas/demo.sh --auto     sin pausas (para ensayar)
#     BASE=http://localhost:5001 bash pruebas/demo.sh   si la API usa otro puerto
#
# Requiere la base recién cargada (logical_model.sql, catalog.sql, seed.sql)
# y la API encendida. El pedido de la demo será el 7, con las líneas 15 y 16.
# =====================================================================

BASE=${BASE:-http://localhost:5000}
H='Content-Type: application/json'
AUTO=0; [ "$1" = "--auto" ] && AUTO=1
N=0; BIEN=0

AZUL='\033[1;34m'; VERDE='\033[1;32m'; ROJO='\033[1;31m'; GRIS='\033[0;90m'; FIN='\033[0m'

# paso "título" "qué demuestra" código_esperado MÉTODO RUTA [JSON]
paso() {
  local titulo="$1" explica="$2" esperado="$3" metodo="$4" ruta="$5" cuerpo="$6"
  N=$((N + 1))
  echo
  echo -e "${AZUL}━━━ Paso $N. $titulo ━━━${FIN}"
  echo -e "${GRIS}$explica${FIN}"
  if [ -n "$cuerpo" ]; then
    echo "\$ curl -X $metodo $BASE$ruta -d '$cuerpo'"
  else
    echo "\$ curl -X $metodo $BASE$ruta"
  fi
  [ $AUTO -eq 0 ] && read -r -p "  [Enter] para ejecutar " _
  local salida codigo
  if [ -n "$cuerpo" ]; then
    salida=$(curl -s -w '\n%{http_code}' -X "$metodo" "$BASE$ruta" -H "$H" -d "$cuerpo")
  else
    salida=$(curl -s -w '\n%{http_code}' -X "$metodo" "$BASE$ruta")
  fi
  codigo=$(echo "$salida" | tail -n 1)
  echo "$salida" | sed '$d'
  if [ "$codigo" = "$esperado" ]; then
    BIEN=$((BIEN + 1)); echo -e "${VERDE}  -> HTTP $codigo  (esperado $esperado) ✔${FIN}"
  else
    echo -e "${ROJO}  -> HTTP $codigo  (esperado $esperado) ✘${FIN}"
  fi
}

# --- Comprobaciones previas ---
if [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/prendas")" != "200" ]; then
  echo -e "${ROJO}La API no responde en $BASE. Enciéndela con: python app.py${FIN}"; exit 1
fi
if [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/pedidos/7")" != "404" ]; then
  echo -e "${ROJO}El pedido 7 ya existe: recarga la base (logical_model, catalog, seed) antes de la demo.${FIN}"; exit 1
fi
echo -e "${VERDE}API lista en $BASE y base recién cargada.${FIN}"

# --- 1. Catálogo y cascada ---
paso "Cascada, nivel 1: prendas" \
     "FR-05. El cajero empieza eligiendo la prenda." \
     200 GET "/prendas"
paso "Cascada, nivel 2: servicios del pantalón" \
     "Solo aparecen los servicios que tienen precio para esa prenda en precio_servicio." \
     200 GET "/prendas/1/servicios"
paso "Cascada, nivel 3: descripciones con su rango" \
     "Cada descripción trae su id_precio y su precio mínimo y máximo." \
     200 GET "/prendas/1/servicios/1/descripciones"

# --- 2. Clientes ---
paso "Alerta de deuda al buscar un cliente" \
     "FR-03. Carlos debe 20.00 (deuda exigible) aunque su saldo total es 21.00: una prenda de 1.00 sigue en el taller." \
     200 GET "/clientes/buscar?q=Carlos"
paso "Validación de Marshmallow: tipo de cliente no permitido" \
     "Primera barrera: la API rechaza el formato antes de tocar la base (400)." \
     400 POST "/clientes" '{"tipo_cliente":"otro","nombre":"X","telefono":"0990000099"}'
paso "Regla CHECK de MySQL: persona sin apellido" \
     "Última barrera: lo rechaza MySQL con ck_cliente_apellido_tipo (409)." \
     409 POST "/clientes" '{"tipo_cliente":"persona","nombre":"Sin Apellido","telefono":"0990000098"}'

# --- 3. Pedido ---
paso "Crear un pedido de dos líneas con 5 % de descuento" \
     "FR-04, FR-08, FR-09. Cabecera y líneas en una sola transacción. Será el pedido 7, líneas 15 y 16." \
     201 POST "/pedidos" '{"id_cliente":5,"descuento_porcentaje":5,"detalles":[{"id_precio":1,"precio_acordado":6,"fecha_entrega_estimada":"2026-12-01","notas":"azul"},{"id_precio":9,"precio_acordado":7,"fecha_entrega_estimada":"2026-12-03","usa_repuesto":true}]}'
paso "Precio acordado fuera de rango" \
     "FR-08. El rango vive en otra tabla, por eso lo valida la API. Rollback: no se guarda nada." \
     400 POST "/pedidos" '{"id_cliente":5,"detalles":[{"id_precio":1,"precio_acordado":50,"fecha_entrega_estimada":"2026-12-01"}]}'
paso "Resumen del pedido desde la vista v_pedido_resumen" \
     "FR-11. Subtotal 13.00, descuento 0.65, total 12.35. Nada de esto está guardado: lo calcula la vista." \
     200 GET "/pedidos/7/resumen"

# --- 4. Pagos y entregas ---
paso "Adelanto de 5.00" \
     "FR-10. La API verifica que la suma de pagos no supere el total." \
     201 POST "/pagos" '{"id_pedido":7,"monto":5,"tipo_pago":"adelanto","metodo_pago":"efectivo"}'
paso "Entregar una prenda sin pagarla completa y sin motivo" \
     "FR-14. La prenda vale 6.65 con su parte del descuento y solo hay 5.00 pagados: falta el motivo." \
     400 POST "/pedidos/7/entregas" '{"lineas":[16]}'
paso "La misma entrega, con motivo" \
     "Entrega parcial: se lleva una prenda, la otra sigue en el taller." \
     201 POST "/pedidos/7/entregas" '{"lineas":[16],"motivo_deuda":"Paga el lunes"}'
paso "La deuda exigible de la clienta" \
     "6.65 entregado - 5.00 pagado = 1.65. La prenda que sigue en el taller no cuenta como deuda." \
     200 GET "/clientes/5/deuda"

# --- 5. Integridad ---
paso "Entregar otra vez la misma prenda" \
     "NFR-04. La PK de detalle_entrega es id_detalle: una prenda sale una sola vez (error 1062)." \
     409 POST "/pedidos/7/entregas" '{"lineas":[16],"motivo_deuda":"x"}'
paso "Borrar un cliente que tiene pedidos" \
     "NFR-04. ON DELETE RESTRICT: el historial no se pierde (error 1451)." \
     409 DELETE "/clientes/5"

# --- 6. Cierre ---
paso "Cobrar el saldo" \
     "Pago final de 7.35: el pedido queda pagado por completo." \
     201 POST "/pagos" '{"id_pedido":7,"monto":7.35,"tipo_pago":"saldo_final","metodo_pago":"efectivo"}'
paso "Entregar la última prenda" \
     "Ya no hay deuda, así que no pide motivo." \
     201 POST "/pedidos/7/entregas" '{"lineas":[15]}'
paso "El pedido queda entregado" \
     "El estado no se guarda: la vista lo deduce porque todas las líneas están en detalle_entrega." \
     200 GET "/pedidos/7/resumen"
paso "Reporte de deudores" \
     "FR-19. Solo queda Carlos; Ana Belén ya no debe nada." \
     200 GET "/clientes/con-deuda"

echo
echo -e "${AZUL}Demostración terminada: $BIEN de $N pasos dieron el código esperado.${FIN}"
