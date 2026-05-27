from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Dict, List, Optional
from datetime import datetime

from app.core.security import get_current_active_user
from app.core.database import get_session
from app.models.user import User, InternalRoleEnum
from app.models.ppr import PPR, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

month_name_map = {
    1: 'ene', 2: 'feb', 3: 'mar', 4: 'abr', 5: 'may', 6: 'jun',
    7: 'jul', 8: 'ago', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dic'
}

# Esquema para respuesta de PPRs asignados
from pydantic import BaseModel
from app.schemas.ppr import SubproductAvanceUpdate

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

from app.services.comparison_service import ComparisonService

class PPRSummaryResponse(BaseModel):
    id_ppr: int
    nombre_ppr: str
    anio: int
    avance_general: float
    subproductos_criticos: int
    subproductos_ok: int
    subproductos_atencion: int
    total_diferencias: int # Nuevo campo para el conteo de discrepancias

class MonthlyAvanceData(BaseModel):
    month: int
    year: int
    month_name: str
    prog_mensual: float
    ejec_mensual: float

class PPRPerformance(BaseModel):
    id_ppr: int
    nombre_ppr: str
    cumplimiento: float

class CriticalAlert(BaseModel):
    subproducto: str
    ppr: str
    programado: float
    ejecutado: float
    porcentaje: float

class AdminStatsResponse(BaseModel):
    total_pprs: int
    total_subproductos: int
    total_diferencias: int
    cumplimiento_periodo: float
    avance_anual: float
    subproductos_en_riesgo: int
    ppr_performance_ranking: List[PPRPerformance]
    alertas_criticas: List[CriticalAlert]

