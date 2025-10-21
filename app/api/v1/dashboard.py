from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from app.core.security import get_current_active_user
from app.core.database import get_session
from app.models.user import User, InternalRoleEnum
from app.models.ppr import PPR, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Esquema para respuesta de PPRs asignados
from pydantic import BaseModel

class AssignedPPRResponse(BaseModel):
    id_ppr: int
    codigo_ppr: str
    nombre_ppr: str
    anio: int
    estado: Optional[str] = None
    fecha_creacion: Optional[datetime] = None

class DashboardMetricsResponse(BaseModel):
    avance_general: float
    subproductos_criticos: int
    subproductos_ok: int
    subproductos_atencion: int

class SubproductoResponse(BaseModel):
    id_subproducto: int
    codigo_subproducto: str
    nombre_subproducto: str
    unidad_medida: Optional[str] = None
    meta_anual: Optional[float] = None
    avance_actual: Optional[float] = None
    brecha: Optional[float] = None
    porcentaje_avance: float
    estado: str  # "OK", "ATENCIÓN", "CRÍTICO"
    id_producto: int
    nombre_producto: str
    id_actividad: int
    nombre_actividad: str

class PPRSubproductosResponse(BaseModel):
    ppr_info: AssignedPPRResponse
    subproductos: List[SubproductoResponse]

