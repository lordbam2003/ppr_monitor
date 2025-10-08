from sqlmodel import SQLModel, Field

class UsuarioPPRAsignacion(SQLModel, table=True):
    """
    Modelo para la relación muchos a muchos entre usuarios y PPRs (Tabla de enlace).
    """
    __tablename__ = "usuarios_ppr_asignaciones"
    
    id_usuario: int = Field(foreign_key="usuarios.id_usuario", primary_key=True)
    id_ppr: int = Field(foreign_key="pprs.id_ppr", primary_key=True)
