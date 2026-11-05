# Sistema de Exoma Clínico (TTPS)

## Estructura

```
backend/                 API Flask del core (MVC)
  main.py                arranque local: create_app() + app.run(debug=True)
  src/
    config.py            configuración por entorno (variables del .env)
    core/                M · negocio y base de datos, agrupado por dominio
      database.py        Base, sesión por request, reset_db y seed_db
      enums.py           enums de Postgres (estados, roles…)
      models.py          importa todos los modelos (lo usa create_all)
      common/            errors.py, validation.py
      auth/              models.py, service.py (login), password.py
      usuarios/ clinico/ estudios/ pagos/ turnos/ logistica/    models.py de cada dominio
      avisos/            models.py, mail_service.py
      seeds/             datos iniciales (permisos, catálogos, usuarios demo)
    web/                 C + V
      __init__.py        create_app(): config, CORS, base, errores, rutas y comandos reset-db / seed-db
      security.py        autenticación por token y @require_permission
      controllers/       C · rutas de la API (un archivo por área, bajo /api)
      views/             V · arman el JSON que devuelve cada ruta
  tests/                 pytest, una carpeta por dominio (auth/, health/)
frontend/                React (Vite): la interfaz que usan las personas
  docs/diseno/           guía de diseño (DESIGN.md), tokens y maquetas de referencia
  src/api/client.js      único punto de contacto con el backend
  src/components/        componentes comunes (botón, campo, tabla, chip de estado, historial…)
  src/layout/            marco de la app (barra lateral por rol) y de las pantallas de acceso
  src/constants/         estados del estudio y menú de cada rol
  src/sesion/            sesión del usuario (login, token, guards de rutas)
  src/styles/            tokens.css (colores, tipografías) y estilos de la base
docs/                    base de datos (DER, decisiones de diseño) y decisiones del equipo
```

Cada capa tiene un ejemplo funcionando: la ruta `GET /api/health`
(`src/web/controllers/health.py` → `src/web/views/health_view.py`) y la pantalla de `frontend/src/App.jsx`
que la consulta. Para sumar algo nuevo, copiar ese mismo patrón.

## Cómo funciona un pedido (MVC)

Pantalla de React → `src/api/client.js` → **controlador** (`src/web/controllers/`) → **servicio**
(`src/core/<dominio>/service.py`) → **modelos** (`src/core/<dominio>/models.py`) → el controlador responde con una
**vista** (`src/web/views/`) → React la muestra. `web` importa de `core`, nunca al revés.

Reglas del equipo:
- Los controladores no tienen lógica de negocio: validan permisos y llaman a un servicio.
- Ningún controlador devuelve un modelo directo: siempre pasa por una vista.
- Los cambios de estado del estudio se registran siempre en `estudio_historial_estado` (auditoría).

| Si buscás… | Está en… |
|---|---|
| una tabla de la base | `src/core/<dominio>/models.py` |
| login, código de verificación, contraseñas | `src/core/auth/service.py` y `password.py` |
| permisos de cada rol | `src/core/seeds/seed_permisos.py` y `@require_permission` en `src/web/security.py` |
| qué responde un endpoint | `src/web/controllers/<área>.py` y `src/web/views/` |
| errores de la API | `src/core/common/errors.py` |
| envío de mails | `src/core/avisos/mail_service.py` |
| datos iniciales | `src/core/seeds/` |
| configuración y variables de entorno | `src/config.py` y `backend/.env` |
| cómo arranca la app | `main.py` y `src/web/__init__.py` |

## Puesta en marcha

Requisitos: **Python 3.11 o superior**, **Poetry** (gestor de dependencias del backend) y
**Node.js 20 o superior** (en Windows, instalarlos desde python.org y nodejs.org; en Linux, con el gestor de
paquetes de la distribución o con nvm). Poetry se instala una sola vez con `pipx install poetry`
(o con el instalador de https://python-poetry.org/docs/#installation).

Hacen falta dos terminales: una para el backend y otra para el frontend.

### Backend

1. Entrar a la carpeta, crear el archivo de variables y dejar que Poetry cree el entorno virtual
   (queda en `backend/.venv`; solo la primera vez):

   | Linux / Mac | Windows (PowerShell) |
   |---|---|
   | `cd backend` | `cd backend` |
   | `cp .env.example .env` | `copy .env.example .env` |
   | `poetry install --no-root` | `poetry install --no-root` |

   Los comandos se ejecutan con `poetry run ...` (no hace falta activar el entorno a mano).
   Si querés activarlo igual: `poetry env activate` imprime el comando para tu terminal.

2. Completar el `.env` (`DATABASE_URL`: una base local o la de Supabase; pedir los datos al grupo) y levantar:

   ```bash
   poetry run flask --app main:create_app reset-db     # recrea las tablas (ver docs/base_de_datos.md)
   poetry run flask --app main:create_app seed-db      # permisos, catálogos y usuarios de prueba, uno por rol (solo desarrollo)
   poetry run python main.py                           # http://localhost:5001/api/health
   poetry run pytest                                   # tests
   ```

   **No hay migraciones.** `reset-db` borra todos los datos de la base de `DATABASE_URL`: si cambia un modelo,
   se corren `reset-db` y `seed-db`. Los tests que usan la base necesitan `TEST_DATABASE_URL`, una base aparte
   que se borra y recrea en cada corrida (ver `docs/login.md`).
   Para agregar una dependencia: `poetry add <paquete>` (y se versionan `pyproject.toml` y `poetry.lock`).
   Los tests que usan la base necesitan `TEST_DATABASE_URL` (una base de prueba aparte, ver `docs/login.md`).

   El puerto es 5001 porque en macOS el 5000 lo usa AirPlay. Para usar otro sin tocar el repo, poner `FLASK_RUN_PORT` en `backend/.env` y `VITE_API_URL` en `frontend/.env.local` (ninguno de los dos se sube).

### Frontend

| Linux / Mac | Windows (PowerShell) |
|---|---|
| `cd frontend` | `cd frontend` |
| `npm install` | `npm install` |
| `cp .env.example .env.local` | `copy .env.example .env.local` |
| `npm run dev` | `npm run dev` |

Abrir http://localhost:5173/design para ver todos los componentes y cómo usarlos
(con el backend corriendo, arriba dice "API: ok"). Para ingresar con un usuario real hay que cargar los
usuarios de prueba (ver arriba). Para armar pantallas sin backend, poner `VITE_SESION_DEV=true` en
`.env.local`: la barra lateral muestra entonces un selector para cambiar de rol y probar el menú de cada uno.

Para sumar una pantalla: crear el componente (por ejemplo `src/pages/paciente/SacarTurno.jsx`),
agregar su `<Route>` en `src/App.jsx` y, si va en el menú, su ítem en `src/constants/roles.js`.
Antes de diseñar algo nuevo, leer `docs/diseno/DESIGN.md`.

## Documentación
- Base de datos: `docs/base_de_datos.md`
- Login, permisos y protección de rutas: `docs/login.md`
- Decisiones del equipo: `docs/decisiones.md`
