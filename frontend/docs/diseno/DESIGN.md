# Dirección visual — Sistema de Exoma Clínico

Guía para implementar el front. Es la fuente de verdad del estilo: si algo no está acá, seguir el espíritu de estos principios en lugar de inventar uno nuevo.

Archivos del paquete:
- `DESIGN.md` — esta guía.
- `tokens.css` — variables CSS y clases base de componentes (copiar al proyecto).
- `dna.svg` — molécula de ADN (decoración grande).
- `referencia/` — las 3 pantallas de la maqueta en HTML (guía de estilo, ingreso, panel). Son **solo para mirar** estilos, medidas y estructura. Vienen de una herramienta de diseño: ignorar `support.js`, `x-dc`, `<script type="text/x-dc">` y `{{ }}`. No copiar el código tal cual; reimplementar con el stack del proyecto.

## 1. Principios

1. **Naranja y violeta en degradé** como identidad. Evitar el verde/celeste típico de lo médico.
2. **Futurista sin exagerar.** Lo futurista vive en el color, los brillos suaves, la grilla fina del fondo oscuro y la hélice de ADN. Dentro de la app las superficies son claras, sobrias y legibles.
3. **Fondo oscuro solo en ingreso y portadas.** Adentro (paneles, tablas, formularios) fondo claro `--niebla` con tarjetas blancas.
4. **El degradé es un detalle, no un baño.** Se usa en botones primarios, el filo superior de tarjetas, la marca, el avatar y gráficos. Nunca como fondo de pantallas de trabajo.
5. **Accesibilidad primero.** Contraste mínimo 4.5:1 en texto (3:1 en bordes de campos y texto ≥24 px). Objetivos táctiles ≥44 px. Los estados no se distinguen solo por color (los chips llevan punto + texto).

## 2. Color

| Token | Hex | Uso |
|---|---|---|
| `--violeta-600` | `#6D28D9` | Acciones, enlaces, foco, énfasis |
| `--violeta-400` | `#8B5CF6` | Solo decoración y gráficos (no texto sobre claro) |
| `--violeta-300` | `#A78BFA` | Texto/acentos sobre fondo oscuro |
| `--naranja-600` | `#C2410C` | Acciones secundarias, etiquetas de sección, atención |
| `--naranja-400` | `#FF8A3D` | ADN, brillos, gráficos; texto solo sobre fondo oscuro |
| `--tinta` | `#160F2E` | Texto principal y barra lateral |
| `--ground-oscuro` | `#130C28` | Fondo de ingreso/portadas |
| `--niebla` | `#F8F6FC` | Fondo de la app |
| `--blanco` | `#FFFFFF` | Tarjetas, tablas, campos |
| `--linea` | `#E4DEF2` | Bordes de tarjetas y separadores |
| `--texto-suave` | `#5B5373` | Texto secundario sobre claro |
| `--texto-suave-oscuro` | `#BDB3DD` | Texto secundario sobre oscuro |
| `--texto-oscuro` | `#F5F1FF` | Texto principal sobre oscuro |
| `--borde-campo` | `#8A81A8` | Borde de inputs (3:1) |

**Degradés**
- Acción (texto blanco encima, pasa contraste en todo el recorrido): `linear-gradient(90deg, #6D28D9 0%, #C2410C 100%)` (en diagonal `135deg` para íconos/marca).
- Decorativo (sin texto encima): `linear-gradient(90deg, #8B5CF6 0%, #FF8A3D 100%)`.
- Brillos sobre fondo oscuro: dos `radial-gradient` (violeta arriba-izquierda a ~50% de opacidad, naranja abajo-derecha a ~35%) más una grilla de líneas `rgba(255,255,255,.04)` cada 32 px.

**Estados (chips)** — fondo suave + texto oscuro + punto del color fuerte:

| Tipo | Fondo | Texto | Punto |
|---|---|---|---|
| Neutro | `#ECE9F5` | `#3B3354` | `#3B3354` |
| En curso (violeta) | `#EDE7FE` | `#4C1D95` | `#6D28D9` |
| Atención (naranja) | `#FFEDD5` | `#9A3412` | `#C2410C` |
| Error/rechazo | `#FFE4E6` | `#9F1239` | `#BE123C` |
| Completado | `#6D28D9` | `#FFFFFF` | `#FFFFFF` |

Los nombres de estado de la maqueta (Presupuestado, Pagado, Turno asignado, Listo para retirar, Rechazado, Completado) son **ilustrativos**. Usar los estados reales del dominio y mapearlos a estos tipos.

