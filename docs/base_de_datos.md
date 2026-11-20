# Base de datos — Sistema de Exoma Clínico

PostgreSQL + SQLAlchemy 2.0, sin migraciones: `reset-db` borra y recrea las tablas y los enums desde los modelos
(`backend/src/core/**/models.py`) y `seed-db` carga los datos iniciales. Todo vive en el schema `public`.

El módulo 6 (Obras Sociales) es una API aparte, desplegada por separado y fuera de este repo: el core la consume
y guarda en `cobertura` una foto (id externo, nombre, %) de lo que devuelve, sin FK entre ambos.

Sin FK entre ambos: el core guarda en `cobertura` una foto (id externo, nombre, %) de lo que devuelve la API.

## Puesta en marcha

```bash
cd backend
poetry install --no-root
# DATABASE_URL en backend/.env: postgresql+psycopg2://USER:PASS@HOST:5432/DB
poetry run flask --app main:create_app reset-db   # borra y crea tablas, enums e índices, y activa RLS
poetry run flask --app main:create_app seed-db    # provincias, patologías, config CDSS, permisos y usuarios demo
```

`reset-db` **borra todos los datos** de la base de `DATABASE_URL`. Si cambia un modelo, se vuelve a correr junto con `seed-db`.

Supabase: para correr la app podés usar el pooler en modo transacción (puerto 6543) con psycopg2; para `reset-db`
usá la conexión directa o el session pooler (5432).

## Decisiones de diseño

- PKs UUID (`gen_random_uuid()`), nombres en español y singular, enums nativos de Postgres.
- `usuario` + perfiles 1:1 (`medico`, `gerente_medico`, `paciente`, `transportista`); un rol por usuario.
  Administrativo y bioinformático no tienen datos propios. Especialidades en `usuario_especialidad`.
- Autenticación propia: hash de contraseña, `debe_cambiar_password`, `dispositivo` y `codigo_verificacion`.
- `estudio` = caso que recorre la logística; `analisis` = cada ronda de lectura de genes (1 = original, 2+ = re-análisis).
  Patologías, genes y variantes cuelgan del análisis. Una variante solo puede cargarse sobre un gen pedido (FK compuesta).
- `estudio_historial_estado` registra cada cambio de estado (tablero de tiempos y cuellos de botella).
- Datos de otros módulos: `sintoma` y `gen` son cachés locales (código único); variantes, obra social y cupón se guardan como código + foto.
- Archivos (familiograma, PDFs, CSV): se guardan con el servicio de almacenamiento (`core/almacenamiento/service.py`)
  y los modelos guardan solo la ruta que devuelve. Por ahora van a la tabla `archivo` (en la base): funciona en
  cualquier despliegue sin configurar nada (el disco de Render y similares se borra en cada reinicio) y el archivo
  entra en la misma transacción. Antes se pensaba en Supabase Storage: si hace falta (archivos grandes), se suma
  como otra implementación del servicio, sin cambiar el código que lo usa.
- RLS activado en todas las tablas (sin políticas): reset_db() lo activa en todas las tablas; no hace falta repetirlo;
  la app accede por conexión directa. Las tablas nuevas deben repetir `ENABLE ROW LEVEL SECURITY`.

### Decisiones que tomé sin que me las confirmaras (revisalas)

1. `estado_estudio` incluye `esperando_autorizacion` y `rechazado` (aparecen en los scenarios, no en el glosario).
2. `estado_lote` incluye `esperando_autorizacion_ministerio` (el flujo de "Armar el lote" puede pasar directo a `esperando_retiro`).
3. `configuracion` guarda `cdss_estrategia` (módulo 4), sembrada con `mayor_cantidad_sintomas`.
4. `lote.token_retiro`: UUID que va en la URL que invoca FedEx (no se expone el id interno).
5. `parada_estudio` relaciona estudios con paradas: permite mostrar qué transportista lleva una muestra.
6. `patologia_sintoma`: una patología puede tener uno o más síntomas cardinales (`es_cardinal`), y un mismo síntoma puede ser cardinal de varias patologías.
7. `cobertura` no tiene estado propio: autorizada/rechazada se deduce del estado del estudio y su historial.
8. `paciente.familiograma_url` es opcional (el cliente dijo que puede quedar vacío). Es la ruta del SVG que devuelve
   el módulo 1 (la issue decía PDF, pero la API devuelve SVG y se guarda tal cual).
9. El diagnóstico presuntivo del paciente es una o más patologías (`paciente_patologia`). Una patología sospechada
   en algún paciente no se puede borrar (RESTRICT); al borrar el paciente se borran su diagnóstico y sus familiares.
10. `familiar.sexo` (hombre, mujer o no_identificado): lo necesita el módulo de familiograma para ubicar a los
    abuelos, tíos y medio hermanos de cada lado (deduce el lado por el sexo del progenitor).


## Queda en la aplicación (no en la base)

Tope de 10 estudios por lote; grilla de turnos (15 min, L–V, 9–18, sin feriados); coherencia entre `usuario.rol` y su perfil;
precio (USD 500 hasta 5 genes + USD 30 por gen adicional); `es_pompe_urgente` (Pompe y menor de 4 meses de calendario al dar de alta: `core/clinico/edad.py`);
al menos una patología en el diagnóstico presuntivo; quién ve los datos clínicos del paciente (su médico y él mismo);
transiciones válidas de estado; reinicio de `inasistencias` al volver a `creado`.

Nota ORM: entre tablas sin `relationship()` SQLAlchemy no garantiza el orden de INSERT dentro de un mismo flush;
si creás un `Medico` y un `Paciente` en la misma operación, hacé `session.flush()` entre ambos.

## Verificado

`reset-db`, `seed-db` y la suite de tests (`poetry run pytest` con `TEST_DATABASE_URL`) corren sin errores sobre PostgreSQL local.