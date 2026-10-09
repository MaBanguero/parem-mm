# PARE.MM — Matriz de seguimiento

Web para generar la **Matriz de seguimiento PARE.MM** (Plan de aceleración para
la reducción de la mortalidad materna) a partir del **reporte201**
("comportamiento de citas"). Subís el archivo mensual, calcula las 5 métricas por
municipio y te descarga la matriz Excel con el formato oficial intacto.

## Qué hace

La matriz oficial tiene **una fila por municipio** (Puerto Tejada, Padilla, Villa
Rica) y las columnas **I..M** son las métricas. El resto (ESE, resolución, EBS,
territorios, microterritorios) es texto estático que se conserva tal cual.

| Col | Métrica | Cálculo |
|---|---|---|
| I | No de pruebas de embarazo | `cupscodigo == 904508` |
| J | No de gestantes captadas | mujeres **distintas** con `programapyp` prenatal *(asumido, ver abajo)* |
| K | No controles Control Pre Natal | `cupscodigo ∈ {890201, 890301}` + `programapyp` prenatal |
| L | No controles puerperio | `cupscodigo ∈ {890201, 890301}` + `programapyp` posparto |
| M | No controles de RN | `cupscodigo ∈ {890201, 890301}` + `programapyp` recién nacido |

El marcador de programa se lee del campo **`programapyp`** (valores
`PROGRAMA PRENATAL`, `POSPARTO`, `RECIEN NACIDO`). El matching es
case-insensitive y sin acentos; `PRENATAL` **no** matchea `PRECONCEPCIONAL`.

## Formato de entrada

`reporte201_<fecha>_<fecha>_0.csv` (tab-delimited) o el `.xlsx` equivalente.
Columnas requeridas: `cupscodigo`, `programapyp`, `identificacion`, `municipio`.

- `cupscodigo` viene como float (`904508.0`) → se normaliza a `904508`.
- Solo se cuentan filas cuyo `municipio` ∈ {PUERTO TEJADA, PADILLA, VILLA RICA}.
  El resto (Cali, Guachene, Miranda, etc.) se reporta como "fuera de municipio".

## Ejecutar local

```bash
cd parem-mm
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# abrir http://localhost:8000
```

## Deploy en Coolify

1. Creá un recurso **Dockerfile** apuntando a este repo.
2. Puerto expuesto: **8000** (el `EXPOSE` del Dockerfile).
3. Build: `docker build` automático (Nixpacks no hace falta; hay Dockerfile).
4. Configurá el dominio/TLS como cualquier app.
5. Push a `main` → auto-deploy.

## Pendiente de confirmar con Lucas

1. **J — "gestantes captadas"**: no tiene explicación en la cabecera. Quedó como
   *mujeres distintas con `programapyp` prenatal*. La UI además muestra dos
   señales alternativas: `grupopoblacional = MUJER EMBARAZADA` y
   `cups 890201 (1ª vez) + prenatal`, por si el criterio correcto es otro.
2. **Fuente canónica**: se asumió `reporte201_*.csv` (el "comportamiento de
   citas" completo). Los valores de ejemplo que trae la plantilla (112/4/0/0/2)
   no coinciden con el reporte201 completo de febrero; parecen de un archivo
   filtrado por EBS/EPS. Confirmar que `reporte201` es la fuente.
3. **Acumulado vs mensual**: hoy cada archivo subido genera la matriz de ese
   periodo. Si la matriz "FEBRERO–JUNIO" debe acumular varios meses, se agrega.
