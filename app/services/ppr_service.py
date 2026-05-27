from typing import List, Dict
from datetime import datetime
from sqlmodel import Session, select
from app.models.ppr import PPR, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR, ProgramacionCEPLAN
from app.core.logging_config import get_logger
from app.schemas.ppr import SubproductProgrammingUpdate

logger = get_logger(__name__)

def delete_ppr_data_by_year(year: int, session: Session) -> int:
    """
    Deletes all PPR data for a given year.
    """
    logger.info(f"Attempting to delete all PPR data for year {year}")

    # Find all PPRs for the given year
    pprs_to_delete = session.exec(select(PPR).where(PPR.anio == year)).all()
    
    if not pprs_to_delete:
        logger.warning(f"No PPRs found for year {year} to delete.")
        return 0

    deleted_ppr_count = 0
    for ppr in pprs_to_delete:
        logger.info(f"Deleting PPR {ppr.id_ppr} ('{ppr.nombre_ppr}') and all related data.")
        
        # Find all products related to the PPR
        productos = session.exec(select(Producto).where(Producto.id_ppr == ppr.id_ppr)).all()
        for producto in productos:
            # Find all activities related to the product
            actividades = session.exec(select(Actividad).where(Actividad.id_producto == producto.id_producto)).all()
            for actividad in actividades:
                # Find all subproducts related to the activity
                subproductos = session.exec(select(Subproducto).where(Subproducto.id_actividad == actividad.id_actividad)).all()
                for subproducto in subproductos:
                    # Delete programming data
                    prog_ppr = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == subproducto.id_subproducto)).all()
                    for prog in prog_ppr:
                        session.delete(prog)
                    
                    prog_ceplan = session.exec(select(ProgramacionCEPLAN).where(ProgramacionCEPLAN.id_subproducto == subproducto.id_subproducto)).all()
                    for prog in prog_ceplan:
                        session.delete(prog)
                    
                    session.delete(subproducto)
                session.delete(actividad)
            session.delete(producto)
        
        session.delete(ppr)
        deleted_ppr_count += 1

    session.commit()
    logger.info(f"Successfully deleted {deleted_ppr_count} PPRs and their related data for year {year}.")
    return deleted_ppr_count

def synchronize_ppr_with_cartera(year: int, session: Session) -> Dict:
    """
    Synchronizes the PPR structure with the Cartera de Servicios for a given year.
    It creates missing Programs, Products, Activities, and Subproducts,
    and initializes programming tables with zero values for new subproducts.
    Existing records are not modified.
    """
    from app.models.cartera_servicios import CarteraServicios
    
    logger.info(f"Synchronizing PPR structure with Cartera for year {year}")

    # 1. Get all Cartera records for the year
    cartera_records = session.exec(
        select(CarteraServicios).where(CarteraServicios.anio == year)
    ).all()

    if not cartera_records:
        logger.warning(f"No Cartera records found for year {year} to synchronize.")
        return {"created_pprs": [], "total_new_subproducts": 0, "message": "No hay datos en la cartera para sincronizar."}

    # Tracking metrics
    new_ppr_count = 0
    new_subproduct_count = 0
    synced_ppr_ids = []

    # 2. Group by hierarchy and process
    # We iterate through each record to ensure the full path exists
    for record in cartera_records:
        # A. Find or Create PPR
        ppr = session.exec(
            select(PPR).where(PPR.codigo_ppr == record.programa_codigo, PPR.anio == year)
        ).first()

        if not ppr:
            ppr = PPR(
                codigo_ppr=record.programa_codigo,
                nombre_ppr=record.programa_nombre,
                anio=year,
                estado="activo"
            )
            session.add(ppr)
            session.flush() # Get ID
            new_ppr_count += 1
            logger.info(f"Created new PPR: {ppr.codigo_ppr}")
        
        if ppr.id_ppr not in synced_ppr_ids:
            synced_ppr_ids.append(ppr.id_ppr)

        # B. Find or Create Producto
        producto = session.exec(
            select(Producto).where(
                Producto.codigo_producto == record.producto_codigo,
                Producto.id_ppr == ppr.id_ppr
            )
        ).first()

        if not producto:
            producto = Producto(
                codigo_producto=record.producto_codigo,
                nombre_producto=record.producto_nombre,
                id_ppr=ppr.id_ppr
            )
            session.add(producto)
            session.flush()
            logger.info(f"Created new Producto: {producto.codigo_producto} for PPR {ppr.codigo_ppr}")

        # C. Find or Create Actividad
        actividad = session.exec(
            select(Actividad).where(
                Actividad.codigo_actividad == record.actividad_codigo,
                Actividad.id_producto == producto.id_producto
            )
        ).first()

        if not actividad:
            actividad = Actividad(
                codigo_actividad=record.actividad_codigo,
                nombre_actividad=record.actividad_nombre,
                id_producto=producto.id_producto
            )
            session.add(actividad)
            session.flush()
            logger.info(f"Created new Actividad: {actividad.codigo_actividad} for Producto {producto.codigo_producto}")

        # D. Find or Create Subproducto
        subproducto = session.exec(
            select(Subproducto).where(
                Subproducto.codigo_subproducto == record.sub_producto_codigo,
                Subproducto.id_actividad == actividad.id_actividad
            )
        ).first()

        if not subproducto:
            subproducto = Subproducto(
                codigo_subproducto=record.sub_producto_codigo,
                nombre_subproducto=record.sub_producto_nombre,
                unidad_medida=record.unidad_medida,
                id_actividad=actividad.id_actividad
            )
            session.add(subproducto)
            session.flush()
            new_subproduct_count += 1
            logger.info(f"Created new Subproducto: {subproducto.codigo_subproducto}")

            # E. Initialize Programming (PPR and CEPLAN) for NEW subproducts only
            session.add(ProgramacionPPR(
                id_subproducto=subproducto.id_subproducto,
                anio=year,
                meta_anual=0.0,
                prog_ene=0.0, ejec_ene=0.0, prog_feb=0.0, ejec_feb=0.0, prog_mar=0.0, ejec_mar=0.0,
                prog_abr=0.0, ejec_abr=0.0, prog_may=0.0, ejec_may=0.0, prog_jun=0.0, ejec_jun=0.0,
                prog_jul=0.0, ejec_jul=0.0, prog_ago=0.0, ejec_ago=0.0, prog_sep=0.0, ejec_sep=0.0,
                prog_oct=0.0, ejec_oct=0.0, prog_nov=0.0, ejec_nov=0.0, prog_dic=0.0, ejec_dic=0.0
            ))
            
            session.add(ProgramacionCEPLAN(
                id_subproducto=subproducto.id_subproducto,
                anio=year,
                prog_ene=0.0, ejec_ene=0.0, prog_feb=0.0, ejec_feb=0.0, prog_mar=0.0, ejec_mar=0.0,
                prog_abr=0.0, ejec_abr=0.0, prog_may=0.0, ejec_may=0.0, prog_jun=0.0, ejec_jun=0.0,
                prog_jul=0.0, ejec_jul=0.0, prog_ago=0.0, ejec_ago=0.0, prog_sep=0.0, ejec_sep=0.0,
                prog_oct=0.0, ejec_oct=0.0, prog_nov=0.0, ejec_nov=0.0, prog_dic=0.0, ejec_dic=0.0
            ))

    session.commit()
    logger.info(f"Synchronization complete for year {year}. New PPRs: {new_ppr_count}, New Subproducts: {new_subproduct_count}")
    
    return {
        "new_pprs": new_ppr_count,
        "new_subproducts": new_subproduct_count,
        "total_synced_pprs": len(synced_ppr_ids),
        "message": f"Sincronización exitosa para {year}: {new_ppr_count} PPR(s) nuevos y {new_subproduct_count} subproducto(s) añadidos."
    }

