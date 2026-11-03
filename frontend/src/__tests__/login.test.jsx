// Flujo de login contra un backend simulado (fetch falso que respeta el contrato de /api/auth/*).
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { api } from '../api/client.js'
import App from '../App.jsx'
import { destinoTrasIngresar, puedeAcceder } from '../sesion/acceso.js'
import { SesionProvider } from '../sesion/SesionContext.jsx'

const USUARIOS = {
  medico: { id: '1', nombre: 'Marta', apellido: 'Médica', correo: 'medico@exoma.test', rol: 'medico', debe_cambiar_contrasena: false },
  paciente: { id: '2', nombre: 'Paula', apellido: 'Paciente', correo: 'paciente@exoma.test', rol: 'paciente', debe_cambiar_contrasena: false },
}

const respuesta = (status, cuerpo) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => {
    if (cuerpo === undefined) throw new Error('sin cuerpo')
    return cuerpo
  },
})
const error = (status, codigo, detalle = {}) => respuesta(status, { error: { codigo, mensaje: codigo, detalle } })

/** Instala un fetch falso que simula la API. Devuelve las llamadas para poder inspeccionarlas. */
function instalarBackend({ rol = 'medico', dispositivoConocido = true, debeCambiar = false, sesionVencida = false } = {}) {
  let usuario = USUARIOS[rol]
  const llamadas = []
  let intentos = 0
  const permisos = ['aviso_listar']
  const tokenValido = (h) => ['Bearer tok-completo', 'Bearer tok-limitado'].includes(h?.Authorization)

  const fetchFalso = vi.fn(async (url, opciones) => {
    const ruta = url.replace('http://localhost:5001/api', '')
    const cuerpo = opciones.body ? JSON.parse(opciones.body) : undefined
    llamadas.push({ ruta, metodo: opciones.method, cuerpo, headers: opciones.headers })
    if (sesionVencida && opciones.headers.Authorization) return error(401, 'TOKEN_EXPIRADO')

    if (ruta === '/auth/login') {
      usuario = Object.values(USUARIOS).find((u) => u.correo === cuerpo.correo) ?? usuario
      if (cuerpo.contrasena !== 'clave-ok') return error(401, 'CREDENCIALES_INVALIDAS')
      if (debeCambiar) return respuesta(200, { estado: 'cambio_contrasena_requerido', token: 'tok-limitado', usuario, permisos: [] })
      if (dispositivoConocido) return respuesta(200, { estado: 'autenticado', token: 'tok-completo', usuario, permisos })
      return respuesta(200, { estado: 'verificacion_requerida', desafio_id: 'des-1', correo: 'me****@exoma.test' })
    }
    if (ruta === '/auth/verify-device') {
      if (cuerpo.codigo === '123456') return respuesta(200, { estado: 'autenticado', token: 'tok-completo', usuario, permisos })
      intentos += 1
      return intentos >= 5 ? error(401, 'DESAFIO_AGOTADO') : error(401, 'CODIGO_INCORRECTO', { intentos_restantes: 5 - intentos })
    }
    if (ruta === '/auth/change-password') {
      if (opciones.headers.Authorization !== 'Bearer tok-limitado') return error(401, 'TOKEN_INVALIDO')
      if (cuerpo.contrasena_actual !== 'clave-ok') return error(400, 'CONTRASENA_ACTUAL_INCORRECTA')
      return respuesta(200, { estado: 'autenticado', token: 'tok-completo', usuario, permisos })
    }
    if (ruta === '/auth/me') {
      if (!tokenValido(opciones.headers)) return error(401, 'TOKEN_INVALIDO')
      const limitado = opciones.headers.Authorization === 'Bearer tok-limitado'
      return respuesta(200, { estado: limitado ? 'cambio_contrasena_requerido' : 'autenticado', usuario, permisos: limitado ? [] : permisos })
    }
    if (ruta === '/auth/logout') return respuesta(204, undefined)
    return respuesta(200, {})
  })
  vi.stubGlobal('fetch', fetchFalso)
  return llamadas
}

function montar(ruta = '/') {
  return render(
    <SesionProvider>
      <MemoryRouter initialEntries={[ruta]}>
        <App />
      </MemoryRouter>
    </SesionProvider>,
  )
}

async function completarIngreso(user, correo = 'medico@exoma.test', contrasena = 'clave-ok') {
  await user.type(await screen.findByLabelText('Correo electrónico'), correo)
  await user.type(screen.getByLabelText('Contraseña'), contrasena)
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
}

