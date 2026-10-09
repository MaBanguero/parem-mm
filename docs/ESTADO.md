# ESTADO — Web PARE.MM (matriz de seguimiento)

**Fecha:** 2026-10-06
**Estado:** ✅ listo para revisar en local (sin commit/push todavía)

## Qué se construyó

App FastAPI en `/home/marvin/parem-mm` que:
1. Recibe el **reporte201** ("comportamiento de citas") mensual (.csv tab/comma o .xlsx).
2. Calcula las 5 métricas (columnas **I..M**) por municipio.
3. Descarga la **matriz oficial** rellenada, preservando formato (titulo, merges, EBS/territorios/microterritorios intactos).

## Métricas (columna I..M)

| Col | Métrica | Regla |
|---|---|---|
| I | Pruebas de embarazo | `cupscodigo = 904508` |
| J | Gestantes captadas | mujeres distintas con `programapyp` prenatal ⚠️ |
| K | Control prenatal | `cups ∈ {890201,890301}` + prenatal |
| L | Puerperio | `cups ∈ {890201,890301}` + posparto |
| M | Recién nacido | `cups ∈ {890201,890301}` + recién nacido |

Marcador leído de `programapyp` = `PROGRAMA PRENATAL` / `POSPARTO` / `RECIEN NACIDO`.

## Cómo probarlo (corriendo ahora en :8017)

- http://localhost:8017  → subís el archivo, calcula y descarga el .xlsx

Si lo querés levantar a mano:
```bash
cd /home/marvin/parem-mm && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Resultados de prueba (datos reales)

| | Puerto Tejada | Padilla | Villa Rica |
|---|---|---|---|
| **Febrero** | 163/135/141/19/16 | 32/32/32/6/7 | 44/35/38/9/6 |
| **Septiembre** | 158/175/189/31/20 | 29/28/30/4/5 | 55/43/48/6/6 |

(formato I/J/K/L/M)

## Pendiente de confirmar con Lucas

1. **J (gestantes captadas)**: la cabecera no lo explica. Asumí *mujeres distintas con
   programa prenatal*. La UI muestra señales alternativas (MUJER EMBARAZADA / 1ª vez).
2. **Fuente**: asumí `reporte201_*.csv`. Los valores de ejemplo de la plantilla
   (112/4/0/0/2) no cuadran con el reporte201 completo; parecen de un export filtrado
   por EBS/EPS. Confirmar que `reporte201` es la fuente correcta.
3. **Acumulado vs mensual**: hoy cada archivo = una matriz de ese periodo. Si
   "FEBRERO–JUNIO" debe acumular varios meses, se agrega.

## Deploy Coolify (cuando esté aprobado)

Dockerfile listo (puerto 8000). Crear recurso Dockerfile → push a `main` → auto-deploy.
