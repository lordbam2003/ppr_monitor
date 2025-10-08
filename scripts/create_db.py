#!/usr/bin/env python3
"""
Script para crear la base de datos MariaDB si no existe
"""
import subprocess
import sys
import os
from app.core.config import settings
import re

def extract_db_credentials(database_url):
    """Extraer credenciales de la URL de la base de datos"""
    # Patrón para mariadb+pymysql://usuario:contraseña@host:puerto/database
    pattern = r"mariadb\+pymysql://([^:]*):?([^@]*)@([^:]*):(\d+)/(.*)"
    match = re.match(pattern, database_url)
    
    if match:
        user = match.group(1) or 'root'  # Si no hay usuario, usar 'root'
        password = match.group(2)
        host = match.group(3)
        port = match.group(4)
        database = match.group(5)
        return user, password, host, port, database
    else:
        # Para el caso donde no hay contraseña
        pattern = r"mariadb\+pymysql://([^:@]*)(@[^:]*):(\d+)/(.*)"
        match = re.match(pattern, database_url)
        if match:
            user = match.group(1) or 'root'
            host_port_db = match.group(2) + ':' + match.group(3) + '/' + match.group(4)
            # Extraer host, port, database de host_port_db
            host_pattern = r"@([^:]*):(\d+)/(.*)"
            host_match = re.search(host_pattern, host_port_db)
            if host_match:
                host = host_match.group(1)
                port = host_match.group(2)
                database = host_match.group(3)
                return user, "", host, port, database
    
    # Para el caso específico de la URL actual: mariadb+pymysql://root:@localhost:3306/monitor_ppr
    if "mariadb+pymysql://root:@" in database_url and "localhost" in database_url:
        return "root", "", "localhost", "3306", "monitor_ppr"
    
    raise ValueError(f"No se pudo parsear la URL de la base de datos: {database_url}")

def create_database():
    """Crear la base de datos si no existe"""
    try:
        user, password, host, port, database = extract_db_credentials(settings.database_url)
        
        print(f"Intentando crear la base de datos '{database}' en {host}:{port}")
        
        # Determinar el comando de MySQL/MariaDB basado en el sistema operativo
        mysql_cmd = "mysql"
        if os.name == 'nt':  # Windows
            # En Windows, comprobar si mysql.exe está en PATH o en directorios comunes
            possible_paths = [
                "mysql.exe",
                "C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysql.exe",
                "C:\\Program Files (x86)\\MySQL\\MySQL Server 8.0\\bin\\mysql.exe",
                "C:\\Program Files\\MariaDB 11.4\\bin\\mysql.exe",
                "C:\\Program Files\\MariaDB\\MariaDB 10.11\\bin\\mysql.exe",
                "C:\\Program Files (x86)\\MariaDB\\MariaDB 10.11\\bin\\mysql.exe"
            ]
            
            for path in possible_paths:
                # Intentar ejecutar el comando para ver si existe
                try:
                    if os.path.isfile(path):
                        mysql_cmd = path
                        break
                    # Para comprobar si está en PATH
                    subprocess.run([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    mysql_cmd = path
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
        else:
            # En Linux/macOS, verificar si mysql está disponible
            if subprocess.run(["which", "mysql"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
                print("Error: mysql no encontrado. Asegúrate de tener MariaDB/MySQL cliente instalado.")
                if os.name == 'posix':  # Linux/macOS
                    print("En Ubuntu/Debian: sudo apt-get install mariadb-client")
                    print("En CentOS/RHEL: sudo yum install mariadb")
                    print("En macOS: brew install mariadb")
                return False
        
        # Comando para crear la base de datos
        args = [mysql_cmd, "-u", user]
        if password:
            args.extend([f"-p{password}"])
        args.extend(["-h", host, "-P", port, "-e", f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"])
        
        # En Windows, se puede necesitar usar shell=True para que funcione correctamente
        result = subprocess.run(args, capture_output=True, text=True, shell=(os.name=='nt'))
        
        if result.returncode == 0 or "database exists" in result.stderr.lower() or "database exists" in result.stdout.lower():
            print(f"Base de datos '{database}' creada exitosamente (si no existía).")
            return True
        else:
            print(f"Error al crear la base de datos:")
            print(f"Comando ejecutado: {' '.join(args)}")
            print(f"Error: {result.stderr}")
            if os.name == 'nt':
                print("NOTA: En Windows, asegúrate que el cliente de MySQL/MariaDB esté instalado y en el PATH.")
                print("Puedes descargar MySQL desde: https://dev.mysql.com/downloads/installer/")
                print("O MariaDB desde: https://mariadb.org/download/")
            return False
            
    except ValueError as e:
        print(f"Error al parsear la URL de la base de datos: {e}")
        return False
    except FileNotFoundError:
        print("Error: mysql no encontrado. Asegúrate de tener MariaDB/MySQL cliente instalado.")
        if os.name == 'nt':  # Windows
            print("Descarga MariaDB o MySQL desde:")
            print("  - MariaDB: https://mariadb.org/download/")
            print("  - MySQL: https://dev.mysql.com/downloads/installer/")
        elif os.name == 'posix':  # Linux/macOS
            print("En Ubuntu/Debian: sudo apt-get install mariadb-client")
            print("En CentOS/RHEL: sudo yum install mariadb")
            print("En macOS: brew install mariadb")
        return False
    except Exception as e:
        print(f"Error al crear la base de datos: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_database()
    if not success:
        sys.exit(1)