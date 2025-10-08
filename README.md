# Sistema de Monitoreo PPR

Sistema de monitoreo para Programas Presupuestales (PPR) y CEPLAN.

## Estructura del Proyecto

```
monitor_ppr/
├── alembic/              # Migraciones de base de datos
├── app/
│   ├── api/              # Endpoints de la API
│   ├── core/             # Configuración y utilidades
│   ├── models/           # Modelos de base de datos
│   ├── schemas/          # Esquemas de validación
│   ├── services/         # Lógica de negocio
│   ├── static/           # Archivos estáticos (CSS, JS, HTML)
│   │   ├── css/          # Archivos CSS (Bootstrap, Font Awesome locales)
│   │   ├── js/           # Archivos JS (Bootstrap, SweetAlert2 locales)
│   │   ├── webfonts/     # Archivos de fuentes de Font Awesome
│   │   ├── uploads/      # Directorio para archivos subidos
│   │   ├── style.css     # Estilos personalizados
│   │   ├── main.js       # Funcionalidades JavaScript
│   │   └── index.html    # Página principal con interfaz web
│   └── templates/        # Plantillas HTML (si se usan)
├── scripts/
│   ├── install.sh        # Script para instalar dependencias en entorno virtual
│   ├── start.sh          # Script para iniciar la aplicación
│   ├── init_db.py        # Script para inicializar la base de datos
│   ├── download_frontend_libs.py  # Script para descargar bibliotecas frontend localmente
│   └── test_api.py       # Script para probar la API
├── venv/                 # Entorno virtual (creado por install.sh)
├── pyproject.toml        # Configuración de dependencias del proyecto
├── requirements.txt      # Dependencias instaladas
└── README.md

## Scripts Adicionales

Además de los scripts mencionados anteriormente, se han añadido nuevos scripts útiles:

```
monitor_ppr/
├── scripts/
│   ├── load_json_to_db.py      # Script para cargar JSON directamente a la base de datos
│   └── load_latest_json.py     # Utilidad para cargar el JSON más reciente
```

## Utilidades de Carga Directa

### Carga de JSON directo a la base de datos

Para cargar un archivo JSON de datos PPR directamente a la base de datos:

```bash
python scripts/load_json_to_db.py path/to/your/file.json
```

### Carga del archivo JSON más reciente

Para cargar el archivo JSON más reciente del directorio `temp/uploads`:

```bash
# Listar archivos disponibles
python scripts/load_latest_json.py list

# Cargar el archivo más reciente
python scripts/load_latest_json.py latest

# Cargar un archivo específico
python scripts/load_latest_json.py nombre_del_archivo.json
```

## Funcionalidad Integrada en la Aplicación Web

La lógica mejorada de carga de datos PPR ha sido completamente integrada en la aplicación web. Ahora:

- El proceso de carga a través de la interfaz web incluye validación de estructura de datos
- Se asegura la correcta asignación de código y nombre del PPR en la base de datos
- Se manejan adecuadamente valores nulos y tipos de datos problemáticos
- Se proporcionan mensajes detallados de progreso y logging

Los endpoints API para carga de archivos PPR (`/api/v1/upload/ppr`, `/api/v1/upload/commit/{id}`) ahora utilizan la lógica mejorada para garantizar una persistencia correcta de los datos.

## Funcionalidades Adicionales Implementadas

### Carga y Procesamiento de Archivos CEPLAN

Además de la funcionalidad PPR, se ha implementado soporte completo para archivos CEPLAN:

- **Carga de archivos CEPLAN**: Endpoint `/api/v1/upload/ceplan` para subir archivos CEPLAN
- **Vista previa CEPLAN**: Endpoint `/api/v1/upload/preview-ceplan/{id}` para revisar datos antes de confirmar
- **Confirmación de datos CEPLAN**: Endpoint `/api/v1/upload/commit-ceplan/{id}` para persistir los datos

### Visualización de Estructura PPR

Se ha agregado un endpoint para visualizar la estructura de un PPR en formato consistente con los previews:

- **Estructura PPR**: Endpoint `/api/v1/ppr/{id}/estructura` devuelve la jerarquía completa (PPR → Productos → Actividades → Subproductos) en formato similar al de los previews
- Este endpoint facilita la visualización de la estructura en la interfaz web de manera similar a los previews generados

### Vista Detallada de PPR

Además de la estructura API, se ha implementado una vista web detallada para mostrar la información completa de un PPR:

- **Página de detalle**: `/ppr_detalle?id={pprId}` muestra una vista jerárquica completa del PPR
- **Visualización jerárquica**: Muestra productos, actividades y subproductos en un diseño de acordeón
- **Datos mensuales**: Incluye tabla con valores de programación/ejecución mensual para cada subproducto
- **Redirección desde lista**: Al hacer clic en el ícono de ver (ojo) en `/ppr`, ahora se redirige a la vista detallada
```

