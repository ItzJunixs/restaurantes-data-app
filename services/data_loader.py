"""
data_loader.py  (Prompt 2 - Módulo de carga)
Responsabilidad: leer el archivo CSV y devolver un DataFrame.
No limpia ni valida nada: solo carga.
"""
import pandas as pd


def cargar_csv(archivo):
    """
    Recibe el archivo subido con st.file_uploader y devuelve (df, error).
    - Si todo sale bien: (DataFrame, None)
    - Si falla:          (None, "mensaje claro del error")
    """
    try:
        # dtype=str: leemos todo como texto para NO perder información
        # (ej: "$32,000" se convertiría en NaN si pandas adivina el tipo).
        # La conversión de tipos se hace después, en cleaning_service.
        df = pd.read_csv(archivo, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        # Algunos CSV vienen guardados desde Excel en otra codificación
        archivo.seek(0)
        df = pd.read_csv(archivo, dtype=str, encoding="latin-1")
    except pd.errors.EmptyDataError:
        return None, "El archivo está vacío."
    except pd.errors.ParserError:
        return None, "El archivo no tiene un formato CSV válido."
    except Exception as e:
        return None, f"No se pudo leer el archivo: {e}"

    if df.empty:
        return None, "El archivo no tiene filas."

    # Quitamos espacios accidentales en los nombres de las columnas
    df.columns = df.columns.str.strip()
    return df, None
