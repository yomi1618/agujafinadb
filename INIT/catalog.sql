-- catalogo_inserts.sql
-- Carga del catalogo de prendas, servicios y precios en afdb.
-- Ejecutar DESPUES de crear el esquema (logical_erd.sql).

SET NAMES utf8mb4;
USE `afdb`;

-- prendas

INSERT INTO `prenda` (`tipo_prenda`) VALUES
  ('Pantalón'),
  ('Chaqueta'),
  ('Camisa');

-- servicios (se comparten entre prendas: Entalle, Cambio y Largo aparecen en varias)

INSERT INTO `servicio` (`nombre_servicio`) VALUES
  ('Subir/Bajar bastas'),
  ('Entalle'),
  ('Cambio'),
  ('Largo'),
  ('Ojales'),
  ('Virar');

-- ids en variables para no depender del orden del AUTO_INCREMENT

SET @pantalon = (SELECT `id_prenda` FROM `prenda` WHERE `tipo_prenda` = 'Pantalón');
SET @chaqueta = (SELECT `id_prenda` FROM `prenda` WHERE `tipo_prenda` = 'Chaqueta');
SET @camisa   = (SELECT `id_prenda` FROM `prenda` WHERE `tipo_prenda` = 'Camisa');

SET @bastas  = (SELECT `id_servicio` FROM `servicio` WHERE `nombre_servicio` = 'Subir/Bajar bastas');
SET @entalle = (SELECT `id_servicio` FROM `servicio` WHERE `nombre_servicio` = 'Entalle');
SET @cambio  = (SELECT `id_servicio` FROM `servicio` WHERE `nombre_servicio` = 'Cambio');
SET @largo   = (SELECT `id_servicio` FROM `servicio` WHERE `nombre_servicio` = 'Largo');
SET @ojales  = (SELECT `id_servicio` FROM `servicio` WHERE `nombre_servicio` = 'Ojales');
SET @virar   = (SELECT `id_servicio` FROM `servicio` WHERE `nombre_servicio` = 'Virar');

-- precios

INSERT INTO `precio_servicio`
  (`id_prenda`, `id_servicio`, `descripcion_arreglo`, `precio_minimo`, `precio_maximo`)
VALUES
  -- Pantalón
  (@pantalon, @bastas,  '20-24',                          5.00,  7.00),
  (@pantalon, @bastas,  '>24',                            8.00, 10.00),
  (@pantalon, @entalle, 'Cintura',                        8.00, 10.00),
  (@pantalon, @entalle, 'Cadera',                         8.00, 10.00),
  (@pantalon, @entalle, 'Muslo',                          8.00, 10.00),
  (@pantalon, @entalle, 'Rodilla',                        8.00, 10.00),
  (@pantalon, @entalle, 'Basta',                          8.00, 10.00),
  (@pantalon, @entalle, 'Completo',                      15.00, 20.00),
  (@pantalon, @cambio,  'Cierre',                         6.00,  8.00),
  (@pantalon, @cambio,  'Botón por unidad (con repuesto)', 0.50,  1.00),
  (@pantalon, @cambio,  'Botón por unidad (sin repuesto)', 1.50,  2.00),

  -- Chaqueta
  (@chaqueta, @largo,   'Cuerpo',                        25.00, 30.00),
  (@chaqueta, @largo,   'Mangas',                        25.00, 30.00),
  (@chaqueta, @entalle, 'Hombros',                       20.00, 25.00),
  (@chaqueta, @entalle, 'Cuerpo',                        30.00, 35.00),
  (@chaqueta, @cambio,  'Botón por unidad (con repuesto)', 1.00,  1.50),
  (@chaqueta, @cambio,  'Botón por unidad (sin repuesto)', 1.50,  2.00),
  (@chaqueta, @ojales,  'Por unidad',                     1.00,  1.50),

  -- Camisa
  (@camisa,   @largo,   'Cuerpo',                         8.00, 10.00),
  (@camisa,   @largo,   'Mangas',                         8.00, 10.00),
  (@camisa,   @entalle, 'Hombros',                        8.00, 10.00),
  (@camisa,   @entalle, 'Cuerpo',                        10.00, 12.00),
  (@camisa,   @virar,   'Cuello',                         6.00,  8.00),
  (@camisa,   @virar,   'Puños',                          6.00,  8.00),
  (@camisa,   @cambio,  'Cuello',                        10.00, 12.00),
  (@camisa,   @cambio,  'Puños',                         10.00, 12.00);
