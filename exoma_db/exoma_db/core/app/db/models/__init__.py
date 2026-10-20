"""Importar todos los módulos registra las tablas en Base.metadata (necesario para Alembic)."""
from app.db.models.avisos import Aviso, Configuracion
from app.db.models.clinico import (Familiar, Paciente, Patologia,
                                   PatologiaSintoma, Sintoma, familiar_sintoma,
                                   paciente_sintoma)
from app.db.models.estudios import (Analisis, AnalisisGen, AnalisisPatologia,
                                    AnalisisVariante, Estudio,
                                    EstudioHistorialEstado, Gen)
from app.db.models.logistica import (Lote, OrdenDelDia, OrdenParada,
                                     ParadaEstudio)
from app.db.models.pagos import (Cobertura, Cupon, DocumentacionJudicial,
                                 MovimientoFinanciero, Presupuesto)
from app.db.models.turnos import CentroExtraccion, Feriado, Turno
from app.db.models.usuarios import (CodigoVerificacion, Dispositivo,
                                    Especialidad, GerenteMedico, Medico,
                                    Provincia, Transportista, Usuario,
                                    usuario_especialidad)