describe('ingreso', () => {
  it('sin sesión redirige al login y, al ingresar, vuelve a la ruta que se intentaba abrir', async () => {
    const llamadas = instalarBackend()
    const user = userEvent.setup()
    montar('/medico/pacientes')
    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()

    await completarIngreso(user)
    expect(await screen.findByText(/En construcción.*\/medico\/pacientes/)).toBeInTheDocument()
    const login = llamadas.find((l) => l.ruta === '/auth/login')
    expect(login.cuerpo).toEqual({ correo: 'medico@exoma.test', contrasena: 'clave-ok' })
    expect(login.headers['X-Device-Id']).toMatch(/.{16,}/)
    expect(login.headers.Authorization).toBeUndefined()
    expect(sessionStorage.getItem('exoma:token')).toBe('tok-completo')
  })

  it('con credenciales incorrectas muestra el error, vacía la contraseña y no guarda ningún token', async () => {
    instalarBackend()
    const user = userEvent.setup()
    montar('/ingreso')
    await completarIngreso(user, 'medico@exoma.test', 'mala')
    expect(await screen.findByRole('alert')).toHaveTextContent('Correo o contraseña incorrectos.')
    expect(screen.getByLabelText('Contraseña')).toHaveValue('')
    expect(sessionStorage.getItem('exoma:token')).toBeNull()
  })

  it('valida en el cliente antes de llamar a la API', async () => {
    const llamadas = instalarBackend()
    const user = userEvent.setup()
    montar('/ingreso')
    await user.click(await screen.findByRole('button', { name: 'Ingresar' }))
    expect(screen.getAllByRole('alert').map((a) => a.textContent)).toEqual(['Ingresá tu correo electrónico.', 'Ingresá tu contraseña.'])
    await user.type(screen.getByLabelText('Correo electrónico'), 'no-es-un-correo')
    await user.click(screen.getByRole('button', { name: 'Ingresar' }))
    expect(screen.getAllByRole('alert')[0]).toHaveTextContent('formato válido')
    expect(llamadas).toHaveLength(0)
  })

  it('si no hay conexión muestra un mensaje claro', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    const user = userEvent.setup()
    montar('/ingreso')
    await completarIngreso(user)
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos conectarnos con el servidor')
  })

  it('el id de dispositivo se genera una vez y se reutiliza', async () => {
    const llamadas = instalarBackend()
    await api.get('/algo')
    await api.get('/algo')
    const ids = llamadas.map((l) => l.headers['X-Device-Id'])
    expect(ids[0]).toBe(ids[1])
    expect(localStorage.getItem('exoma:dispositivo')).toBe(ids[0])
  })
})

