// Íconos de trazo (2 px, esquinas redondeadas, currentColor). Ver DESIGN.md §8.
// Para sumar uno: agregar su dibujo (viewBox 0 0 24 24) a TRAZOS.
const TRAZOS = {
  lista: <path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />,
  persona: <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" /></>,
  calendario: <><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M3 10h18M8 3v4M16 3v4" /></>,
  tarjeta: <><rect x="2" y="5" width="20" height="14" rx="3" /><path d="M2 10h20" /></>,
  caja: <path d="M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8" />,
  reloj: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  buscar: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>,
  campana: <path d="M6 9a6 6 0 0 1 12 0c0 5 2 7 2 7H4s2-2 2-7M10 20a2 2 0 0 0 4 0" />,
  documento: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></>,
  chat: <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />,
  cupon: <><path d="M3 9V7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a3 3 0 0 0 0 6v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a3 3 0 0 0 0-6z" /><path d="M10 9h.01M14 15h.01M14 9l-4 6" /></>,
  escudo: <path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z" />,
  camion: <><path d="M3 6h11v10H3zM14 10h4l3 3v3h-7" /><circle cx="7" cy="18" r="2" /><circle cx="17" cy="18" r="2" /></>,
  adn: <path d="M7 3c0 6 10 6 10 12 0 3-2 5-2 6M17 3c0 6-10 6-10 12 0 3 2 5 2 6M8 7h8M8 17h8" />,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  cerrar: <path d="M6 6l12 12M18 6L6 18" />,
  mas: <path d="M12 5v14M5 12h14" />,
}

export default function Icono({ nombre, tamano = 20, titulo }) {
  return (
    <svg
      width={tamano} height={tamano} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden={titulo ? undefined : true} role={titulo ? 'img' : undefined}
    >
      {titulo && <title>{titulo}</title>}
      {TRAZOS[nombre]}
    </svg>
  )
}
