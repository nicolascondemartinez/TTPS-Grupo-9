// Logo: cuadrado con degradé y una vuelta de hélice (DESIGN.md §5).
// variante "claro": hélice blanca sobre violeta→naranja (fondos claros).
// variante "oscuro": hélice tinta sobre violeta-400→naranja-400 (fondos oscuros).
export default function Logo({ variante = 'claro', conTexto = true }) {
  const color = variante === 'claro' ? '#FFFFFF' : '#160F2E'
  return (
    <span className={`logo logo--${variante}`}>
      <span className="logo__marca">
        <svg width="16" height="28" viewBox="0 0 120 200" fill="none" aria-hidden="true">
          <path d="M31.7 25H88.3M20 50H100M31.7 75H88.3M31.7 125H88.3M20 150H100M31.7 175H88.3" stroke={color} strokeWidth="10" strokeLinecap="round" opacity="0.8" />
          <path d="M60 0C113 33 113 67 60 100C7 133 7 167 60 200" stroke={color} strokeWidth="15" strokeLinecap="round" />
          <path d="M60 0C7 33 7 67 60 100C113 133 113 167 60 200" stroke={color} strokeWidth="15" strokeLinecap="round" />
        </svg>
      </span>
      {conTexto && <span className="logo__texto">Exoma Clínico</span>}
    </span>
  )
}
