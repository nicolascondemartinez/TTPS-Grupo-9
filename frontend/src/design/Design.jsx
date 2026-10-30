import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import AdnHelice from '../components/AdnHelice.jsx'
import Boton from '../components/Boton.jsx'
import Campo from '../components/Campo.jsx'
import Chip from '../components/Chip.jsx'
import EncabezadoPagina from '../components/EncabezadoPagina.jsx'
import EstadoChip from '../components/EstadoChip.jsx'
import Icono from '../components/Icono.jsx'
import LineaDeTiempo from '../components/LineaDeTiempo.jsx'
import Logo from '../components/Logo.jsx'
import ModalConfirmacion from '../components/ModalConfirmacion.jsx'
import Monto from '../components/Monto.jsx'
import { useNotificar } from '../components/Notificaciones.jsx'
import SubirArchivo from '../components/SubirArchivo.jsx'
import Tabla from '../components/Tabla.jsx'
import Tarjeta from '../components/Tarjeta.jsx'
import { ESTADOS_ESTUDIO } from '../constants/estados.js'

// Catálogo de la base de frontend: muestra cada componente y cómo usarlo.
// Datos de ejemplo solamente.
const FILAS = [
  { id: 1, codigo: 'EST-0001', paciente: 'Apellido, Nombre', estado: 'turno_sacado', fecha: '30/10/2026' },
  { id: 2, codigo: 'EST-0002', paciente: 'Apellido, Nombre', estado: 'esperando_autorizacion', fecha: '29/10/2026' },
  { id: 3, codigo: 'EST-0003', paciente: 'Apellido, Nombre', estado: 'finalizado', fecha: '28/10/2026' },
]
const HISTORIAL = [
  { id: 3, titulo: 'Turno sacado', fecha: '30/10/2026 10:15', usuario: 'Paciente' },
  { id: 2, titulo: 'Pagado', fecha: '29/10/2026 18:02', usuario: 'Paciente' },
  { id: 1, titulo: 'Creado', fecha: '28/10/2026 09:40', usuario: 'Médico tratante' },
]

function Seccion({ etiqueta, titulo, codigo, children }) {
  return (
    <section className="design__seccion">
      <div>
        <span className="etiqueta">{etiqueta}</span>
        <h2>{titulo}</h2>
      </div>
      {children}
      {codigo && <pre>{codigo}</pre>}
    </section>
  )
}

