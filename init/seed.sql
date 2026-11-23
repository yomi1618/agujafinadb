-- ============================================================
-- SEED DE PRUEBA PARA afdb  (solo ASCII)
-- Ejecutar DESPUES de logical_model.sql
-- ============================================================

USE `afdb`;

-- 1. CLIENTES ------------------------------------------------

INSERT INTO `cliente`
  (`id_cliente`, `tipo_cliente`, `nombre`, `apellido`, `tipo_identificacion`,
   `numero_identificacion`, `telefono`, `direccion`, `ciudad`, `email`, `fecha_registro`) VALUES
  (1, 'persona', 'Maria Fernanda', 'Lopez',     'cedula', '1002345678',    '0991234567',
      'Calle Bolivar y Sucre',        'Atuntaqui', 'mafe.lopez@example.com', '2026-01-15'),
  (2, 'persona', 'Carlos Andres',    'Perez',    'cedula', '1003456789',    '0982345678',
      'Av. Cristobal de Troya 123',   'Ibarra',    NULL,                     '2026-02-03'),
  (3, 'persona', 'Lucia',            'Morales',  'cedula', '1004567890',    '0973456789',
      NULL,                           NULL,        'lucia.m@example.com',    '2026-03-20'),
  (4, 'persona', 'Jose Luis',        'Torres',   'ruc',    '1005678901001', '0964567890',
      'Calle Garcia Moreno 45',       'Atuntaqui', NULL,                     '2026-04-10'),
  (5, 'persona', 'Ana Belen',        'Cevallos', NULL,     NULL,            '0955678901',
      NULL,                           NULL,        'ana.cevallos@example.com','2026-05-02'),
  (6, 'empresa', 'Boutique Elegance S.A.', NULL,   'ruc',  '1790012345001', '062601122',
      'Av. Julio Miguel Aguinaga 200','Atuntaqui', 'ventas@elegance.example.com', '2026-06-18'),
  (7, 'empresa', 'Textiles Imbabura Cia. Ltda.', NULL, 'ruc', '1791234567001', '062900300',
      NULL,                           NULL,        NULL,                     '2026-07-25');

-- 2. PEDIDOS Y DETALLES -------------------------------------

INSERT INTO `pedido`
  (`id_pedido`, `id_cliente`, `fecha_hora_recepcion`, `descuento_porcentaje`, `observaciones_pedido`) VALUES
  (1, 1, '2026-10-01 09:30:00',  0.00, 'Pedido completo y pagado'),
  (2, 2, '2026-10-10 11:00:00',  0.00, 'Entrega parcial con deuda'),
  (3, 3, '2026-11-05 15:45:00', 10.00, 'Cliente frecuente, descuento maximo'),
  (4, 6, '2026-11-02 08:15:00',  5.00, 'Lote de jeans de la boutique'),
  (5, 4, '2026-11-18 10:20:00',  0.00, 'Sin adelanto todavia'),
  (6, 5, '2026-11-12 16:00:00',  0.00, 'Arreglo rapido');

INSERT INTO `detalle_pedido`
  (`id_detalle`, `id_precio`, `id_pedido`, `precio_acordado`, `fecha_entrega_estimada`, `usa_repuesto`, `notas`) VALUES
  -- Pedido 1
  ( 1,  1, 1,  6.00, '2026-10-04', FALSE, 'Pantalon azul'),
  ( 2,  4, 1, 10.00, '2026-10-04', FALSE, 'Camisa blanca'),
  -- Pedido 2
  ( 3,  8, 2, 25.00, '2026-10-15', FALSE, 'Vestido de fiesta'),
  ( 4,  7, 2, 10.00, '2026-10-15', FALSE, NULL),
  ( 5,  5, 2,  3.00, '2026-10-20', TRUE,  'Botones dorados provistos por el taller'),
  -- Pedido 3
  ( 6, 10, 3, 18.00, '2026-11-12', TRUE,  'Cierre metalico'),
  ( 7, 11, 3, 20.00, '2026-11-12', FALSE, NULL),
  -- Pedido 4
  ( 8, 14, 4,  6.00, '2026-11-06', FALSE, NULL),
  ( 9, 14, 4,  6.00, '2026-11-06', FALSE, NULL),
  (10, 14, 4,  6.00, '2026-11-06', FALSE, NULL),
  (11, 15, 4,  8.00, '2026-11-09', FALSE, 'Remiendo en rodilla'),
  -- Pedido 5
  (12, 12, 5,  5.00, '2026-11-25', FALSE, NULL),
  (13, 13, 5,  8.00, '2026-11-25', FALSE, NULL),
  -- Pedido 6
  (14,  2, 6,  8.00, '2026-11-14', TRUE,  'Cierre negro');

