"""
app.py — Interfaz Streamlit (solo interfaz y navegación).
Toda la lógica vive en services/: aquí solo se llaman funciones y se muestran resultados.

Ejecutar:  python -m streamlit run app.py
"""
import pandas as pd
import streamlit as st

from services.data_loader import cargar_csv
from services import quality_service as calidad
from services import cleaning_service as limpieza
from services import chart_service as graficos

st.set_page_config(page_title="Restaurantes Data Quality", page_icon="🍽️", layout="wide")

DATASET_EJEMPLO = "data/pedidos_restaurantes_raw.csv"
COLUMNAS_TEXTO = list(calidad.VALORES_VALIDOS.keys())

# ---------------------------------------------------------------
# Estado de la sesión: df_original (nunca se toca), df (versión actual), historial
# ---------------------------------------------------------------
for clave, inicial in {"df_original": None, "df": None, "historial": [],
                       "nombre": None, "mensaje": None}.items():
    if clave not in st.session_state:
        st.session_state[clave] = inicial


def iniciar(df, nombre):
    st.session_state.df_original = df
    st.session_state.df = df.copy()
    st.session_state.nombre = nombre
    st.session_state.historial = [f"Dataset cargado: {nombre} ({len(df)} filas)"]


def aplicar(nuevo_df, descripcion, clave_confirmacion):
    """Guarda el cambio, lo registra en el historial y recarga la página."""
    st.session_state.df = nuevo_df
    st.session_state.historial.append(descripcion)
    st.session_state.mensaje = descripcion
    st.session_state.pop(clave_confirmacion, None)  # desmarca el checkbox de confirmación
    st.rerun()


def boton_confirmado(texto_boton, clave):
    """Ninguna corrección se aplica sin que el usuario la confirme primero."""
    ok = st.checkbox("Revisé el cambio y quiero aplicarlo", key=f"conf_{clave}")
    return st.button(texto_boton, key=clave, disabled=not ok, type="primary"), f"conf_{clave}"


def tipos_convertidos(df):
    return pd.api.types.is_numeric_dtype(df["total_pagado"])


# ---------------------------------------------------------------
# Barra lateral: carga, navegación e historial
# ---------------------------------------------------------------
with st.sidebar:
    st.title("🍽️ Restaurantes Data Quality")
    st.caption("Cadena Sazón Colombiana · Minería de Datos")

    archivo = st.file_uploader("Carga el CSV de pedidos", type=["csv"])
    if archivo is not None and archivo.name != st.session_state.nombre:
        df, error = cargar_csv(archivo)
        if error:
            st.error(error)
        else:
            iniciar(df, archivo.name)

    if st.session_state.df is None and st.button("Usar dataset de ejemplo"):
        with open(DATASET_EJEMPLO, "rb") as f:
            df, error = cargar_csv(f)
        iniciar(df, "pedidos_restaurantes_raw.csv")
        st.rerun()

    seccion = st.radio("Secciones", ["📁 Cargar", "🔎 Diagnóstico", "⚠️ Calidad de datos",
                                     "🧹 Limpieza", "📊 Visualización", "💾 Exportar"])

    if st.session_state.historial:
        st.subheader("Historial de cambios")
        for i, paso in enumerate(st.session_state.historial, start=1):
            st.write(f"{i}. {paso}")

if st.session_state.df is None:
    st.title("🍽️ Restaurantes Data Quality")
    st.info("Carga un archivo CSV en la barra lateral (o usa el dataset de ejemplo) para comenzar.")
    st.stop()

df = st.session_state.df
if st.session_state.mensaje:
    st.success(f"✅ {st.session_state.mensaje}")
    st.session_state.mensaje = None


# ===============================================================
# 1. CARGAR
# ===============================================================
if seccion == "📁 Cargar":
    st.header("📁 Dataset cargado")
    st.write(f"Archivo: **{st.session_state.nombre}** · {df.shape[0]} filas · {df.shape[1]} columnas")
    st.subheader("Primeras 10 filas")
    st.dataframe(df.head(10), width="stretch")


