# Sistema de Monitoreo PPR - Documentación Consolidada

## Índice
1. [Descripción del Proyecto](#descripción-del-proyecto)
2. [Arquitectura y Tecnologías](#arquitectura-y-tecnologías)
3. [Instalación y Configuración](#instalación-y-configuración)
4. [Estado Actual del Proyecto](#estado-actual-del-proyecto)
5. [Roadmap y Funcionalidades Pendientes](#roadmap-y-funcionalidades-pendientes)
6. [Desarrollo y Contribución](#desarrollo-y-contribución)

## Descripción del Proyecto

Sistema de monitoreo para Programas Presupuestales (PPR) y CEPLAN (cartera de servicios) desarrollado con FastAPI (backend) y HTML/CSS/JS/Bootstrap (frontend).

### Objetivo Principal
- Importar y procesar archivos Excel PPR (estructura jerárquica: PPR → producto → actividad → subproducto → metas y cronograma mensual)
- Importar y procesar archivos CEPLAN (lista de subproductos con programación y ejecución por mes)
- Comparar datos PPR vs CEPLAN por código de subproducto
- Permitir actualizaciones mensuales por responsables
- Generar dashboards y reportes profesionales

## Arquitectura y Tecnologías

### Stack Técnico
- **Backend**: FastAPI con Python 3.12
- **ORM**: SQLModel (basado en SQLAlchemy y Pydantic)
- **Base de datos**: MariaDB/MySQL (con migraciones Alembic)
- **Frontend**: HTML5, CSS3 (Bootstrap 5), JavaScript
- **Autenticación**: JWT con roles de usuario
- **Procesamiento Excel**: Pandas

### Características Técnicas
- Sistema de roles RBAC (Role-Based Access Control) completamente implementado
- Extracción inteligente de archivos Excel con detección dinámica de columnas
- Soporte para diferentes formatos de archivos (PPR, CEPLAN, Cartera de Servicios)
- Validación robusta de estructura de datos y detección de problemas

## Instalación y Configuración

### Requisitos
- Python 3.12
- MariaDB/MySQL Server

### Instalación
```bash
# 1. Crear entorno virtual e instalar dependencias
bash scripts/install.sh

# 2. Configurar base de datos (asegurarse que MariaDB esté corriendo)
python scripts/create_db.py

# 3. Aplicar migraciones
alembic upgrade head

# 4. Crear usuario administrador
python scripts/init_db.py
```

### Ejecución
```bash
bash scripts/start.sh
```

La aplicación estará disponible en `http://localhost:8000`

## Estado Actual del Proyecto

### Funcionalidades Completadas
✅ **Autenticación y Autorización**: Sistema completo con JWT y roles
✅ **Gestión de Usuarios**: CRUD completo de usuarios con control de roles  
✅ **Gestión de PPRs**: Estructura jerárquica completa (PPR → Producto → Actividad → Subproducto)
✅ **Carga de Archivos**: Sistema robusto para cargar archivos Excel PPR y CEPLAN
✅ **Extractor Inteligente**: Capacidad para detectar dinámicamente estructuras de archivos Excel
✅ **Cartera de Servicios**: Funcionalidad completa para cargar, previsualizar y persistir datos
✅ **Visualización Jerárquica**: Vista detallada de PPRs con estructura completa en modo acordeón
✅ **API Completa**: Endpoints RESTful para todas las operaciones principales
✅ **Frontend Responsivo**: Interfaz web moderna con Bootstrap 5
✅ **Migraciones de Base de Datos**: Sistema completo con Alembic

### Estructura de la Base de Datos
- **PPR**: Programa Presupuestal (id_ppr, codigo_ppr, nombre_ppr, anio, estado)
- **Producto**: (id_producto, codigo_producto, nombre_producto, FK → id_ppr)
- **Actividad**: (id_actividad, codigo_actividad, nombre_actividad, FK → id_producto)
- **Subproducto**: (id_subproducto, codigo_subproducto, nombre_subproducto, unidad_medida, FK → id_actividad)
- **Programación PPR**: (id_prog_ppr, id_subproducto, anio, meta_anual, campos mensuales)
- **Programación CEPLAN**: (id_prog_ceplan, id_subproducto, anio, campos mensuales)
- **Diferencias**: (id_diferencia, id_subproducto, anio, campos diferencia mensual, estado)
- **Usuario**: (id_usuario, nombre, email, rol, relación N:M con PPR)

## Roadmap y Funcionalidades Pendientes

### ✅ Completado
- [x] Autenticación y Autorización con JWT
- [x] Gestión de Usuarios y Roles
- [x] Estructura Jerárquica PPR → Producto → Actividad → Subproducto
- [x] Carga de Archivos Excel PPR y CEPLAN
- [x] Extractor Inteligente con detección dinámica de estructura
- [x] Cartera de Servicios
- [x] Visualización Jerárquica
- [x] API Completa
- [x] Frontend Responsivo
- [x] Migraciones de Base de Datos

### 🔴 Alta Prioridad
1. **Comparación PPR ↔ CEPLAN**: Implementar motor de comparación para cruzar datos entre ambas fuentes
2. **Dashboards y Reportes**: Desarrollar interfaces gráficas para métricas y comparaciones visuales
3. **Actualizaciones Mensuales**: Funcionalidad para que responsables actualicen ejecuciones mensuales
4. **Pruebas de Integración**: Suite de tests automatizados para validar flujos completos

### 🟡 Media Prioridad
5. **Sistema de Notificaciones**: Alertas automáticas para responsables sobre desviaciones
6. **Exportación de Reportes**: Funcionalidad para generar PDFs y reportes detallados
7. **Auditoría Avanzada**: Histórico completo de cambios y trazabilidad

### 🟢 Baja Prioridad
8. **CI/CD Pipeline**: Integración continua con GitHub Actions
9. **Dockerización**: Contenedores para despliegue simplificado
10. **Monitorización**: Logging estructurado y métricas de rendimiento
11. **Cacheo**: Para mejorar rendimiento de vistas jerárquicas complejas
12. **Dashboard de Métricas**: KPIs, % de cumplimiento, alertas por subproducto

## Desarrollo y Contribución

### Scripts Disponibles
- `install.sh` / `install.bat` - Instalación de dependencias
- `start.sh` / `start.bat` - Iniciar la aplicación  
- `init_db.py` - Inicializar base de datos
- `create_db.py` - Crear base de datos
- Scripts para carga de JSON directamente a la base de datos

### Principales Características Implementadas
- **Carga y Procesamiento de Archivos CEPLAN**: Endpoints para subir, previsualizar y confirmar datos CEPLAN
- **Visualización de Estructura PPR**: Endpoint `/api/v1/ppr/{id}/estructura` para obtener jerarquía completa
- **Vista Detallada de PPR**: Página `/ppr_detalle?id={pprId}` con vista jerárquica completa en acordeón
- **Extractor Inteligente**: Detección dinámica de columnas y posición de meses, extracción flexible basada en localización de headers

### Últimas Actualizaciones
- Implementación de extracción flexible basada en detección dinámica de estructura
- Normalización de texto para comparación de nombres
- Uso de archivo de referencia `ppr.txt` para identificación precisa de PPRs
- Detección automática de columnas y posición de meses
- Correcciones en la visualización de cartera de servicios