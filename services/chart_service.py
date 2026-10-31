"""
chart_service.py  (Prompt 7 - Módulo de visualización)
Responsabilidad: preparar los datos (groupby, sort...) y devolver figuras de Plotly.
app.py solo las muestra con st.plotly_chart.
"""
import pandas as pd
import plotly.express as px

COLOR = "#0B8A4C"  # verde institucional


def preparar_datos(df, excluir_cancelados=True):
    """Datos base para los gráficos: un pedido cancelado no es una venta real."""
    datos = df.dropna(subset=["total_pagado"])
    if excluir_cancelados:
        datos = datos[datos["estado_pedido"] != "Cancelado"]
    return datos


def _barras(tabla, x, y, titulo, etiqueta_x):
    """Barra horizontal ordenada de mayor a menor (para rankings)."""
    fig = px.bar(tabla, x=x, y=y, orientation="h", title=titulo,
                 text_auto=".3s", labels={x: etiqueta_x, y: ""},
                 color_discrete_sequence=[COLOR])
    fig.update_layout(yaxis={"autorange": "reversed"})
    return fig


def _ventas_por(df, columna, titulo):
    """Suma total_pagado agrupando por una columna categórica."""
    tabla = (df.groupby(columna, as_index=False)["total_pagado"].sum()
               .sort_values("total_pagado", ascending=False))
    return _barras(tabla, "total_pagado", columna, titulo, "Ventas (COP)")


# ---------------- Rankings (barras) ----------------
def top_ciudades_cantidad(df):
    top = (df.groupby("ciudad", as_index=False)["cantidad"].sum()
             .sort_values("cantidad", ascending=False).head(10))
    return _barras(top, "cantidad", "ciudad", "Top ciudades por unidades vendidas", "Unidades")


def top_ciudades_facturacion(df):
    top = (df.groupby("ciudad", as_index=False)["total_pagado"].sum()
             .sort_values("total_pagado", ascending=False).head(10))
    return _barras(top, "total_pagado", "ciudad", "Top ciudades por facturación", "Ventas (COP)")


def ventas_por_categoria(df):
    return _ventas_por(df, "categoria", "Ventas por categoría del menú")


def ventas_por_canal(df):
    return _ventas_por(df, "canal", "Ventas por canal")


def ventas_por_tipo_cliente(df):
    return _ventas_por(df, "tipo_cliente", "Ventas por tipo de cliente")


def ventas_por_sede(df):
    return _ventas_por(df, "sede", "Ventas por sede")


def top_platos(df):
    top = (df.groupby("plato", as_index=False)["cantidad"].sum()
             .sort_values("cantidad", ascending=False).head(10))
    return _barras(top, "cantidad", "plato", "Top 10 platos más vendidos", "Unidades")


# ---------------- Participación (pie) ----------------
def participacion_metodo_pago(df):
    tabla = df["metodo_pago"].value_counts().reset_index()
    tabla.columns = ["metodo_pago", "pedidos"]
    return px.pie(tabla, names="metodo_pago", values="pedidos", hole=0.4,
                  title="Participación de los métodos de pago")


# ---------------- Tendencia (líneas) ----------------
def tendencia_mensual(df):
    tabla = df.dropna(subset=["fecha"]).copy()
    tabla["mes"] = pd.to_datetime(tabla["fecha"]).dt.to_period("M").dt.to_timestamp()
    tabla = tabla.groupby("mes", as_index=False)["total_pagado"].sum()
    fig = px.line(tabla, x="mes", y="total_pagado", markers=True,
                  title="Tendencia mensual de ventas",
                  labels={"mes": "Mes", "total_pagado": "Ventas (COP)"},
                  color_discrete_sequence=[COLOR])
    return fig


def pedidos_por_hora(df):
    tabla = df.dropna(subset=["hora"]).copy()
    tabla["hora_del_dia"] = tabla["hora"].str[:2].astype(int)
    tabla = tabla.groupby("hora_del_dia", as_index=False).size()
    return px.bar(tabla, x="hora_del_dia", y="size", title="Pedidos por hora del día",
                  labels={"hora_del_dia": "Hora", "size": "Pedidos"},
                  color_discrete_sequence=[COLOR])


# ---------------- Relación y dispersión ----------------
def scatter_precio_cantidad(df):
    return px.scatter(df, x="precio_unitario", y="cantidad", color="categoria",
                      title="Precio unitario vs cantidad",
                      labels={"precio_unitario": "Precio unitario (COP)", "cantidad": "Cantidad"},
                      hover_data=["id_pedido", "plato"])


def boxplot_total_categoria(df):
    return px.box(df, x="categoria", y="total_pagado", points="outliers",
                  title="Distribución del total pagado por categoría",
                  labels={"categoria": "Categoría", "total_pagado": "Total pagado (COP)"},
                  color_discrete_sequence=[COLOR])


def histograma_tiempo_entrega(df):
    return px.histogram(df.dropna(subset=["tiempo_entrega_min"]), x="tiempo_entrega_min", nbins=30,
                        title="Distribución del tiempo de entrega (domicilios)",
                        labels={"tiempo_entrega_min": "Minutos"},
                        color_discrete_sequence=[COLOR])