## Instalación

Ejecutar el script de instalación para crear el entorno virtual e instalar todas las dependencias:

```bash
bash scripts/install.sh
```

Esto:
- Creará un entorno virtual en el directorio `venv`
- Instalará todas las dependencias necesarias
- Instalará el paquete en modo editable

### Configuración de base de datos

Antes de inicializar la base de datos, debes tener un servidor MariaDB/MySQL corriendo en tu entorno de desarrollo:

1. Asegúrate de tener MariaDB instalado y corriendo en tu sistema
2. Crea una base de datos llamada `monitor_ppr` de forma manual o usando el script:
   ```sql
   CREATE DATABASE monitor_ppr;
   ```
   O usando el script proporcionado:
   ```bash
   python scripts/create_db.py
   ```
3. El archivo `.env` está configurado por defecto para usar MariaDB:
   ```
   DATABASE_URL=mariadb+pymysql://root:@localhost:3306/monitor_ppr
   ```
   Cambia las credenciales si usas otro usuario/contraseña en tu instalación de MariaDB.

### Migraciones de base de datos con Alembic

Para crear las tablas en la base de datos usando Alembic:

```bash
# Generar migración inicial (si es necesario)
alembic revision --autogenerate -m "Initial migration"

# Aplicar migraciones a la base de datos
alembic upgrade head
```

Esto creará todas las tablas necesarias en la base de datos MariaDB.

### Inicialización completa de la base de datos

Para inicializar completamente la base de datos con tablas y datos iniciales:

```bash
# 1. Crear la base de datos (si no existe)
python scripts/create_db.py

# 2. Aplicar migraciones
alembic upgrade head

# 3. Crear el usuario administrador
python scripts/init_db.py
```

Después de la instalación y configuración, inicializa la base de datos:

```bash
python scripts/init_db.py
```

Esto creará todas las tablas y un usuario administrador con credenciales:
- Email: admin@monitorppr.com
- Contraseña: admin123

## Ejecución

Para iniciar la aplicación:

```bash
bash scripts/start.sh
```

La aplicación estará disponible en `http://localhost:8000`

## Tecnologías Utilizadas

- **Backend**: FastAPI con Python 3.12
- **ORM**: SQLModel (basado en SQLAlchemy y Pydantic)
- **Frontend**: HTML5, CSS3 (Bootstrap 5), JavaScript
- **Iconos**: Font Awesome 6
- **Notificaciones**: SweetAlert2
- **Base de datos**: MariaDB/MySQL
- **Servidor**: Uvicorn (ASGI)
- **Autenticación**: JWT con roles de usuario

## Características del Sistema

### Autenticación y Autorización
- Sistema de login/logout con tokens JWT
- Roles de usuario: Administrador, Responsable PPR, Responsable Planificación
- Control de acceso basado en roles (RBAC)

### Gestión de Archivos
- Carga de archivos Excel PPR y CEPLAN
- Validación de formato y tamaño de archivos
- Procesamiento de datos Excel con pandas

### Interfaz Web
- Interfaz de usuario moderna con Bootstrap 5 (archivos locales)
- Iconos de Font Awesome para una mejor experiencia visual
- Notificaciones interactivas con SweetAlert2 (archivos locales)
- Diseño responsive para dispositivos móviles y de escritorio
- Panel de control con resumen de actividades
- Sección de gestión de PPRs, usuarios y reportes
- Integración con backend FastAPI

### Seguridad
- Contraseñas hasheadas con bcrypt
- Validación de tokens JWT
- Control de roles y permisos