"""Cálculo de métricas PARE.MM a partir del reporte201 ("comportamiento de citas").

La matriz de seguimiento tiene UNA fila por municipio (Puerto Tejada, Padilla,
Villa Rica) y las columnas I..M son las 5 métricas:

    I  No de pruebas de embarazo        -> CUPS 904508
    J  No de gestantes captadas         -> mujeres distintas con programa prenatal
    K  No controles Control Pre Natal   -> CUPS 890201/890301 + programa prenatal
    L  No controles puerperio           -> CUPS 890201/890301 + programa posparto
    M  No controles de RN               -> CUPS 890201/890301 + programa recién nacido
"""

import csv
import io
import unicodedata
from collections import defaultdict
from datetime import date, datetime

# --------------------------------------------------------------------------- #
# Constantes de dominio
# --------------------------------------------------------------------------- #

MUNICIPIOS = ["PUERTO TEJADA", "PADILLA", "VILLA RICA"]

CUPS_PRUEBA_EMBARAZO = "904508"
CUPS_CONTROL = {"890201", "890301"}   # consulta 1ª vez / control-seguimiento

COL_CUPS = "cupscodigo"
COL_PROGRAMA = "programapyp"
COL_ID = "identificacion"
COL_MUNICIPIO = "municipio"
COL_GRUPO = "grupopoblacional"
COL_FECHA = "fechaprocedimiento"   # fecha de atención / prestación del servicio
COL_CONVENIO = "convenio"


# --------------------------------------------------------------------------- #
# Normalización
# --------------------------------------------------------------------------- #

