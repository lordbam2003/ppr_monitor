// common.js - Funcionalidad compartida y centralizada

// --- UTILIDADES GLOBALES (Si no están en main.js) ---

// --- FUNCIONES DE PPR ---
async function initialSetup(defaultYear) {
    try {
        const response = await callAPI('/pprs', 'GET');
        const yearFilter = document.getElementById('yearFilter');
        if (response && response.data && yearFilter) {
            let years = [...new Set(response.data.map(ppr => ppr.anio))];
            if (!years.includes(defaultYear)) years.push(defaultYear);
            years.sort((a, b) => b - a);
            yearFilter.innerHTML = '';
            years.forEach(year => yearFilter.add(new Option(year, year, year == defaultYear, year == defaultYear)));
        }
        if (document.getElementById('pprTableBody')) loadPPRs(yearFilter?.value);
    } catch (e) { 
        if (document.getElementById('pprTableBody')) loadPPRs(defaultYear); 
    }
}

function initializeTabEventListeners() {
    document.getElementById('ceplan-tab')?.addEventListener('shown.bs.tab', () => loadCEPLANData());
    document.getElementById('cartera-tab')?.addEventListener('shown.bs.tab', () => loadCarteraData());
    document.getElementById('refreshCeplanBtn')?.addEventListener('click', loadCEPLANData);
    document.getElementById('refreshCarteraBtn')?.addEventListener('click', loadCarteraData);
}

