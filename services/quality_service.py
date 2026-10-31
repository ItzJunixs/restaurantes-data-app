"""
quality_service.py  (Prompts 3 y 4 - Perfil y detección de problemas)
Responsabilidad: DETECTAR problemas. Nunca corrige ni elimina nada.
Todas las funciones reciben un DataFrame y lo dejan intacto.
"""
import pandas as pd

# ---------------------------------------------------------------
# Reglas del negocio (sacadas del diccionario de datos)
# ---------------------------------------------------------------
COLUMNAS_NUMERICAS = [
    "cantidad", "precio_unitario", "descuento_pct", "costo_domicilio", "propina",
    "subtotal", "total_pagado", "tiempo_preparacion_min", "tiempo_entrega_min", "calificacion",
]

# Menú oficial: plato -> categoría
MENU = {
    "Bandeja paisa": "Plato fuerte", "Ajiaco santafereño": "Plato fuerte",
    "Asado huilense": "Plato fuerte", "Sancocho de gallina": "Plato fuerte",
    "Mojarra frita": "Plato fuerte", "Lechona tolimense": "Plato fuerte",
    "Hamburguesa artesanal": "Comida rápida", "Perro caliente especial": "Comida rápida",
    "Salchipapa": "Comida rápida", "Empanadas x3": "Entrada", "Patacones con hogao": "Entrada",
    "Arepa de choclo": "Entrada", "Limonada de coco": "Bebida", "Jugo natural": "Bebida",
    "Gaseosa": "Bebida", "Cerveza nacional": "Bebida", "Postre de natas": "Postre",
    "Brownie con helado": "Postre", "Achiras con café": "Postre",
}

# Ciudad -> departamento
CIUDAD_DEPARTAMENTO = {
    "Neiva": "Huila", "Pitalito": "Huila", "Bogotá": "Cundinamarca", "Medellín": "Antioquia",
    "Cali": "Valle del Cauca", "Ibagué": "Tolima", "Bucaramanga": "Santander",
}

SEDES = ["Sede Centro Neiva", "Sede Norte Neiva", "Sede Pitalito", "Sede Chapinero", "Sede Usaquén",
         "Sede El Poblado", "Sede Granada", "Sede Ibagué", "Sede Cabecera"]

# Valores permitidos en las columnas categóricas
VALORES_VALIDOS = {
    "sede": SEDES,
    "ciudad": list(CIUDAD_DEPARTAMENTO.keys()),
    "departamento": sorted(set(CIUDAD_DEPARTAMENTO.values())),
    "plato": list(MENU.keys()),
    "canal": ["Salón", "Para llevar", "Domicilio propio", "Rappi"],
    "metodo_pago": ["Efectivo", "Tarjeta débito", "Tarjeta crédito", "Nequi", "Daviplata", "Transferencia"],
    "estado_pedido": ["Entregado", "Cancelado", "Reclamado", "En preparación"],
    "tipo_cliente": ["Ocasional", "Frecuente", "Empresarial", "Nuevo"],
    "categoria": ["Plato fuerte", "Comida rápida", "Entrada", "Bebida", "Postre"],
}

FECHA_INICIO = pd.Timestamp("2026-01-01")
FECHA_FIN = pd.Timestamp("2026-09-30")

# Columnas donde un vacío es NORMAL según el diccionario:
# - calificacion: no todos los clientes califican
# - tiempo_entrega_min: solo aplica a domicilios
# - tiempo_preparacion_min: no aplica a pedidos cancelados
COLUMNAS_OPCIONALES = ["calificacion", "tiempo_entrega_min", "tiempo_preparacion_min"]


def columnas_obligatorias(df):
    return [c for c in df.columns if c not in COLUMNAS_OPCIONALES]


def _num(df, col):
    """Convierte una columna a número SOLO para revisarla (no modifica el df)."""
    return pd.to_numeric(df[col], errors="coerce")


# ---------------------------------------------------------------
# Prompt 3: perfil general
# ---------------------------------------------------------------
def perfilar_dataset(df):
    """Devuelve un diccionario con el resumen general del dataset."""
    faltantes = df.isnull().sum()
    return {
        "filas": df.shape[0],
        "columnas": df.shape[1],
        "nombres_columnas": list(df.columns),
        "tipos": df.dtypes.astype(str),
        "faltantes_por_columna": faltantes[faltantes > 0].sort_values(ascending=False),
        "total_faltantes": int(faltantes.sum()),
        # faltantes en columnas donde el vacío SÍ es un error
        "faltantes_obligatorios": int(df[columnas_obligatorias(df)].isnull().sum().sum()),
        "duplicados": int(df.duplicated().sum()),
        "ids_repetidos": int(df["id_pedido"].duplicated().sum()) if "id_pedido" in df else 0,
        "estadisticas": df.describe(include="all").T,
    }