@router.get("/pprs-assigned", response_model=List[AssignedPPRResponse])
async def get_assigned_pprs(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener PPRs asignados al usuario actual
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requesting assigned PPRs")
    
    # Verificar que el usuario sea Responsable PPR o Administrador
    if current_user.rol not in [InternalRoleEnum.admin, InternalRoleEnum.responsable_ppr, InternalRoleEnum.responsable_planificacion]:
        logger.warning(f"User {current_user.email} attempted to access assigned PPRs without proper permissions. Role: {current_user.rol}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para acceder a esta funcionalidad"
        )
    
    # Si es admin, devolver todos los PPRs
    if current_user.rol == InternalRoleEnum.admin:
        pprs = session.exec(select(PPR)).all()
    else:
        # Para otros roles, devolver solo los PPRs asignados
        # La relación está definida en el modelo PPR con el campo responsables
        # Accedemos a través de una relación muchos a muchos
        from app.models.asignacion import UsuarioPPRAsignacion
        statement = (
            select(PPR)
            .join(UsuarioPPRAsignacion)
            .where(UsuarioPPRAsignacion.id_usuario == current_user.id_usuario)
        )
        pprs = session.exec(statement).all()
    
    result = []
    for ppr in pprs:
        ppr_response = AssignedPPRResponse(
            id_ppr=ppr.id_ppr,
            codigo_ppr=ppr.codigo_ppr,
            nombre_ppr=ppr.nombre_ppr,
            anio=ppr.anio,
            estado=ppr.estado,
            fecha_creacion=ppr.fecha_creacion
        )
        result.append(ppr_response)
    
    logger.info(f"Successfully retrieved {len(result)} assigned PPRs for user {current_user.email}")
    return result

@router.get("/ppr/{ppr_id}/metrics", response_model=DashboardMetricsResponse)
async def get_ppr_metrics(
    ppr_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener métricas resumidas de un PPR
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requesting metrics for PPR ID {ppr_id}")
    
    # Verificar permisos para acceder a este PPR
    from app.models.asignacion import UsuarioPPRAsignacion
    if current_user.rol != InternalRoleEnum.admin:
        # Verificar que el PPR esté asignado al usuario
        asignacion = session.exec(
            select(UsuarioPPRAsignacion)
            .where(UsuarioPPRAsignacion.id_ppr == ppr_id)
            .where(UsuarioPPRAsignacion.id_usuario == current_user.id_usuario)
        ).first()
        
        if not asignacion:
            logger.warning(f"User {current_user.email} attempted to access unauthorized PPR ID {ppr_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para acceder a este PPR"
            )
    
    # Verificar que el PPR existe
    ppr = session.get(PPR, ppr_id)
    if not ppr:
        logger.warning(f"User {current_user.email} requested non-existent PPR ID {ppr_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PPR no encontrado"
        )
    
    # Obtener subproductos del PPR
    # Primero obtenemos todos los subproductos asociados a este PPR a través de productos y actividades
    subproductos_query = (
        select(Subproducto)
        .join(Actividad, Actividad.id_actividad == Subproducto.id_actividad)
        .join(Producto, Producto.id_producto == Actividad.id_producto)
        .where(Producto.id_ppr == ppr_id)
    )
    subproductos = session.exec(subproductos_query).all()
    
    if not subproductos:
        logger.info(f"No subproductos found for PPR ID {ppr_id}")
        return DashboardMetricsResponse(
            avance_general=0.0,
            subproductos_criticos=0,
            subproductos_ok=0,
            subproductos_atencion=0
        )
    
    # Calcular métricas
    total_avance = 0
    subproductos_con_avance = 0
    subproductos_criticos = 0
    subproductos_ok = 0
    subproductos_atencion = 0
    
    for subproducto in subproductos:
        # Obtener la programación más reciente para este subproducto
        programacion_query = select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == subproducto.id_subproducto)
        if month is not None:
            programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"ejec_{month}", None) is not None) # Check if month has data
        if year is not None:
            programacion_query = programacion_query.where(ProgramacionPPR.anio == year)
        programacion_query = programacion_query.where(ProgramacionPPR.meta_anual > 0) # Filter for meta_anual > 0
        
        programacion = session.exec(programacion_query.order_by(ProgramacionPPR.fecha_actualizacion.desc())).first()
        
        if programacion and programacion.meta_anual and programacion.meta_anual > 0:
            programacion_avance_total = sum(getattr(programacion, f"ejec_{month}", 0) or 0 for month in ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"])
            avance_porcentaje = (programacion_avance_total / programacion.meta_anual) * 100 if programacion_avance_total else 0
            total_avance += avance_porcentaje
            subproductos_con_avance += 1
            
            # Clasificar según porcentaje de avance
            if avance_porcentaje < 70:
                subproductos_criticos += 1
            elif avance_porcentaje < 90:
                subproductos_atencion += 1
            else:
                subproductos_ok += 1
        else:
            # Si no hay meta, no se puede calcular el porcentaje, considerar como ATENCIÓN
            subproductos_atencion += 1
    
    # Calcular avance general promedio
    avance_general = (total_avance / subproductos_con_avance) if subproductos_con_avance > 0 else 0
    
    logger.info(f"Successfully calculated metrics for PPR ID {ppr_id}: "
                f"avance_general={avance_general:.2f}, "
                f"subproductos_criticos={subproductos_criticos}, "
                f"subproductos_ok={subproductos_ok}, "
                f"subproductos_atencion={subproductos_atencion}")
    
    return DashboardMetricsResponse(
        avance_general=round(avance_general, 2),
        subproductos_criticos=subproductos_criticos,
        subproductos_ok=subproductos_ok,
        subproductos_atencion=subproductos_atencion
    )


@router.get("/ppr/metrics", response_model=DashboardMetricsResponse)
async def get_general_metrics(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener métricas generales de todos los PPRs asignados al usuario
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requesting general metrics for all assigned PPRs")

    # Obtener los IDs de los PPRs asignados al usuario
    from app.models.asignacion import UsuarioPPRAsignacion
    if current_user.rol != InternalRoleEnum.admin:
        # Verificar PPRs asignados al usuario
        asignaciones = session.exec(
            select(UsuarioPPRAsignacion)
            .where(UsuarioPPRAsignacion.id_usuario == current_user.id_usuario)
        ).all()
        ppr_ids = [a.id_ppr for a in asignaciones]
    else:
        # Si es admin, obtener todos los PPRs
        all_pprs = session.exec(select(PPR)).all()
        ppr_ids = [ppr.id_ppr for ppr in all_pprs]

    if not ppr_ids:
        logger.info(f"No PPRs assigned to user {current_user.email}")
        return DashboardMetricsResponse(
            avance_general=0.0,
            subproductos_criticos=0,
            subproductos_ok=0,
            subproductos_atencion=0
        )

    # Obtener todos los subproductos de los PPRs asignados
    subproductos_query = (
        select(Subproducto)
        .join(Actividad, Actividad.id_actividad == Subproducto.id_actividad)
        .join(Producto, Producto.id_producto == Actividad.id_producto)
        .where(Producto.id_ppr.in_(ppr_ids))
    )
    subproductos_db = session.exec(subproductos_query).all()

    if not subproductos_db:
        logger.info(f"No subproductos found for user {current_user.email}'s assigned PPRs")
        return DashboardMetricsResponse(
            avance_general=0.0,
            subproductos_criticos=0,
            subproductos_ok=0,
            subproductos_atencion=0
        )

    # Calcular métricas generales
    total_avance = 0
    subproductos_con_avance = 0
    subproductos_criticos = 0
    subproductos_ok = 0
    subproductos_atencion = 0    
    
    for subproducto in subproductos_db:
        # Obtener la programación más reciente para este subproducto
        programacion_query = select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == subproducto.id_subproducto)
        if month is not None:
            programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"ejec_{month}", None) is not None) # Check if month has data
        if year is not None:
            programacion_query = programacion_query.where(ProgramacionPPR.anio == year)
        programacion_query = programacion_query.where(ProgramacionPPR.meta_anual > 0) # Filter for meta_anual > 0
        
        programacion = session.exec(programacion_query.order_by(ProgramacionPPR.fecha_actualizacion.desc())).first()

        if programacion and programacion.meta_anual and programacion.meta_anual > 0:
            programacion_avance_total = sum(getattr(programacion, f"ejec_{month}", 0) or 0 for month in ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"])
            avance_porcentaje = (programacion_avance_total / programacion.meta_anual) * 100 if programacion_avance_total else 0
            total_avance += avance_porcentaje
            subproductos_con_avance += 1

            # Clasificar según porcentaje de avance
            if avance_porcentaje < 70:
                subproductos_criticos += 1
            elif avance_porcentaje < 90:
                subproductos_atencion += 1
            else:
                subproductos_ok += 1
        else:
            # Si no hay meta, no se puede calcular el porcentaje, considerar como ATENCIÓN
            subproductos_atencion += 1

    # Calcular avance general promedio
    avance_general = (total_avance / subproductos_con_avance) if subproductos_con_avance > 0 else 0

    logger.info(f"Successfully calculated general metrics for user {current_user.email}: "
                f"avance_general={avance_general:.2f}, "
                f"subproductos_criticos={subproductos_criticos}, "
                f"subproductos_ok={subproductos_ok}, "
                f"subproductos_atencion={subproductos_atencion}")

    return DashboardMetricsResponse(
        avance_general=round(avance_general, 2),
        subproductos_criticos=subproductos_criticos,
        subproductos_ok=subproductos_ok,
        subproductos_atencion=subproductos_atencion
    )
@router.get("/ppr/{ppr_id}/subproductos", response_model=List[SubproductoResponse])
async def get_ppr_subproductos(
    ppr_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener subproductos de un PPR con sus métricas
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requesting subproducts for PPR ID {ppr_id}")
    
    # Verificar permisos para acceder a este PPR
    from app.models.asignacion import UsuarioPPRAsignacion
    if current_user.rol != InternalRoleEnum.admin:
        # Verificar que el PPR esté asignado al usuario
        asignacion = session.exec(
            select(UsuarioPPRAsignacion)
            .where(UsuarioPPRAsignacion.id_ppr == ppr_id)
            .where(UsuarioPPRAsignacion.id_usuario == current_user.id_usuario)
        ).first()
        
        if not asignacion:
            logger.warning(f"User {current_user.email} attempted to access unauthorized PPR ID {ppr_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para acceder a este PPR"
            )
    
    # Verificar que el PPR existe
    ppr = session.get(PPR, ppr_id)
    if not ppr:
        logger.warning(f"User {current_user.email} requested non-existent PPR ID {ppr_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PPR no encontrado"
        )
    
    # Obtener subproductos del PPR con sus productos y actividades
    subproductos_query = (
        select(Subproducto)
        .join(Actividad, Actividad.id_actividad == Subproducto.id_actividad)
        .join(Producto, Producto.id_producto == Actividad.id_producto)
        .where(Producto.id_ppr == ppr_id)
    )
    subproductos_db = session.exec(subproductos_query).all()
    
    result = []
    for subproducto in subproductos_db:
        # Obtener datos del producto y actividad
        actividad = session.get(Actividad, subproducto.id_actividad)
        producto = session.get(Producto, actividad.id_producto) if actividad else None
        
        # Obtener la programación más reciente para este subproducto
        programacion_query = select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == subproducto.id_subproducto)
        if month is not None:
            programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"ejec_{month}", None) is not None) # Check if month has data
        if year is not None:
            programacion_query = programacion_query.where(ProgramacionPPR.anio == year)
        programacion_query = programacion_query.where(ProgramacionPPR.meta_anual > 0) # Filter for meta_anual > 0
        
        programacion = session.exec(programacion_query.order_by(ProgramacionPPR.fecha_actualizacion.desc())).first()
        
        # Calcular valores basados en la programación o en el subproducto
        meta_anual = 0
        avance_actual = 0
        
        if programacion:
            meta_anual = programacion.meta_anual or 0
            programacion_avance_total = sum(getattr(programacion, f"ejec_{month}", 0) or 0 for month in ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"])
            avance_actual = programacion_avance_total or 0

        
        # Calcular brecha y porcentaje de avance
        brecha = meta_anual - avance_actual if meta_anual > 0 else 0
        porcentaje_avance = (avance_actual / meta_anual * 100) if meta_anual > 0 else 0
        
        # Determinar estado según porcentaje de avance
        if porcentaje_avance < 70:
            estado = "CRÍTICO"
        elif porcentaje_avance < 90:
            estado = "ATENCIÓN"
        else:
            estado = "OK"
        
        subproducto_response = SubproductoResponse(
            id_subproducto=subproducto.id_subproducto,
            codigo_subproducto=subproducto.codigo_subproducto,
            nombre_subproducto=subproducto.nombre_subproducto,
            unidad_medida=subproducto.unidad_medida,
            meta_anual=meta_anual,
            avance_actual=avance_actual,
            brecha=brecha,
            porcentaje_avance=round(porcentaje_avance, 2),
            estado=estado,
            id_producto=producto.id_producto if producto else 0,
            nombre_producto=producto.nombre_producto if producto else "N/A",
            id_actividad=actividad.id_actividad if actividad else 0,
            nombre_actividad=actividad.nombre_actividad if actividad else "N/A"
        )
        
        result.append(subproducto_response)
    
    logger.info(f"Successfully retrieved {len(result)} subproducts for PPR ID {ppr_id}")
    return result

@router.get("/subproductos", response_model=List[SubproductoResponse])
async def get_all_assigned_subproductos(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener todos los subproductos de los PPRs asignados al usuario
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requesting all assigned subproducts")
    
    # Obtener los IDs de los PPRs asignados al usuario
    from app.models.asignacion import UsuarioPPRAsignacion
    if current_user.rol != InternalRoleEnum.admin:
        # Verificar PPRs asignados al usuario
        asignaciones = session.exec(
            select(UsuarioPPRAsignacion)
            .where(UsuarioPPRAsignacion.id_usuario == current_user.id_usuario)
        ).all()
        ppr_ids = [a.id_ppr for a in asignaciones]
    else:
        # Si es admin, obtener todos los PPRs
        all_pprs = session.exec(select(PPR)).all()
        ppr_ids = [ppr.id_ppr for ppr in all_pprs]
    
    if not ppr_ids:
        logger.info(f"No PPRs assigned to user {current_user.email}")
        return []
    
    # Obtener todos los subproductos de los PPRs asignados
    subproductos_query = (
        select(Subproducto)
        .join(Actividad, Actividad.id_actividad == Subproducto.id_actividad)
        .join(Producto, Producto.id_producto == Actividad.id_producto)
        .where(Producto.id_ppr.in_(ppr_ids))
    )
    subproductos_db = session.exec(subproductos_query).all()
    
    result = []
    for subproducto in subproductos_db:
        # Obtener datos del producto y actividad
        actividad = session.get(Actividad, subproducto.id_actividad)
        producto = session.get(Producto, actividad.id_producto) if actividad else None
        
        # Obtener la programación más reciente para este subproducto
        programacion = session.exec(
            select(ProgramacionPPR)
            .where(ProgramacionPPR.id_subproducto == subproducto.id_subproducto)
            .order_by(ProgramacionPPR.fecha_actualizacion.desc())
        ).first()
        
        # Calcular valores basados en la programación o en el subproducto
        meta_anual = 0
        avance_actual = 0
        
        if programacion:
            meta_anual = programacion.meta_anual or 0
            avance_actual = programacion.avance_total or 0
        elif subproducto.meta_anual is not None:
            meta_anual = float(subproducto.meta_anual)
            avance_actual = float(subproducto.avance_actual or 0)
        
        # Calcular brecha y porcentaje de avance
        brecha = meta_anual - avance_actual if meta_anual > 0 else 0
        porcentaje_avance = (avance_actual / meta_anual * 100) if meta_anual > 0 else 0
        
        # Determinar estado según porcentaje de avance
        if porcentaje_avance < 70:
            estado = "CRÍTICO"
        elif porcentaje_avance < 90:
            estado = "ATENCIÓN"
        else:
            estado = "OK"
        
        subproducto_response = SubproductoResponse(
            id_subproducto=subproducto.id_subproducto,
            codigo_subproducto=subproducto.codigo_subproducto,
            nombre_subproducto=subproducto.nombre_subproducto,
            unidad_medida=subproducto.unidad_medida,
            meta_anual=meta_anual,
            avance_actual=avance_actual,
            brecha=brecha,
            porcentaje_avance=round(porcentaje_avance, 2),
            estado=estado,
            id_producto=producto.id_producto if producto else 0,
            nombre_producto=producto.nombre_producto if producto else "N/A",
            id_actividad=actividad.id_actividad if actividad else 0,
            nombre_actividad=actividad.nombre_actividad if actividad else "N/A"
        )
        
        result.append(subproducto_response)
    
    logger.info(f"Successfully retrieved {len(result)} subproducts for user {current_user.email}")
    return result