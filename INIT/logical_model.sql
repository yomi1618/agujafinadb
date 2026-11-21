-- initialization

CREATE DATABASE IF NOT EXISTS `afdb`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `afdb`;

-- table creation

CREATE TABLE `cliente` (
  `id_cliente` int PRIMARY KEY AUTO_INCREMENT,
  `tipo_cliente` varchar(7) NOT NULL COMMENT 'CHECK: persona o empresa',
  `nombre` varchar(150) NOT NULL COMMENT 'nombre de la persona o razon social',
  `apellido` varchar(100) COMMENT 'obligatorio si tipo_cliente = persona; NULL si empresa',
  `tipo_identificacion` varchar(20) COMMENT 'CHECK: cedula o RUC; cedula solo si tipo_cliente = persona',
  `numero_identificacion` varchar(20) COMMENT 'requiere tipo_identificacion; cedula = 10 digitos, RUC = 13 digitos',
  `telefono` varchar(20) NOT NULL,
  `direccion` varchar(200),
  `email` varchar(120),
  `fecha_registro` date NOT NULL DEFAULT ((CURRENT_DATE))
);

CREATE TABLE `prenda` (
  `id_prenda` int PRIMARY KEY AUTO_INCREMENT,
  `tipo_prenda` varchar(60) NOT NULL,
  `descripcion` varchar(200)
);

CREATE TABLE `servicio` (
  `id_servicio` int PRIMARY KEY AUTO_INCREMENT,
  `nombre_servicio` varchar(80) NOT NULL,
  `descripcion` varchar(200)
);

CREATE TABLE `precio_servicio` (
  `id_precio` int PRIMARY KEY AUTO_INCREMENT,
  `id_servicio` int NOT NULL,
  `id_prenda` int NOT NULL,
  `descripcion_arreglo` varchar(120) NOT NULL,
  `precio_minimo` decimal(8,2) NOT NULL,
  `precio_maximo` decimal(8,2) NOT NULL
);

CREATE TABLE `pedido` (
  `id_pedido` int PRIMARY KEY AUTO_INCREMENT,
  `id_cliente` int NOT NULL,
  `fecha_hora_recepcion` datetime NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `fecha_entrega_estimada` date NOT NULL COMMENT 'CHECK: >= DATE(fecha_hora_recepcion)',
  `fecha_hora_entrega_real` datetime,
  `estado` varchar(10) NOT NULL DEFAULT 'activa' COMMENT 'CHECK: activa o entregada',
  `descuento_porcentaje` decimal(4,2) NOT NULL DEFAULT 0 COMMENT 'CHECK: 0, o entre 5 y 10',
  `observaciones` varchar(255),
  `motivo_excepcion_entrega` varchar(255),
  `observaciones_entrega` varchar(255) COMMENT 'detalle de las prendas entregadas cuando no se entrega todo el pedido'
);

CREATE TABLE `detalle_pedido` (
  `id_detalle` int PRIMARY KEY AUTO_INCREMENT,
  `id_precio` int NOT NULL,
  `id_pedido` int NOT NULL,
  `precio_acordado` decimal(8,2) NOT NULL COMMENT 'CHECK > 0',
  `usa_repuesto` boolean NOT NULL DEFAULT false,
  `notas` varchar(255) COMMENT 'notas visuales libres: color, patron'
);

CREATE TABLE `pago` (
  `id_pago` int PRIMARY KEY AUTO_INCREMENT,
  `id_pedido` int NOT NULL,
  `monto` decimal(10,2) NOT NULL COMMENT 'CHECK > 0',
  `fecha_hora_pago` datetime NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `tipo_pago` varchar(12) NOT NULL COMMENT 'CHECK: adelanto o saldo_final',
  `metodo_pago` varchar(15) COMMENT 'CHECK: efectivo, transferencia o cheque'
);

-- constraints 

