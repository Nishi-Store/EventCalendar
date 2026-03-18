"""
data_loader.py
==============
Lee Google Sheet o Excel, filtra por semana y devuelve SEMANA dict.

USO
---
    from data_loader import cargar_semana

    semana, week_start, semana_label = cargar_semana(
        fuente = "https://docs.google.com/spreadsheets/d/ID",
        lunes  = "2026-03-23"
    )

    # O desde Excel local:
    semana, week_start, semana_label = cargar_semana("agenda.xlsx", "2026-03-23")

COLUMNAS ESPERADAS EN EL SHEET
-------------------------------
    fecha         → 23/03/2026  o  2026-03-23
    nombre_evento → nombre del evento (vacío = día sin eventos)
    hora_inicio   → 3:00 PM
    hora_fin      → 6:00 PM
    descripcion   → texto corto
    imagen        → MTG.png
"""

import pandas as pd
from pathlib import Path

DIAS_ES = {
    0: "LUNES",
    1: "MARTES",
    2: "MIÉRCOLES",
    3: "JUEVES",
    4: "VIERNES",
    5: "SÁBADO",
    6: "DOMINGO",
}

MESES_ES = {
    1: "Ene", 2: "Feb",  3: "Mar", 4: "Abr",
    5: "May", 6: "Jun",  7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def cargar_semana(fuente: str, lunes: str) -> tuple:
    """
    Retorna (semana, week_start, semana_label).

    semana       → {"LUNES": [...], "MARTES": [...], "JUEVES": [], ...}
    week_start   → "2026-03-23"
    semana_label → "Mar. 23 – 29, 2026"
    """
    lunes_dt = pd.Timestamp(lunes)
    if lunes_dt.weekday() != 0:
        lunes_dt = lunes_dt - pd.Timedelta(days=lunes_dt.weekday())
        print(f"  [info] Ajustado al lunes: {lunes_dt.date()}")

    domingo_dt = lunes_dt + pd.Timedelta(days=6)

    df = _leer(fuente)
    df = _normalizar(df)

    # Filtrar solo la semana pedida
    mask      = (df["fecha"] >= lunes_dt) & (df["fecha"] <= domingo_dt)
    df_semana = df[mask].copy()

    if df_semana.empty:
        print(f"  [warn] Sin eventos para {lunes_dt.date()} – {domingo_dt.date()}")

    semana       = _construir_semana(df_semana)
    week_start   = lunes_dt.strftime("%Y-%m-%d")
    semana_label = (f"{MESES_ES[lunes_dt.month]}. "
                    f"{lunes_dt.day} – {domingo_dt.day}, {lunes_dt.year}")

    return semana, week_start, semana_label


def _leer(fuente: str) -> pd.DataFrame:
    fuente = fuente.strip()

    if "docs.google.com/spreadsheets" in fuente:
        try:
            sheet_id = fuente.split("/d/")[1].split("/")[0]
        except IndexError:
            raise ValueError(f"URL de Google Sheets inválida: {fuente}")
        url = (f"https://docs.google.com/spreadsheets/d/"
               f"{sheet_id}/export?format=csv&gid=0")
        try:
            df = pd.read_csv(url)
        except Exception as e:
            raise ConnectionError(
                "No se pudo leer el Sheet. Publícalo como CSV:\n"
                "  Archivo → Compartir → Publicar en la web → CSV\n"
                f"Error: {e}"
            )

    elif fuente.endswith((".xlsx", ".xls")):
        if not Path(fuente).exists():
            raise FileNotFoundError(f"Archivo no encontrado: {fuente}")
        df = pd.read_excel(fuente)

    elif fuente.startswith("http") or fuente.endswith(".csv"):
        df = pd.read_csv(fuente)

    else:
        raise ValueError(f"Fuente no reconocida: '{fuente}'")

    return df


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns.str.strip().str.lower()
        .str.replace(" ", "_")
        .str.replace("á","a").str.replace("é","e")
        .str.replace("í","i").str.replace("ó","o").str.replace("ú","u")
    )

    aliases = {
        "date":           "fecha",
        "evento":         "nombre_evento",
        "nombre":         "nombre_evento",
        "event":          "nombre_evento",
        "hora_de_inicio": "hora_inicio",
        "inicio":         "hora_inicio",
        "hora_de_fin":    "hora_fin",
        "fin":            "hora_fin",
        "desc":           "descripcion",
        "description":    "descripcion",
        "img":            "imagen",
        "logo":           "imagen",
        "image":          "imagen",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})

    for col in ["fecha", "nombre_evento"]:
        if col not in df.columns:
            raise ValueError(
                f"Falta la columna '{col}'.\n"
                f"Columnas encontradas: {list(df.columns)}"
            )

    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce")
    n_bad = df["fecha"].isna().sum()
    if n_bad:
        print(f"  [warn] {n_bad} fila(s) con fecha inválida — ignoradas")
    df = df.dropna(subset=["fecha"]).copy()

    if df.empty:
        raise ValueError("El sheet no tiene filas con fecha válida.")

    for col in ["hora_inicio", "hora_fin", "descripcion", "imagen"]:
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("").astype(str).str.strip()

    df["nombre_evento"] = df["nombre_evento"].fillna("").astype(str).str.strip()

    return df.sort_values("fecha").reset_index(drop=True)


def _construir_semana(df: pd.DataFrame) -> dict:
    # Los 7 días siempre presentes, vacíos por defecto
    semana = {DIAS_ES[i]: [] for i in range(7)}

    for fecha, grupo in df.groupby("fecha"):
        dia_nombre = DIAS_ES[fecha.weekday()]
        eventos = []
        for _, row in grupo.iterrows():
            nombre = row["nombre_evento"]
            if not nombre:
                continue
            hora_i = str(row["hora_inicio"]).strip()
            hora_f = str(row["hora_fin"]).strip()
            if hora_i and hora_f:
                hora = f"{hora_i} – {hora_f}"
            elif hora_i:
                hora = hora_i
            elif hora_f:
                hora = f"Hasta {hora_f}"
            else:
                hora = "Todo el día"
            eventos.append({
                "nombre":      nombre,
                "hora":        hora,
                "descripcion": row["descripcion"],
                "imagen":      row["imagen"],
            })
        semana[dia_nombre] = eventos

    return semana
