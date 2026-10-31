"""
Generador del dataset simulado: Cadena de restaurantes "Sazón Colombiana".
Produce:
  - pedidos_restaurantes_raw.csv            (con errores intencionales)
  - pedidos_restaurantes_limpio_referencia.csv (versión limpia, para validar la app)
  - mapa_errores.csv                        (qué error se metió en qué fila)
Reproducible: semilla fija.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(2026)
N = 2000

# ---------------- Catálogos ----------------
SEDES = {  # sede: (ciudad, departamento, peso)
    "Sede Centro Neiva": ("Neiva", "Huila", 0.18),
    "Sede Norte Neiva": ("Neiva", "Huila", 0.12),
    "Sede Pitalito": ("Pitalito", "Huila", 0.08),
    "Sede Chapinero": ("Bogotá", "Cundinamarca", 0.16),
    "Sede Usaquén": ("Bogotá", "Cundinamarca", 0.10),
    "Sede El Poblado": ("Medellín", "Antioquia", 0.12),
    "Sede Granada": ("Cali", "Valle del Cauca", 0.10),
    "Sede Ibagué": ("Ibagué", "Tolima", 0.08),
    "Sede Cabecera": ("Bucaramanga", "Santander", 0.06),
}
MENU = {  # plato: (categoria, precio)
    "Bandeja paisa": ("Plato fuerte", 32000),
    "Ajiaco santafereño": ("Plato fuerte", 28000),
    "Asado huilense": ("Plato fuerte", 35000),
    "Sancocho de gallina": ("Plato fuerte", 27000),
    "Mojarra frita": ("Plato fuerte", 38000),
    "Lechona tolimense": ("Plato fuerte", 26000),
    "Hamburguesa artesanal": ("Comida rápida", 24000),
    "Perro caliente especial": ("Comida rápida", 16000),
    "Salchipapa": ("Comida rápida", 15000),
    "Empanadas x3": ("Entrada", 9000),
    "Patacones con hogao": ("Entrada", 12000),
    "Arepa de choclo": ("Entrada", 8500),
    "Limonada de coco": ("Bebida", 9500),
    "Jugo natural": ("Bebida", 7000),
    "Gaseosa": ("Bebida", 5000),
    "Cerveza nacional": ("Bebida", 7500),
    "Postre de natas": ("Postre", 9000),
    "Brownie con helado": ("Postre", 11000),
    "Achiras con café": ("Postre", 6500),
}
CANALES = {"Salón": 0.45, "Domicilio propio": 0.20, "Rappi": 0.20, "Para llevar": 0.15}
PAGOS = {"Efectivo": 0.30, "Tarjeta débito": 0.22, "Tarjeta crédito": 0.18,
         "Nequi": 0.18, "Daviplata": 0.07, "Transferencia": 0.05}
ESTADOS = {"Entregado": 0.86, "Cancelado": 0.06, "Reclamado": 0.05, "En preparación": 0.03}
TIPO_CLIENTE = {"Ocasional": 0.50, "Frecuente": 0.32, "Empresarial": 0.08, "Nuevo": 0.10}

def pick(d, n):
    k = list(d); p = np.array([d[x] if not isinstance(d[x], tuple) else d[x][-1] for x in k], float)
    return rng.choice(k, size=n, p=p / p.sum())

# ---------------- Base limpia ----------------
fechas = pd.to_datetime("2026-01-01") + pd.to_timedelta(rng.integers(0, 273, N), unit="D")  # ene-sep 2026
# horas con picos de almuerzo y cena
franja = rng.choice(["alm", "cena", "otra"], N, p=[0.5, 0.35, 0.15])
h = np.where(franja == "alm", rng.integers(11, 15, N),
     np.where(franja == "cena", rng.integers(18, 22, N), rng.integers(8, 23, N)))
horas = [f"{a:02d}:{b:02d}" for a, b in zip(h, rng.integers(0, 60, N))]

sede = pick(SEDES, N)
platos = rng.choice(list(MENU), N, p=None)
canal = pick(CANALES, N)
cant = rng.choice([1, 1, 1, 2, 2, 3, 4, 5, 6], N)
precio = np.array([MENU[p][1] for p in platos])
# ajuste leve de precio en Bogotá/Medellín (realista)
precio = np.where(np.isin([SEDES[s][0] for s in sede], ["Bogotá", "Medellín"]), (precio * 1.1).round(-2), precio).astype(int)
desc = rng.choice([0, 0, 0, 0, 5, 10, 15, 20], N)
dom = np.where(canal == "Domicilio propio", rng.choice([4000, 5000, 6000], N),
       np.where(canal == "Rappi", rng.choice([3500, 5500, 7900], N), 0))
subtotal = cant * precio
propina = np.where(canal == "Salón", (subtotal * rng.choice([0, 0.10], N, p=[0.35, 0.65])).round(-2), 0)
total = (subtotal * (1 - desc / 100) + dom + propina).round(0)
estado = pick(ESTADOS, N)
t_prep = rng.normal(22, 7, N).clip(5, 55).round(0)
t_entrega = np.where(np.isin(canal, ["Domicilio propio", "Rappi"]), rng.normal(35, 10, N).clip(12, 80).round(0), np.nan)
calif = rng.choice([1, 2, 3, 4, 5], N, p=[0.04, 0.06, 0.15, 0.35, 0.40]).astype(float)
calif[rng.random(N) < 0.25] = np.nan  # no todos califican
# reglas de negocio
cancel = estado == "Cancelado"; prep = estado == "En preparación"; recl = estado == "Reclamado"
t_entrega[cancel | prep] = np.nan
calif[cancel | prep] = np.nan
calif[recl] = rng.choice([1, 2, 3], recl.sum(), p=[0.5, 0.35, 0.15])
t_prep[cancel] = np.nan

df = pd.DataFrame({
    "id_pedido": [f"PED-{i:05d}" for i in range(1, N + 1)],
    "fecha": fechas.strftime("%Y-%m-%d"),
    "hora": horas,
    "id_cliente": [f"CL-{x:04d}" for x in rng.integers(1, 700, N)],
    "tipo_cliente": pick(TIPO_CLIENTE, N),
    "sede": sede,
    "ciudad": [SEDES[s][0] for s in sede],
    "departamento": [SEDES[s][1] for s in sede],
    "canal": canal,
    "plato": platos,
    "categoria": [MENU[p][0] for p in platos],
    "cantidad": cant,
    "precio_unitario": precio,
    "descuento_pct": desc,
    "costo_domicilio": dom,
    "propina": propina.astype(int),
    "subtotal": subtotal,
    "total_pagado": total,
    "metodo_pago": pick(PAGOS, N),
    "estado_pedido": estado,
    "tiempo_preparacion_min": t_prep,
    "tiempo_entrega_min": t_entrega,
    "calificacion": calif,
})
# un par de ventas grandes REALES (eventos empresariales) -> outliers legítimos
big = rng.choice(N, 6, replace=False)
df.loc[big, "cantidad"] = rng.integers(25, 60, 6)
df.loc[big, "tipo_cliente"] = "Empresarial"
df.loc[big, "canal"] = "Para llevar"; df.loc[big, "costo_domicilio"] = 0; df.loc[big, "propina"] = 0
df.loc[big, "tiempo_entrega_min"] = np.nan
df["subtotal"] = df["cantidad"] * df["precio_unitario"]
df["total_pagado"] = (df["subtotal"] * (1 - df["descuento_pct"] / 100) + df["costo_domicilio"] + df["propina"]).round(0)
df = df.sort_values(["fecha", "hora"]).reset_index(drop=True)
df["id_pedido"] = [f"PED-{i:05d}" for i in range(1, N + 1)]
clean = df.copy()

# ---------------- Ensuciar ----------------
raw = df.astype(object).copy()
log = []
def ruin(col, frac, fn, tipo):
    idx = rng.choice(len(raw), int(len(raw) * frac), replace=False)
    for i in idx:
        old = raw.at[i, col]
        new = fn(old, i)
        if new is not None:
            raw.at[i, col] = new
            log.append((raw.at[i, "id_pedido"], col, tipo, str(old), str(new)))

c = lambda x: rng.choice(x)
# 1 faltantes
for col in ["metodo_pago", "tipo_cliente", "ciudad", "plato", "precio_unitario", "fecha", "hora"]:
    ruin(col, 0.015, lambda o, i: np.nan, "faltante")
# 2 mayúsculas / espacios / tildes
ruin("ciudad", 0.08, lambda o, i: c([str(o).upper(), str(o).lower(), f"  {o} ", str(o).replace("á", "a").replace("é", "e")]), "formato_texto")
ruin("canal", 0.08, lambda o, i: c([str(o).lower(), str(o).upper(), f"{o} ", {"Salón": "Salon", "Rappi": "rappi app", "Domicilio propio": "Domicilio", "Para llevar": "Para Llevar"}.get(o, o)]), "formato_texto")
ruin("metodo_pago", 0.08, lambda o, i: c([str(o).lower(), str(o).upper(), {"Efectivo": "efectvo", "Nequi": "NEQUI ", "Tarjeta débito": "T. Debito", "Tarjeta crédito": "Credito", "Daviplata": "Davi plata", "Transferencia": "transf"}.get(o, o)]), "ortografia")
ruin("plato", 0.05, lambda o, i: c([str(o).lower(), f" {o}", {"Bandeja paisa": "Bandeja Paiza", "Ajiaco santafereño": "Ajiaco santafereno", "Salchipapa": "Salchi papa", "Hamburguesa artesanal": "Hamburgesa artesanal"}.get(o, str(o).upper())]), "ortografia")
ruin("tipo_cliente", 0.06, lambda o, i: c([str(o).lower(), str(o).upper(), {"Frecuente": "frecuent", "Empresarial": "Empresa", "Ocasional": "ocacional"}.get(o, o)]), "formato_texto")
ruin("estado_pedido", 0.07, lambda o, i: c([str(o).lower(), str(o).upper(), {"Entregado": "entregad0", "Cancelado": "CANCEL", "Reclamado": "Con reclamo", "En preparación": "preparando"}.get(o, o)]), "formato_texto")
ruin("sede", 0.04, lambda o, i: c([str(o).upper(), str(o).replace("Sede ", ""), f"{o}  "]), "formato_texto")
# 3 categoría incoherente
ruin("categoria", 0.025, lambda o, i: c([x for x in ["Plato fuerte", "Entrada", "Bebida", "Postre", "Comida rápida"] if x != o]), "categoria_incoherente")
ruin("categoria", 0.02, lambda o, i: c(["bebidas", "PLATO FUERTE", "postres", "Rapida"]), "formato_texto")
# 4 ciudad-departamento incoherente
ruin("departamento", 0.02, lambda o, i: c([x for x in ["Huila", "Cundinamarca", "Antioquia", "Valle del Cauca", "Tolima", "Santander"] if x != o]), "ciudad_dpto_incoherente")
# 5 fechas multiformato e imposibles
def fecha_mala(o, i):
    if pd.isna(o): return None
    d = pd.to_datetime(o)
    return c([d.strftime("%d/%m/%Y"), d.strftime("%m-%d-%Y"), d.strftime("%Y/%m/%d"), d.strftime("%d-%b-%Y"),
              "2026-02-30", "2026-13-05", "2025-12-15", "2027-03-01", "sin fecha"])
ruin("fecha", 0.07, fecha_mala, "fecha")
# 6 horas
ruin("hora", 0.04, lambda o, i: c(["25:10", "12:75", "7:5", "1:30 PM", "13h20", "mediodia", "-"]), "hora")
# 7 cantidad
ruin("cantidad", 0.03, lambda o, i: c([0, -2, -1, "dos", 1.5, 999, "3 und"]), "cantidad")
# 8 precio
ruin("precio_unitario", 0.04, lambda o, i: None if pd.isna(o) else c([f"${int(o):,}", f"{int(o):,}".replace(",", "."), f"{o} COP", -int(o), 0, int(o) * 100, "gratis"]), "precio")
# 9 descuento
ruin("descuento_pct", 0.025, lambda o, i: c([-10, 150, "10%", "diez", 0.15, 300]), "descuento")
# 10 domicilio / propina
ruin("costo_domicilio", 0.02, lambda o, i: c([-5000, 250000, "gratis", "5 mil"]), "domicilio")
ruin("propina", 0.015, lambda o, i: c([-3000, "voluntaria", 500000]), "propina")
# 11 totales inconsistentes
ruin("total_pagado", 0.03, lambda o, i: c([float(o) * c([0.5, 1.3, 10]), 0, float(o) + 99999]), "total_inconsistente")
ruin("subtotal", 0.015, lambda o, i: int(o) + c([1000, -5000, 20000]), "subtotal_inconsistente")
# 12 tiempos
ruin("tiempo_preparacion_min", 0.02, lambda o, i: c([-10, 0, 600, "20 min", "rapido"]), "tiempo")
ruin("tiempo_entrega_min", 0.015, lambda o, i: c([-15, 1440, "media hora"]), "tiempo")
# 13 calificación
ruin("calificacion", 0.025, lambda o, i: c([0, 6, 10, -1, "excelente", "4/5", 4.5]), "calificacion")
# 14 ids cliente mal formados
ruin("id_cliente", 0.02, lambda o, i: c([str(o).replace("-", ""), str(o).lower(), "CL-?", "cliente " + str(o)[-4:]]), "id_cliente")
# 15 plato no catalogado
ruin("plato", 0.008, lambda o, i: c(["Plato del día", "Combo X", "Sushi roll"]), "plato_no_catalogado")
# 16 canal no previsto
ruin("canal", 0.01, lambda o, i: c(["Uber Eats", "WhatsApp", "Teléfono"]), "canal_no_previsto")
# 17 contradicciones lógicas
cidx = raw.index[raw["estado_pedido"] == "Cancelado"]
for i in rng.choice(cidx, min(20, len(cidx)), replace=False):
    raw.at[i, "calificacion"] = c([4, 5]); raw.at[i, "tiempo_entrega_min"] = c([25, 40])
    log.append((raw.at[i, "id_pedido"], "estado/calificacion", "cancelado_con_calificacion", "", ""))
sidx = raw.index[raw["canal"] == "Salón"]
for i in rng.choice(sidx, 15, replace=False):
    raw.at[i, "costo_domicilio"] = 5000
    log.append((raw.at[i, "id_pedido"], "canal/costo_domicilio", "salon_con_domicilio", "0", "5000"))

# 18 duplicados exactos y IDs repetidos con info distinta
dup = raw.sample(35, random_state=1)
conf = raw.sample(15, random_state=2).copy()
conf["total_pagado"] = pd.to_numeric(conf["total_pagado"], errors="coerce") + 7000
conf["metodo_pago"] = "Efectivo"
for i in dup["id_pedido"]: log.append((i, "fila", "duplicado_exacto", "", ""))
for i in conf["id_pedido"]: log.append((i, "fila", "id_repetido_info_distinta", "", ""))
# 19 filas casi vacías
vac = pd.DataFrame([{col: np.nan for col in raw.columns} for _ in range(6)]).astype(object)
vac["id_pedido"] = [f"PED-9{k:04d}" for k in range(6)]
vac.loc[::2, "fecha"] = "2026-05-10"
for i in vac["id_pedido"]: log.append((i, "fila", "fila_casi_vacia", "", ""))

raw = pd.concat([raw, dup, conf, vac], ignore_index=True).sample(frac=1, random_state=7).reset_index(drop=True)

raw.to_csv("pedidos_restaurantes_raw.csv", index=False, encoding="utf-8-sig")
clean.to_csv("pedidos_restaurantes_limpio_referencia.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(log, columns=["id_pedido", "columna", "tipo_error", "valor_original", "valor_sucio"]).to_csv("mapa_errores.csv", index=False, encoding="utf-8-sig")
print("raw", raw.shape, "| limpio", clean.shape, "| errores registrados", len(log))