@router.get("/admin-stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    year: int,
    month: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener estadísticas globales para el Dashboard de Administrador (Vista Gerencial)
    """
    if current_user.rol not in [InternalRoleEnum.admin, InternalRoleEnum.responsable_planificacion]:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    # 1. Obtener todos los PPRs del año
    pprs = session.exec(select(PPR).where(PPR.anio == year)).all()
    if not pprs:
        return AdminStatsResponse(
            total_pprs=0, total_subproductos=0, total_diferencias=0,
            cumplimiento_periodo=0, avance_anual=0, subproductos_en_riesgo=0,
            ppr_performance_ranking=[], alertas_criticas=[]
        )

    ppr_ids = [p.id_ppr for p in pprs]
    ppr_map = {p.id_ppr: p.nombre_ppr for p in pprs}

    # 2. Obtener subproductos y programaciones en bloque
    subproductos_query = (
        select(Subproducto, Producto.id_ppr)
        .join(Actividad, Actividad.id_actividad == Subproducto.id_actividad)
        .join(Producto, Producto.id_producto == Actividad.id_producto)
        .where(Producto.id_ppr.in_(ppr_ids))
    )
    subproductos_db = session.exec(subproductos_query).all()
    
    sub_ids = [s.id_subproducto for s, _ in subproductos_db]
    programaciones = session.exec(
        select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto.in_(sub_ids), ProgramacionPPR.anio == year)
    ).all()
    prog_map = {p.id_subproducto: p for p in programaciones}

    # 3. Cálculos Institucionales
    total_prog_periodo = 0.0
    total_ejec_periodo = 0.0
    total_meta_anual = 0.0
    total_ejec_anual = 0.0
    riesgo_count = 0
    
    ppr_stats = {pid: {"prog": 0.0, "ejec": 0.0} for pid in ppr_ids}
    alertas = []

    months_to_date = [month_name_map[m] for m in range(1, month + 1)]
    all_months = [month_name_map[m] for m in range(1, 13)]

    for sub, ppr_id in subproductos_db:
        prog = prog_map.get(sub.id_subproducto)
        if not prog: continue

        # Acumulados del periodo (Ene -> Mes seleccionado)
        sub_prog_p = sum(getattr(prog, f"prog_{m}", 0) or 0 for m in months_to_date)
        sub_ejec_p = sum(getattr(prog, f"ejec_{m}", 0) or 0 for m in months_to_date)
        
        total_prog_periodo += sub_prog_p
        total_ejec_periodo += sub_ejec_p
        
        # Ranking data
        ppr_stats[ppr_id]["prog"] += sub_prog_p
        ppr_stats[ppr_id]["ejec"] += sub_ejec_p

        # Avance Anual
        total_meta_anual += prog.meta_anual or 0
        sub_ejec_total = sum(getattr(prog, f"ejec_{m}", 0) or 0 for m in all_months)
        total_ejec_anual += sub_ejec_total

        # Alertas y Riesgos
        cumplimiento_sub = (sub_ejec_p / sub_prog_p * 100) if sub_prog_p > 0 else 0
        if sub_prog_p > 0 and cumplimiento_sub < 70:
            riesgo_count += 1
            alertas.append(CriticalAlert(
                subproducto=sub.nombre_subproducto,
                ppr=ppr_map[ppr_id],
                programado=sub_prog_p,
                ejecutado=sub_ejec_p,
                porcentaje=round(cumplimiento_sub, 2)
            ))

    # 4. Consolidar Ranking
    ranking = []
    for pid, stats in ppr_stats.items():
        cump = (stats["ejec"] / stats["prog"] * 100) if stats["prog"] > 0 else 0
        ranking.append(PPRPerformance(id_ppr=pid, nombre_ppr=ppr_map[pid], cumplimiento=round(cump, 2)))
    
    ranking.sort(key=lambda x: x.cumplimiento, reverse=True)
    alertas.sort(key=lambda x: x.porcentaje) # Peores primero

    # 5. Conteo de diferencias (PPR vs CEPLAN)
    from app.models.programacion import Diferencia
    total_dif = session.exec(select(Diferencia).where(Diferencia.anio == year)).all()

    return AdminStatsResponse(
        total_pprs=len(pprs),
        total_subproductos=len(subproductos_db),
        total_diferencias=len(total_dif),
        cumplimiento_periodo=round((total_ejec_periodo / total_prog_periodo * 100), 2) if total_prog_periodo > 0 else 0,
        avance_anual=round((total_ejec_anual / total_meta_anual * 100), 2) if total_meta_anual > 0 else 0,
        subproductos_en_riesgo=riesgo_count,
        ppr_performance_ranking=ranking,
        alertas_criticas=alertas[:10] # Top 10 críticas
    )

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
    
    # Si es admin o responsable de planificación, devolver todos los PPRs
    if current_user.rol in [InternalRoleEnum.admin, InternalRoleEnum.responsable_planificacion]:
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


@router.get("/assigned-pprs-summary", response_model=List[PPRSummaryResponse])
async def get_assigned_pprs_summary(
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtiene un resumen de métricas para cada PPR asignado al usuario.
    """
    logger.info(f"User {current_user.email} requesting assigned PPRs summary for year {year}")

    # 1. Obtener los PPRs asignados
    if current_user.rol in [InternalRoleEnum.admin, InternalRoleEnum.responsable_planificacion]:
        statement = select(PPR)
        if year:
            statement = statement.where(PPR.anio == year)
        pprs = session.exec(statement).all()
    else:
        from app.models.asignacion import UsuarioPPRAsignacion
        statement = (
            select(PPR)
            .join(UsuarioPPRAsignacion)
            .where(UsuarioPPRAsignacion.id_usuario == current_user.id_usuario)
        )
        if year:
            statement = statement.where(PPR.anio == year)
        pprs = session.exec(statement).all()
    
    if not pprs:
        return []

    ppr_ids = [ppr.id_ppr for ppr in pprs]
    
    # Diccionario para almacenar las métricas por PPR
    ppr_metrics = {
        ppr.id_ppr: {
            "id_ppr": ppr.id_ppr,
            "nombre_ppr": ppr.nombre_ppr,
            "anio": ppr.anio,
            "total_avance": 0,
            "subproductos_con_avance": 0,
            "subproductos_criticos": 0,
            "subproductos_ok": 0,
            "subproductos_atencion": 0
        } for ppr in pprs
    }
    # 2. Obtener todos los subproductos y sus relaciones en menos consultas
    subproductos_query = (
        select(Subproducto, Producto.id_ppr)
        .join(Actividad, Actividad.id_actividad == Subproducto.id_actividad)
        .join(Producto, Producto.id_producto == Actividad.id_producto)
        .where(Producto.id_ppr.in_(ppr_ids))
    )
    subproductos_results = session.exec(subproductos_query).all()

    if not subproductos_results:
        return [PPRSummaryResponse(avance_general=0, **metrics) for metrics in ppr_metrics.values()]

    subproducto_ids = [sub.id_subproducto for sub, _ in subproductos_results]

    # 3. Obtener todas las programaciones relevantes
    programaciones_query = (
        select(ProgramacionPPR)
        .where(ProgramacionPPR.id_subproducto.in_(subproducto_ids))
    )
    programaciones_results = session.exec(programaciones_query).all()
    
    # Mapear programaciones a subproductos para acceso rápido
    programacion_map = {prog.id_subproducto: prog for prog in programaciones_results}

    # 4. Procesar los datos en memoria
    for subproducto, id_ppr in subproductos_results:
        programacion = programacion_map.get(subproducto.id_subproducto)
        
        if programacion and programacion.meta_anual and programacion.meta_anual > 0:
            avance_total = sum(getattr(programacion, f"ejec_{month_name_map.get(m)}", 0) or 0 for m in range(1, 13))
            avance_porcentaje = (avance_total / programacion.meta_anual) * 100 if avance_total else 0
            
            ppr_metrics[id_ppr]["total_avance"] += avance_porcentaje
            ppr_metrics[id_ppr]["subproductos_con_avance"] += 1
            
            if avance_porcentaje < 70:
                ppr_metrics[id_ppr]["subproductos_criticos"] += 1
            elif avance_porcentaje < 90:
                ppr_metrics[id_ppr]["subproductos_atencion"] += 1
            else:
                ppr_metrics[id_ppr]["subproductos_ok"] += 1
        else:
            ppr_metrics[id_ppr]["subproductos_atencion"] += 1

    # 5. Calcular el avance general y formatear la respuesta final
    summary_list = []
    for ppr_id, metrics in ppr_metrics.items():
        avance_general = 0
        if metrics["subproductos_con_avance"] > 0:
            avance_general = metrics["total_avance"] / metrics["subproductos_con_avance"]
        
        # Obtener el resumen de comparación para este PPR
        comparison_summary = ComparisonService.get_comparison_summary(session, ppr_id)

        summary_list.append(
            PPRSummaryResponse(
                id_ppr=metrics["id_ppr"],
                nombre_ppr=metrics["nombre_ppr"],
                anio=metrics["anio"],
                avance_general=round(avance_general, 2),
                subproductos_criticos=metrics["subproductos_criticos"],
                subproductos_ok=metrics["subproductos_ok"],
                subproductos_atencion=metrics["subproductos_atencion"],
                total_diferencias=comparison_summary.get("total_differences", 0)
            )
        )

    logger.info(f"Successfully generated summary for {len(summary_list)} PPRs for user {current_user.email}")
    return summary_list



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
            month_str = month_name_map.get(month)
            if month_str:
                programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"ejec_{month_str}", None) is not None) # Check if month has data
                # Filter by prog_ value for the selected month if month is provided
                programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"prog_{month_str}", 0) > 0)
            else:
                logger.warning(f"Invalid month number {month} provided for filtering in get_ppr_metrics.")
                continue # Skip this subproduct if month is invalid
        if year is not None:
            programacion_query = programacion_query.where(ProgramacionPPR.anio == year)
        
        programacion = session.exec(programacion_query.order_by(ProgramacionPPR.fecha_actualizacion.desc())).first()
        
        if programacion and programacion.meta_anual and programacion.meta_anual > 0:
            programacion_avance_total = sum(getattr(programacion, f"ejec_{month_name_map.get(month)}", 0) or 0 for month in [1,2,3,4,5,6,7,8,9,10,11,12])
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
            month_str = month_name_map.get(month)
            if month_str:
                programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"ejec_{month_str}", None) is not None) # Check if month has data
                # Filter by prog_ value for the selected month if month is provided
                programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"prog_{month_str}", 0) > 0)
            else:
                logger.warning(f"Invalid month number {month} provided for filtering in get_general_metrics.")
                continue # Skip this subproduct if month is invalid
        if year is not None:
            programacion_query = programacion_query.where(ProgramacionPPR.anio == year)
        
        programacion = session.exec(programacion_query.order_by(ProgramacionPPR.fecha_actualizacion.desc())).first()

        if programacion and programacion.meta_anual and programacion.meta_anual > 0:
            programacion_avance_total = sum(getattr(programacion, f"ejec_{month_name_map.get(month)}", 0) or 0 for month in [1,2,3,4,5,6,7,8,9,10,11,12])
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
            month_str = month_name_map.get(month)
            if month_str:
                programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"ejec_{month_str}", None) is not None) # Check if month has data
                # Filter by prog_ value for the selected month if month is provided
                programacion_query = programacion_query.where(getattr(ProgramacionPPR, f"prog_{month_str}", 0) > 0)
            else:
                logger.warning(f"Invalid month number {month} provided for filtering in get_ppr_subproductos.")
                continue # Skip this subproduct if month is invalid
        if year is not None:
            programacion_query = programacion_query.where(ProgramacionPPR.anio == year)
        
        programacion = session.exec(programacion_query.order_by(ProgramacionPPR.fecha_actualizacion.desc())).first()

        # The following condition was too strict and hid subproducts with no programmed value for the month.
        # It has been removed to ensure all subproducts for the selected PPR are always displayed.
        # if not (programacion and getattr(programacion, f"prog_{month_name_map.get(month)}", 0) > 0):
        #     continue # Skip this subproduct if no valid programacion with prog_ > 0 for the month
        
        # Calcular valores basados en la programación o en el subproducto
        meta_anual = 0
        avance_actual = 0
        
        if programacion:
            meta_anual = programacion.meta_anual or 0
            programacion_avance_total = sum(getattr(programacion, f"ejec_{month_name_map.get(month)}", 0) or 0 for month in [1,2,3,4,5,6,7,8,9,10,11,12]) # Sum all ejec_ for the year
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

