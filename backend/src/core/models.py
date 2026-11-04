"""Importar todos los modelos registra las tablas en Base.metadata (lo necesita create_all)."""
from src.core.auth.models import Permiso, RolPermiso, Sesion
from src.core.avisos.models import Aviso, Configuracion
from src.core.clinico.models import (Familiar, Paciente, Patologia,
                                   PatologiaSintoma, Sintoma, familiar_sintoma,
                                   paciente_sintoma)
from src.core.estudios.models import (Analisis, AnalisisGen, AnalisisPatologia,
                                    AnalisisVariante, Estudio,
                                    EstudioHistorialEstado, Gen)
from src.core.logistica.models import (Lote, OrdenDelDia, OrdenParada,
                                     ParadaEstudio)
from src.core.pagos.models import (Cobertura, Cupon, DocumentacionJudicial,
                                 MovimientoFinanciero, Presupuesto)
from src.core.turnos.models import CentroExtraccion, Feriado, Turno
from src.core.usuarios.models import (CodigoVerificacion, Dispositivo,
                                    Especialidad, GerenteMedico, Medico,
                                    Provincia, Transportista, Usuario,
                                    usuario_especialidad)
