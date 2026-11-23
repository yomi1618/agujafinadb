-- TC-29: agrega 10 000 pedidos de prueba (con una línea cada uno) a la base afdb
USE afdb;
SET SESSION cte_max_recursion_depth = 20000;
INSERT INTO pedido (id_cliente, descuento_porcentaje)
  WITH RECURSIVE s(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM s WHERE n < 10000)
  SELECT 1 + (n % 7), 0 FROM s;
INSERT INTO detalle_pedido (id_precio, id_pedido, precio_acordado, fecha_entrega_estimada)
  SELECT 1, id_pedido, 6.00, CURRENT_DATE + INTERVAL 7 DAY FROM pedido WHERE id_pedido > 6;
SELECT COUNT(*) AS pedidos FROM pedido;