# ===============================================================
# 2. DIAGNÓSTICO (perfil general)
# ===============================================================
elif seccion == "🔎 Diagnóstico":
    st.header("🔎 Diagnóstico general")
    perfil = calidad.perfilar_dataset(df)
    problemas = calidad.detectar_problemas(df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Filas", perfil["filas"])
    c2.metric("Columnas", perfil["columnas"])
    c3.metric("Valores faltantes", perfil["total_faltantes"])
    c4, c5, c6 = st.columns(3)
    c4.metric("Duplicados completos", perfil["duplicados"])
    c5.metric("IDs repetidos", perfil["ids_repetidos"])
    c6.metric("Tipos de problema detectados", len(problemas))

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Tipos de datos")
        st.dataframe(perfil["tipos"].rename("tipo"), width="stretch")
    with col_b:
        st.subheader("Faltantes por columna")
        st.dataframe(perfil["faltantes_por_columna"].rename("faltantes"), width="stretch")
        st.caption("Ojo: en calificacion, tiempo_entrega_min y tiempo_preparacion_min "
                   "un vacío puede ser normal (ver diccionario de datos).")

    with st.expander("Estadísticas descriptivas"):
        st.dataframe(perfil["estadisticas"].astype(str), width="stretch")


# ===============================================================
# 3. CALIDAD DE DATOS (un problema -> una evidencia)
# ===============================================================
elif seccion == "⚠️ Calidad de datos":
    st.header("⚠️ Calidad de datos")
    problemas = calidad.detectar_problemas(df)

    if not problemas:
        st.success("No quedan problemas detectados por las reglas del sistema.")
    else:
        resumen = pd.DataFrame({"Problema": list(problemas.keys()),
                                "Casos": [len(r) for r in problemas.values()]})
        st.dataframe(resumen, hide_index=True, width="stretch")

        st.subheader("Evidencia por problema")
        for nombre, registros in problemas.items():
            with st.expander(f"{nombre} — {len(registros)} registros"):
                st.dataframe(registros, width="stretch")

    st.subheader("Valores atípicos en total_pagado (método IQR)")
    if tipos_convertidos(df):
        outliers, lim_inf, lim_sup = calidad.detectar_outliers(df)
        st.write(f"Rango normal: **{lim_inf:,.0f}** a **{lim_sup:,.0f}** COP · "
                 f"**{len(outliers)}** pedidos fuera del rango.")
        st.warning("Atípico no significa incorrecto. Un pedido empresarial grande puede ser una venta real. "
                   "Revisa el contexto antes de decidir.")
        st.dataframe(outliers, width="stretch")
    else:
        st.info("Primero convierte los tipos de datos en la sección Limpieza (paso 4) "
                "para poder calcular outliers.")


# ===============================================================
# 4. LIMPIEZA (nada se aplica sin confirmación)
# ===============================================================
elif seccion == "🧹 Limpieza":
    st.header("🧹 Limpieza controlada")
    st.caption("Sugerencia: sigue los pasos en orden. Cada cambio queda en el historial.")

    # Paso 1
    with st.expander("1. Eliminar filas duplicadas (copias exactas)"):
        n = int(df.duplicated().sum())
        st.write(f"Hay **{n}** filas que son copia exacta de otra.")
        aplicar_btn, clave = boton_confirmado("Eliminar duplicados", "dup")
        if aplicar_btn:
            nuevo, n = limpieza.eliminar_duplicados(df)
            aplicar(nuevo, f"Eliminados {n} duplicados exactos", clave)

    # Paso 2
    with st.expander("2. Resolver id_pedido repetidos"):
        n = int(df["id_pedido"].duplicated().sum())
        st.write(f"Hay **{n}** registros con un id_pedido que ya apareció antes. "
                 "Decisión: conservar el primer registro de cada id.")
        aplicar_btn, clave = boton_confirmado("Conservar solo el primer registro", "ids")
        if aplicar_btn:
            nuevo, n = limpieza.resolver_ids_repetidos(df)
            aplicar(nuevo, f"Eliminados {n} registros con id_pedido repetido", clave)

    # Paso 3
    with st.expander("3. Normalizar texto (mayúsculas, tildes, espacios, errores conocidos)"):
        columnas = st.multiselect("Columnas a normalizar", COLUMNAS_TEXTO, default=COLUMNAS_TEXTO)
        ver = st.selectbox("Ver valores actuales de:", COLUMNAS_TEXTO)
        st.dataframe(df[ver].value_counts(dropna=False), width="stretch")
        aplicar_btn, clave = boton_confirmado("Normalizar texto", "texto")
        if aplicar_btn and columnas:
            nuevo = limpieza.normalizar_texto(df, columnas)
            aplicar(nuevo, f"Normalizado texto en: {', '.join(columnas)}", clave)

    # Paso 4
    with st.expander("4. Convertir tipos de datos (números, fechas y horas)"):
        st.write("Convierte '$32,000' → 32000, '10%' → 10, '15/03/2026' → 2026-03-15, '7:5' → 07:05. "
                 "Lo que no se pueda interpretar (ej: 'dos', 'gratis', '25:10') queda vacío para tratarlo después.")
        if tipos_convertidos(df):
            st.info("Los tipos ya fueron convertidos.")
        else:
            aplicar_btn, clave = boton_confirmado("Convertir tipos", "tipos")
            if aplicar_btn:
                nuevo, n = limpieza.convertir_tipos(df)
                aplicar(nuevo, f"Convertidos tipos de datos ({n} valores no interpretables quedaron vacíos)", clave)

    # Paso 5
    with st.expander("5. Eliminar registros con problemas"):
        problemas = calidad.detectar_problemas(df)
        if problemas:
            problema = st.selectbox("Problema", list(problemas.keys()))
            registros = problemas[problema]
            st.dataframe(registros, width="stretch")
            seleccion = st.multiselect(
                "Registros a eliminar", list(registros.index), default=list(registros.index),
                format_func=lambda i: f"{df.at[i, 'id_pedido']} (fila {i})")
            aplicar_btn, clave = boton_confirmado("Eliminar registros seleccionados", "borrar")
            if aplicar_btn:
                nuevo, n = limpieza.eliminar_registros(df, seleccion)
                aplicar(nuevo, f"Eliminados {n} registros por: {problema}", clave)
        else:
            st.success("No hay problemas pendientes.")

    # Paso 6
    with st.expander("6. Corregir categoría y departamento con el catálogo"):
        st.write("La categoría se toma del menú según el plato, y el departamento según la ciudad. "
                 "Ej: Bandeja paisa siempre es Plato fuerte; Neiva siempre es Huila.")
        aplicar_btn, clave = boton_confirmado("Corregir con catálogo", "catalogo")
        if aplicar_btn:
            aplicar(limpieza.corregir_con_catalogo(df), "Corregidas categoría y departamento con el catálogo", clave)

    # Paso 7
    with st.expander("7. Corregir pedidos cancelados"):
        st.write("Un pedido cancelado no puede tener calificación ni tiempos: esos valores se dejan vacíos.")
        aplicar_btn, clave = boton_confirmado("Corregir cancelados", "cancel")
        if aplicar_btn:
            nuevo, n = limpieza.corregir_cancelados(df)
            aplicar(nuevo, f"Corregidos {n} pedidos cancelados", clave)

    # Paso 8
    with st.expander("8. Completar valores faltantes"):
        st.caption("subtotal y total_pagado no se imputan: se recalculan en el paso 9.")
        obligatorias = [c for c in calidad.columnas_obligatorias(df) if c not in ("subtotal", "total_pagado")]
        con_faltantes = [c for c in obligatorias if df[c].isnull().any()]
        if not con_faltantes:
            st.success("No hay faltantes en columnas obligatorias.")
        else:
            columna = st.selectbox("Columna", con_faltantes,
                                   format_func=lambda c: f"{c} ({df[c].isnull().sum()} faltantes)")
            if pd.api.types.is_numeric_dtype(df[columna]):
                opciones = ["Mediana", "Valor fijo", "Eliminar filas"]
            else:
                opciones = ["Moda", "Valor fijo", "Eliminar filas"]
            estrategia = st.radio("Estrategia", opciones, horizontal=True)
            valor = None
            if estrategia == "Valor fijo":
                valor = st.text_input("Valor para rellenar", "Sin dato")
                if pd.api.types.is_numeric_dtype(df[columna]):
                    valor = pd.to_numeric(valor, errors="coerce")
            aplicar_btn, clave = boton_confirmado("Aplicar estrategia", "faltantes")
            if aplicar_btn:
                nuevo, n = limpieza.completar_faltantes(df, columna, estrategia, valor)
                aplicar(nuevo, f"Faltantes en {columna}: {estrategia} ({n} registros)", clave)

    # Paso 9
    with st.expander("9. Recalcular subtotal y total_pagado (hazlo al final)"):
        st.write("subtotal = cantidad × precio_unitario  ·  "
                 "total = subtotal × (1 − descuento/100) + domicilio + propina")
        if not tipos_convertidos(df):
            st.info("Primero convierte los tipos (paso 4).")
        else:
            aplicar_btn, clave = boton_confirmado("Recalcular totales", "totales")
            if aplicar_btn:
                aplicar(limpieza.recalcular_totales(df), "Recalculados subtotal y total_pagado", clave)

    st.divider()
    if st.button("↩️ Restaurar dataset original"):
        iniciar(st.session_state.df_original, st.session_state.nombre)
        st.session_state.historial.append("Dataset restaurado al original")
        st.rerun()


# ===============================================================
# 5. VISUALIZACIÓN
# ===============================================================
elif seccion == "📊 Visualización":
    st.header("📊 Análisis para la toma de decisiones")
    if not tipos_convertidos(df):
        st.warning("Primero convierte los tipos de datos (Limpieza → paso 4).")
        st.stop()

    pendientes = sum(len(r) for r in calidad.detectar_problemas(df).values())
    if pendientes:
        st.warning(f"Aún hay {pendientes} casos de calidad pendientes: los gráficos pueden estar sesgados.")

    excluir = st.checkbox("Excluir pedidos cancelados de las ventas", value=True)
    datos = graficos.preparar_datos(df, excluir)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ventas totales", f"${datos['total_pagado'].sum():,.0f}")
    k2.metric("Pedidos", f"{len(datos):,}")
    k3.metric("Ticket promedio", f"${datos['total_pagado'].mean():,.0f}")
    k4.metric("Calificación promedio", f"{datos['calificacion'].mean():.2f} / 5")

    t1, t2, t3, t4 = st.tabs(["Dónde vendemos", "Qué vendemos", "Cuándo vendemos", "Distribución"])
    with t1:
        a, b = st.columns(2)
        a.plotly_chart(graficos.top_ciudades_facturacion(datos), width="stretch")
        b.plotly_chart(graficos.top_ciudades_cantidad(datos), width="stretch")
        a.plotly_chart(graficos.ventas_por_sede(datos), width="stretch")
        b.plotly_chart(graficos.ventas_por_canal(datos), width="stretch")
    with t2:
        a, b = st.columns(2)
        a.plotly_chart(graficos.ventas_por_categoria(datos), width="stretch")
        b.plotly_chart(graficos.top_platos(datos), width="stretch")
        a.plotly_chart(graficos.ventas_por_tipo_cliente(datos), width="stretch")
        b.plotly_chart(graficos.participacion_metodo_pago(datos), width="stretch")
    with t3:
        st.plotly_chart(graficos.tendencia_mensual(datos), width="stretch")
        st.plotly_chart(graficos.pedidos_por_hora(datos), width="stretch")
    with t4:
        st.plotly_chart(graficos.boxplot_total_categoria(datos), width="stretch")
        a, b = st.columns(2)
        a.plotly_chart(graficos.scatter_precio_cantidad(datos), width="stretch")
        b.plotly_chart(graficos.histograma_tiempo_entrega(datos), width="stretch")


# ===============================================================
# 6. EXPORTAR
# ===============================================================
elif seccion == "💾 Exportar":
    st.header("💾 Exportar dataset limpio")
    perfil = calidad.perfilar_dataset(df)
    problemas = calidad.detectar_problemas(df)

    c1, c2 = st.columns(2)
    c1.metric("Filas finales", perfil["filas"], delta=perfil["filas"] - len(st.session_state.df_original))
    c2.metric("Columnas finales", perfil["columnas"])
    c3, c4, c5 = st.columns(3)
    c3.metric("Faltantes pendientes (obligatorios)", perfil["faltantes_obligatorios"])
    c4.metric("Duplicados pendientes", perfil["duplicados"])
    c5.metric("Casos de reglas pendientes", sum(len(r) for r in problemas.values()))

    if problemas:
        st.warning("Todavía hay problemas detectados. Puedes exportar, pero revisa la sección Calidad.")
    else:
        st.success("Todos los problemas detectados fueron resueltos. "
                   "(Aún pueden existir errores que las reglas del sistema no conocen.)")

    # Se exporta el estado ACTUAL, no el original
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Descargar dataset limpio", data=csv,
                       file_name="dataset_restaurantes_limpio.csv", mime="text/csv", type="primary")
