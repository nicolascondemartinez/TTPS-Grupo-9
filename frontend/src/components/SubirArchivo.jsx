import { useId, useRef, useState } from 'react'
import Icono from './Icono.jsx'

// Subida de un archivo PDF (cupón, resolución judicial, datos crudos)
// Se puede elegir con el botón o arrastrar el archivo, valida tipo y tamaño antes de avisar
// onChange recibe el archivo (File) o null si se quita
// valida que sea PDF y que no supere maxMB (por defecto 5 MB)
export default function SubirArchivo({ etiqueta, ayuda = 'Solo PDF, hasta 5 MB.', maxMB = 5, error, onChange }) {
  const id = useId() //id de uso para identificar los elementos del componente
  const input = useRef(null) //es una forma de agarrar el input de tipo file para poder resetearlo cuando se quita el archivo
  //3 estados: null si no hay archivo y file si hay archivo, error y arrastrando para cuando la persona esta arrastrando el archivo
  const [archivo, setArchivo] = useState(null)
  const [errorLocal, setErrorLocal] = useState(null)
  const [arrastrando, setArrastrando] = useState(false)

  //elegir un archivo con las validaciones, es la fx que se ejecuta cunado llega un archivo
  const elegir = (nuevo) => {
    if (!nuevo) return ///si no hay archivo no hace nada
    if (nuevo.type !== 'application/pdf') { //si no es pdf tira error
      setErrorLocal('El archivo tiene que ser un PDF.')
      return
    }
    if (nuevo.size > maxMB * 1024 * 1024) { //si pesa mas de lo permitido tira error
      setErrorLocal(`El archivo supera los ${maxMB} MB.`)
      return
    }
    //si paso todos los controles, limpia el error y setea el archivo
    setErrorLocal(null)
    setArchivo(nuevo) 
    onChange?.(nuevo)
  }
  //borrar el archivo, limpia el input y llama a onChange con null
  const quitar = () => {
    setArchivo(null)
    input.current.value = ''
    onChange?.(null)
  }
  //decide que error mostrar
  const mensajeError = errorLocal ?? error

  //el dibujo tiene 2 versiones: si hay archivo elegido muestra el nombre y un boton para quitarlo, si no hay archivo muestra la zona de arrastre y el boton para elegir
  return (
    <div className="campo-grupo">
      <span className="campo-grupo__label" id={`${id}-etiqueta`}>{etiqueta}</span>
      {archivo ? (
        <div className="subir__elegido">
          <Icono nombre="documento" />
          <span className="subir__nombre">{archivo.name}</span>
          <button type="button" className="enlace" onClick={quitar}>Quitar</button>
        </div>
      ) : (
        <div
          className={`subir__zona${arrastrando ? ' subir__zona--activa' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setArrastrando(true) }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={(e) => { e.preventDefault(); setArrastrando(false); elegir(e.dataTransfer.files[0]) }}
        >
          <Icono nombre="documento" tamano={24} />
          <span>Arrastrá el archivo acá o</span>
          <label htmlFor={id} className="btn btn-secundario subir__boton">Elegir PDF</label>
          <input
            ref={input} id={id} type="file" accept="application/pdf" className="sr-only"
            aria-labelledby={`${id}-etiqueta`} aria-describedby={`${id}-ayuda`}
            onChange={(e) => elegir(e.target.files[0])}
          />
        </div>
      )}
      <span id={`${id}-ayuda`} className={mensajeError ? 'campo-grupo__error' : 'campo-grupo__ayuda'}>
        {mensajeError ?? ayuda}
      </span>
    </div>
  )
}
