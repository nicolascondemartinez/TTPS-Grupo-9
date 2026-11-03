import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { ROLES } from '../constants/roles.js'
import { clearToken, getToken, onNoAutorizado, setToken } from './almacen.js'

// Sesión del usuario, disponible en toda la app con useSesion().
//
// estado:  'cargando'                    comprobando si hay una sesión guardada
//          'anonimo'                     sin sesión
//          'cambio_contrasena_requerido' primer ingreso: solo puede cambiar la contraseña
//          'autenticado'                 sesión completa
//
// MODO DESARROLLO SIN BACKEND: con VITE_SESION_DEV=true en .env.local se mantiene el comportamiento
// provisorio de antes (usuario de prueba + selector de rol en la barra lateral), para armar pantallas
// sin tener la API levantada. Por defecto está apagado y se usa el login real.
const SesionContext = createContext(null)
const CLAVE_ROL = 'exoma:rol-dev'
const MODO_DEV = import.meta.env.DEV && import.meta.env.VITE_SESION_DEV === 'true'

// El backend devuelve nombre y apellido por separado; las pantallas muestran `nombre` completo.
const aUsuario = (u) => ({ ...u, nombre: `${u.nombre} ${u.apellido}`.trim() })

function useSesionReal() {
  const [estado, setEstado] = useState(() => (getToken() ? 'cargando' : 'anonimo'))
  const [usuario, setUsuario] = useState(null)
  const [permisos, setPermisos] = useState([])

  const abrir = useCallback((respuesta) => {
    setToken(respuesta.token)
    setUsuario(aUsuario(respuesta.usuario))
    setPermisos(respuesta.permisos ?? [])
    setEstado(respuesta.estado)
  }, [])

  const limpiar = useCallback(() => {
    clearToken()
    setUsuario(null)
    setPermisos([])
    setEstado('anonimo')
  }, [])

  // Al cargar la app: si quedó un token en la pestaña, se valida con el backend
  useEffect(() => {
    if (!getToken()) return
    api.get('/auth/me')
      .then((r) => {
        setUsuario(aUsuario(r.usuario))
        setPermisos(r.permisos ?? [])
        setEstado(r.estado)
      })
      .catch(limpiar)
  }, [limpiar])

  // Ante un 401 en cualquier pedido autenticado: sesión local cerrada (el guard redirige al login)
  useEffect(() => onNoAutorizado(limpiar), [limpiar])

  // Devuelve la respuesta del backend; `estado` indica cómo sigue el flujo:
  // 'autenticado' | 'cambio_contrasena_requerido' | 'verificacion_requerida' (con desafio_id y correo)
  const ingresar = useCallback(async (correo, contrasena) => {
    const r = await api.post('/auth/login', { correo, contrasena })
    if (r.estado !== 'verificacion_requerida') abrir(r)
    return r
  }, [abrir])

  const verificarCodigo = useCallback(async (desafioId, codigo) => {
    const r = await api.post('/auth/verify-device', { desafio_id: desafioId, codigo })
    abrir(r)
    return r
  }, [abrir])

  const cambiarContrasena = useCallback(async (actual, nueva) => {
    const r = await api.post('/auth/change-password', { contrasena_actual: actual, contrasena_nueva: nueva })
    abrir(r)
    return r
  }, [abrir])

  const cerrarSesion = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // aunque el backend no responda, la sesión local se cierra igual
    }
    limpiar()
  }, [limpiar])

  return { estado, usuario, permisos, ingresar, verificarCodigo, cambiarContrasena, cerrarSesion, cambiarRol: () => {}, modoDev: false }
}

function useSesionDev() {
  const [rol, setRol] = useState(() => {
    const guardado = localStorage.getItem(CLAVE_ROL)
    return guardado in ROLES ? guardado : 'administrativo'
  })
  const cambiarRol = (nuevo) => {
    localStorage.setItem(CLAVE_ROL, nuevo)
    setRol(nuevo)
  }
  const noDisponible = async () => {
    throw new Error('Modo desarrollo: no hay login (VITE_SESION_DEV=true)')
  }
  return {
    estado: 'autenticado', usuario: { nombre: 'Usuario de prueba', rol }, permisos: [], cambiarRol, modoDev: true,
    ingresar: noDisponible, verificarCodigo: noDisponible, cambiarContrasena: noDisponible, cerrarSesion: async () => {},
  }
}

export function SesionProvider({ children }) {
  const real = useSesionReal()
  const dev = useSesionDev()
  return <SesionContext.Provider value={MODO_DEV ? dev : real}>{children}</SesionContext.Provider>
}

export function useSesion() {
  return useContext(SesionContext)
}
