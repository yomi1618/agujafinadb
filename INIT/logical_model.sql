-- 1. BASE DE DATOS

CREATE DATABASE IF NOT EXISTS `afdb`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `afdb`;

-- 2. TABLAS (columnas, PK y valores por defecto; sin relaciones)

--    2.1 Catálogo: prenda, servicio, precio_servicio

CREATE TABLE `prenda` (
  `id_prenda` int PRIMARY KEY AUTO_INCREMENT,
  `tipo_prenda` varchar(60) NOT NULL
);

CREATE TABLE `servicio` (
  `id_servicio` int PRIMARY KEY AUTO_INCREMENT,
  `nombre_servicio` varchar(80) NOT NULL
);

CREATE TABLE `precio_servicio` (
  `id_precio` int PRIMARY KEY AUTO_INCREMENT,
  `id_servicio` int NOT NULL,
  `id_prenda` int NOT NULL,
  `descripcion_arreglo` varchar(120) NOT NULL,
  `precio_minimo` decimal(8,2) NOT NULL,
  `precio_maximo` decimal(8,2) NOT NULL
);

--    2.2 Operación: cliente, pedido, detalle_pedido

CREATE TABLE `cliente` (
  `id_cliente` int PRIMARY KEY AUTO_INCREMENT,
  `tipo_cliente` varchar(7) NOT NULL,
  `nombre` varchar(150) NOT NULL COMMENT 'nombre de la persona o razon social',
  `apellido` varchar(100) COMMENT 'obligatorio si tipo_cliente = persona; NULL si empresa',
  `tipo_identificacion` varchar(20),
  `numero_identificacion` varchar(20),
  `telefono` varchar(20) NOT NULL,
  `direccion` varchar(200),
  `ciudad` varchar(60) COMMENT 'obligatoria si hay direccion',
  `email` varchar(120),
  `fecha_registro` date NOT NULL DEFAULT ((CURRENT_DATE))
);

CREATE TABLE `pedido` (
  `id_pedido` int PRIMARY KEY AUTO_INCREMENT,
  `id_cliente` int NOT NULL,
  `fecha_hora_recepcion` datetime NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `descuento_porcentaje` decimal(4,2) NOT NULL DEFAULT 0,
  `observaciones_pedido` varchar(255)
);

CREATE TABLE `detalle_pedido` (
  `id_detalle` int PRIMARY KEY AUTO_INCREMENT,
  `id_precio` int NOT NULL,
  `id_pedido` int NOT NULL,
  `precio_acordado` decimal(8,2) NOT NULL,
  `fecha_entrega_estimada` date NOT NULL,
  `usa_repuesto` boolean NOT NULL,
  `notas` varchar(255)
);

--    2.3 Salida: entrega, entrega_detalle, pago

CREATE TABLE `entrega` (
  `id_entrega` int PRIMARY KEY AUTO_INCREMENT,
  `id_pedido` int NOT NULL,
  `fecha_hora_entrega` datetime NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `observaciones_entrega` varchar(255),
  `con_deuda` boolean NOT NULL DEFAULT false COMMENT 'true si tras esta entrega el pedido queda con deuda exigible',
  `motivo_excepcion` varchar(255) COMMENT 'obligatorio si con_deuda = true; NULL si no'
);

CREATE TABLE `entrega_detalle` (
  `id_entrega` int NOT NULL,
  `id_detalle` int NOT NULL,
  `id_pedido` int NOT NULL,
  PRIMARY KEY (`id_detalle`)
);

CREATE TABLE `pago` (
  `id_pago` int PRIMARY KEY AUTO_INCREMENT,
  `id_pedido` int NOT NULL,
  `monto` decimal(10,2) NOT NULL,
  `fecha_hora_pago` datetime NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `tipo_pago` varchar(12) NOT NULL,
  `metodo_pago` varchar(15) NOT NULL COMMENT 'efectivo, transferencia o cheque'
);

-- 3. ÍNDICES ÚNICOS
--    3.1 Evitan duplicados (regla de negocio)

CREATE UNIQUE INDEX `uq_cliente_identificacion` ON `cliente` (`tipo_identificacion`, `numero_identificacion`);
CREATE UNIQUE INDEX `uq_prenda_tipo_prenda` ON `prenda` (`tipo_prenda`);
CREATE UNIQUE INDEX `uq_servicio_nombre_servicio` ON `servicio` (`nombre_servicio`);
CREATE UNIQUE INDEX `uq_precio_servicio_id_prenda_id_servicio_descripcion_arreglo` ON `precio_servicio` (`id_prenda`, `id_servicio`, `descripcion_arreglo`);

--    3.2 Destino de las FK compuestas de entrega_detalle

CREATE UNIQUE INDEX `uq_entrega_id_entrega_id_pedido` ON `entrega` (`id_entrega`, `id_pedido`);
CREATE UNIQUE INDEX `uq_detalle_pedido_id_detalle_id_pedido` ON `detalle_pedido` (`id_detalle`, `id_pedido`);