@router.put("/ppr/{subproducto_id}/update-avance")
async def update_subproduct_avance(
    subproducto_id: int,
    avance_data: SubproductAvanceUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Actualizar el avance mensual de un subproducto.
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) attempting to update avance for subproducto ID {subproducto_id} for month {avance_data.month}/{avance_data.year}")

    # Verificar que el usuario sea Responsable PPR o Administrador
    if current_user.rol not in [InternalRoleEnum.admin, InternalRoleEnum.responsable_ppr]:
        logger.warning(f"User {current_user.email} attempted to update avance without proper permissions. Role: {current_user.rol}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para actualizar el avance de subproductos"
        )

    # Obtener la programación PPR para el subproducto y año/mes
    programacion = session.exec(
        select(ProgramacionPPR)
        .where(ProgramacionPPR.id_subproducto == subproducto_id)
        .where(ProgramacionPPR.anio == avance_data.year)
    ).first()

    if not programacion:
        logger.warning(f"ProgramacionPPR not found for subproducto ID {subproducto_id} and year {avance_data.year}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Programación PPR no encontrada para el subproducto y año especificados"
        )

    # Construir el nombre del campo de ejecución (ej. 'ejec_ene')
    month_name_map = {
        1: 'ene', 2: 'feb', 3: 'mar', 4: 'abr', 5: 'may', 6: 'jun',
        7: 'jul', 8: 'ago', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dic'
    }
    ejec_field_name = f"ejec_{month_name_map.get(avance_data.month)}"
    prog_field_name = f"prog_{month_name_map.get(avance_data.month)}"

    if not hasattr(programacion, ejec_field_name) or not hasattr(programacion, prog_field_name):
        logger.error(f"Invalid month number {avance_data.month} for execution field name construction.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mes inválido proporcionado"
        )

    # Actualizar valor programado mensual si se proporciona
    if avance_data.prog_mensual is not None:
        setattr(programacion, prog_field_name, avance_data.prog_mensual)

    # Actualizar valor ejecutado mensual si se proporciona
    if avance_data.ejec_mensual is not None:
        setattr(programacion, ejec_field_name, avance_data.ejec_mensual)

    # Actualizar fecha de actualización
    programacion.fecha_actualizacion = datetime.now()

    session.add(programacion)
    session.commit()
    session.refresh(programacion)

    logger.info(f"Successfully updated programacion for subproducto ID {subproducto_id}, month {avance_data.month}/{avance_data.year}. Meta: {programacion.meta_anual}, Avance: {getattr(programacion, ejec_field_name)}")
    return {"message": "Programación actualizada exitosamente"}