def _sin_acentos(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm_cups(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s.endswith(".0"):          # 904508.0 -> 904508
        s = s[:-2]
    return s


def norm_municipio(v):
    if v is None:
        return None
    s = _sin_acentos(str(v)).strip().upper()
    return s if s in MUNICIPIOS else None


def norm_programa(v) -> str:
    return _sin_acentos(str(v or "")).strip().upper()


def norm_fecha(v):
    """Normaliza una fecha (str o datetime) a 'YYYY-MM-DD'; None si no hay."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip()
    if not s:
        return None
    return s[:10]


def is_prenatal(p: str) -> bool:
    return "PRENATAL" in p          # no matchea "PRECONCEPCIONAL"


def is_posparto(p: str) -> bool:
    return "POSPARTO" in p


def is_recien_nacido(p: str) -> bool:
    return "RECIEN NACIDO" in p


def es_equipos_basicos(v) -> bool:
    """True si el convenio corresponde a 'equipos básicos' (EBS).

    Cubre 'EQUIPOS BASICOS' y el typo del dato 'EQUIPOS BASCIOS' matcheando
    el prefijo 'EQUIPOS BAS'.
    """
    s = _sin_acentos(str(v or "")).strip().upper()
    return "EQUIPOS BAS" in s


# --------------------------------------------------------------------------- #
# Parseo de entrada (CSV tab/comma/; o XLSX)
# --------------------------------------------------------------------------- #

def _sniff_delimiter(sample: str) -> str:
    if "\t" in sample:
        return "\t"
    if "," in sample:
        return ","
    if ";" in sample:
        return ";"
    return "\t"


def _parse_csv(data: bytes):
    text = data.decode("utf-8-sig", errors="replace")
    delim = _sniff_delimiter(text[:4096])
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    header = next(reader, None)
    if header is None:
        return []
    header = [(_sin_acentos(str(h)).strip().lower().replace(" ", "")) for h in header]
    rows = []
    for line in reader:
        if not any(cell and str(cell).strip() for cell in line):
            continue
        rows.append(dict(zip(header, line)))
    return rows


def _parse_xlsx(data: bytes):
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    header = next(it, None)
    if header is None:
        return []
    header = [(_sin_acentos(str(h)).strip().lower().replace(" ", "")) for h in header]
    rows = []
    for line in it:
        rows.append(dict(zip(header, line)))
    return rows


def parse_rows(data: bytes, filename: str):
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        return _parse_xlsx(data)
    return _parse_csv(data)


# --------------------------------------------------------------------------- #
# Agregación
# --------------------------------------------------------------------------- #

def compute(data: bytes, filename: str, fecha_inicio: str = None, fecha_fin: str = None,
            fecha_col: str = COL_FECHA, solo_equipos_basicos: bool = False) -> dict:
    rows = parse_rows(data, filename)

    # Columnas requeridas (claves ya normalizadas)
    required = {COL_CUPS, COL_ID, COL_MUNICIPIO}
    missing = required - set(rows[0].keys()) if rows else required
    if not rows or missing:
        return {
            "error": True,
            "mensaje": (
                "No se encontraron las columnas necesarias. "
                f"Faltan: {', '.join(sorted(missing))}. "
                "El archivo debe ser el reporte201 (comportamiento de citas) con "
                "columnas cupscodigo, identificacion, municipio, programapyp."
            ),
        }

    per = {m: defaultdict(int) for m in MUNICIPIOS}
    docs = {m: set() for m in MUNICIPIOS}          # gestantes captadas (distinct)
    docs_grupo = {m: set() for m in MUNICIPIOS}    # señal alternativa: MUJER EMBARAZADA
    docs_primera = {m: set() for m in MUNICIPIOS}  # señal: 1ª vez prenatal

    fuera = defaultdict(int)
    total_filas = 0
    filas_ok = 0

    for r in rows:
        total_filas += 1

        # Filtro por fecha (de atención o de facturación), si se pidió.
        if fecha_inicio or fecha_fin:
            f = norm_fecha(r.get(fecha_col))
            if f is None:
                continue
            if fecha_inicio and f < fecha_inicio:
                continue
            if fecha_fin and f > fecha_fin:
                continue

        # Filtro por convenio: solo equipos básicos (EBS), si se pidió.
        if solo_equipos_basicos and not es_equipos_basicos(r.get(COL_CONVENIO)):
            continue

        mun = norm_municipio(r.get(COL_MUNICIPIO))
        if mun is None:
            m_raw = _sin_acentos(str(r.get(COL_MUNICIPIO) or "")).strip().upper() or "(vacío)"
            fuera[m_raw] += 1
            continue
        filas_ok += 1

        cups = norm_cups(r.get(COL_CUPS))
        prog = norm_programa(r.get(COL_PROGRAMA))
        grupo = norm_programa(r.get(COL_GRUPO))
        doc = (str(r.get(COL_ID) or "")).strip()

        # I — pruebas de embarazo
        if cups == CUPS_PRUEBA_EMBARAZO:
            per[mun]["I"] += 1

        es_consulta = cups in CUPS_CONTROL
        prenatal = is_prenatal(prog)
        posparto = is_posparto(prog)
        rn = is_recien_nacido(prog)

        # J — gestantes captadas (distinct mujeres con programa prenatal)
        if prenatal:
            if doc:
                docs[mun].add(doc)
            # K — controles de control prenatal (consultas con programa prenatal)
            if es_consulta:
                per[mun]["K"] += 1

        # L — puerperio
        if posparto and es_consulta:
            per[mun]["L"] += 1

        # M — recién nacido
        if rn and es_consulta:
            per[mun]["M"] += 1

        # Señales alternativas para "gestantes captadas" (para revisar con Lucas)
        if grupo == "MUJER EMBARAZADA" and doc:
            docs_grupo[mun].add(doc)
        if prenatal and cups == "890201" and doc:
            docs_primera[mun].add(doc)

    municipios = {}
    for m in MUNICIPIOS:
        municipios[m] = {
            "I": per[m]["I"],
            "J": len(docs[m]),
            "K": per[m]["K"],
            "L": per[m]["L"],
            "M": per[m]["M"],
            "_senales": {
                "gestantes_prenatal_distinct": len(docs[m]),
                "gestantes_mujer_embarazada": len(docs_grupo[m]),
                "gestantes_primera_vez_prenatal": len(docs_primera[m]),
            },
        }

    totales = {
        "I": sum(municipios[m]["I"] for m in MUNICIPIOS),
        "J": sum(municipios[m]["J"] for m in MUNICIPIOS),
        "K": sum(municipios[m]["K"] for m in MUNICIPIOS),
        "L": sum(municipios[m]["L"] for m in MUNICIPIOS),
        "M": sum(municipios[m]["M"] for m in MUNICIPIOS),
    }

    return {
        "error": False,
        "municipios": municipios,
        "totales": totales,
        "total_filas": total_filas,
        "filas_ok": filas_ok,
        "fuera_de_municipio": dict(fuera),
    }