-- 4. ÍNDICES DE BÚSQUEDA

CREATE INDEX `ix_cliente_telefono` ON `cliente` (`telefono`);

-- 5. LLAVES FORÁNEAS (relaciones entre tablas)

ALTER TABLE `precio_servicio` ADD CONSTRAINT `fk_precio_servicio_prenda` FOREIGN KEY (`id_prenda`) REFERENCES `prenda` (`id_prenda`) ON DELETE RESTRICT;
ALTER TABLE `precio_servicio` ADD CONSTRAINT `fk_precio_servicio_servicio` FOREIGN KEY (`id_servicio`) REFERENCES `servicio` (`id_servicio`) ON DELETE RESTRICT;
ALTER TABLE `pedido` ADD CONSTRAINT `fk_pedido_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`) ON DELETE RESTRICT;
ALTER TABLE `detalle_pedido` ADD CONSTRAINT `fk_detalle_pedido_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`) ON DELETE RESTRICT;
ALTER TABLE `detalle_pedido` ADD CONSTRAINT `fk_detalle_pedido_precio_servicio` FOREIGN KEY (`id_precio`) REFERENCES `precio_servicio` (`id_precio`) ON DELETE RESTRICT;
ALTER TABLE `pago` ADD CONSTRAINT `fk_pago_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`) ON DELETE RESTRICT;
ALTER TABLE `entrega` ADD CONSTRAINT `fk_entrega_pedido`
  FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`) ON DELETE RESTRICT;
ALTER TABLE `entrega_detalle` ADD CONSTRAINT `fk_ed_entrega`
  FOREIGN KEY (`id_entrega`, `id_pedido`)
  REFERENCES `entrega` (`id_entrega`, `id_pedido`) ON DELETE RESTRICT;
ALTER TABLE `entrega_detalle` ADD CONSTRAINT `fk_ed_detalle`
  FOREIGN KEY (`id_detalle`, `id_pedido`)
  REFERENCES `detalle_pedido` (`id_detalle`, `id_pedido`) ON DELETE RESTRICT;

-- 6. REGLAS DE NEGOCIO (CHECK)
--    6.1 cliente

ALTER TABLE `cliente`
  ADD CONSTRAINT `ck_cliente_tipo`
    CHECK (`tipo_cliente` IN ('persona', 'empresa')),
  ADD CONSTRAINT `ck_cliente_apellido_tipo`
    CHECK ((`tipo_cliente` = 'persona' AND `apellido` IS NOT NULL) OR (`tipo_cliente` = 'empresa' AND `apellido` IS NULL)),
  ADD CONSTRAINT `ck_cliente_tipo_identificacion`
    CHECK (`tipo_identificacion` IS NULL OR `tipo_identificacion` IN ('cedula', 'ruc')),
  ADD CONSTRAINT `ck_cliente_cedula_persona`
    CHECK (`tipo_identificacion` IS NULL OR `tipo_identificacion` <> 'cedula' OR `tipo_cliente` = 'persona'),
  ADD CONSTRAINT `ck_cliente_identificacion`
    CHECK (
      (`tipo_identificacion` IS NULL) = (`numero_identificacion` IS NULL)
      AND (
        `tipo_identificacion` IS NULL
        OR (`tipo_identificacion` = 'cedula' AND `numero_identificacion` REGEXP '^[0-9]{10}$')
        OR (`tipo_identificacion` = 'ruc' AND `numero_identificacion` REGEXP '^[0-9]{13}$')
      )
    ),
  ADD CONSTRAINT `ck_cliente_ciudad_direccion`
    CHECK (`direccion` IS NULL OR (`ciudad` IS NOT NULL AND CHAR_LENGTH(`ciudad`) > 0));

--    6.2 precio_servicio

ALTER TABLE `precio_servicio`
  ADD CONSTRAINT `ck_precio_servicio_rango`
    CHECK (`precio_minimo` > 0 AND `precio_minimo` <= `precio_maximo`);

--    6.3 pedido

ALTER TABLE `pedido`
  ADD CONSTRAINT `ck_pedido_descuento`
    CHECK (`descuento_porcentaje` = 0 OR `descuento_porcentaje` BETWEEN 5 AND 10);

--    6.4 detalle_pedido

ALTER TABLE `detalle_pedido`
  ADD CONSTRAINT `ck_detalle_pedido_precio_positivo`
    CHECK (`precio_acordado` > 0);

--    6.5 pago

ALTER TABLE `pago`
  ADD CONSTRAINT `ck_pago_monto_positivo`
    CHECK (`monto` > 0),
  ADD CONSTRAINT `ck_pago_tipo`
    CHECK (`tipo_pago` IN ('adelanto', 'saldo_final')),
  ADD CONSTRAINT `ck_pago_metodo`
    CHECK (`metodo_pago` IN ('efectivo', 'transferencia', 'cheque'));

--    6.6 entrega

ALTER TABLE `entrega`
  ADD CONSTRAINT `ck_entrega_motivo_deuda`
    CHECK (
      (`con_deuda` AND `motivo_excepcion` IS NOT NULL AND CHAR_LENGTH(`motivo_excepcion`) > 0)
      OR (NOT `con_deuda` AND `motivo_excepcion` IS NULL)
    );

-- 7. VISTAS: v_pedido_resumen, v_cliente_saldo

-- Resumen por pedido: subtotal, descuento, total neto, pagado y saldo pendiente.
-- Lineas y pagos se suman por separado para no duplicar montos al unir las dos tablas.

CREATE OR REPLACE VIEW `v_pedido_resumen` AS
SELECT
  t.`id_pedido`,
  t.`id_cliente`,
  CASE WHEN t.`lineas_total` > 0 AND t.`lineas_entregadas` = t.`lineas_total`
       THEN 'entregado' ELSE 'activo' END AS `estado`,
  t.`lineas_total`,
  t.`lineas_entregadas`,
  t.`subtotal`,
  t.`descuento_monto`,
  t.`subtotal` - t.`descuento_monto` AS `total_neto`,
  t.`monto_pagado`,
  t.`subtotal` - t.`descuento_monto` - t.`monto_pagado` AS `saldo_total_pendiente`,
  t.`subtotal_entregado` - t.`descuento_entregado` AS `total_entregado_neto`,
  GREATEST(t.`subtotal_entregado` - t.`descuento_entregado` - t.`monto_pagado`, 0) AS `deuda_exigible`,
  GREATEST(t.`monto_pagado` - (t.`subtotal_entregado` - t.`descuento_entregado`), 0) AS `saldo_favor`
FROM (
  SELECT
    b.`id_pedido`,
    b.`id_cliente`,
    b.`lineas_total`,
    b.`lineas_entregadas`,
    b.`subtotal`,
    b.`descuento_monto`,
    b.`subtotal_entregado`,
    CASE
      WHEN b.`subtotal` = 0 THEN 0.00
      WHEN b.`lineas_entregadas` = b.`lineas_total` THEN b.`descuento_monto`
      ELSE ROUND(b.`descuento_monto` * (b.`subtotal_entregado` / b.`subtotal`), 2)
    END AS `descuento_entregado`,
    b.`monto_pagado`
  FROM (
    SELECT
      p.`id_pedido`,
      p.`id_cliente`,
      COALESCE(d.`lineas_total`, 0) AS `lineas_total`,
      COALESCE(d.`lineas_entregadas`, 0) AS `lineas_entregadas`,
      COALESCE(d.`subtotal`, 0) AS `subtotal`,
      ROUND(COALESCE(d.`subtotal`, 0) * p.`descuento_porcentaje` / 100, 2) AS `descuento_monto`,
      COALESCE(d.`subtotal_entregado`, 0) AS `subtotal_entregado`,
      COALESCE(g.`pagado`, 0) AS `monto_pagado`
    FROM `pedido` p
    LEFT JOIN (
      SELECT
        dp.`id_pedido`,
        COUNT(*) AS `lineas_total`,
        COUNT(ed.`id_detalle`) AS `lineas_entregadas`,
        SUM(dp.`precio_acordado`) AS `subtotal`,
        SUM(CASE WHEN ed.`id_detalle` IS NOT NULL THEN dp.`precio_acordado` ELSE 0 END) AS `subtotal_entregado`
      FROM `detalle_pedido` dp
      LEFT JOIN `entrega_detalle` ed ON ed.`id_detalle` = dp.`id_detalle`
      GROUP BY dp.`id_pedido`
    ) d ON d.`id_pedido` = p.`id_pedido`
    LEFT JOIN (
      SELECT `id_pedido`, SUM(`monto`) AS `pagado`
      FROM `pago`
      GROUP BY `id_pedido`
    ) g ON g.`id_pedido` = p.`id_pedido`
  ) b
) t;

-- Deuda historica por cliente: suma de la deuda exigible (prendas entregadas
-- menos pagos) de todos sus pedidos, sin importar si el pedido esta completo.
-- Alimenta la alerta de deuda (FR-03) y el reporte de clientes con saldo (FR-19):

CREATE OR REPLACE VIEW `v_cliente_deuda` AS
SELECT
  c.`id_cliente`, c.`tipo_cliente`, c.`nombre`, c.`apellido`, c.`telefono`,
  COALESCE(SUM(r.`deuda_exigible`), 0) AS `saldo_pendiente`
FROM `cliente` c
LEFT JOIN `v_pedido_resumen` r
  ON r.`id_cliente` = c.`id_cliente`
GROUP BY c.`id_cliente`, c.`tipo_cliente`, c.`nombre`, c.`apellido`, c.`telefono`;