-- 3. ENTREGAS ------------------------------------------------

INSERT INTO `entrega`
  (`id_entrega`, `id_pedido`, `fecha_hora_entrega`, `observaciones_entrega`, `motivo_deuda`) VALUES
  (1, 1, '2026-10-04 17:00:00', 'Entrega completa',   NULL),
  (2, 2, '2026-10-15 12:30:00', 'Entrega parcial',    'Cliente olvido la cartera, pagara el lunes'),
  (3, 4, '2026-11-06 10:00:00', 'Primera entrega lote', NULL),
  (4, 4, '2026-11-09 10:30:00', 'Segunda entrega lote', NULL),
  (5, 6, '2026-11-14 18:00:00', NULL,                 NULL);

INSERT INTO `detalle_entrega` (`id_entrega`, `id_detalle`, `id_pedido`) VALUES
  (1,  1, 1),
  (1,  2, 1),
  (2,  3, 2),
  (2,  4, 2),
  (3,  8, 4),
  (3,  9, 4),
  (3, 10, 4),
  (4, 11, 4),
  (5, 14, 6);

-- 4. PAGOS ---------------------------------------------------

INSERT INTO `pago`
  (`id_pago`, `id_pedido`, `monto`, `fecha_hora_pago`, `tipo_pago`, `metodo_pago`) VALUES
  (1, 1,  6.00, '2026-10-01 09:35:00', 'adelanto',    'efectivo'),
  (2, 1, 10.00, '2026-10-04 17:05:00', 'saldo_final', 'efectivo'),
  (3, 2, 15.00, '2026-10-10 11:05:00', 'adelanto',    'transferencia'),
  (4, 3, 10.00, '2026-11-05 15:50:00', 'adelanto',    'cheque'),
  (5, 4, 10.00, '2026-11-02 08:20:00', 'adelanto',    'transferencia'),
  (6, 4, 14.70, '2026-11-09 10:40:00', 'saldo_final', 'transferencia'),
  (7, 6,  8.00, '2026-11-14 18:05:00', 'saldo_final', 'efectivo');

-- 5. VERIFICACION (valores esperados en comentarios) --------

-- SELECT * FROM v_pedido_resumen ORDER BY id_pedido;
--   P1: entregado | subtotal 16.00 | desc 0.00    | neto 16.00 | pagado 16.00 | saldo 0.00  | deuda_exigible 0.00
--   P2: activo    | subtotal 38.00 | desc 0.00    | neto 38.00 | pagado 15.00 | saldo 23.00 | deuda_exigible 20.00
--   P3: activo    | subtotal 38.00 | desc 3.80    | neto 34.20 | pagado 10.00 | saldo 24.20 | deuda_exigible 0.00
--   P4: entregado | subtotal 26.00 | desc 1.30    | neto 24.70 | pagado 24.70 | saldo 0.00  | deuda_exigible 0.00
--   P5: activo    | subtotal 13.00 | desc 0.00    | neto 13.00 | pagado 0.00  | saldo 13.00 | deuda_exigible 0.00
--   P6: entregado | subtotal 8.00  | desc 0.00    | neto 8.00  | pagado 8.00  | saldo 0.00  | deuda_exigible 0.00

-- SELECT * FROM v_cliente_deuda ORDER BY id_cliente;
--   Solo el cliente 2 (Carlos Perez) debe tener saldo_pendiente = 20.00; los demas 0.00.

-- Pruebas de reglas (cada una DEBE fallar):
-- INSERT INTO cliente (tipo_cliente, nombre, apellido, telefono) VALUES ('persona', 'Sin Apellido', NULL, '0900000001');
-- INSERT INTO cliente (tipo_cliente, nombre, apellido, tipo_identificacion, numero_identificacion, telefono)
--   VALUES ('empresa', 'Empresa Cedula', NULL, 'cedula', '1234567890', '0900000002');
-- INSERT INTO pedido (id_cliente, descuento_porcentaje) VALUES (1, 15.00);
-- INSERT INTO detalle_entrega (id_entrega, id_detalle, id_pedido) VALUES (1, 12, 5);  -- detalle de otro pedido
-- INSERT INTO pago (id_pedido, monto, tipo_pago, metodo_pago) VALUES (1, 5.00, 'adelanto', 'tarjeta');
