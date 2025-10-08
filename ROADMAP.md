# Roadmap del Sistema de Monitoreo PPR

## Visión General
El Sistema de Monitoreo PPR tiene como objetivo principal proveer una plataforma completa para el monitoreo y seguimiento de Programas Presupuestales (PPR) y su comparación con datos oficiales de CEPLAN, permitiendo a los responsables actualizar información mensualmente y generar reportes detallados.

## Estado Actual (Versión 1.0)
Funcionalidades completadas y en producción:
- ✅ Autenticación y autorización con JWT
- ✅ Gestión de usuarios y roles (Administrador, Responsable PPR, Responsable Planificación)
- ✅ Estructura jerárquica completa (PPR → Producto → Actividad → Subproducto)
- ✅ Carga de archivos Excel PPR y CEPLAN
- ✅ Extractor inteligente con detección dinámica de estructura
- ✅ Cartera de servicios funcional
- ✅ Visualización jerárquica en modo acordeón
- ✅ API RESTful completa
- ✅ Frontend responsive con Bootstrap 5
- ✅ Migraciones de base de datos con Alembic

---

## Roadmap Detallado

### Versión 1.1 - Integración de Datos Transversales (Próximos 1-2 semanas)  
**Objetivo**: Fusionar la vista de datos transversales con la vista PPR en una interfaz unificada con pestañas de Bootstrap

#### 1. Integración de Vista de Datos Transversales
- **ID**: FEAT-000
- **Prioridad**: Muy Alta
- **Descripción**: Migrar y fusionar la vista de datos transversales a la vista PPR con interfaz de pestañas
- **Tareas**:
  - Modificar la vista `/ppr` para incluir pestañas de Bootstrap
  - 1ra pestaña: Lista de PPRs cargados (actual funcionalidad existente)
  - 2da pestaña: Datos de CEPLAN cargados (actual funcionalidad de CEPLAN)
  - 3era pestaña: Cartera de servicios (actual funcionalidad de cartera)
  - Mantener botones de importación/subida en ubicaciones actuales
  - Asegurar que toda la funcionalidad existente se mantenga
  - Implementar navegación por pestañas sin recarga de página
  - Implementar carga de datos mediante AJAX para evitar sobrecarga del HTML
  - Consultar detalles/información adicional vía AJAX cuando sea necesario
  - Adaptar estilos para consistencia visual
- **Criterios de Aceptación**:
  - Interfaz unificada con pestañas de Bootstrap funcionando
  - Todas las funcionalidades existentes de PPR, CEPLAN y Cartera disponibles
  - Navegación entre pestañas fluida sin recarga de página principal
  - Uso eficiente de AJAX para carga de datos detallados
  - HTML no sobrecargado con grandes volúmenes de datos
  - Mantenimiento de la funcionalidad de carga de archivos
  - Experiencia de usuario mejorada sin pérdida de funcionalidad
  - Mejora en el rendimiento de la interfaz

### Versión 1.2 - Comparación y Reportes (Próximos 2-4 semanas)
**Objetivo**: Implementar funcionalidad de comparación PPR vs CEPLAN y dashboards básicos

#### 2. Motor de Comparación PPR ↔ CEPLAN
- **ID**: FEAT-001
- **Prioridad**: Alta
- **Descripción**: Implementar motor de comparación para cruzar datos entre ambas fuentes
- **Tareas**:
  - Implementar matching por `codigo_subproducto` (normalizado)
  - Crear heurísticas fuzzy para mismatches (Levenshtein)
  - Generar diferencias por mes y anual
  - UI para validar coincidencias dudosas
- **Criterios de Aceptación**:
  - El sistema debe identificar coincidencias exactas por código
  - Las coincidencias aproximadas deben ser validadas por el usuario
  - Generar reporte de diferencias mensuales/anuales
  - Resultados reproducibles y trazables

#### 3. Dashboards y Reportes Básicos
- **ID**: FEAT-002
- **Prioridad**: Alta
- **Descripción**: Desarrollar interfaces gráficas para métricas y comparaciones visuales
- **Tareas**:
  - Crear dashboard por PPR (KPIs, % de cumplimiento)
  - Implementar visualizaciones comparativas PPR vs CEPLAN
  - Desarrollar reportes exportables (CSV/PDF)
  - Vista tabular con semáforos (verde, amarillo, rojo)
- **Criterios de Aceptación**:
  - El usuario con rol adecuado puede filtrar datos
  - Se pueden exportar reportes
  - Visualización clara de métricas y KPIs
  - Responsive design

#### 4. Actualizaciones Mensuales
- **ID**: FEAT-003
- **Prioridad**: Alta
- **Descripción**: Funcionalidad para que responsables actualicen ejecuciones mensuales
- **Tareas**:
  - Endpoint PUT `/ppr/{id}/monthly-update` para responsable
  - Validaciones para evitar sobrescritura no autorizada
  - Historial de cambios por usuario
  - UI de edición mensual con control de cambios
- **Criterios de Aceptación**:
  - Los cambios quedan registrados en auditoría
  - Validación de rango de fechas y valores
  - Control de acceso por rol

