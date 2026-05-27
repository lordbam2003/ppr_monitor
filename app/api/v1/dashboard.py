from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Dict, List, Optional
from datetime import datetime

from app.core.security import get_current_active_user
from app.core.database import get_session
from app.models.user import User, InternalRoleEnum
from app.models.ppr import PPR, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR, ProgramacionCEPLAN, Diferencia
from app.schemas.ppr import SubproductAvanceUpdate
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

month_name_map = {
    1: 'ene', 2: 'feb', 3: 'mar', 4: 'abr', 5: 'may', 6: 'jun',
    7: 'jul', 8: 'ago', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dic'
}

# --- Esquemas de Respuesta ---
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
    estado: str
    id_producto: int
    nombre_producto: str
    id_actividad: int
    nombre_actividad: str

class PPRSummaryResponse(BaseModel):
    id_ppr: int
    nombre_ppr: str
    anio: int
    avance_general: float
    subproductos_criticos: int
    subproductos_ok: int
    subproductos_atencion: int
    total_diferencias: int

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

# --- Endpoints ---

@router.get("/admin-stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    year: int,
    month: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Estadísticas globales para Administrador"""
    if current_user.rol not in [InternalRoleEnum.admin, InternalRoleEnum.responsable_planificacion]:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    pprs = session.exec(select(PPR).where(PPR.anio == year)).all()
    if not pprs:
        return AdminStatsResponse(
            total_pprs=0, total_subproductos=0, total_diferencias=0,
            cumplimiento_periodo=0, avance_anual=0, subproductos_en_riesgo=0,
            ppr_performance_ranking=[], alertas_criticas=[]
        )

    ppr_ids = [p.id_ppr for p in pprs]
    ppr_map = {p.id_ppr: p.nombre_ppr for p in pprs}

    subproductos_db = session.exec(
        select(Subproducto, Producto.id_ppr)
        .join(Actividad, Actividad.id_actividad == Subproducto.id_actividad)
        .join(Producto, Producto.id_producto == Actividad.id_producto)
        .where(Producto.id_ppr.in_(ppr_ids))
    ).all()
    
    sub_ids = [s.id_subproducto for s, _ in subproductos_db]
    programaciones = session.exec(
        select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto.in_(sub_ids), ProgramacionPPR.anio == year)
    ).all()
    prog_map = {p.id_subproducto: p for p in programaciones}

    total_prog_p, total_ejec_p, total_meta_a, total_ejec_a, riesgo_count = 0.0, 0.0, 0.0, 0.0, 0
    ppr_stats = {pid: {"prog": 0.0, "ejec": 0.0} for pid in ppr_ids}
    alertas = []
    months_to_date = [month_name_map[m] for m in range(1, month + 1)]
    all_months = [month_name_map[m] for m in range(1, 13)]

    for sub, ppr_id in subproductos_db:
        prog = prog_map.get(sub.id_subproducto)
        if not prog: continue
        sub_prog_p = sum(getattr(prog, f"prog_{m}", 0) or 0 for m in months_to_date)
        sub_ejec_p = sum(getattr(prog, f"ejec_{m}", 0) or 0 for m in months_to_date)
        total_prog_p += sub_prog_p
        total_ejec_p += sub_ejec_p
        ppr_stats[ppr_id]["prog"] += sub_prog_p
        ppr_stats[ppr_id]["ejec"] += sub_ejec_p
        total_meta_a += prog.meta_anual or 0
        sub_ejec_a = sum(getattr(prog, f"ejec_{m}", 0) or 0 for m in all_months)
        total_ejec_a += sub_ejec_a
        cump_sub = (sub_ejec_p / sub_prog_p * 100) if sub_prog_p > 0 else 0
        if sub_prog_p > 0 and cump_sub < 70:
            riesgo_count += 1
            alertas.append(CriticalAlert(subproducto=sub.nombre_subproducto, ppr=ppr_map[ppr_id], programado=sub_prog_p, ejecutado=sub_ejec_p, porcentaje=round(cump_sub, 2)))

    ranking = [PPRPerformance(id_ppr=pid, nombre_ppr=ppr_map[pid], cumplimiento=round((s["ejec"]/s["prog"]*100),2) if s["prog"]>0 else 0) for pid, s in ppr_stats.items()]
    ranking.sort(key=lambda x: x.cumplimiento, reverse=True)
    alertas.sort(key=lambda x: x.porcentaje)
    total_dif = len(session.exec(select(Diferencia).where(Diferencia.anio == year)).all())

    return AdminStatsResponse(
        total_pprs=len(pprs), total_subproductos=len(subproductos_db), total_diferencias=total_dif,
        cumplimiento_periodo=round((total_ejec_p / total_prog_p * 100), 2) if total_prog_p > 0 else 0,
        avance_anual=round((total_ejec_a / total_meta_a * 100), 2) if total_meta_a > 0 else 0,
        subproductos_en_riesgo=riesgo_count, ppr_performance_ranking=ranking, alertas_criticas=alertas[:10]
    )

@router.get("/pprs-assigned", response_model=List[AssignedPPRResponse])
async def get_assigned_pprs(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """PPRs visibles para el usuario"""
    if current_user.rol in [InternalRoleEnum.admin, InternalRoleEnum.responsable_planificacion]:
        pprs = session.exec(select(PPR)).all()
    else:
        from app.models.asignacion import UsuarioPPRAsignacion
        pprs = session.exec(select(PPR).join(UsuarioPPRAsignacion).where(UsuarioPPRAsignacion.id_usuario == current_user.id_usuario)).all()
    return [AssignedPPRResponse(id_ppr=p.id_ppr, codigo_ppr=p.codigo_ppr, nombre_ppr=p.nombre_ppr, anio=p.anio, estado=p.estado, fecha_creacion=p.fecha_creacion) for p in pprs]

@router.get("/assigned-pprs-summary", response_model=List[PPRSummaryResponse])
async def get_assigned_pprs_summary(
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Resumen de PPRs para tabla superior del dashboard"""
    eff_year = year or datetime.now().year
    if current_user.rol in [InternalRoleEnum.admin, InternalRoleEnum.responsable_planificacion]:
        pprs = session.exec(select(PPR).where(PPR.anio == eff_year)).all()
    else:
        from app.models.asignacion import UsuarioPPRAsignacion
        pprs = session.exec(select(PPR).join(UsuarioPPRAsignacion).where(UsuarioPPRAsignacion.id_usuario == current_user.id_usuario, PPR.anio == eff_year)).all()
    
    if not pprs: return []
    ppr_ids = [p.id_ppr for p in pprs]
    
    subproductos_db = session.exec(
        select(Subproducto, Producto.id_ppr)
        .join(Actividad, Actividad.id_actividad == Subproducto.id_actividad)
        .join(Producto, Producto.id_producto == Actividad.id_producto)
        .where(Producto.id_ppr.in_(ppr_ids))
    ).all()
    
    sub_ids = [s.id_subproducto for s, _ in subproductos_db]
    programaciones = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto.in_(sub_ids), ProgramacionPPR.anio == eff_year)).all()
    prog_map = {p.id_subproducto: p for p in programaciones}
    
    from app.services.comparison_service import ComparisonService
    results = []
    all_months = [month_name_map[m] for m in range(1, 13)]

    for ppr in pprs:
        total_p, count_sub, crit, ok, att = 0.0, 0, 0, 0, 0
        p_subproductos = [s for s, pid in subproductos_db if pid == ppr.id_ppr]
        for sub in p_subproductos:
            prog = prog_map.get(sub.id_subproducto)
            if prog and prog.meta_anual and prog.meta_anual > 0:
                ejec_a = sum(getattr(prog, f"ejec_{m}", 0) or 0 for m in all_months)
                cump = (ejec_a / prog.meta_anual) * 100
                total_p += cump
                count_sub += 1
                if cump < 70: crit += 1
                elif cump < 90: att += 1
                else: ok += 1
            else: att += 1
        
        comp_sum = ComparisonService.get_comparison_summary(session, ppr.id_ppr)
        results.append(PPRSummaryResponse(
            id_ppr=ppr.id_ppr, nombre_ppr=ppr.nombre_ppr, anio=ppr.anio,
            avance_general=round(total_p/count_sub, 2) if count_sub > 0 else 0,
            subproductos_criticos=crit, subproductos_ok=ok, subproductos_atencion=att,
            total_diferencias=comp_sum.get("total_differences", 0)
        ))
    return results

