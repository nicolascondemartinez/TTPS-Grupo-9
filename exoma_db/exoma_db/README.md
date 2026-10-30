# Base de datos — Sistema de Exoma Clínico

PostgreSQL (Supabase) + SQLAlchemy 2.0 + Alembic. Dos proyectos independientes, cada uno con su propio Alembic:

| Carpeta | Qué es | Dónde vive en Postgres |
|---|---|---|
| `core/` | Sistema principal (37 tablas, 11 enums) | schema `public` |
| `obras_sociales_api/` | Módulo 6 (Obras Sociales), API que consumen los demás grupos (3 tablas) | schema `obras_sociales` |

Sin FK entre ambos: el core guarda en `cobertura` una foto (id externo, nombre, %) de lo que devuelve la API.
Diagramas (Mermaid, generados desde los modelos): `docs/der_core.md`, `docs/der_obras_sociales.md`.

## Puesta en marcha

```bash
cd core                       # (o obras_sociales_api)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://USER:PASS@HOST:5432/postgres"   # conexión directa / session pooler
alembic upgrade head          # crea tablas, enums, índices y activa RLS
python -m seeds.seed_catalogos                         # core: 24 provincias, 5 patologías, config CDSS
python -m seeds.seed_obras_sociales --csv obras.csv    # módulo 6: CSV con columnas rnos,nombre,sigla
python -m tests.smoke_test    # prueba constraints (hace rollback, no deja datos)
```

Supabase: para la app en runtime podés usar el pooler en modo transacción (puerto 6543) con psycopg2; para Alembic
usá la conexión directa o el session pooler (5432). Ambos proyectos pueden apuntar a la misma base: cada uno
lleva su propia tabla de versiones (`public.alembic_version` y `obras_sociales.alembic_version`).

## Decisiones de diseño

- PKs UUID (`gen_random_uuid()`), nombres en español y singular, enums nativos de Postgres.
- `usuario` + perfiles 1:1 (`medico`, `gerente_medico`, `paciente`, `transportista`); un rol por usuario.
  Administrativo y bioinformático no tienen datos propios. Especialidades en `usuario_especialidad`.
- Autenticación propia: hash de contraseña, `debe_cambiar_password`, `dispositivo` y `codigo_verificacion`.
- `estudio` = caso que recorre la logística; `analisis` = cada ronda de lectura de genes (1 = original, 2+ = re-análisis).
  Patologías, genes y variantes cuelgan del análisis. Una variante solo puede cargarse sobre un gen pedido (FK compuesta).
- `estudio_historial_estado` registra cada cambio de estado (tablero de tiempos y cuellos de botella).
- Datos de otros módulos: `sintoma` y `gen` son cachés locales (código único); variantes, obra social y cupón se guardan como código + foto.
- Archivos (PDFs, CSV, datos crudos) en Supabase Storage; la base guarda solo la ruta/URL.
- RLS activado en todas las tablas (sin políticas): la API REST automática de Supabase no puede leerlas;
  la app accede por conexión directa. Las tablas nuevas deben repetir `ENABLE ROW LEVEL SECURITY`.

### Decisiones que tomé sin que me las confirmaras (revisalas)

1. `estado_estudio` incluye `esperando_autorizacion` y `rechazado` (aparecen en los scenarios, no en el glosario).
2. `estado_lote` incluye `esperando_autorizacion_ministerio` (el flujo de "Armar el lote" puede pasar directo a `esperando_retiro`).
3. `configuracion` guarda `cdss_estrategia` (módulo 4), sembrada con `mayor_cantidad_sintomas`.
4. `lote.token_retiro`: UUID que va en la URL que invoca FedEx (no se expone el id interno).
5. `parada_estudio` relaciona estudios con paradas: permite mostrar qué transportista lleva una muestra.
6. `patologia_sintoma`: un solo síntoma cardinal por patología (índice único parcial).
7. `cobertura` no tiene estado propio: autorizada/rechazada se deduce del estado del estudio y su historial.
8. `paciente.familiograma_url` es opcional (el cliente dijo que puede quedar vacío).
9. Módulo 6: `consumidor` (API key hasheada por grupo) y `solicitud_estudio.referencia_externa` (id del estudio en el core de cada grupo).

## Queda en la aplicación (no en la base)

Tope de 10 estudios por lote; grilla de turnos (15 min, L–V, 9–18, sin feriados); coherencia entre `usuario.rol` y su perfil;
precio (USD 500 hasta 5 genes + USD 30 por gen adicional); `es_pompe_urgente` (Pompe y menor de 4 meses al dar de alta);
transiciones válidas de estado; reinicio de `inasistencias` al volver a `creado`.

Nota ORM: entre tablas sin `relationship()` SQLAlchemy no garantiza el orden de INSERT dentro de un mismo flush;
si creás un `Medico` y un `Paciente` en la misma operación, hacé `session.flush()` entre ambos.

## Verificado

PostgreSQL 16, SQLAlchemy 2.0.43, Alembic 1.16.5: `upgrade → downgrade → upgrade` sin errores, `alembic check` sin diferencias
entre modelos y migraciones, ambos schemas conviviendo en la misma base, y 27 pruebas de constraints (`tests/smoke_test.py`).
