# 🍽️ Restaurantes Data Quality

App en Streamlit que **carga, analiza, detecta, corrige, grafica y exporta** el dataset de pedidos de la cadena de restaurantes "Sazón Colombiana".

Minería de Datos · Ingeniería de Sistemas · CORHUILA

---

## Cómo ejecutarla (desde Visual Studio Code)

Abre una terminal en la carpeta `restaurantes-data-app` y ejecuta:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```

Se abre en el navegador. En la barra lateral puedes subir el CSV o pulsar **"Usar dataset de ejemplo"**.

---

## Estructura (arquitectura por capas)

```
restaurantes-data-app/
├── app.py                     ← interfaz Streamlit y navegación (sin lógica de datos)
├── requirements.txt
├── data/
│   ├── pedidos_restaurantes_raw.csv            ← dataset sucio
│   └── DICCIONARIO_DATOS_PEDIDOS_RESTAURANTES.md
└── services/
    ├── data_loader.py         ← carga el CSV            (Prompt 2)
    ├── quality_service.py     ← DETECTA problemas       (Prompts 3 y 4)
    ├── cleaning_service.py    ← CORRIGE lo confirmado   (Prompt 6)
    └── chart_service.py       ← prepara los gráficos    (Prompt 7)
```

**Idea clave:** cada archivo tiene una sola responsabilidad.
- `quality_service` **nunca** modifica los datos: solo encuentra problemas y devuelve los registros como evidencia.
- `cleaning_service` **nunca** decide solo: cada función recibe un DataFrame y devuelve una **copia** modificada; `app.py` pide confirmación antes de llamarla.
- `app.py` no tiene reglas ni cálculos: solo llama funciones y muestra resultados.

---

## Secciones de la app

| Sección | Qué hace | Diapositiva |
|---|---|---|
| 📁 Cargar | Sube el CSV y muestra las primeras 10 filas | 10–11 |
| 🔎 Diagnóstico | Filas, columnas, tipos, faltantes, duplicados, IDs repetidos, estadísticas | 12–13 |
| ⚠️ Calidad de datos | Tabla de problemas + un expander por problema con los registros exactos. Outliers por IQR (solo se marcan) | 14–17, 19 |
| 🧹 Limpieza | 9 pasos; cada uno pide confirmación y queda en el historial | 18, 20–21 |
| 📊 Visualización | KPIs + 13 gráficos de Plotly en 4 pestañas | 23–25 |
| 💾 Exportar | Métricas finales y descarga de `dataset_restaurantes_limpio.csv` | 22, 26–27 |

---

## Problemas que detecta

**Reglas generales:** valores faltantes (solo en columnas obligatorias), filas duplicadas, id_pedido repetido con datos distintos, texto en columnas numéricas, categorías mal escritas, fechas inválidas o fuera del periodo, horas inválidas.

**Reglas del negocio:** cantidad ≤ 0 o decimal, precio ≤ 0, descuento fuera de 0–100, domicilio o propina negativos, calificación fuera de 1–5, tiempos negativos.

**Reglas entre columnas:** categoría que no corresponde al plato, departamento que no corresponde a la ciudad, total_pagado que no cuadra con la fórmula, pedido cancelado con calificación.

> ¿Por qué no todos los vacíos son error? Según el diccionario, `calificacion` puede estar vacía (no todos califican), `tiempo_entrega_min` solo aplica a domicilios y `tiempo_preparacion_min` no aplica a cancelados.

---

## Orden recomendado de limpieza (y por qué)

| Paso | Decisión | Justificación |
|---|---|---|
| 1. Duplicados exactos | **Eliminar** | Son el mismo pedido registrado dos veces; inflan las ventas. |
| 2. IDs repetidos | **Conservar el primero** | Un id_pedido identifica una sola transacción. |
| 3. Normalizar texto | **Estandarizar** | "BOGOTA", " bogotá " y "Bogota" son la misma ciudad. Va antes que todo lo demás para no borrar datos que solo estaban mal escritos. |
| 4. Convertir tipos | **Corregir formato** | "$32,000" → 32000, "15/03/2026" → 2026-03-15. Lo que no se puede interpretar ("dos", "gratis") queda vacío. |
| 5. Registros inválidos | **Eliminar** | Cantidades negativas, descuentos de 150 %, fechas imposibles: violan reglas del negocio y no hay forma segura de adivinar el valor real. |
| 6. Catálogo | **Recalcular** | La categoría se deduce del plato y el departamento de la ciudad. |
| 7. Cancelados | **Corregir** | Un pedido cancelado no puede tener calificación. |
| 8. Faltantes | **Imputar o eliminar** | Mediana para números (no le afectan los outliers), moda para texto, y eliminar filas si falta algo clave como la fecha o el plato. |
| 9. Totales | **Recalcular (al final)** | subtotal y total se derivan de otras columnas; si se calculan antes de imputar, quedan mal. |

### Outliers: no se borran
Hay pedidos empresariales de 25–60 unidades. El método IQR los marca como atípicos, pero cumplen todas las reglas: **son ventas reales**. La app los muestra para revisión y no los elimina.

---

## Resultado con el dataset de ejemplo

| Indicador | Antes | Después |
|---|---|---|
| Filas | 2.056 | 1.610 |
| Duplicados exactos | 35 | 0 |
| Faltantes en columnas obligatorias | 322 | 0 |
| Casos de reglas inválidas | ~1.800 | 0 |

*(Los números pueden variar un poco según las estrategias que elijas en el paso 8.)*

> No es "100 % calidad real": son **problemas detectados resueltos**. Pueden existir errores que las reglas del sistema no conocen.

---

## Transferir: ¿qué cambiar para usarla con otro negocio?

Casi todo lo específico del negocio está en las constantes del inicio de `quality_service.py` (`MENU`, `CIUDAD_DEPARTAMENTO`, `VALORES_VALIDOS`, `COLUMNAS_NUMERICAS`, `COLUMNAS_OPCIONALES`, fechas del periodo) y en `CORRECCIONES` de `cleaning_service.py`. Cambiando esas listas y los nombres de columnas, la misma arquitectura sirve para otro dataset.
