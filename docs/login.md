# Login, permisos y protección de rutas

Responsable: Persona 1 (Auth y roles). Esta página es lo que necesita el resto del equipo para usar el login.

## Cómo funciona

El frontend manda `correo` y `contrasena` a `POST /api/auth/login` y el backend responde con un campo `estado`
que indica cómo sigue el ingreso:

| `estado` | Cuándo | Qué hace el frontend |
|---|---|---|
| `autenticado` | Contraseña correcta y dispositivo ya verificado | Guarda el token y entra a la app |
| `verificacion_requerida` | Dispositivo nuevo: se envió un código de 6 dígitos por mail | Va a `/acceso/verificar`; con `POST /api/auth/verify-device` obtiene el token |
| `cambio_contrasena_requerido` | Primer ingreso (usuario creado por otro, con contraseña enviada por mail) | Va a `/acceso/cambiar-contrasena`; con `POST /api/auth/change-password` obtiene el token completo |

- **Token**: aleatorio, válido 8 horas, se manda en `Authorization: Bearer <token>`. En la base solo se guarda su hash
  (tabla `sesion`); al cerrar sesión se revoca. El token del primer ingreso solo sirve para cambiar la contraseña.
- **Dispositivo**: el navegador genera un identificador una sola vez y lo manda en cada pedido (`X-Device-Id`). El backend guarda
  su hash en `dispositivo` al verificar el código; desde ese dispositivo ya no vuelve a pedir código. El código solo vale para
  el dispositivo que lo pidió, vence a los 10 minutos, admite 5 intentos y solo vale el último que se pidió.
- **Primer ingreso**: alcanza con cambiar la contraseña (no se pide código por mail, como pidió el cliente); el dispositivo queda
  registrado. El cambio de contraseña cierra todas las demás sesiones del usuario.
- **Errores genéricos**: correo inexistente y contraseña incorrecta dan el mismo `401` (y tardan lo mismo).

## Endpoints

Todos bajo `/api`. Los errores tienen el formato `{"error": {"codigo", "mensaje", "detalle"}}`.

| Método y ruta | Entrada | Salida | Errores |
|---|---|---|---|
| `POST /auth/login` | `{correo, contrasena}` + header `X-Device-Id` | `{estado, token, expira_at, usuario, permisos}` o `{estado: "verificacion_requerida", desafio_id, correo}` | 400 `VALIDACION`, 401 `CREDENCIALES_INVALIDAS`, 403 `CUENTA_INACTIVA`, 503 `MAIL_NO_DISPONIBLE` |
| `POST /auth/verify-device` | `{desafio_id, codigo}` + `X-Device-Id` | igual que un login exitoso | 400, 401 `CODIGO_INCORRECTO` (con `intentos_restantes`), `CODIGO_VENCIDO`, `DESAFIO_AGOTADO`, `DESAFIO_INVALIDO` |
| `POST /auth/change-password` | `{contrasena_actual, contrasena_nueva}` + token + `X-Device-Id` | igual que un login exitoso (token nuevo) | 400 `VALIDACION`, 400 `CONTRASENA_ACTUAL_INCORRECTA`, 401 |
| `POST /auth/logout` | token | 204 | 401 |
| `GET /auth/me` | token | `{estado, usuario, permisos}` | 401 |

Errores de token (cualquier endpoint protegido): 401 `TOKEN_AUSENTE`, `TOKEN_INVALIDO`, `TOKEN_EXPIRADO`;
403 `CAMBIO_CONTRASENA_REQUERIDO` (sesión del primer ingreso) y 403 `PERMISO_DENEGADO`.
La contraseña actual incorrecta es 400 y no 401 a propósito: un 401 con token hace que el frontend cierre la sesión.

## Proteger un endpoint (backend)

```python
from app.controllers.security import require_auth, require_permission

@bp.get("/pacientes")
@require_permission("paciente_listar")     # sesión completa + el rol tiene ese permiso
def listar(): ...

@bp.get("/algo")
@require_auth                               # solo sesión completa (cualquier rol)
def algo(): ...
```

