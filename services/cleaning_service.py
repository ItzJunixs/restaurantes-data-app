"""
cleaning_service.py  (Prompt 6 - Servicio de limpieza)
Responsabilidad: APLICAR correcciones que el usuario ya confirmó en la interfaz.
Regla: cada función recibe un DataFrame y devuelve una COPIA modificada
(el DataFrame original nunca se toca).
"""
import re
import unicodedata

import numpy as np
import pandas as pd

from services.quality_service import (CIUDAD_DEPARTAMENTO, COLUMNAS_NUMERICAS, MENU, SEDES,
                                      VALORES_VALIDOS)

COLUMNAS_DINERO = ["precio_unitario", "costo_domicilio", "propina", "subtotal", "total_pagado"]

# Errores de escritura conocidos que no se arreglan solo con mayúsculas/tildes.
# La clave se escribe ya "normalizada": minúsculas, sin tildes y sin espacios extra.
CORRECCIONES = {
    "canal": {"salon": "Salón", "domicilio": "Domicilio propio", "rappi app": "Rappi"},
    "metodo_pago": {"efectvo": "Efectivo", "t. debito": "Tarjeta débito", "credito": "Tarjeta crédito",
                    "davi plata": "Daviplata", "transf": "Transferencia"},
    "estado_pedido": {"entregad0": "Entregado", "cancel": "Cancelado",
                      "con reclamo": "Reclamado", "preparando": "En preparación"},
    "tipo_cliente": {"frecuent": "Frecuente", "empresa": "Empresarial", "ocacional": "Ocasional"},
    "categoria": {"bebidas": "Bebida", "postres": "Postre", "rapida": "Comida rápida"},
    "plato": {"bandeja paiza": "Bandeja paisa", "salchi papa": "Salchipapa",
              "hamburgesa artesanal": "Hamburguesa artesanal"},
    # 'Chapinero' -> 'Sede Chapinero' (a veces escriben la sede sin la palabra "Sede")
    "sede": {s.lower().replace("sede ", "").replace("é", "e"): s for s in SEDES},
}


# ---------------------------------------------------------------
# Duplicados
# ---------------------------------------------------------------
def eliminar_duplicados(df):
    """Elimina las filas que son copias exactas. Devuelve (df_nuevo, filas_eliminadas)."""
    nuevo = df.drop_duplicates()
    return nuevo, len(df) - len(nuevo)


def resolver_ids_repetidos(df):
    """Si un id_pedido aparece varias veces, conserva solo el primer registro."""
    nuevo = df.drop_duplicates(subset="id_pedido", keep="first")
    return nuevo, len(df) - len(nuevo)


# ---------------------------------------------------------------
# Normalización de texto (diapositiva 18)
# ---------------------------------------------------------------
def _clave(texto):
    """'  BOGOTA ' -> 'bogota'   (minúsculas, sin tildes, sin espacios de sobra)"""
    if pd.isna(texto):
        return texto
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().split())


def normalizar_texto(df, columnas):
    """
    Lleva cada valor a su forma oficial del catálogo.
    Ej: 'BOGOTA', ' bogotá ', 'Bogota'  ->  'Bogotá'
    Los valores que no se reconocen se dejan como están (para revisarlos a mano).
    """
    nuevo = df.copy()
    for col in columnas:
        # 1. diccionario  clave -> valor oficial
        mapa = {_clave(v): v for v in VALORES_VALIDOS.get(col, [])}
        mapa.update(CORRECCIONES.get(col, {}))
        # 2. aplicar: si la clave está en el mapa uso el valor oficial; si no, solo quito espacios
        claves = nuevo[col].map(_clave)
        nuevo[col] = claves.map(mapa).fillna(nuevo[col].str.strip())
    return nuevo