@router.get("/ppr/{ppr_id}/metrics", response_model=DashboardMetricsResponse)
async def get_ppr_metrics(
    ppr_id: int, month: Optional[int] = None, year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)
):
    """Métricas de las TARJETAS (Cards) para un PPR específico"""
    ppr = session.get(PPR, ppr_id)
    if not ppr: raise HTTPException(status_code=404, detail="PPR no encontrado")
    eff_year, eff_month = year or ppr.anio, month or datetime.now().month
    
    subproductos = session.exec(select(Subproducto).join(Actividad).join(Producto).where(Producto.id_ppr == ppr_id)).all()
    if not subproductos: return DashboardMetricsResponse(avance_general=0, subproductos_criticos=0, subproductos_ok=0, subproductos_atencion=0)

    total_p, count_s, crit, ok, att = 0.0, 0, 0, 0, 0
    months_to_date = [month_name_map[m] for m in range(1, eff_month + 1)]

    all_months_short = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

    for sub in subproductos:
        # Filtro visibilidad CEPLAN
        cp = session.exec(select(ProgramacionCEPLAN).where(ProgramacionCEPLAN.id_subproducto == sub.id_subproducto, ProgramacionCEPLAN.anio == eff_year)).first()
        if not cp: continue
        meta_c_anual = sum([getattr(cp, f"prog_{m}", 0) or 0 for m in all_months_short])
        if meta_c_anual <= 0: continue
        
        prog = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == sub.id_subproducto, ProgramacionPPR.anio == eff_year)).first()
        if prog:
            p_acum = sum(getattr(prog, f"prog_{m}", 0) or 0 for m in months_to_date)
            e_acum = sum(getattr(prog, f"ejec_{m}", 0) or 0 for m in months_to_date)
            cump = (e_acum / p_acum * 100) if p_acum > 0 else 0
            total_p += cump
            count_s += 1
            if cump < 70: crit += 1
            elif cump < 90: att += 1
            else: ok += 1
        else: att += 1

    return DashboardMetricsResponse(avance_general=round(total_p/count_s, 2) if count_s > 0 else 0, subproductos_criticos=crit, subproductos_ok=ok, subproductos_atencion=att)

