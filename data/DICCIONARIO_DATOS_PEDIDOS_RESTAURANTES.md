# Diccionario de datos — Pedidos cadena de restaurantes "Sazón Colombiana"

**Archivo principal:** `pedidos_restaurantes_raw.csv`
**Contexto:** Registros simulados de pedidos de una cadena de restaurantes de comida colombiana con 9 sedes en Huila, Cundinamarca, Antioquia, Valle del Cauca, Tolima y Santander. Vende en salón, para llevar, domicilio propio y Rappi.

**Nota:** El archivo RAW contiene errores, formatos inconsistentes, faltantes, duplicados y anomalías introducidos a propósito. Este diccionario describe cómo *deberían* ser los datos.

| Concepto | Valor |
|---|---|
| Variables | 23 |
| Registros base esperados | 2.000 |
| Registros del archivo RAW | 2.056 |
| Periodo esperado | 2026-01-01 a 2026-09-30 |
| Moneda | Pesos colombianos (COP) |

## Variables

| Variable | Tipo esperado | Descripción | Reglas / dominio esperado | Ejemplo |
|---|---|---|---|---|
| id_pedido | Texto | Identificador único del pedido | Formato `PED-#####`. No debe repetirse. | PED-00125 |
| fecha | Fecha | Fecha del pedido | `AAAA-MM-DD`, dentro del periodo esperado | 2026-03-14 |
| hora | Hora | Hora de registro del pedido | `HH:MM`, 24 horas (00–23 : 00–59) | 13:42 |
| id_cliente | Texto | Identificador del cliente | Formato `CL-####`. Puede repetirse en varios pedidos | CL-0231 |
| tipo_cliente | Categórica | Segmento del cliente | Ocasional, Frecuente, Empresarial, Nuevo | Frecuente |
| sede | Categórica | Restaurante donde se generó el pedido | Sede Centro Neiva, Sede Norte Neiva, Sede Pitalito, Sede Chapinero, Sede Usaquén, Sede El Poblado, Sede Granada, Sede Ibagué, Sede Cabecera | Sede Chapinero |
| ciudad | Categórica | Ciudad de la sede | Debe corresponder a la sede y al departamento | Bogotá |
| departamento | Categórica | Departamento de la sede | Coherente con la ciudad | Cundinamarca |
| canal | Categórica | Canal de venta | Salón, Para llevar, Domicilio propio, Rappi | Rappi |
| plato | Categórica | Producto vendido | Debe pertenecer al menú (ver abajo) | Bandeja paisa |
| categoria | Categórica | Categoría del plato | Plato fuerte, Comida rápida, Entrada, Bebida, Postre. Coherente con el plato | Plato fuerte |
| cantidad | Entero | Unidades pedidas | Entero > 0 | 2 |
| precio_unitario | Numérica (COP) | Precio por unidad antes de descuento | Numérico > 0. Bogotá y Medellín tienen precios ~10 % más altos | 32000 |
| descuento_pct | Numérica (%) | Descuento aplicado al subtotal | 0 a 100. En la base se usan 0, 5, 10, 15 y 20 | 10 |
| costo_domicilio | Numérica (COP) | Cobro por envío | ≥ 0. Debe ser 0 en Salón y Para llevar | 5000 |
| propina | Numérica (COP) | Propina voluntaria | ≥ 0. Solo aplica en Salón (normalmente 0 o 10 % del subtotal) | 6400 |
| subtotal | Numérica (COP) | Valor antes de descuento, domicilio y propina | cantidad × precio_unitario | 64000 |
| total_pagado | Numérica (COP) | Valor final pagado | subtotal × (1 − descuento_pct/100) + costo_domicilio + propina | 63600 |
| metodo_pago | Categórica | Medio de pago | Efectivo, Tarjeta débito, Tarjeta crédito, Nequi, Daviplata, Transferencia | Nequi |
| estado_pedido | Categórica | Estado del pedido | Entregado, Cancelado, Reclamado, En preparación | Entregado |
| tiempo_preparacion_min | Numérica | Minutos de preparación en cocina | Positivo y razonable (aprox. 5–60). Vacío si fue Cancelado | 22 |
| tiempo_entrega_min | Numérica | Minutos de entrega al cliente | Solo para Domicilio propio y Rappi. Positivo y razonable (aprox. 10–90) | 35 |
| calificacion | Numérica | Valoración del cliente | 1 a 5. Puede estar vacía (no todos califican) | 4 |

## Menú (catálogo)

| Plato | Categoría | Precio base (COP) |
|---|---|---|
| Bandeja paisa | Plato fuerte | 32.000 |
| Ajiaco santafereño | Plato fuerte | 28.000 |
| Asado huilense | Plato fuerte | 35.000 |
| Sancocho de gallina | Plato fuerte | 27.000 |
| Mojarra frita | Plato fuerte | 38.000 |
| Lechona tolimense | Plato fuerte | 26.000 |
| Hamburguesa artesanal | Comida rápida | 24.000 |
| Perro caliente especial | Comida rápida | 16.000 |
| Salchipapa | Comida rápida | 15.000 |
| Empanadas x3 | Entrada | 9.000 |
| Patacones con hogao | Entrada | 12.000 |
| Arepa de choclo | Entrada | 8.500 |
| Limonada de coco | Bebida | 9.500 |
| Jugo natural | Bebida | 7.000 |
| Gaseosa | Bebida | 5.000 |
| Cerveza nacional | Bebida | 7.500 |
| Postre de natas | Postre | 9.000 |
| Brownie con helado | Postre | 11.000 |
| Achiras con café | Postre | 6.500 |

## Reglas de consistencia entre columnas

- `subtotal = cantidad × precio_unitario`
- `total_pagado = subtotal × (1 − descuento_pct/100) + costo_domicilio + propina`
- La categoría debe corresponder al plato según el menú.
- La ciudad y el departamento deben corresponder a la sede.
- Un `id_pedido` identifica una sola transacción.
- Pedidos en **Salón** o **Para llevar** no tienen costo de domicilio ni tiempo de entrega.
- Solo los pedidos en **Salón** llevan propina.
- Pedidos **Cancelados** no deben tener calificación, tiempo de entrega ni tiempo de preparación.
- Pedidos **En preparación** aún no tienen calificación ni tiempo de entrega.
- Pedidos **Reclamados** suelen tener calificación baja (1–3).

## Ojo con los outliers

Hay algunos pedidos empresariales con cantidades grandes (25–60 unidades). Son **ventas reales**, no errores: cumplen todas las reglas. La app no debería borrarlos automáticamente.
