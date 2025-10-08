from enum import Enum

class InternalRoleEnum(str, Enum):
    admin = "admin"
    responsable_ppr = "responsable_ppr"
    responsable_planificacion = "responsable_planificacion"

def get_display_role(internal_role):
    """Convertir rol interno a rol amigable"""
    mapping = {
        InternalRoleEnum.admin: "Administrador",
        InternalRoleEnum.responsable_ppr: "Responsable PPR",
        InternalRoleEnum.responsable_planificacion: "Responsable Planificación"
    }
    return mapping.get(internal_role, str(internal_role))

def get_internal_role(display_role):
    """Convertir rol amigable a rol interno"""
    reverse_mapping = {
        "Administrador": InternalRoleEnum.admin,
        "Responsable PPR": InternalRoleEnum.responsable_ppr,
        "Responsable Planificación": InternalRoleEnum.responsable_planificacion,
        "admin": InternalRoleEnum.admin,
        "responsable_ppr": InternalRoleEnum.responsable_ppr,
        "responsable_planificacion": InternalRoleEnum.responsable_planificacion
    }
    return reverse_mapping.get(display_role)