@router.get("/ppr/{ppr_id}/subproductos", response_model=List[SubproductoResponse])
async def get_ppr_subproductos(
    ppr_id: int, month: Optional[int] = None, year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)
):
    """Lista de subproductos para la TABLA del responsable"""
    ppr = session.get(PPR, ppr_id)
    if not ppr: raise HTTPException(status_code=404, detail="PPR no encontrado")
    eff_year, eff_month = year or ppr.anio, month or datetime.now().month
    
    # Check permissions
    if current_user.rol not in [InternalRoleEnum.admin, InternalRoleEnum.responsable_planificacion]:
        from app.models.asignacion import UsuarioPPRAsignacion
        asig = session.exec(select(UsuarioPPRAsignacion).where(UsuarioPPRAsignacion.id_ppr == ppr_id, UsuarioPPRAsignacion.id_usuario == current_user.id_usuario)).first()
        if not asig: raise HTTPException(status_code=403, detail="Sin permiso")

    subproductos_db = session.exec(select(Subproducto).join(Actividad).join(Producto).where(Producto.id_ppr == ppr_id)).all()
    result = []
    months_to_date = [month_name_map[m] for m in range(1, eff_month + 1)]
    target_m_str = month_name_map[eff_month]

    for sub in subproductos_db:
        # Visibilidad CEPLAN
        cp = session.exec(select(ProgramacionCEPLAN).where(ProgramacionCEPLAN.id_subproducto == sub.id_subproducto, ProgramacionCEPLAN.anio == eff_year)).first()
        if not cp: continue
        meta_c_a = sum([getattr(cp, f'prog_{m}', 0) or 0 for m in ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']])
        if meta_c_a <= 0: continue

        prog = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == sub.id_subproducto, ProgramacionPPR.anio == eff_year)).first()
        meta_m, e_acum, p_acum = 0.0, 0.0, 0.0
        if prog:
            meta_m = getattr(prog, f"prog_{target_m_str}", 0.0) or 0.0
            e_acum = sum(getattr(prog, f"ejec_{m}", 0.0) or 0.0 for m in months_to_date)
            p_acum = sum(getattr(prog, f"prog_{m}", 0.0) or 0.0 for m in months_to_date)

        cump = (e_acum / p_acum * 100) if p_acum > 0 else 0.0
        if cump < 70: est = "CRÍTICO"
        elif cump < 90: est = "ATENCIÓN"
        else: est = "OK"
        
        act = session.get(Actividad, sub.id_actividad)
        prod = session.get(Producto, act.id_producto) if act else None

        result.append(SubproductoResponse(
            id_subproducto=sub.id_subproducto, codigo_subproducto=sub.codigo_subproducto, nombre_subproducto=sub.nombre_subproducto,
            unidad_medida=sub.unidad_medida, meta_anual=meta_m, avance_actual=e_acum, brecha=p_acum-e_acum, porcentaje_avance=round(cump, 2),
            estado=est, id_producto=prod.id_producto if prod else 0, nombre_producto=prod.nombre_producto if prod else "N/A",
            id_actividad=act.id_actividad if act else 0, nombre_actividad=act.nombre_actividad if act else "N/A"
        ))
    return result