def sync_ppr_with_ceplan_data(year: int, session: Session) -> Dict:
    """
    Sincroniza los valores PROGRAMADOS de CEPLAN hacia la tabla de PPR.
    Copia los campos prog_ene...prog_dic y actualiza la meta_anual.
    """
    logger.info(f"Iniciando sincronización masiva de metas CEPLAN -> PPR para el año {year}")
    
    # 1. Obtener todas las programaciones de CEPLAN para el año
    ceplan_records = session.exec(
        select(ProgramacionCEPLAN).where(ProgramacionCEPLAN.anio == year)
    ).all()
    
    if not ceplan_records:
        return {"count": 0, "message": f"No se encontraron datos de CEPLAN para el año {year}"}
    
    updated_count = 0
    months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    
    for cp in ceplan_records:
        # 2. Buscar el registro PPR correspondiente
        ppr_prog = session.exec(
            select(ProgramacionPPR).where(
                ProgramacionPPR.id_subproducto == cp.id_subproducto,
                ProgramacionPPR.anio == year
            )
        ).first()
        
        if ppr_prog:
            # 3. Copiar valores de programación
            total_meta = 0.0
            for m in months:
                val = getattr(cp, f"prog_{m}", 0.0) or 0.0
                setattr(ppr_prog, f"prog_{m}", val)
                total_meta += val
            
            ppr_prog.meta_anual = total_meta
            ppr_prog.fecha_actualizacion = datetime.now()
            session.add(ppr_prog)
            updated_count += 1
            
    session.commit()
    logger.info(f"Sincronización CEPLAN -> PPR completada. {updated_count} subproductos actualizados.")
    
    return {
        "count": updated_count,
        "message": f"Se han sincronizado las metas de {updated_count} subproductos desde CEPLAN para el año {year}."
    }

def update_subproduct_programming(subproducto_id: int, data: SubproductProgrammingUpdate, session: Session):
    logger.info(f"Updating programming for subproduct {subproducto_id}")

    if data.ppr:
        ppr_programacion = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == subproducto_id)).first()
        if ppr_programacion:
            if data.ppr.get('programado'):
                for month, value in data.ppr['programado'].items():
                    setattr(ppr_programacion, f'prog_{month}', float(value))
            if data.ppr.get('ejecutado'):
                for month, value in data.ppr['ejecutado'].items():
                    setattr(ppr_programacion, f'ejec_{month}', float(value))
            session.add(ppr_programacion)

    session.commit()
