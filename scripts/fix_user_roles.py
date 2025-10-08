#!/usr/bin/env python3
"""
Script para corregir los roles en la base de datos
"""
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel, Session, select
from app.core.database import engine, get_session
from app.models.user import User, InternalRoleEnum as RoleEnum

def fix_user_roles():
    """Corregir los roles de los usuarios en la base de datos"""
    print("Corrigiendo roles de usuarios en la base de datos...")
    
    # Obtener sesión
    session = next(get_session())
    
    # Obtener todos los usuarios
    users = session.exec(select(User)).all()
    
    for user in users:
        print(f"Usuario: {user.nombre} (ID: {user.id_usuario})")
        print(f"Rol actual: '{user.rol}'")
        
        # Verificar si el rol actual es un valor de enum o un nombre de enum
        if hasattr(user.rol, 'name'):
            # Es un objeto enum, obtener su nombre
            rol_nombre = user.rol.name
            rol_valor = user.rol.value
            print(f"Objeto enum detectado - Nombre: {rol_nombre}, Valor: {rol_valor}")
            
            # Actualizar al valor correcto del enum
            if rol_nombre == 'admin':
                nuevo_rol = RoleEnum.admin
            elif rol_nombre == 'responsable_ppr':
                nuevo_rol = RoleEnum.responsable_ppr
            elif rol_nombre == 'responsable_planificacion':
                nuevo_rol = RoleEnum.responsable_planificacion
            else:
                print(f"Rol desconocido: {rol_nombre}")
                continue
            
            user.rol = nuevo_rol
            session.add(user)
            session.commit()
            print(f"Rol actualizado a: '{user.rol}'")
        elif isinstance(user.rol, str):
            # Es una cadena, verificar si coincide con un nombre de enum
            if user.rol == 'admin':
                user.rol = RoleEnum.admin
            elif user.rol == 'responsable_ppr':
                user.rol = RoleEnum.responsable_ppr
            elif user.rol == 'responsable_planificacion':
                user.rol = RoleEnum.responsable_planificacion
            elif user.rol == 'Administrador':
                user.rol = RoleEnum.admin
            elif user.rol == 'Responsable PPR':
                user.rol = RoleEnum.responsable_ppr
            elif user.rol == 'Responsable Planificación':
                user.rol = RoleEnum.responsable_planificacion
            
            session.add(user)
            session.commit()
            print(f"Rol actualizado a: '{user.rol}'")
        else:
            print(f"Tipo de rol desconocido: {type(user.rol)}")
        
        print("-" * 50)
    
    session.close()
    print("Corrección de roles completada.")

if __name__ == "__main__":
    fix_user_roles()