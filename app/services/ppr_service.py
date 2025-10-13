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
