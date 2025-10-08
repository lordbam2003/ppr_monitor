// Funciones JavaScript para la aplicación de monitoreo PPR

// Función para obtener el token de autenticación
function getAuthToken() {
    return localStorage.getItem('access_token');
}

// Función para incluir el token en las cabeceras de las solicitudes
function getAuthHeaders() {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
}

// Función para mostrar el dashboard
function showDashboard() {
    window.location.href = '/ppr';
}

// Función para mostrar mensaje de error
function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'Error',
        text: message,
        confirmButtonColor: '#dc3545'
    });
}

// Función para mostrar confirmación de acción
function confirmAction(title, text, callback) {
    Swal.fire({
        title: title,
        text: text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#0d6efd',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, continuar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            callback();
        }
    });
}

// Función para inicializar la aplicación
document.addEventListener('DOMContentLoaded', function() {
    console.log('Aplicación de monitoreo PPR cargada');
    
    // Actualizar la navegación basada en el estado de autenticación
    updateNavigation();
    
    // Aquí puedes añadir inicializaciones necesarias cuando se carga la página
    initializeComponents();
});

// Función para actualizar la navegación según el estado de autenticación
function updateNavigation() {
    const loginLink = document.querySelector('a[href="/login"]');
    if (!loginLink) return;
    
    const token = getAuthToken();
    if (token) {
        loginLink.innerHTML = '<i class="fas fa-sign-out-alt me-1"></i> Cerrar Sesión';
        loginLink.href = '#';
        loginLink.onclick = function(e) {
            e.preventDefault();
            logout();
        };
    } else {
        loginLink.innerHTML = '<i class="fas fa-user-circle me-1"></i> Iniciar Sesión';
        loginLink.href = '/login';
        loginLink.onclick = null;
    }
}

// Función para cerrar sesión
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_type');
    updateNavigation();
    showSuccess('Sesión cerrada exitosamente');
    // Redirigir al usuario a la página principal
    setTimeout(() => {
        window.location.href = '/';
    }, 1000);
}

// Función para inicializar componentes
function initializeComponents() {
    // Inicializar tooltips de Bootstrap si existen
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Cualquier otra inicialización necesaria
    setupEventListeners();
}

// Función para configurar listeners de eventos
function setupEventListeners() {
    // Ejemplo: listener para botones de acción
    const actionButtons = document.querySelectorAll('.btn[data-action]');
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            performAction(action);
        });
    });
    
    // Añadir funcionalidad a los enlaces de navegación
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href && href !== '#' && !href.startsWith('http')) {
                e.preventDefault();
                window.location.href = href;
            }
        });
    });
    
    // Añadir funcionalidad a los botones de las tarjetas
    document.querySelectorAll('.btn-outline-primary[data-action], .btn-outline-success[data-action], .btn-outline-info[data-action]').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.getAttribute('data-action');
            if (action) {
                performAction(action);
            }
        });
    });
}

// Función para realizar acciones basadas en el botón presionado
function performAction(action) {
    switch(action) {
        case 'view-ppr':
            window.location.href = '/ppr';
            break;
        case 'manage-users':
            // Verificar autenticación y permisos
            if (getAuthToken()) {
                window.location.href = '/users';
            } else {
                showLoginPrompt();
            }
            break;
        case 'view-reports':
            window.location.href = '/reports';
            break;
        default:
            console.log('Acción desconocida:', action);
    }
}

// Función para mostrar un prompt de login
function showLoginPrompt() {
    // Clear any existing invalid token
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_type');
    updateNavigation();
    
    Swal.fire({
        title: 'Requiere autenticación',
        text: 'Debe iniciar sesión para acceder a esta funcionalidad',
        icon: 'info',
        showCancelButton: true,
        confirmButtonText: 'Iniciar Sesión',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#0d6efd'
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = '/login';
        }
    });
}

// Función para hacer llamadas a la API
async function callAPI(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: getAuthHeaders()
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(`/api/v1${endpoint}`, options);
        
        if (!response.ok) {
            if (response.status === 401) {
                // Token expirado o inválido, redirigir al login
                localStorage.removeItem('access_token');
                localStorage.removeItem('token_type');
                updateNavigation();
                showLoginPrompt();
                throw new Error('No autorizado. Por favor inicie sesión.');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error en la llamada a la API:', error);
        if (error.message.includes('No autorizado')) {
            throw error;
        }
        showError('Error al comunicarse con el servidor');
        throw error;
    }
}

// Función para hacer llamadas a la API con archivos
async function callAPIWithFile(endpoint, fileData, method = 'POST') {
    try {
        const token = getAuthToken();
        
        if (!token) {
            showLoginPrompt();
            throw new Error('No autorizado. Por favor inicie sesión.');
        }

        const formData = new FormData();
        // Assuming fileData is an object with file information
        if (fileData instanceof File) {
            formData.append('file', fileData);
        } else if (fileData.file) {
            formData.append('file', fileData.file);
        } else {
            // If fileData is an object with other properties
            Object.keys(fileData).forEach(key => {
                if (fileData[key] instanceof File || typeof fileData[key] !== 'object') {
                    formData.append(key, fileData[key]);
                }
            });
        }

        const response = await fetch(`/api/v1${endpoint}`, {
            method: method,
            body: formData,
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                // Token expirado o inválido, redirigir al login
                localStorage.removeItem('access_token');
                localStorage.removeItem('token_type');
                updateNavigation();
                showLoginPrompt();
                throw new Error('No autorizado. Por favor inicie sesión.');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error en la llamada a la API con archivo:', error);
        if (error.message.includes('No autorizado')) {
            throw error;
        }
        showError('Error al comunicarse con el servidor');
        throw error;
    }
}

// Función para mostrar mensaje de éxito
function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: 'Éxito',
        text: message,
        timer: 2000,
        showConfirmButton: false,
        confirmButtonColor: '#198754'
    });
}

// Función para mostrar loading
function showLoading(message) {
    Swal.fire({
        title: message || 'Procesando...',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        willOpen: () => {
            Swal.showLoading();
        }
    });
}

// Función para ocultar loading
function hideLoading() {
    Swal.close();
}

// Función para verificar si el usuario está autenticado
function isAuthenticated() {
    return !!getAuthToken();
}

// Función para obtener información del usuario actual
async function getCurrentUser() {
    try {
        const userData = await callAPI('/auth/me', 'GET');
        return userData;
    } catch (error) {
        console.error('Error getting current user:', error);
        return null;
    }
}

// Función para inicializar autenticación en páginas
function initializeAuth() {
    // Actualizar la navegación basada en el estado de autenticación
    updateNavigation();
    
    // Verificar si el usuario está autenticado
    if (!isAuthenticated()) {
        // Si no está autenticado, redirigir al login
        window.location.href = '/login';
    } else {
        // Cargar información del usuario si es necesario
        getCurrentUser().then(user => {
            if (user) {
                console.log('Usuario autenticado:', user.nombre);
            }
        });
    }
}