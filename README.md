# Sistema de Exoma Clínico (TTPS)

## Estructura

```
backend/                 API Flask del core (MVC)
  app/db/models/         M · modelos SQLAlchemy (tablas)
  app/controllers/       C · rutas de la API (un archivo por área)
  app/views/             V · arman el JSON que devuelve cada ruta
  app/services/          reglas de negocio, testeables sin HTTP
  alembic/               migraciones de la base
  seeds/                 datos iniciales
  tests/                 pytest
frontend/                React (Vite): la interfaz que usan las personas
  docs/diseno/           guía de diseño (DESIGN.md), tokens y maquetas de referencia
  src/api/client.js      único punto de contacto con el backend
  src/components/        componentes comunes (botón, campo, tabla, chip de estado, historial…)
  src/layout/            marco de la app (barra lateral por rol) y de las pantallas de acceso
  src/constants/         estados del estudio y menú de cada rol
  src/sesion/            sesión del usuario (login, token, guards de rutas)
  src/styles/            tokens.css (colores, tipografías) y estilos de la base
obras_sociales_api/      base de datos del módulo 6 (pendiente confirmar si sigue en este repo)
docs/                    base de datos (DER, decisiones de diseño) y decisiones del equipo
tools/                   scripts auxiliares (generar el DER)
```

Cada capa tiene un ejemplo funcionando: la ruta `GET /api/health`
(`controllers/health_controller.py` → `views/health_view.py`) y la pantalla de `frontend/src/App.jsx`
que la consulta. Para sumar algo nuevo, copiar ese mismo patrón.

## Cómo funciona un pedido (MVC)

Pantalla de React → `src/api/client.js` → **controlador** (`app/controllers/`) → **servicio** (`app/services/`)
→ **modelos** (`app/db/models/`) → el controlador responde con una **vista** (`app/views/`) → React la muestra.

Reglas del equipo:
- Los controladores no tienen lógica de negocio: validan permisos y llaman a un servicio.
- Ningún controlador devuelve un modelo directo: siempre pasa por una vista.
- Los cambios de estado del estudio se registran siempre en `estudio_historial_estado` (auditoría).

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

2. Completar el `.env` (pedir los datos de Supabase al grupo) y levantar:

   ```bash
   poetry run alembic upgrade head            # crea las tablas (ver docs/base_de_datos.md)
   poetry run python -m seeds.seed_catalogos
   poetry run python -m seeds.seed_permisos   # permisos de cada rol (ver docs/login.md)
   poetry run python -m seeds.seed_usuarios_demo   # usuarios de prueba, uno por rol (solo desarrollo)
   poetry run flask run                       # http://localhost:5001/api/health
   poetry run pytest                          # tests
   ```

   Para agregar una dependencia: `poetry add <paquete>` (y se versionan `pyproject.toml` y `poetry.lock`).
   Los tests que usan la base necesitan `TEST_DATABASE_URL` (una base de prueba aparte, ver `docs/login.md`).

   El puerto es 5001 (configurado en `backend/.flaskenv`) porque en macOS el 5000 lo usa AirPlay.

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
- Base de datos: `docs/base_de_datos.md`, `docs/der_core.md`, `docs/der_obras_sociales.md`
- Login, permisos y protección de rutas: `docs/login.md`
- Decisiones del equipo: `docs/decisiones.md`