describe('dispositivo nuevo', () => {
  it('pide el código, muestra los intentos que quedan y entra con el código correcto', async () => {
    const llamadas = instalarBackend({ dispositivoConocido: false })
    const user = userEvent.setup()
    montar('/medico/estudios')
    await completarIngreso(user)

    expect(await screen.findByRole('heading', { name: 'Verificá tu dispositivo' })).toBeInTheDocument()
    expect(screen.getByText(/me\*\*\*\*@exoma\.test/)).toBeInTheDocument()
    expect(sessionStorage.getItem('exoma:token')).toBeNull() // todavía no hay sesión

    const campo = screen.getByLabelText('Código de verificación')
    await user.type(campo, '12ab34')
    expect(campo).toHaveValue('1234') // solo dígitos
    await user.click(screen.getByRole('button', { name: 'Verificar' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Ingresá los 6 dígitos')

    await user.type(campo, '00')
    await user.click(screen.getByRole('button', { name: 'Verificar' }))
    expect(await screen.findByText('Código incorrecto. Te quedan 4 intentos.')).toBeInTheDocument()

    await user.type(campo, '123456')
    await user.click(screen.getByRole('button', { name: 'Verificar' }))
    expect(await screen.findByText(/En construcción.*\/medico\/estudios/)).toBeInTheDocument()
    const verificacion = llamadas.filter((l) => l.ruta === '/auth/verify-device').at(-1)
    expect(verificacion.cuerpo).toEqual({ desafio_id: 'des-1', codigo: '123456' })
  })

  it('al agotar los intentos bloquea el formulario y ofrece volver a ingresar', async () => {
    instalarBackend({ dispositivoConocido: false })
    const user = userEvent.setup()
    montar('/ingreso')
    await completarIngreso(user)
    const campo = await screen.findByLabelText('Código de verificación')
    for (let i = 0; i < 5; i += 1) {
      await user.type(campo, '000000')
      await user.click(screen.getByRole('button', { name: 'Verificar' }))
      await screen.findByRole('alert')
    }
    expect(await screen.findByText(/Superaste el máximo de intentos/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Verificar' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Volver a ingresar' }))
    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()
  })

  it('sin un desafío en curso vuelve al login', async () => {
    instalarBackend()
    montar('/acceso/verificar')
    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()
  })
})

describe('primer ingreso (cambio de contraseña)', () => {
  it('lleva al cambio de contraseña, valida y, al terminar, entra al inicio de su rol', async () => {
    const llamadas = instalarBackend({ rol: 'paciente', debeCambiar: true })
    const user = userEvent.setup()
    montar('/')
    await completarIngreso(user, 'paciente@exoma.test')
    expect(await screen.findByRole('heading', { name: 'Cambiá tu contraseña' })).toBeInTheDocument()

    const actual = screen.getByLabelText(/Contraseña actual/)
    const nueva = screen.getByLabelText('Contraseña nueva')
    const repetir = screen.getByLabelText('Repetí la contraseña nueva')
    const boton = () => screen.getByRole('button', { name: 'Cambiar contraseña' })

    await user.type(actual, 'clave-ok')
    await user.type(nueva, 'corta')
    await user.click(boton())
    expect(screen.getAllByRole('alert').map((a) => a.textContent).join(' ')).toMatch(/al menos 8 caracteres.*no coincide/)

    await user.clear(nueva)
    await user.type(nueva, 'clave-ok')
    await user.type(repetir, 'clave-ok')
    await user.clear(repetir)
    await user.type(repetir, 'clave-ok')
    await user.click(boton())
    expect(screen.getByRole('alert')).toHaveTextContent('distinta de la actual')

    await user.clear(nueva)
    await user.clear(repetir)
    await user.type(nueva, 'Clave-nueva-2026')
    await user.type(repetir, 'Clave-nueva-2026')
    await user.clear(actual)
    await user.type(actual, 'incorrecta')
    await user.click(boton())
    expect(await screen.findByText('La contraseña actual es incorrecta.')).toBeInTheDocument()
    expect(sessionStorage.getItem('exoma:token')).toBe('tok-limitado') // sigue en sesión limitada, no se cerró

    await user.clear(actual)
    await user.type(actual, 'clave-ok')
    await user.click(boton())
    expect(await screen.findByText(/En construcción.*\/paciente\/estudios/)).toBeInTheDocument()
    const cambio = llamadas.filter((l) => l.ruta === '/auth/change-password').at(-1)
    expect(cambio.cuerpo).toEqual({ contrasena_actual: 'clave-ok', contrasena_nueva: 'Clave-nueva-2026' })
    expect(cambio.headers.Authorization).toBe('Bearer tok-limitado')
  })

  it('con la sesión limitada no se puede abrir el resto de la app: vuelve al cambio de contraseña', async () => {
    instalarBackend({ rol: 'paciente', debeCambiar: true })
    sessionStorage.setItem('exoma:token', 'tok-limitado')
    montar('/paciente/estudios')
    expect(await screen.findByRole('heading', { name: 'Cambiá tu contraseña' })).toBeInTheDocument()
    expect(screen.queryByText(/En construcción/)).not.toBeInTheDocument()
  })

  it('"Cancelar y salir" cierra la sesión limitada y vuelve al login', async () => {
    const llamadas = instalarBackend({ rol: 'paciente', debeCambiar: true })
    sessionStorage.setItem('exoma:token', 'tok-limitado')
    const user = userEvent.setup()
    montar('/acceso/cambiar-contrasena')
    await user.click(await screen.findByRole('button', { name: 'Cancelar y salir' }))
    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()
    expect(llamadas.some((l) => l.ruta === '/auth/logout')).toBe(true)
    expect(sessionStorage.getItem('exoma:token')).toBeNull()
  })
})

describe('sesión guardada y guards', () => {
  it('al recargar con un token guardado lo valida y no pide ingresar de nuevo', async () => {
    const llamadas = instalarBackend()
    sessionStorage.setItem('exoma:token', 'tok-completo')
    montar('/medico/cupones')
    expect(await screen.findByText(/En construcción.*\/medico\/cupones/)).toBeInTheDocument()
    expect(llamadas.find((l) => l.ruta === '/auth/me').headers.Authorization).toBe('Bearer tok-completo')
  })

  it('un token guardado que ya no sirve se descarta y lleva al login', async () => {
    instalarBackend({ sesionVencida: true })
    sessionStorage.setItem('exoma:token', 'tok-viejo')
    montar('/medico/cupones')
    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()
    expect(sessionStorage.getItem('exoma:token')).toBeNull()
  })

  it('cada rol solo entra a su área; las rutas inexistentes dan "Página no encontrada"', async () => {
    instalarBackend({ rol: 'paciente' })
    sessionStorage.setItem('exoma:token', 'tok-completo')
    const { unmount } = montar('/administrativo/lotes')
    expect(await screen.findByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
    unmount()
    const otra = montar('/paciente/turno')
    expect(await screen.findByText(/En construcción.*\/paciente\/turno/)).toBeInTheDocument()
    otra.unmount()
    montar('/avisos')
    expect(await screen.findByText(/En construcción.*\/avisos/)).toBeInTheDocument()
  })

  it('una ruta que no es de ningún rol muestra "Página no encontrada" y no "Acceso denegado"', async () => {
    instalarBackend()
    sessionStorage.setItem('exoma:token', 'tok-completo')
    montar('/cualquier-cosa')
    expect(await screen.findByText(/Página no encontrada/)).toBeInTheDocument()
  })

  it('ante un 401 durante la sesión se cierra la sesión local y se vuelve al login', async () => {
    instalarBackend()
    const user = userEvent.setup()
    montar('/medico/pacientes')
    await completarIngreso(user)
    await screen.findByText(/En construcción/)

    vi.stubGlobal('fetch', vi.fn(async () => error(401, 'TOKEN_EXPIRADO')))
    await act(async () => {
      await expect(api.get('/auth/me')).rejects.toMatchObject({ status: 401 })
    })
    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()
    expect(sessionStorage.getItem('exoma:token')).toBeNull()
  })

  it('cerrar sesión avisa al backend (con el token), borra el token y vuelve al login', async () => {
    const llamadas = instalarBackend()
    const user = userEvent.setup()
    montar('/medico/pacientes')
    await completarIngreso(user)
    await user.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))
    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument()
    const logout = llamadas.find((l) => l.ruta === '/auth/logout')
    expect(logout.metodo).toBe('POST')
    expect(logout.headers.Authorization).toBe('Bearer tok-completo')
    expect(sessionStorage.getItem('exoma:token')).toBeNull()
  })

  it('al cerrar sesión y entrar otra persona con otro rol, no la manda a una ruta que no le corresponde', async () => {
    instalarBackend()
    const user = userEvent.setup()
    montar('/medico/pacientes')
    await completarIngreso(user) // médico
    await user.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))
    await completarIngreso(user, 'paciente@exoma.test') // ahora entra una paciente
    expect(await screen.findByText(/En construcción.*\/paciente\/estudios/)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Acceso denegado' })).not.toBeInTheDocument()
  })

  it('el token nunca aparece en la URL ni en la pantalla', async () => {
    instalarBackend()
    const user = userEvent.setup()
    montar('/medico/pacientes')
    await completarIngreso(user)
    await screen.findByText(/En construcción/)
    expect(document.body.textContent).not.toContain('tok-completo')
    await waitFor(() => expect(window.location.href).not.toContain('tok-completo'))
  })
})

describe('puedeAcceder', () => {
  it('cada rol entra a su área y a /avisos', () => {
    expect(puedeAcceder('medico', '/medico/pacientes/42')).toBe(true)
    expect(puedeAcceder('gerente_medico', '/gerente/patologias')).toBe(true) // el área no se llama como el rol
    expect(puedeAcceder('medico', '/gerente/patologias')).toBe(false)
    expect(puedeAcceder('transportista', '/administrativo/lotes')).toBe(false)
    expect(puedeAcceder('bioinformatico', '/avisos')).toBe(true)
    expect(puedeAcceder('paciente', '/')).toBe(true)
  })

  it('destinoTrasIngresar vuelve a la ruta pedida solo si el rol puede verla', () => {
    const medico = { rol: 'medico' }
    expect(destinoTrasIngresar(medico, { pathname: '/medico/pacientes', search: '?q=1' })).toBe('/medico/pacientes?q=1')
    expect(destinoTrasIngresar(medico, { pathname: '/administrativo/lotes' })).toBe('/')
    expect(destinoTrasIngresar(medico, undefined)).toBe('/')
  })
})