export default function Design() {
  const [api_estado, setApiEstado] = useState('consultando…')
  const [seleccionada, setSeleccionada] = useState(1)
  const [modalAbierto, setModalAbierto] = useState(false)
  const notificar = useNotificar()

  useEffect(() => {
    api.get('/health').then((d) => setApiEstado(d.status)).catch(() => setApiEstado('sin conexión'))
  }, [])

  return (
    <div className="design">
      <div className="design__fila" style={{ justifyContent: 'space-between' }}>
        <Logo />
        <span className="tarjeta__subtitulo">API: {api_estado} · <Link to="/">Ir a la app</Link> · <Link to="/ingreso">Ver ingreso</Link></span>
      </div>

      <EncabezadoPagina etiqueta="Base de frontend" titulo="Componentes" />
      <p>Guía completa de estilo en <code>docs/diseno/DESIGN.md</code>. Cada bloque muestra el componente y cómo usarlo.</p>

      <Seccion etiqueta="01" titulo="Botones" codigo={`<Boton>Guardar</Boton>\n<Boton variante="secundario">Filtrar</Boton>\n<Boton variante="ghost">Cancelar</Boton>`}>
        <div className="design__fila">
          <Boton>Guardar</Boton>
          <Boton variante="secundario">Filtrar</Boton>
          <Boton variante="ghost">Cancelar</Boton>
          <Boton icono={<Icono nombre="mas" />}>Nuevo estudio</Boton>
          <Boton disabled>Deshabilitado</Boton>
        </div>
      </Seccion>

      <Seccion etiqueta="02" titulo="Campos" codigo={`<Campo etiqueta="Correo electrónico" type="email" />\n<Campo etiqueta="Buscar" etiquetaOculta icono="buscar" />\n<Campo etiqueta="Provincia" opciones={[{ valor: 'ba', texto: 'Buenos Aires' }]} />`}>
        <div className="design__grilla">
          <Campo etiqueta="Correo electrónico" type="email" placeholder="nombre@dominio.com" />
          <Campo etiqueta="DNI" ayuda="Sin puntos" placeholder="30111222" />
          <Campo etiqueta="Contraseña" type="password" error="La contraseña es incorrecta" />
          <Campo etiqueta="Buscar estudio" etiquetaOculta icono="buscar" placeholder="Buscar por paciente, DNI o número" />
          <Campo etiqueta="Provincia" opciones={[{ valor: 'ba', texto: 'Buenos Aires' }, { valor: 'cba', texto: 'Córdoba' }]} />
        </div>
      </Seccion>

      <Seccion etiqueta="03" titulo="Estados del estudio" codigo={`<EstadoChip estado={estudio.estado} />   // valor del backend, ej. "turno_sacado"\n<Chip tipo="atencion">Texto libre</Chip>`}>
        <div className="design__fila">
          {Object.keys(ESTADOS_ESTUDIO).map((e) => <EstadoChip key={e} estado={e} />)}
        </div>
        <div className="design__fila">
          <Chip tipo="neutro">Neutro</Chip><Chip tipo="curso">En curso</Chip><Chip tipo="atencion">Atención</Chip>
          <Chip tipo="error">Error</Chip><Chip tipo="listo">Completado</Chip>
        </div>
      </Seccion>

      <Seccion etiqueta="04" titulo="Tabla y tarjeta con historial" codigo={`<Tabla columnas={[{ clave: 'codigo', titulo: 'Estudio' }, ...]} filas={estudios}\n       seleccionadaId={id} onSeleccionar={(fila) => ...} />\n<Tarjeta titulo="Historial de cambios" subtitulo="EST-0001" filo>\n  <LineaDeTiempo items={historial} />\n</Tarjeta>`}>
        <div className="design__fila" style={{ alignItems: 'flex-start' }}>
          <div style={{ flex: '999 1 480px', minWidth: 0 }}>
            <Tabla
              titulo="Estudios"
              columnas={[
                { clave: 'codigo', titulo: 'Estudio', render: (f) => <strong>{f.codigo}</strong> },
                { clave: 'paciente', titulo: 'Paciente' },
                { clave: 'estado', titulo: 'Estado', render: (f) => <EstadoChip estado={f.estado} /> },
                { clave: 'fecha', titulo: 'Último cambio' },
              ]}
              filas={FILAS}
              seleccionadaId={seleccionada}
              onSeleccionar={(f) => setSeleccionada(f.id)}
            />
          </div>
          <div style={{ flex: '1 1 260px', minWidth: 0 }}>
            <Tarjeta titulo="Historial de cambios" subtitulo="EST-0001" filo>
              <LineaDeTiempo items={HISTORIAL} />
            </Tarjeta>
          </div>
        </div>
      </Seccion>

      <Seccion etiqueta="05" titulo="Encabezado de pantalla" codigo={`<EncabezadoPagina etiqueta="Seguimiento" titulo="Estudios">\n  <Boton>Nuevo estudio</Boton>\n</EncabezadoPagina>`}>
        <EncabezadoPagina etiqueta="Seguimiento" titulo="Estudios"><Boton>Nuevo estudio</Boton></EncabezadoPagina>
      </Seccion>

      <Seccion etiqueta="06" titulo="Íconos" codigo={`<Icono nombre="calendario" />   // nombres en components/Icono.jsx`}>
        <div className="design__fila">
          {['lista', 'persona', 'calendario', 'tarjeta', 'caja', 'reloj', 'buscar', 'campana', 'documento', 'chat', 'cupon', 'escudo', 'camion', 'adn', 'menu', 'cerrar', 'mas'].map((n) => (
            <span key={n} title={n}><Icono nombre={n} tamano={24} /></span>
          ))}
        </div>
      </Seccion>

      <Seccion etiqueta="07" titulo="Marca" codigo={`<Logo />                    // fondos claros\n<Logo variante="oscuro" />  // fondos oscuros\n<AdnHelice />               // solo ingreso y portadas`}>
        <div className="design__oscuro fondo-oscuro">
          <Logo variante="oscuro" />
          <AdnHelice alto={200} />
          <span className="etiqueta">Fondo oscuro con brillos</span>
        </div>
      </Seccion>

      <Seccion etiqueta="08" titulo="Layouts" codigo={`// Pantallas internas: agregar la ruta dentro de <AppLayout> en App.jsx\n// Pantallas de acceso: <IngresoLayout> {formulario} </IngresoLayout>`}>
        <p>La app interna usa <code>AppLayout</code> (barra lateral con el menú del rol, definido en <code>constants/roles.js</code>). Las pantallas de acceso usan <code>IngresoLayout</code>.</p>
      </Seccion>
      
      <Seccion etiqueta="09" titulo="Montos, archivos, confirmaciones y avisos" codigo={`<Monto valor={estudio.monto} />          // "590.00" se ve como "USD 590"\nformatearUSD(552.5)                        // "USD 552,50", para usar dentro de un texto\n\n<SubirArchivo etiqueta="Resolución judicial" onChange={(archivo) => setArchivo(archivo)} />\n\n<ModalConfirmacion abierto={abierto} titulo="¿Cancelar el turno?" peligro\n  textoConfirmar="Cancelar turno" onConfirmar={cancelar} onCancelar={() => setAbierto(false)}>\n  El turno queda libre para otra persona.\n</ModalConfirmacion>\n\nconst notificar = useNotificar()\nnotificar('Pago registrado')               // tipos: exito (por defecto) | error | info`}>
        <div className="design__fila">
          <Monto valor="500.00" /><Monto valor={590} /><Monto valor={1250} /><Monto valor="552.5" />
        </div>
        <div className="design__grilla">
          <SubirArchivo etiqueta="Resolución judicial" onChange={(a) => a && notificar(`Archivo elegido: ${a.name}`, 'info')} />
        </div>
        <div className="design__fila">
          <Boton variante="secundario" onClick={() => setModalAbierto(true)}>Abrir confirmación</Boton>
          <Boton variante="secundario" onClick={() => notificar('Pago registrado')}>Aviso de éxito</Boton>
          <Boton variante="secundario" onClick={() => notificar('No se pudo guardar el pago', 'error')}>Aviso de error</Boton>
        </div>
        <ModalConfirmacion
          abierto={modalAbierto} titulo="¿Cancelar el turno?" peligro textoConfirmar="Cancelar turno"
          onConfirmar={() => { setModalAbierto(false); notificar('Turno cancelado') }}
          onCancelar={() => setModalAbierto(false)}
        >
          El turno del lunes 10 de noviembre a las 9:15 queda libre. Vas a poder sacar otro.
        </ModalConfirmacion>
      </Seccion>
    </div>
  )
}