## 3. Tipografía

- **Títulos, números, etiquetas y botones:** Space Grotesk (500/600/700). Títulos con `letter-spacing: -0.02em`.
- **Texto, tablas y formularios:** IBM Plex Sans (400/500/600).
- Google Fonts: `https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap`
- Escala: h1 de pantalla 36/40 · h2 de sección 28–32 · título de tarjeta 18–20 · texto 15–16 · auxiliar 13.
- Etiqueta de sección: Space Grotesk 600, 13 px, mayúsculas, `letter-spacing: .12em`, color `--naranja-600` (o `--naranja-400` sobre oscuro).

## 4. Componentes

- **Botón primario:** alto 46 px, radio 12, degradé de acción, texto blanco Space Grotesk 600/16, sombra `0 6px 18px rgba(109,40,217,.28)`.
- **Botón secundario:** blanco, borde 1.5 px `--violeta-600`, texto `--violeta-600`.
- **Botón ghost:** transparente, texto `--naranja-600`, subrayado con `text-underline-offset: 4px`.
- **Input:** alto 46–48, radio 12, borde 1 px `--borde-campo`, texto 16. Foco: borde 2 px `--violeta-600` + `box-shadow: 0 0 0 4px rgba(109,40,217,.16)`. Siempre con `<label>` visible (o `sr-only` en buscadores). Placeholder `#6B6384`.
- **Tarjeta:** blanco, borde 1 px `--linea`, radio 20, `overflow: hidden`. Con filo de degradé: franja superior de 4 px con el degradé de acción.
- **Tabla:** encabezado `#F1EDFA` con texto `#3B3354` 13/600; filas con `border-top: 1px solid --linea`; fila seleccionada `#F5F0FF` con barra izquierda de 4 px `--violeta-600`. Contenida en un contenedor con `overflow-x: auto` (en móvil scrollea, no se rompe).
- **Barra lateral:** fondo `--tinta` con brillos radiales sutiles; ítems de 44 px, radio 12, texto `--texto-suave-oscuro`; activo con fondo `rgba(139,92,246,.28)`, texto blanco y barra izquierda de 3 px `--naranja-400`. En pantallas angostas se apila arriba.
- **Línea de tiempo (historial de auditoría):** columna con puntos de 14 px unidos por línea de 2 px `--linea`; el más reciente con punto en degradé decorativo. Cada ítem: estado en 600/15 y debajo `fecha hora · usuario` en 13 px `--texto-suave`.
- **Avatar:** círculo con degradé `135deg, #8B5CF6 → #FF8A3D`.

## 5. Marca y ADN

- Logo: cuadrado redondeado (radio ≈ 30 % del lado) con degradé `135deg` y una hélice de **una vuelta** adentro (blanca sobre `violeta→naranja`; tinta sobre `violeta-400→naranja-400` en fondos oscuros), más el texto "Exoma Clínico" en Space Grotesk 600.
- Hélice grande: `dna.svg` (2 hebras con degradé vertical invertido entre sí, peldaños finos y pocos). Se usa grande en ingreso/portadas con `filter: drop-shadow(0 0 16px rgba(139,92,246,.5))`; no repetirla como patrón ni usarla en pantallas de trabajo.

## 6. Layout y responsive

- Pantallas de aplicación son **fluidas**: fila con `flex-wrap`, barra lateral `flex: 1 1 248px`, contenido `flex: 999 1 560px; min-width: 0`.
- Padding de contenido 32–36 px en escritorio; 16 px de gutter en móvil.
- **Vista del transportista: pensada para celular** (ancho 390 px de referencia): una columna, tarjetas apiladas, botones de ancho completo y ≥44 px. Misma paleta, sin barra lateral fija (menú superior o inferior).

## 7. Tono del texto

Español rioplatense, trato de vos ("Ingresá", "¿Olvidaste tu contraseña?"). Directo y corto. Sin signos de exclamación en mensajes de error o de estado.

## 8. Qué evitar

- Verde/celeste como color de marca.
- Texto blanco sobre `--naranja-400` o `--violeta-400` (no pasa contraste).
- Degradés como fondo de áreas de trabajo, texto sobre el degradé decorativo, o más de un degradé grande por pantalla.
- Emojis como íconos. Íconos: trazo de 2 px, esquinas redondeadas, `currentColor`.
- Agregar colores nuevos fuera de esta paleta sin avisar.