Dentro de la ruta, `g.usuario` es el usuario logueado y `g.sesion` la sesión. El 401 se resuelve antes que cualquier regla
de negocio. Por regla del equipo, el controlador valida permisos y llama a un servicio; no tiene lógica de negocio.

## Agregar un permiso

Los permisos siguen el patrón `modulo_accion` (por ejemplo `estudio_crear`). Se agregan en `backend/seeds/seed_permisos.py`
(una línea bajo cada rol que lo tiene) y se cargan con `poetry run python -m seeds.seed_permisos` (se puede repetir sin problema).
Los permisos de cada rol son una **matriz inicial** armada desde los escenarios: cada responsable ajusta los de su área.

## Frontend

- `useSesion()` devuelve `{ estado, usuario, permisos, ingresar, verificarCodigo, cambiarContrasena, cerrarSesion }`.
  `usuario.nombre` es el nombre completo y `usuario.rol` uno de `constants/roles.js`.
- Todas las llamadas pasan por `src/api/client.js`, que agrega el token y el `X-Device-Id`. Ante un 401 con sesión abierta
  cierra la sesión local y `RutaProtegida` manda al login guardando la ruta para volver después.
- Después de ingresar se vuelve a la ruta que se intentaba abrir solo si el rol del usuario puede verla; si no (por ejemplo, entra
  otra persona con otro rol), al inicio de su rol (`destinoTrasIngresar` en `sesion/acceso.js`).
- `RutaProtegida` (en `App.jsx`) exige sesión, redirige al cambio de contraseña si corresponde y deja entrar a cada rol solo a
  su área (`/medico/...`, `/paciente/...`; `/avisos` es de todos). Ocultar ítems del menú no reemplaza los permisos del backend.
- **Sin backend**: con `VITE_SESION_DEV=true` en `.env.local` se vuelve al usuario de prueba con selector de rol.

### Dónde se guarda el token
El token va en `sessionStorage` (sobrevive a recargar la página y se borra al cerrar la pestaña). Se descartó la memoria (se pierde al
recargar) y `localStorage` (queda guardado aunque se cierre el navegador). Como cualquier almacenamiento accesible desde JavaScript, un
XSS podría leerlo: por eso no se usa `dangerouslySetInnerHTML`, el token nunca va en la URL ni se muestra, vence a las 8 horas y se
revoca en el servidor al cerrar sesión. El id de dispositivo va en `localStorage` porque tiene que persistir (no es una credencial).

## Variables de entorno (backend)

Agregar al `.env.example` (todas opcionales; estos son los valores por defecto):

```
SESSION_TTL_HOURS=8
# Mails: console = simulado (el código de verificación aparece en la terminal del backend); smtp = envío real
MAIL_MODE=console
MAIL_FROM=no-responder@exoma.local
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true
```

Con `MAIL_MODE=console` el código llega a la terminal donde corre `flask run` (línea `[MAIL SIMULADO]`).
En producción, `SECRET_KEY` tiene que ser un valor propio (con él se firma el hash de los códigos).

## Usuarios de prueba

`poetry run python -m seeds.seed_usuarios_demo` crea (solo en desarrollo) un usuario por rol con la contraseña `Exoma2026!`:
`paciente@`, `medico@`, `gerente@`, `administrativo@`, `bioinformatico@`, `transportista@` y `paciente.nuevo@` (primer ingreso),
todos `@exoma.test`. Solo crean la fila de `usuario`: los perfiles (matrícula, DNI, etc.) los crea el registro de usuarios.

## Tests

- Backend: `TEST_DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/ttps_test poetry run pytest`
  (una base vacía aparte: el test la migra con Alembic y la vacía antes de cada prueba; sin la variable, esos tests se saltean).
- Frontend (opcional): `npm i -D vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom`,
  agregar `"test": "vitest run"` a los scripts y correr `npm test`. Usan un `fetch` simulado con el contrato de esta página.

## Todavía no incluido
Recuperación de contraseña (no está en los escenarios), bloqueo temporal por contraseñas incorrectas y login con Google (decididos
afuera), y el registro de usuarios (otro paquete).