---

### Versión 1.3 - Mejoras y Automatización (Próximos 4-8 semanas)
**Objetivo**: Implementar automatización, notificaciones y herramientas de calidad

#### 5. Sistema de Notificaciones
- **ID**: FEAT-004
- **Prioridad**: Media
- **Descripción**: Alertas automáticas para responsables sobre desviaciones
- **Tareas**:
  - Implementar alertas cuando avance < threshold
  - Enviar notificaciones por email/UI
  - Crear tareas/observaciones para responsables
- **Criterios de Aceptación**:
  - Notificaciones configurables
  - Pruebas integradas de notificación completadas

#### 6. Exportación Avanzada de Reportes
- **ID**: FEAT-005
- **Prioridad**: Media
- **Descripción**: Funcionalidad para generar PDFs y reportes detallados
- **Tareas**:
  - Generar reportes en formato PDF
  - Implementar plantillas de reportes
  - Opciones de personalización
- **Criterios de Aceptación**:
  - Reportes visualmente atractivos
  - Formato profesional
  - Opciones de filtro

#### 7. Auditoría Avanzada
- **ID**: FEAT-006
- **Prioridad**: Media
- **Descripción**: Histórico completo de cambios y trazabilidad
- **Tareas**:
  - Registro detallado de todas las operaciones
  - Vista de historial de cambios
  - Herramientas de trazabilidad
- **Criterios de Aceptación**:
  - Registro completo de todas las acciones
  - Fácil navegación por el historial
  - Exportación de auditoría

---

### Versión 1.4 - Optimización y Escalabilidad (Próximos 2-3 meses)
**Objetivo**: Implementar optimizaciones técnicas y preparar para producción a gran escala

#### 8. CI/CD Pipeline
- **ID**: FEAT-007
- **Prioridad**: Baja
- **Descripción**: Integración continua con GitHub Actions
- **Tareas**:
  - Configurar GitHub Actions con lint, tests, build, deploy
  - Implementar validaciones en PR
  - Automatizar pruebas
- **Criterios de Aceptación**:
  - CI ejecutado en cada push
  - PRs bloqueados si fallan tests
  - Despliegue automático

#### 9. Dockerización
- **ID**: FEAT-008
- **Prioridad**: Baja
- **Descripción**: Contenedores para despliegue simplificado
- **Tareas**:
  - Crear Dockerfile para la aplicación
  - Configurar docker-compose para infraestructura completa
  - Documentación de despliegue con Docker
- **Criterios de Aceptación**:
  - Despliegue con un solo comando
  - Configuración de entornos aislados
  - Documentación completa

#### 10. Monitorización y Observabilidad
- **ID**: FEAT-009
- **Prioridad**: Baja
- **Descripción**: Logging estructurado y métricas de rendimiento
- **Tareas**:
  - Implementar logging estructurado
  - Configurar métricas de rendimiento
  - Dashboard de monitoreo del sistema
- **Criterios de Aceptación**:
  - Logs estructurados y buscables
  - Métricas de rendimiento disponibles
  - Alertas de sistema

#### 11. Cacheo y Optimización de Rendimiento
- **ID**: FEAT-010
- **Prioridad**: Baja
- **Descripción**: Para mejorar rendimiento de vistas jerárquicas complejas
- **Tareas**:
  - Implementar cacheo para vistas jerárquicas
  - Optimizar consultas a la base de datos
  - Configurar CDN para assets
- **Criterios de Aceptación**:
  - Mejora significativa en tiempos de respuesta
  - Carga eficiente de estructuras complejas
  - Reducción de carga en la base de datos

#### 12. Dashboard Avanzado de Métricas
- **ID**: FEAT-011
- **Prioridad**: Baja
- **Descripción**: KPIs, % de cumplimiento, alertas por subproducto
- **Tareas**:
  - Desarrollar KPIs avanzados
  - Implementar alertas visuales
  - Dashboard ejecutivo
- **Criterios de Aceptación**:
  - Indicadores de desempeño claros
  - Alertas proactivas
  - Visualizaciones interactivas

---

## Casos de Prueba Importantes (Edge Cases)
- Excel con cabeceras en posiciones distintas / celdas combinadas
- Cabecera PROGRAMA PRESUPUESTAL escrita con variaciones
- Subproductos con prefijos y varios códigos concatenados
- Metas anuales no numéricas o con comas/puntos
- Cronograma con solo "Programado" o solo "Ejecutado"
- Archivo CEPLAN que tiene códigos que no existen en PPR
- Archivo Excel corrupto o con contraseña
- Archivo con meses en nombres completos vs abreviados

## Criterios de Aceptación Generales
- El sistema importa ambos tipos de Excel y detecta PPR dinámicamente
- El preview muestra warnings y permite mapeo manual antes de persistir
- Persistencia en base de datos con auditoría y versionado por año
- Matching CEPLAN ↔ PPR por codigo_subproducto con reporte de diferencias
- Responsables pueden actualizar ejecuciones mensuales con histórico
- UI responsive y accesible, con dashboards y exportación de reportes
- Tests automatizados y CI funcionando correctamente