from enum import Enum

class RoleEnum(str, Enum):
    admin = "admin"
    responsable_ppr = "responsable_ppr"
    responsable_planificacion = "responsable_planificacion"

def get_role_display_name(role_enum):
    """Obtener el nombre amigable para mostrar de un rol"""
    role_display_map = {
        RoleEnum.admin: "Administrador",
        RoleEnum.responsable_ppr: "Responsable PPR",
        RoleEnum.responsable_planificacion: "Responsable Planificación"
    }
    return role_display_map.get(role_enum, str(role_enum))

def get_role_by_display_name(display_name):
    """Obtener el rol enum a partir del nombre amigable"""
    display_to_role_map = {
        "Administrador": RoleEnum.admin,
        "Responsable PPR": RoleEnum.responsable_ppr,
        "Responsable Planificación": RoleEnum.responsable_planificacion,
        "admin": RoleEnum.admin,
        "responsable_ppr": RoleEnum.responsable_ppr,
        "responsable_planificacion": RoleEnum.responsable_planificacion
    }
    return display_to_role_map.get(display_name)

# Test
print("Valores internos del enum:")
for role in RoleEnum:
    print(f"  {role.name} = '{role.value}'")
    print(f"  Nombre amigable: '{get_role_display_name(role)}'")