# ---------------------------------------------------------------
# Prompt 4: detector de problemas
# ---------------------------------------------------------------
def detectar_problemas(df):
    """
    Devuelve un diccionario:  {nombre del problema: DataFrame con los registros afectados}
    Solo se incluyen los problemas que tienen al menos un registro.
    """
    p = {}

    # --- Reglas generales ---
    p["Valores faltantes (columnas obligatorias)"] = df[df[columnas_obligatorias(df)].isnull().any(axis=1)]
    p["Filas duplicadas (copias exactas)"] = df[df.duplicated()]
    # IDs repetidos pero con información distinta (no son copias exactas)
    p["id_pedido repetido con datos distintos"] = df[
        df["id_pedido"].duplicated(keep=False) & ~df.duplicated(keep=False)
    ].sort_values("id_pedido")

    # Texto en columnas que deberían ser numéricas (ej: "$32,000", "dos", "10%")
    mascara = pd.Series(False, index=df.index)
    for col in COLUMNAS_NUMERICAS:
        mascara |= df[col].notna() & _num(df, col).isna()
    p["Valores no numéricos en columnas numéricas"] = df[mascara]

    # Categorías escritas distinto o que no existen en el catálogo
    mascara = pd.Series(False, index=df.index)
    for col, validos in VALORES_VALIDOS.items():
        mascara |= df[col].notna() & ~df[col].isin(validos)
    p["Categorías no válidas o mal escritas"] = df[mascara]

    # Fechas: deben tener formato AAAA-MM-DD y estar dentro del periodo
    fecha = pd.to_datetime(df["fecha"], format="%Y-%m-%d", errors="coerce")
    p["Fechas inválidas o fuera del periodo"] = df[
        df["fecha"].notna() & (fecha.isna() | (fecha < FECHA_INICIO) | (fecha > FECHA_FIN))
    ]

    # Horas: formato HH:MM de 24 horas
    hora_ok = df["hora"].astype("string").str.fullmatch(r"([01]\d|2[0-3]):[0-5]\d")
    p["Horas inválidas"] = df[df["hora"].notna() & ~hora_ok.fillna(False)]

    # --- Reglas del negocio ---
    cant = _num(df, "cantidad")
    p["cantidad <= 0 o no entera"] = df[(cant <= 0) | (cant % 1 > 0)]
    p["precio_unitario <= 0"] = df[_num(df, "precio_unitario") <= 0]
    desc = _num(df, "descuento_pct")
    p["descuento_pct fuera de 0 a 100"] = df[(desc < 0) | (desc > 100)]
    p["costo_domicilio o propina negativos"] = df[
        (_num(df, "costo_domicilio") < 0) | (_num(df, "propina") < 0)
    ]
    cal = _num(df, "calificacion")
    p["calificacion fuera de 1 a 5"] = df[(cal < 1) | (cal > 5) | (cal % 1 > 0)]
    p["Tiempos negativos o en cero"] = df[
        (_num(df, "tiempo_preparacion_min") <= 0) | (_num(df, "tiempo_entrega_min") <= 0)
    ]

    # --- Reglas entre columnas ---
    total_esperado = (
        _num(df, "cantidad") * _num(df, "precio_unitario") * (1 - _num(df, "descuento_pct") / 100)
        + _num(df, "costo_domicilio") + _num(df, "propina")
    )
    categoria_correcta = df["plato"].map(MENU)
    p["categoria no corresponde al plato"] = df[
        categoria_correcta.notna() & df["categoria"].notna() & (df["categoria"] != categoria_correcta)
    ]
    depto_correcto = df["ciudad"].map(CIUDAD_DEPARTAMENTO)
    p["departamento no corresponde a la ciudad"] = df[
        depto_correcto.notna() & df["departamento"].notna() & (df["departamento"] != depto_correcto)
    ]
    p["total_pagado no cuadra con la fórmula"] = df[(total_esperado - _num(df, "total_pagado")).abs() > 1]
    p["Pedido cancelado con calificación o entrega"] = df[
        (df["estado_pedido"] == "Cancelado")
        & (df["calificacion"].notna() | df["tiempo_entrega_min"].notna())
    ]

    # Quitamos los problemas que no tienen registros
    return {nombre: registros for nombre, registros in p.items() if len(registros) > 0}


def detectar_outliers(df, columna="total_pagado"):
    """
    Outliers con el método IQR (diapositiva 19).
    Atípico NO significa incorrecto: solo se marcan para revisión.
    """
    valores = _num(df, columna)
    q1, q3 = valores.quantile(0.25), valores.quantile(0.75)
    iqr = q3 - q1
    lim_inf, lim_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = df[(valores < lim_inf) | (valores > lim_sup)]
    return outliers, lim_inf, lim_sup