CREATE UNIQUE INDEX `uq_cliente_telefono_tipo_cliente` ON `cliente` (`telefono`, `tipo_cliente`);
CREATE UNIQUE INDEX `uq_prenda_tipo_prenda` ON `prenda` (`tipo_prenda`);
CREATE UNIQUE INDEX `uq_servicio_nombre_servicio` ON `servicio` (`nombre_servicio`);
CREATE UNIQUE INDEX `uq_precio_servicio_id_prenda_id_servicio_descripcion_arreglo` ON `precio_servicio` (`id_prenda`, `id_servicio`, `descripcion_arreglo`);
CREATE INDEX `idx_pedido_id_cliente_estado` ON `pedido` (`id_cliente`, `estado`);

-- alterations

ALTER TABLE `precio_servicio` COMMENT = 'CHECK 0 < precio_minimo <= precio_maximo';
ALTER TABLE `pedido` COMMENT = 'CHECKs de fechas y coherencia estado / fecha_hora_entrega_real';

ALTER TABLE `precio_servicio` ADD CONSTRAINT `fk_precio_servicio_prenda` FOREIGN KEY (`id_prenda`) REFERENCES `prenda` (`id_prenda`) ON DELETE RESTRICT;
ALTER TABLE `precio_servicio` ADD CONSTRAINT `fk_precio_servicio_servicio` FOREIGN KEY (`id_servicio`) REFERENCES `servicio` (`id_servicio`) ON DELETE RESTRICT;
ALTER TABLE `pedido` ADD CONSTRAINT `fk_pedido_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`) ON DELETE RESTRICT;
ALTER TABLE `detalle_pedido` ADD CONSTRAINT `fk_detalle_pedido_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`) ON DELETE RESTRICT;
ALTER TABLE `detalle_pedido` ADD CONSTRAINT `fk_detalle_pedido_precio_servicio` FOREIGN KEY (`id_precio`) REFERENCES `precio_servicio` (`id_precio`) ON DELETE RESTRICT;
ALTER TABLE `pago` ADD CONSTRAINT `fk_pago_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedido` (`id_pedido`) ON DELETE RESTRICT;

-- cliente

ALTER TABLE `cliente`
  ADD CONSTRAINT `ck_cliente_tipo`
    CHECK (`tipo_cliente` IN ('persona', 'empresa')),
  ADD CONSTRAINT `ck_cliente_apellido_tipo`
    CHECK (
      (`tipo_cliente` = 'persona' AND `apellido` IS NOT NULL)
      OR (`tipo_cliente` = 'empresa' AND `apellido` IS NULL)
    ),
  ADD CONSTRAINT `ck_cliente_tipo_identificacion`
    CHECK (`tipo_identificacion` IS NULL OR `tipo_identificacion` IN ('cedula', 'ruc')),
  ADD CONSTRAINT `ck_cliente_cedula_persona`
    CHECK (`tipo_identificacion` IS NULL OR `tipo_identificacion` <> 'cedula' OR `tipo_cliente` = 'persona'),
  ADD CONSTRAINT `ck_cliente_numero_identificacion`
    CHECK (
      `numero_identificacion` IS NULL
      OR (
        `tipo_identificacion` IS NOT NULL
        AND (
          (`tipo_identificacion` = 'cedula' AND CHAR_LENGTH(`numero_identificacion`) = 10)
          OR (`tipo_identificacion` = 'ruc' AND CHAR_LENGTH(`numero_identificacion`) = 13)
        )
      )
    );

-- precio_servicio

ALTER TABLE `precio_servicio`
  ADD CONSTRAINT `ck_precio_servicio_rango`
    CHECK (`precio_minimo` > 0 AND `precio_minimo` <= `precio_maximo`);

-- pedido