@router.get("/ppr/{subproducto_id}/programacion-multi-month", response_model=List[MonthlyAvanceData])
async def get_subproduct_programacion_multi_month(
    subproducto_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Obtener la programación PPR de un subproducto para múltiples meses (actual y los 2 anteriores).
    """
    logger.info(f"User {current_user.nombre} ({current_user.email}) requesting multi-month programacion for subproducto ID {subproducto_id}")

    # Verificar permisos (similar a otros endpoints)
    if current_user.rol not in [InternalRoleEnum.admin, InternalRoleEnum.responsable_ppr, InternalRoleEnum.responsable_planificacion]:
        logger.warning(f"User {current_user.email} attempted to access multi-month programacion without proper permissions. Role: {current_user.rol}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para acceder a esta funcionalidad"
        )

    # Obtener el año actual y el mes actual
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    # Calcular los 3 meses de interés (mes actual y los 2 anteriores)
    months_to_fetch = []
    for i in range(3):
        month_num = current_month - i
        year_num = current_year
        if month_num <= 0:
            month_num += 12
            year_num -= 1
        months_to_fetch.append((month_num, year_num))
    
    # Obtener la programación para el subproducto y los años relevantes
    # Podría haber programaciones en años diferentes si los meses abarcan un cambio de año
    programaciones = session.exec(
        select(ProgramacionPPR)
        .where(ProgramacionPPR.id_subproducto == subproducto_id)
        .where(ProgramacionPPR.anio.in_([y for m, y in months_to_fetch]))
    ).all()

    # Mapear programaciones por año para acceso rápido
    programacion_by_year = {p.anio: p for p in programaciones}

    response_data: List[MonthlyAvanceData] = []
    full_month_names = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    for month_num, year_num in months_to_fetch:
        programacion = programacion_by_year.get(year_num)
        
        prog_mensual = 0.0
        ejec_mensual = 0.0

        if programacion:
            month_str_short = month_name_map.get(month_num)
            if month_str_short:
                prog_mensual = getattr(programacion, f"prog_{month_str_short}", 0.0) or 0.0
                ejec_mensual = getattr(programacion, f"ejec_{month_str_short}", 0.0) or 0.0
        
        response_data.append(
            MonthlyAvanceData(
                month=month_num,
                year=year_num,
                month_name=full_month_names.get(month_num, 'Desconocido'),
                prog_mensual=prog_mensual,
                ejec_mensual=ejec_mensual
            )
        )
    
    return response_data