# ---------------------------------------------------------------
# Conversión de tipos (texto -> número / fecha / hora)
# ---------------------------------------------------------------
def _a_dinero(valor):
    """'$32,000' / '32.000' / '32000 COP' / '59400.0'  ->  32000.0   ('gratis' -> NaN)"""
    if pd.isna(valor):
        return np.nan
    s = str(valor).replace("$", "").replace("COP", "").replace(" ", "")
    if re.fullmatch(r"-?\d{1,3}([.,]\d{3})+", s):  # tiene separador de miles
        s = s.replace(".", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def _a_numero(valor):
    """'10%' -> 10   '4,5' -> 4.5   'dos' -> NaN"""
    if pd.isna(valor):
        return np.nan
    s = str(valor).replace("%", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def _a_hora(valor):
    """'7:5' -> '07:05'   '13h20' -> '13:20'   '25:10' -> NaN"""
    if pd.isna(valor):
        return np.nan
    m = re.fullmatch(r"(\d{1,2})[:h](\d{1,2})", str(valor).strip())
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    return np.nan


def convertir_tipos(df):
    """
    Convierte las columnas a su tipo correcto. Lo que no se puede interpretar queda en NaN.
    Devuelve (df_nuevo, cuantos_valores_quedaron_en_NaN).
    """
    nuevo = df.copy()
    faltantes_antes = int(nuevo.isnull().sum().sum())

    for col in COLUMNAS_NUMERICAS:
        convertidor = _a_dinero if col in COLUMNAS_DINERO else _a_numero
        nuevo[col] = nuevo[col].map(convertidor).astype(float)

    # Fechas: probamos varios formatos y nos quedamos con el primero que funcione
    fechas = pd.Series(pd.NaT, index=nuevo.index)
    for formato in ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d", "%d-%b-%Y"]:
        fechas = fechas.fillna(pd.to_datetime(nuevo["fecha"], format=formato, errors="coerce"))
    nuevo["fecha"] = fechas

    nuevo["hora"] = nuevo["hora"].map(_a_hora)

    nuevos_nan = int(nuevo.isnull().sum().sum()) - faltantes_antes
    return nuevo, nuevos_nan


# ---------------------------------------------------------------
# Valores faltantes
# ---------------------------------------------------------------
def completar_faltantes(df, columna, estrategia, valor=None):
    """
    estrategia: 'Mediana', 'Moda', 'Valor fijo' o 'Eliminar filas'.
    Devuelve (df_nuevo, registros_afectados).
    """
    nuevo = df.copy()
    n = int(nuevo[columna].isnull().sum())
    if estrategia == "Eliminar filas":
        nuevo = nuevo[nuevo[columna].notna()]
    elif estrategia == "Mediana":
        nuevo[columna] = nuevo[columna].fillna(pd.to_numeric(nuevo[columna], errors="coerce").median())
    elif estrategia == "Moda":
        nuevo[columna] = nuevo[columna].fillna(nuevo[columna].mode()[0])
    elif estrategia == "Valor fijo":
        nuevo[columna] = nuevo[columna].fillna(valor)
    return nuevo, n


# ---------------------------------------------------------------
# Corregir o eliminar registros
# ---------------------------------------------------------------
def eliminar_registros(df, indices):
    """Elimina las filas cuyos índices el usuario seleccionó."""
    nuevo = df.drop(index=[i for i in indices if i in df.index])
    return nuevo, len(df) - len(nuevo)


def corregir_con_catalogo(df):
    """
    La categoría se deduce del plato (menú) y el departamento de la ciudad.
    Si el plato o la ciudad no se reconocen, se deja el valor que había.
    """
    nuevo = df.copy()
    nuevo["categoria"] = nuevo["plato"].map(MENU).fillna(nuevo["categoria"])
    nuevo["departamento"] = nuevo["ciudad"].map(CIUDAD_DEPARTAMENTO).fillna(nuevo["departamento"])
    return nuevo


def recalcular_totales(df):
    """Recalcula subtotal y total_pagado con las fórmulas del diccionario."""
    nuevo = df.copy()
    nuevo["subtotal"] = nuevo["cantidad"] * nuevo["precio_unitario"]
    nuevo["total_pagado"] = (
        nuevo["subtotal"] * (1 - nuevo["descuento_pct"] / 100)
        + nuevo["costo_domicilio"] + nuevo["propina"]
    ).round(0)
    return nuevo


def corregir_cancelados(df):
    """Un pedido cancelado no puede tener calificación ni tiempo de entrega: se borran esos valores."""
    nuevo = df.copy()
    cancelados = nuevo["estado_pedido"] == "Cancelado"
    nuevo.loc[cancelados, ["calificacion", "tiempo_entrega_min", "tiempo_preparacion_min"]] = np.nan
    return nuevo, int(cancelados.sum())
