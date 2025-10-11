from typing import List, Dict, Optional
from sqlmodel import Session, select
from ..models.programacion import ProgramacionPPR, ProgramacionCEPLAN, Diferencia, EstadoDiferencia
from ..models.ppr import Subproducto
from datetime import datetime


class ComparisonService:
    """
    Service for comparing PPR and CEPLAN data to calculate differences
    """
    
    @staticmethod
    def calculate_comparison(session: Session, ppr_id: int):
        """
        Calculate differences between PPR and CEPLAN data for a specific PPR
        """
        # Get all subproductos for this PPR
        from app.models.ppr import Producto, Actividad
        subproductos = session.exec(
            select(Subproducto)
            .join(Actividad, Subproducto.id_actividad == Actividad.id_actividad)
            .join(Producto, Actividad.id_producto == Producto.id_producto)
            .where(Producto.id_ppr == ppr_id)
        ).all()
        
        # Get all PPR and CEPLAN data for these subproductos
        all_ppr_data = session.exec(
            select(ProgramacionPPR).where(
                ProgramacionPPR.id_subproducto.in_([s.id_subproducto for s in subproductos])
            )
        ).all()
        
        all_ceplan_data = session.exec(
            select(ProgramacionCEPLAN).where(
                ProgramacionCEPLAN.id_subproducto.in_([s.id_subproducto for s in subproductos])
            )
        ).all()
        
        # Create lookup dictionaries by subproducto_id and year
        ppr_lookup = {(p.id_subproducto, p.anio): p for p in all_ppr_data}
        ceplan_lookup = {(c.id_subproducto, c.anio): c for c in all_ceplan_data}
        
        # Calculate differences for matching records
        differences_to_create = []
        
        for (subproducto_id, anio), ppr_record in ppr_lookup.items():
            ceplan_record = ceplan_lookup.get((subproducto_id, anio))
            
            if ceplan_record is not None:
                # Calculate differences between PPR and CEPLAN data
                diff = ComparisonService._calculate_differences(ppr_record, ceplan_record)
                
                # Determine the status based on the differences
                estado = ComparisonService._determine_estado(diff)
                
                # Create difference record
                diferencia = Diferencia(
                    id_subproducto=subproducto_id,
                    anio=anio,
                    estado=estado,
                    fecha_creacion=datetime.now(),
                    **diff
                )
                differences_to_create.append(diferencia)
        
        # Delete existing differences for this PPR before adding new ones
        existing_differences = session.exec(
            select(Diferencia).where(
                Diferencia.id_subproducto.in_([s.id_subproducto for s in subproductos])
            )
        ).all()
        
        for existing_diff in existing_differences:
            session.delete(existing_diff)
        
        # Store the calculated differences
        for diff in differences_to_create:
            session.add(diff)
        
        session.commit()
        
        return {
            "message": f"Comparison completed. Created {len(differences_to_create)} difference records.",
            "total_differences": len(differences_to_create)
        }
    
    @staticmethod
    def _calculate_differences(ppr_record: ProgramacionPPR, ceplan_record: ProgramacionCEPLAN) -> Dict:
        """
        Calculate differences between PPR and CEPLAN monthly values
        """
        differences = {}
        
        # Define monthly fields to compare
        months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 
                  'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        
        for month in months:
            # Calculate difference for programacion
            ppr_prog = getattr(ppr_record, f'prog_{month}', None)
            ceplan_prog = getattr(ceplan_record, f'prog_{month}', None)
            
            if ppr_prog is not None and ceplan_prog is not None:
                differences[f'dif_prog_{month}'] = ppr_prog - ceplan_prog
            else:
                differences[f'dif_prog_{month}'] = None
            
            # Calculate difference for ejecucion
            ppr_ejec = getattr(ppr_record, f'ejec_{month}', None)
            ceplan_ejec = getattr(ceplan_record, f'ejec_{month}', None)
            
            if ppr_ejec is not None and ceplan_ejec is not None:
                differences[f'dif_ejec_{month}'] = ppr_ejec - ceplan_ejec
            else:
                differences[f'dif_ejec_{month}'] = None
        
        return differences
    
    @staticmethod
    def _determine_estado(differences: Dict) -> EstadoDiferencia:
        """
        Determine the status of a difference based on threshold values
        """
        # Check if any difference value is significantly non-zero (>0.1 or <-0.1)
        threshold = 0.1
        for key, value in differences.items():
            if value is not None and abs(value) > threshold:
                return EstadoDiferencia.alerta
        
        # If no significant differences, mark as OK
        return EstadoDiferencia.ok
    
    @staticmethod
    def get_comparison_results(session: Session, ppr_id: int):
        """
        Get comparison results for a specific PPR
        """
        from app.models.ppr import Producto, Actividad
        subproductos = session.exec(
            select(Subproducto)
            .join(Actividad, Subproducto.id_actividad == Actividad.id_actividad)
            .join(Producto, Actividad.id_producto == Producto.id_producto)
            .where(Producto.id_ppr == ppr_id)
        ).all()
        
        subproducto_ids = [s.id_subproducto for s in subproductos]
        
        diferencias = session.exec(
            select(Diferencia).where(
                Diferencia.id_subproducto.in_(subproducto_ids)
            )
        ).all()
        
        # Join with subproducto and programming data to get names, codes, and meta_anual
        results = []
        months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'] # Define months here for use in filtering
        for diff in diferencias:
            # Check if there are any non-zero differences for this subproduct
            has_non_zero_diff = False
            for month in months:
                if (getattr(diff, f'dif_prog_{month}', 0) or 0) != 0 or (getattr(diff, f'dif_ejec_{month}', 0) or 0) != 0:
                    has_non_zero_diff = True
                    break
            
            if not has_non_zero_diff:
                continue # Skip this subproduct if all differences are zero

            subproducto = session.get(Subproducto, diff.id_subproducto)
            ppr_prog = session.exec(select(ProgramacionPPR).where(ProgramacionPPR.id_subproducto == diff.id_subproducto, ProgramacionPPR.anio == diff.anio)).first()
            ceplan_prog = session.exec(select(ProgramacionCEPLAN).where(ProgramacionCEPLAN.id_subproducto == diff.id_subproducto, ProgramacionCEPLAN.anio == diff.anio)).first()

            ceplan_meta_anual_calculated = 0
            if ceplan_prog:
                ceplan_meta_anual_calculated = sum([getattr(ceplan_prog, f'prog_{m}', 0) or 0 for m in months])

            results.append({
                "id_diferencia": diff.id_diferencia,
                "id_subproducto": diff.id_subproducto,
                "codigo_subproducto": subproducto.codigo_subproducto if subproducto else None,
                "nombre_subproducto": subproducto.nombre_subproducto if subproducto else None,
                "anio": diff.anio,
                "estado": diff.estado,
                "ppr_meta_anual": ppr_prog.meta_anual if ppr_prog else 0,
                "ceplan_meta_anual": ceplan_meta_anual_calculated,
                "ppr_programado_mensual": {m: getattr(ppr_prog, f'prog_{m}', 0) or 0 for m in months} if ppr_prog else {m: 0 for m in months},
                "ppr_ejecutado_mensual": {m: getattr(ppr_prog, f'ejec_{m}', 0) or 0 for m in months} if ppr_prog else {m: 0 for m in months},
                "ceplan_programado_mensual": {m: getattr(ceplan_prog, f'prog_{m}', 0) or 0 for m in months} if ceplan_prog else {m: 0 for m in months},
                "ceplan_ejecutado_mensual": {m: getattr(ceplan_prog, f'ejec_{m}', 0) or 0 for m in months} if ceplan_prog else {m: 0 for m in months},
                "diferencias": {
                    "ene": {
                        "prog": diff.dif_prog_ene,
                        "ejec": diff.dif_ejec_ene
                    },
                    "feb": {
                        "prog": diff.dif_prog_feb,
                        "ejec": diff.dif_ejec_feb
                    },
                    "mar": {
                        "prog": diff.dif_prog_mar,
                        "ejec": diff.dif_ejec_mar
                    },
                    "abr": {
                        "prog": diff.dif_prog_abr,
                        "ejec": diff.dif_ejec_abr
                    },
                    "may": {
                        "prog": diff.dif_prog_may,
                        "ejec": diff.dif_ejec_may
                    },
                    "jun": {
                        "prog": diff.dif_prog_jun,
                        "ejec": diff.dif_ejec_jun
                    },
                    "jul": {
                        "prog": diff.dif_prog_jul,
                        "ejec": diff.dif_ejec_jul
                    },
                    "ago": {
                        "prog": diff.dif_prog_ago,
                        "ejec": diff.dif_ejec_ago
                    },
                    "sep": {
                        "prog": diff.dif_prog_sep,
                        "ejec": diff.dif_ejec_sep
                    },
                    "oct": {
                        "prog": diff.dif_prog_oct,
                        "ejec": diff.dif_ejec_oct
                    },
                    "nov": {
                        "prog": diff.dif_prog_nov,
                        "ejec": diff.dif_ejec_nov
                    },
                    "dic": {
                        "prog": diff.dif_prog_dic,
                        "ejec": diff.dif_ejec_dic
                    },
                },
                "fecha_creacion": diff.fecha_creacion
            })
        
        return results
    
    @staticmethod
    def get_comparison_summary(session: Session, ppr_id: int):
        """
        Get summary of comparison results for a specific PPR
        """
        results = ComparisonService.get_comparison_results(session, ppr_id)
        
        total = len(results)
        ok_count = sum(1 for r in results if r['estado'] == EstadoDiferencia.ok)
        alert_count = sum(1 for r in results if r['estado'] == EstadoDiferencia.alerta)
        pending_count = sum(1 for r in results if r['estado'] == EstadoDiferencia.pendiente_revision)
        
        return {
            "total_differences": total,
            "ok": ok_count,
            "alert": alert_count,
            "pending_review": pending_count,
            "completion_percentage": (ok_count + alert_count + pending_count) / total * 100 if total > 0 else 0
        }