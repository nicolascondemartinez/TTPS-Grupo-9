# Adaptadores de módulos externos

Cada módulo externo tiene dos implementaciones con la misma interfaz: **mock** (datos fijos, sin red)
y **real** (llama a la API). Cuál se usa se elige con variables de entorno, sin tocar código.

## Variables de entorno

| Variable          | Valor                                                   |
|-------------------|---------------------------------------------------------|
| `MODULO_MODE`     | `mock` o `real`. Vacía: usa `ADAPTERS_MODE` (y si no, `mock`) |
| `MODULO_API_URL`  | URL base de la API real (obligatoria en modo `real`)    |
| `MODULO_API_KEY`  | Se manda en el header `X-API-Key`                       |
| `MODULO_TIMEOUT`  | Segundos, opcional (10 por defecto)                     |

`MODULO` es el nombre del módulo en mayúsculas: `OBRAS_SOCIALES_MODE`, `OBRAS_SOCIALES_API_URL`, ...
Al agregar un módulo, sumar sus variables vacías a `backend/.env.example`.

## Errores

El cliente HTTP nunca deja escapar una excepción de `requests`: todo se convierte en uno de estos
errores (de `src.adapters`), que el handler general responde como JSON:

| Error                   | Cuándo                                   | HTTP al frontend |
|-------------------------|------------------------------------------|------------------|
| `AdaptadorNoDisponible` | timeout, sin conexión, 5xx o 429         | 503              |
| `AdaptadorNoAutorizado` | 401/403: la API key está mal              | 502              |
| `RespuestaInvalida`     | la respuesta no es JSON o no tiene la forma esperada | 502  |
| `SolicitudRechazada`    | otro 4xx (400, 404, 409...)              | 502              |

`SolicitudRechazada` trae `status_externo` y `cuerpo`: atrapala en el adaptador real cuando un 4xx
tiene significado de negocio (por ejemplo, un 404 = "afiliado no encontrado").

## Cómo agregar un módulo (ejemplo: obras sociales)

```
src/adapters/obras_sociales/
├── __init__.py    # get_obras_sociales()
├── interfaz.py    # Protocol + dataclasses que devuelve
├── mock.py
└── real.py
```

**interfaz.py**: lo que el resto del sistema puede pedirle al módulo. Devolver dataclasses propias,
nunca el JSON crudo de la API.

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Cobertura:
    afiliado: str
    cubre: bool
    porcentaje: int


class ObrasSociales(Protocol):
    def consultar_cobertura(self, obra_social: str, afiliado: str) -> Cobertura | None: ...
```

**mock.py**: datos fijos y deterministas, sin red.

```python
from src.adapters.obras_sociales.interfaz import Cobertura


class ObrasSocialesMock:
    def consultar_cobertura(self, obra_social: str, afiliado: str) -> Cobertura | None:
        if afiliado.startswith("0"):
            return None  # afiliado inexistente, para probar ese caso
        return Cobertura(afiliado=afiliado, cubre=True, porcentaje=80)
```

**real.py**: recibe el `HttpClient` ya configurado; solo traduce el JSON a la dataclass.

```python
from src.adapters import HttpClient, RespuestaInvalida, SolicitudRechazada
from src.adapters.obras_sociales.interfaz import Cobertura


class ObrasSocialesReal:
    def __init__(self, http: HttpClient):
        self.http = http

    def consultar_cobertura(self, obra_social: str, afiliado: str) -> Cobertura | None:
        try:
            datos = self.http.get(f"/obras-sociales/{obra_social}/afiliados/{afiliado}")
        except SolicitudRechazada as e:
            if e.status_externo == 404:
                return None
            raise
        try:
            return Cobertura(afiliado=datos["afiliado"], cubre=datos["cubre"], porcentaje=int(datos["porcentaje"]))
        except (KeyError, TypeError, ValueError):
            raise RespuestaInvalida(self.http.modulo, {"motivo": "faltan_campos"})
```

**\_\_init\_\_.py**: la única función que usa el resto del código.

```python
from src.adapters import crear_adaptador
from src.adapters.obras_sociales.interfaz import ObrasSociales
from src.adapters.obras_sociales.mock import ObrasSocialesMock
from src.adapters.obras_sociales.real import ObrasSocialesReal


def get_obras_sociales() -> ObrasSociales:
    return crear_adaptador("OBRAS_SOCIALES", mock=ObrasSocialesMock, real=ObrasSocialesReal)
```

Si la API usa otro header (por ejemplo `Authorization: Bearer ...`), el adaptador real lo ajusta en
su `__init__`: `http.session.headers["Authorization"] = f"Bearer {...}"`.

## Tests

- El mock se prueba directo, sin variables de entorno.
- El real se prueba pasándole un `HttpClient` con una `session` falsa (ver
  `tests/adapters/test_http_client.py`), nunca contra la API de verdad.
