#!/usr/bin/env python3
"""
Script para descargar las bibliotecas frontend necesarias y copiarlas localmente
"""
import os
import sys
import requests
import zipfile
import tarfile
import shutil
from pathlib import Path
import tempfile


def download_file(url, local_path):
    """Descargar un archivo desde una URL"""
    print(f"Descargando {url}...")
    response = requests.get(url)
    response.raise_for_status()
    
    with open(local_path, 'wb') as f:
        f.write(response.content)
    print(f"Archivo descargado: {local_path}")


def extract_and_copy_bootstrap():
    """Descargar y extraer Bootstrap 5"""
    print("Procesando Bootstrap 5...")
    
    # Crear directorios necesarios
    static_path = Path("app/static")
    css_path = static_path / "css"
    js_path = static_path / "js"
    
    # Crear directorios si no existen
    css_path.mkdir(parents=True, exist_ok=True)
    js_path.mkdir(parents=True, exist_ok=True)
    
    # URLs de Bootstrap
    bootstrap_css_url = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
    bootstrap_js_url = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
    
    # Descargar archivos
    download_file(bootstrap_css_url, css_path / "bootstrap.min.css")
    download_file(bootstrap_js_url, js_path / "bootstrap.bundle.min.js")


def extract_and_copy_fontawesome():
    """Descargar y extraer Font Awesome"""
    print("Procesando Font Awesome...")
    
    # Crear directorio para CSS
    css_path = Path("app/static/css")
    
    # URL de Font Awesome
    fontawesome_css_url = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    fontawesome_webfonts_url = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2"
    
    # Descargar archivos
    download_file(fontawesome_css_url, css_path / "fontawesome.min.css")
    
    # Crear directorio webfonts
    webfonts_path = Path("app/static/webfonts")
    webfonts_path.mkdir(exist_ok=True)
    
    # Intentar descargar algunos archivos de fuentes
    font_urls = [
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2"
    ]
    
    for font_url in font_urls:
        try:
            font_name = font_url.split("/")[-1]
            download_file(font_url, webfonts_path / font_name)
        except:
            print(f"No se pudo descargar {font_name}")


def extract_and_copy_sweetalert2():
    """Descargar y extraer SweetAlert2"""
    print("Procesando SweetAlert2...")
    
    # Crear directorios
    css_path = Path("app/static/css")
    js_path = Path("app/static/js")
    
    # URL de SweetAlert2
    sweetalert2_js_url = "https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.js"
    sweetalert2_css_url = "https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css"
    
    # Descargar archivos
    download_file(sweetalert2_js_url, js_path / "sweetalert2.min.js")
    download_file(sweetalert2_css_url, css_path / "sweetalert2.min.css")


def update_html_references():
    """Actualizar el archivo HTML para usar referencias locales"""
    print("Actualizando referencias en index.html...")
    
    html_path = Path("app/static/index.html")
    
    # Leer el archivo HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Reemplazar referencias CDN con referencias locales
    updated_content = content.replace(
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
        '/static/css/bootstrap.min.css'
    ).replace(
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        '/static/css/fontawesome.min.css'
    ).replace(
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
        '/static/js/bootstrap.bundle.min.js'
    ).replace(
        'https://cdn.jsdelivr.net/npm/sweetalert2@11',
        '/static/js/sweetalert2.min.js'
    )
    
    # Guardar el archivo actualizado
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("Referencias actualizadas en index.html")


def download_frontend_libraries():
    """Descargar y procesar todas las bibliotecas frontend"""
    print("Iniciando descarga de bibliotecas frontend...")
    
    try:
        # Procesar cada biblioteca
        extract_and_copy_bootstrap()
        extract_and_copy_fontawesome()
        extract_and_copy_sweetalert2()
        
        # Actualizar HTML
        update_html_references()
        
        print("¡Todas las bibliotecas frontend descargadas y configuradas!")
        return True
        
    except Exception as e:
        print(f"Error durante la descarga de bibliotecas frontend: {e}")
        return False


if __name__ == "__main__":
    success = download_frontend_libraries()
    if not success:
        sys.exit(1)