@router.put("/ppr/{subproducto_id}/update-avance")
async def update_subproduct_avance(
    subproducto_id: int, avance_data: SubproductAvanceUpdate,
    current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)
):
    """Actualizar avance mensual"""
    if current_user.rol not in [InternalRoleEnum.admin, InternalRoleEnum.responsable_ppr]:
        raise HTTPException(status_code=403, detail="Sin permiso")

    prog = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == subproducto_id, ProgramacionPPR.anio == avance_data.year)).first()
    if not prog: raise HTTPException(status_code=404, detail="Programación no encontrada")

    m_str = month_name_map.get(avance_data.month)
    if avance_data.prog_mensual is not None: setattr(prog, f"prog_{m_str}", avance_data.prog_mensual)
    if avance_data.ejec_mensual is not None: setattr(prog, f"ejec_{m_str}", avance_data.ejec_mensual)
    prog.fecha_actualizacion = datetime.now()
    session.add(prog)
    session.commit()
    return {"message": "Actualizado"}

@router.get("/ppr/{subproducto_id}/programacion-multi-month", response_model=List[MonthlyAvanceData])
async def get_subproduct_programacion_multi_month(
    subproducto_id: int, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)
):
    """Datos multi-mes para el modal"""
    today = datetime.now()
    c_m, c_y = today.month, today.year
    months_to_fetch = []
    for i in range(3):
        m, y = c_m - i, c_y
        if m <= 0: m += 12; y -= 1
        months_to_fetch.append((m, y))
    
    progs = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == subproducto_id, ProgramacionPPR.anio.in_([y for m, y in months_to_fetch]))).all()
    p_map = {p.anio: p for p in progs}
    res = []
    full_names = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
    for m, y in months_to_fetch:
        p, pm, em = p_map.get(y), 0.0, 0.0
        if p:
            ms = month_name_map.get(m)
            pm = getattr(p, f"prog_{ms}", 0.0) or 0.0
            em = getattr(p, f"ejec_{ms}", 0.0) or 0.0
        res.append(MonthlyAvanceData(month=m, year=y, month_name=full_names.get(m), prog_mensual=pm, ejec_mensual=em))
    return res