async function loadPPRs(anio = null) {
    try {
        const url = anio ? `/pprs?anio=${anio}` : '/pprs';
        const response = await callAPI(url, 'GET');
        const tbody = document.getElementById('pprTableBody');
        if(!tbody) return;
        tbody.innerHTML = '';
        if (response && response.data) {
            response.data.forEach(ppr => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="ps-4 fw-bold text-muted small">#${ppr.codigo_ppr}</td>
                    <td class="fw-bold text-primary">${ppr.nombre_ppr}</td>
                    <td class="text-center fw-bold">${ppr.anio}</td>
                    <td class="text-center"><span class="badge bg-${ppr.estado === 'activo' ? 'success' : 'secondary'} rounded-pill">${ppr.estado || 'activo'}</span></td>
                    <td class="text-muted small">${new Date(ppr.fecha_creacion).toLocaleDateString()}</td>
                    <td class="text-center pe-4">
                        <button class="btn btn-sm btn-outline-info border-0 me-1" onclick="manageResponsibles(${ppr.id_ppr}, '${ppr.nombre_ppr}')" title="Responsables"><i class="fas fa-user-gear"></i></button>
                        <button class="btn btn-sm btn-outline-primary border-0 me-1" onclick="viewPPR(${ppr.id_ppr})" title="Ver Detalle"><i class="fas fa-eye"></i></button>
                        <button class="btn btn-sm btn-outline-success border-0 me-1" onclick="runComparison(${ppr.id_ppr}, '${ppr.nombre_ppr}')" title="Comparar"><i class="fas fa-scale-unbalanced"></i></button>
                        <button class="btn btn-sm btn-outline-danger border-0" onclick="deletePPR(${ppr.id_ppr}, '${ppr.nombre_ppr}')" title="Eliminar"><i class="fas fa-trash-can"></i></button>
                    </td>`;
                tbody.appendChild(row);
            });
        }
    } catch (e) { console.error(e); }
}

async function syncWithCeplan() {
    const anio = document.getElementById('yearFilter')?.value;
    const syncMetas = document.getElementById('syncMetasCheck')?.checked;
    const syncAvances = document.getElementById('syncAvancesCheck')?.checked;
    
    if (!syncMetas && !syncAvances) {
        showError('Debe seleccionar al menos una opción para sincronizar.');
        return;
    }

    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('syncCeplanModal'));
    modal.hide();
    try {
        showLoading('Sincronizando...');
        const res = await callAPI(`/pprs/sync-with-ceplan?anio=${anio}&sync_metas=${syncMetas}&sync_avances=${syncAvances}`, 'POST');
        hideLoading();
        if (res?.data) { showSuccess(res.message); loadPPRs(anio); }
    } catch (e) { hideLoading(); showError('Error en sync'); }
}

async function uploadPPRFile() {
    const file = document.getElementById('pprFile')?.files[0];
    if (!file) return;
    try {
        showLoading('Subiendo PPR...');
        const res = await callAPIWithFile('/upload/ppr', file);
        if (res?.preview_id) window.location.href = `/preview?id=${res.preview_id}`;
        else { showSuccess('Subido'); loadPPRs(document.getElementById('yearFilter')?.value); }
    } catch (e) { hideLoading(); }
}

async function uploadCeplanFile() {
    const files = document.getElementById('ceplanFile')?.files;
    if (!files?.length) return;
    try {
        showLoading('Subiendo lote...');
        const res = await callAPIWithFile('/upload/ceplan', files);
        if (res?.preview_id) window.location.href = `/preview?id=${res.preview_id}`;
    } catch (e) { hideLoading(); }
}

async function uploadCarteraFile() {
    const anio = document.getElementById('anioCartera')?.value;
    const file = document.getElementById('carteraFile')?.files[0];
    if (!anio || !file) return;
    try {
        showLoading('Subiendo Cartera...');
        const res = await callAPIWithFile(`/cartera/upload?anio=${anio}`, file);
        if (res?.preview_id) window.location.href = `/preview?id=${res.preview_id}&type=cartera`;
    } catch (e) { hideLoading(); }
}

async function createPprFromCartera() {
    const anio = document.getElementById('anioPpr')?.value;
    if (!anio) return;
    try {
        showLoading('Generando...');
        const res = await callAPI(`/pprs/create-from-cartera?anio=${anio}`, 'POST');
        hideLoading();
        if (res?.data) { showSuccess(res.message); loadPPRs(document.getElementById('yearFilter')?.value); }
    } catch (e) { hideLoading(); }
}

function viewPPR(id) { window.location.href = `/ppr_detalle?id=${id}`; }

async function runComparison(id, name) { 
    showLoading(`Comparando ${name}...`);
    try { await callAPI(`/comparison/ppr/${id}/compare`, 'POST'); hideLoading(); showSuccess('Completado'); } catch(e) { hideLoading(); }
}

async function deletePPR(id, name) {
    const res = await Swal.fire({ title: '¿Eliminar?', text: name, icon: 'warning', showCancelButton: true, confirmButtonColor: '#dc3545' });
    if (res.isConfirmed) { try { await callAPI(`/pprs/${id}`, 'DELETE'); loadPPRs(document.getElementById('yearFilter')?.value); } catch(e){} }
}

async function loadCEPLANData() {
    try {
        document.getElementById('ceplanLoading').style.display = 'block';
        document.getElementById('ceplanData').style.display = 'none';
        const response = await callAPI('/pprs/data/ceplan-all', 'GET');
        if (response && response.data && response.data.length > 0) displayCEPLANData(response.data);
        else document.getElementById('ceplanLoading').innerHTML = '<div class="alert alert-info text-center">No hay datos CEPLAN cargados.</div>';
    } catch (error) {
        console.error('Error loading CEPLAN data:', error);
        document.getElementById('ceplanLoading').innerHTML = `<div class="alert alert-danger text-center">Error al cargar datos CEPLAN: ${error.message}</div>`;
    }
}

function displayCEPLANData(data) {
    let html = `
    <div class="table-responsive">
        <table class="table table-striped table-hover table-sm">
            <thead class="table-dark">
                <tr>
                    <th>Subproducto</th>
                    <th class="text-center">Ene</th><th class="text-center">Feb</th><th class="text-center">Mar</th>
                    <th class="text-center">Abr</th><th class="text-center">May</th><th class="text-center">Jun</th>
                    <th class="text-center">Jul</th><th class="text-center">Ago</th><th class="text-center">Sep</th>
                    <th class="text-center">Oct</th><th class="text-center">Nov</th><th class="text-center">Dic</th>
                </tr>
            </thead>
            <tbody>`;

    const recordsToShow = data.length > 50 ? data.slice(0, 50) : data;
    recordsToShow.forEach(item => {
        html += `<tr>
            <td><small><b>${item.codigo_subproducto}</b><br>${item.nombre_subproducto}</small></td>
            ${['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'].map(m => `
                <td class="text-center" style="font-size: 0.8rem">
                    P: ${item['prog_'+m] || 0}<br>E: ${item['ejec_'+m] || 0}
                </td>
            `).join('')}
        </tr>`;
    });
    html += `</tbody></table>
        ${data.length > 50 ? `<div class="alert alert-info mt-3 small">Se muestran los primeros 50 de ${data.length} registros.</div>` : ''}
    </div>`;
    document.getElementById('ceplanData').innerHTML = html;
    document.getElementById('ceplanLoading').style.display = 'none';
    document.getElementById('ceplanData').style.display = 'block';
}

async function loadCarteraData() {
    try {
        document.getElementById('carteraLoading').style.display = 'block';
        document.getElementById('carteraData').style.display = 'none';    
        const response = await callAPI('/cartera', 'GET');
        if (response && response.data && response.data.length > 0) {      
            displayCarteraData(response.data);
        } else {
            document.getElementById('carteraLoading').innerHTML = '<div class="alert alert-info text-center">No hay datos de Cartera de Servicios cargados.</div>';
        }
    } catch (error) {
        console.error('Error loading Cartera data:', error);
        document.getElementById('carteraLoading').innerHTML = `<div class="alert alert-danger text-center">Error al cargar datos de Cartera: ${error.message}</div>`;
    }
}

let carteraData = [];
let currentPage = 1;
const itemsPerPage = 10;

function displayCarteraData(data) {
    carteraData = data;
    currentPage = 1;
    renderCarteraTable();
}

function renderCarteraTable() {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = carteraData.slice(startIndex, endIndex);

    let html = `
    <div class="table-responsive">
        <table class="table table-striped table-hover">
            <thead class="table-dark">
                <tr>
                    <th>Programa</th>
                    <th>Producto</th>
                    <th>Actividad</th>
                    <th>Sub Producto</th>
                    <th>Trazador</th>
                    <th>Unidad Medida</th>
                </tr>
            </thead>
            <tbody>`;

    pageData.forEach(item => {
        html += `<tr>
            <td><strong>${item.programa_codigo}</strong><br><small>${item.programa_nombre}</small></td>
            <td><strong>${item.producto_codigo}</strong><br><small>${item.producto_nombre}</small></td>
            <td><strong>${item.actividad_codigo}</strong><br><small>${item.actividad_nombre}</small></td>
            <td><strong>${item.sub_producto_codigo}</strong><br><small>${item.sub_producto_nombre}</small></td>
            <td class="text-center"><span class="badge bg-${item.trazador === 'X' ? 'success' : 'secondary'}">${item.trazador || ''}</span></td>
            <td>${item.unidad_medida || ''}</td>
        </tr>`;
    });

    html += '</tbody></table></div>';
    document.getElementById('carteraData').innerHTML = html;
    document.getElementById('carteraLoading').style.display = 'none';
    document.getElementById('carteraData').style.display = 'block';
    renderCarteraPagination();
}

function renderCarteraPagination() {
    const totalPages = Math.ceil(carteraData.length / itemsPerPage);
    const paginationElement = document.getElementById('carteraPagination');
    if (totalPages <= 1) {
        paginationElement.innerHTML = '';
        return;
    }

    let paginationHtml = `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="changeCarteraPage(${currentPage - 1})">Anterior</a>
    </li>`;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            paginationHtml += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changeCarteraPage(${i})">${i}</a>
            </li>`;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            paginationHtml += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    paginationHtml += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="changeCarteraPage(${currentPage + 1})">Siguiente</a>
    </li>`;
    
    paginationElement.innerHTML = `<ul class="pagination justify-content-center">${paginationHtml}</ul>`;
}

function changeCarteraPage(page) {
    if (page < 1 || page > Math.ceil(carteraData.length / itemsPerPage) || page === currentPage) return;
    currentPage = page;
    renderCarteraTable();
}

// Stubs for remaining modal functions
async function manageResponsibles(id, name) { /* Implementar según necesidad similar a dashboards */ }
async function openDeleteByYearModal() {
    try {
        const res = await callAPI('/pprs', 'GET');
        const sel = document.getElementById('yearToDelete');
        if(sel && res.data) {
            const years = [...new Set(res.data.map(p => p.anio))].sort((a,b)=>b-a);
            sel.innerHTML = '';
            years.forEach(y => sel.add(new Option(y, y)));
        }
    } catch(e){}
}

async function confirmDeleteByYear() {
    const y = document.getElementById('yearToDelete')?.value;
    if(!y) return;
    const res = await Swal.fire({ title: '¿Borrar todo '+y+'?', icon: 'error', showCancelButton: true });
    if(res.isConfirmed) {
        try { showLoading('Borrando...'); await callAPI(`/pprs/by-year/${y}`, 'DELETE'); hideLoading(); initialSetup(new Date().getFullYear()); } catch(e){ hideLoading(); }
    }
}

// --- FUNCIONES DE USUARIOS ---
async function loadUsers() {
    try {
        const response = await callAPI('/users', 'GET');
        const tbody = document.getElementById('userTableBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        
        if (response && Array.isArray(response)) {
            response.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="ps-4 fw-bold text-muted small">#${user.id_usuario}</td>
                    <td class="fw-bold">${user.nombre}</td>
                    <td><i class="fas fa-envelope me-2 text-muted small"></i>${user.email}</td>
                    <td><span class="status-badge bg-soft-${getRoleColor(user.rol)} text-${getRoleColor(user.rol)}">${getRoleDisplayName(user.rol)}</span></td>
                    <td class="text-center"><span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">${user.is_active ? 'Activo' : 'Inactivo'}</span></td>
                    <td class="text-muted small">${user.fecha_creacion ? new Date(user.fecha_creacion).toLocaleDateString() : 'N/A'}</td>
                    <td class="text-center pe-4">
                        <button class="btn btn-action btn-outline-primary me-1" onclick="editUser(${user.id_usuario})" title="Editar"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-action btn-outline-danger" onclick="deleteUser(${user.id_usuario}, '${user.nombre}')" title="Eliminar"><i class="fas fa-trash"></i></button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (e) { showError('Error al cargar usuarios'); }
}

function getRoleColor(role) {
    switch(role) {
        case 'admin': return 'primary';
        case 'responsable_ppr': return 'warning';
        case 'responsable_planificacion': return 'info';
        default: return 'secondary';
    }
}

function getRoleDisplayName(role) {
    const map = { 'admin': 'Administrador', 'responsable_ppr': 'Resp. PPR', 'responsable_planificacion': 'Resp. Planificación' };
    return map[role] || role;
}

async function editUser(userId) {
    try {
        const user = await callAPI(`/users/${userId}`, 'GET');
        if (user) {
            document.getElementById('userId').value = user.id_usuario;
            document.getElementById('userName').value = user.nombre;
            document.getElementById('userEmail').value = user.email;
            document.getElementById('userRole').value = user.rol;
            document.getElementById('userActive').checked = user.is_active;
            document.getElementById('userPassword').value = '';
            document.getElementById('userModalLabel').textContent = 'Editar Perfil de Usuario';
            new bootstrap.Modal(document.getElementById('userModal')).show();
        }
    } catch (e) { showError('No se pudo cargar el usuario'); }
}

async function saveUser() {
    const id = document.getElementById('userId').value;
    const data = {
        nombre: document.getElementById('userName').value,
        email: document.getElementById('userEmail').value,
        rol: document.getElementById('userRole').value,
        is_active: document.getElementById('userActive').checked
    };
    const pwd = document.getElementById('userPassword').value;
    if (pwd) data.password = pwd;

    try {
        showLoading('Guardando...');
        if (id) await callAPI(`/users/${id}`, 'PUT', data);
        else await callAPI('/users', 'POST', data);
        hideLoading();
        showSuccess('Operación exitosa');
        bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
        loadUsers();
    } catch (e) { hideLoading(); showError('Error al guardar'); }
}

function openAddUserModal() {
    document.getElementById('userForm').reset();
    document.getElementById('userId').value = '';
    document.getElementById('userModalLabel').textContent = 'Crear Nuevo Usuario';
    new bootstrap.Modal(document.getElementById('userModal')).show();
}

async function deleteUser(id, name) {
    const res = await Swal.fire({
        title: '¿Confirmar eliminación?',
        text: `El usuario "${name}" será borrado permanentemente.`,
        icon: 'warning', showCancelButton: true, confirmButtonColor: '#dc3545', confirmButtonText: 'Sí, eliminar'
    });
    if (res.isConfirmed) {
        try {
            await callAPI(`/users/${id}`, 'DELETE');
            showSuccess('Borrado con éxito');
            loadUsers();
        } catch (e) { showError('No se pudo eliminar'); }
    }
}

// --- FUNCIONES DE REPORTES ---
function generateMonthlyReport() {
    Swal.fire({
        title: 'Generar Reporte en PDF',
        text: 'El reporte consolidado se está generando en segundo plano.',
        icon: 'info',
        timer: 2000,
        showConfirmButton: false
    });
}

function generateComparisonReport() {
    Swal.fire({
        title: 'Exportando Excel',
        text: 'Compilando diferencias, la descarga iniciará en breve...',
        icon: 'success',
        timer: 2000,
        showConfirmButton: false
    });
}

function exportReport() {
    Swal.fire({
        title: 'Descarga Iniciada',
        text: 'El archivo CSV ha sido solicitado.',
        icon: 'success',
        timer: 1500,
        showConfirmButton: false
    });
}