ALTER TABLE `pedido`
  ADD CONSTRAINT `ck_pedido_estado`
    CHECK (`estado` IN ('activa', 'entregada')),
  ADD CONSTRAINT `ck_pedido_descuento`
    CHECK (`descuento_porcentaje` = 0 OR `descuento_porcentaje` BETWEEN 5 AND 10),
  ADD CONSTRAINT `ck_pedido_fecha_estimada`
    CHECK (`fecha_entrega_estimada` >= DATE(`fecha_hora_recepcion`)),
  ADD CONSTRAINT `ck_pedido_entrega_real_fecha`
    CHECK (`fecha_hora_entrega_real` IS NULL OR `fecha_hora_entrega_real` >= `fecha_hora_recepcion`),
  ADD CONSTRAINT `ck_pedido_estado_entrega`
    CHECK (
      (`estado` = 'activa' AND `fecha_hora_entrega_real` IS NULL)
      OR (`estado` = 'entregada' AND `fecha_hora_entrega_real` IS NOT NULL)
    );

-- detalle_pedido

ALTER TABLE `detalle_pedido`
  ADD CONSTRAINT `ck_detalle_pedido_precio_positivo`
    CHECK (`precio_acordado` > 0);

-- pago

ALTER TABLE `pago`
  ADD CONSTRAINT `ck_pago_monto_positivo`
    CHECK (`monto` > 0),
  ADD CONSTRAINT `ck_pago_tipo`
    CHECK (`tipo_pago` IN ('adelanto', 'saldo_final')),
  ADD CONSTRAINT `ck_pago_metodo`
    CHECK (`metodo_pago` IS NULL OR `metodo_pago` IN ('efectivo', 'transferencia', 'cheque'));

-- views (totales and saldos)

-- Resumen por pedido: subtotal, descuento, total neto, pagado y saldo pendiente.
-- Lineas y pagos se suman por separado para no duplicar montos al unir las dos tablas.

CREATE OR REPLACE VIEW `v_pedido_resumen` AS
SELECT
  t.`id_pedido`,
  t.`id_cliente`,
  t.`estado`,
  t.`subtotal`,
  t.`descuento_monto`,
  t.`subtotal` - t.`descuento_monto` AS `total_neto`,
  t.`monto_pagado`,
  t.`subtotal` - t.`descuento_monto` - t.`monto_pagado` AS `saldo_pendiente`
FROM (
  SELECT
    p.`id_pedido`,
    p.`id_cliente`,
    p.`estado`,
    COALESCE(d.`subtotal`, 0) AS `subtotal`,
    ROUND(COALESCE(d.`subtotal`, 0) * p.`descuento_porcentaje` / 100, 2) AS `descuento_monto`,
    COALESCE(g.`pagado`, 0) AS `monto_pagado`
  FROM `pedido` p
  LEFT JOIN (
    SELECT `id_pedido`, SUM(`precio_acordado`) AS `subtotal`
    FROM `detalle_pedido`
    GROUP BY `id_pedido`
  ) d ON d.`id_pedido` = p.`id_pedido`
  LEFT JOIN (
    SELECT `id_pedido`, SUM(`monto`) AS `pagado`
    FROM `pago`
    GROUP BY `id_pedido`
  ) g ON g.`id_pedido` = p.`id_pedido`
) t;

-- Deuda historica por cliente (suma de saldos pendientes de todos sus pedidos).
-- Alimenta la alerta de deuda (FR-03) y el reporte de clientes con saldo (FR-19):

CREATE OR REPLACE VIEW `v_cliente_saldo` AS
SELECT
  c.`id_cliente`, c.`tipo_cliente`, c.`nombre`, c.`apellido`, c.`telefono`,
  COALESCE(SUM(r.`saldo_pendiente`), 0) AS `saldo_pendiente`
FROM `cliente` c
LEFT JOIN `v_pedido_resumen` r
  ON r.`id_cliente` = c.`id_cliente` AND r.`estado` = 'entregada'
GROUP BY c.`id_cliente`, c.`tipo_cliente`, c.`nombre`, c.`apellido`, c.`telefono`;
