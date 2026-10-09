"""Web PARE.MM — sube el reporte201 ("comportamiento de citas") y genera la
matriz de seguimiento con las métricas calculadas por municipio.

Deploy: Coolify detecta el Dockerfile (puerto 8000).
"""

import os
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import matrix, metrics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(BASE, "template", "matriz seguimiento PAREM. MM.xlsx")
STATIC_DIR = os.path.join(BASE, "app", "static")

app = FastAPI(title="PARE.MM — Matriz de seguimiento")

# Almacén en memoria: id -> resultado de métricas. Suficiente para el flujo
# subir -> calcular -> descargar (un solo usuario por instancia). Se pierde al
# reiniciar el contenedor; volver a procesar el archivo es trivial.
STORE: dict[str, dict] = {}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/procesar")
async def procesar(
    file: UploadFile = File(...),
    fecha_inicio: str = Form(None),
    fecha_fin: str = Form(None),
    fecha_col: str = Form("fechaprocedimiento"),
    solo_equipos_basicos: str = Form("0"),
):
    solo_ebs = (solo_equipos_basicos or "0").strip().lower() in ("1", "true", "on", "yes")
    data = await file.read()
    result = metrics.compute(
        data,
        file.filename or "reporte201.csv",
        fecha_inicio=fecha_inicio or None,
        fecha_fin=fecha_fin or None,
        fecha_col=fecha_col or "fechaprocedimiento",
        solo_equipos_basicos=solo_ebs,
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("mensaje"))

    id_ = uuid.uuid4().hex
    STORE[id_] = result

    return {
        "id": id_,
        "municipios": result["municipios"],
        "totales": result["totales"],
        "total_filas": result["total_filas"],
        "filas_ok": result["filas_ok"],
        "fuera_de_municipio": result["fuera_de_municipio"],
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "fecha_col": fecha_col,
        "solo_equipos_basicos": solo_ebs,
    }


@app.get("/api/descargar/{id}")
def descargar(id: str):
    result = STORE.get(id)
    if result is None:
        raise HTTPException(status_code=404, detail="Resultado no encontrado (reprocesá el archivo).")

    buf = matrix.build(TEMPLATE_PATH, result["municipios"])
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="matriz_seguimiento_PAREM_MM.xlsx"'},
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
