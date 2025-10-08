// preview.js - JavaScript for preview page functionality

document.addEventListener('DOMContentLoaded', function() {
    initializePreviewPage();
});

function initializePreviewPage() {
    // Get preview ID from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const previewId = urlParams.get('id');
    
    if (!previewId) {
        showError('No se proporcionó un ID de previsualización válido.');
        return;
    }

    // Load preview data
    loadPreviewData(previewId);
    
    // Set up event listeners
    setupEventListeners(previewId);
}

function loadPreviewData(previewId) {
    showLoading(true);
    
    const token = localStorage.getItem('access_token');
    
    // Determine the type from URL parameters or try both endpoints
    const urlParams = new URLSearchParams(window.location.search);
    const dataType = urlParams.get('type') || 'ppr'; // default to ppr for backward compatibility
    
    let apiUrl;
    if (dataType === 'cartera') {
        apiUrl = `/api/v1/cartera/preview/${previewId}`;
    } else {
        // For backward compatibility, use the original upload endpoint for ppr/ceplan
        apiUrl = `/api/v1/upload/preview/${previewId}`;
    }
    
    fetch(apiUrl, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error al cargar los datos de previsualización: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        showLoading(false);
        if (dataType === 'cartera') {
            displayCarteraPreviewData(data.data);
        } else {
            displayPreviewData(data.data, dataType);
        }
    })
    .catch(error => {
        showLoading(false);
        showError(`Error al cargar los datos: ${error.message}`);
        console.error('Error loading preview data:', error);
    });
}

function displayPreviewData(previewData) {
    try {
        // Check if it's PPR data, CEPLAN data, or Cartera data
        let pprData = null;
        let ceplanData = null;
        let carteraData = null;
        
        if (previewData.ppr_data) {
            pprData = previewData.ppr_data;
        } else if (previewData.ceplan_data) {
            ceplanData = previewData.ceplan_data;
        } else if (previewData.cartera_data) {
            carteraData = previewData.cartera_data;
        } else if (previewData.ppr && previewData.productos) {
            // Direct structure without ppr_data wrapper
            pprData = previewData;
        } else if (previewData.ceplan) {
            // Direct structure for CEPLAN without ceplan_data wrapper
            ceplanData = previewData;
        } else if (previewData.cartera) {
            // Direct structure for Cartera without cartera_data wrapper
            carteraData = { cartera: previewData.cartera };
        }
        
        if (pprData) {
            // Handle PPR data (existing functionality)
            const { ppr, productos } = pprData;

            // Display PPR info
            document.getElementById('pprCodigo').textContent = ppr.codigo || 'N/A';
            document.getElementById('pprNombre').textContent = ppr.nombre || 'N/A';
            document.getElementById('pprAnio').textContent = ppr.anio || 'N/A';

            // Calculate and display summary statistics
            let totalProductos = 0;
            let totalActividades = 0;
            let totalSubproductos = 0;
            let totalWarnings = 0;

            if (productos && Array.isArray(productos)) {
                totalProductos = productos.length;
                
                productos.forEach(producto => {
                    if (producto.actividades && Array.isArray(producto.actividades)) {
                        totalActividades += producto.actividades.length;
                        
                        producto.actividades.forEach(actividad => {
                            if (actividad.subproductos && Array.isArray(actividad.subproductos)) {
                                totalSubproductos += actividad.subproductos.length;
                                
                                actividad.subproductos.forEach(subproducto => {
                                    if (subproducto.warnings && Array.isArray(subproducto.warnings)) {
                                        totalWarnings += subproducto.warnings.length;
                                    }
                                });
                            }
                        });
                    }
                });
            }

            document.getElementById('totalProductos').textContent = totalProductos;
            document.getElementById('totalActividades').textContent = totalActividades;
            document.getElementById('totalSubproductos').textContent = totalSubproductos;
            document.getElementById('totalWarnings').textContent = totalWarnings;

            // Display hierarchical data
            displayHierarchy(productos);

        } else if (ceplanData) {
            // Handle CEPLAN data
            const ceplanSubproductos = ceplanData.subproductos || [];
            const ceplanInfo = ceplanData.ceplan || ceplanData || {};

            // Display CEPLAN info (using placeholders since CEPLAN doesn't have the same PPR structure)
            document.getElementById('pprCodigo').textContent = 'CEPLAN';
            document.getElementById('pprNombre').textContent = ceplanInfo.nombre || 'Datos CEPLAN';
            document.getElementById('pprAnio').textContent = ceplanInfo.anio || 'N/A';

            // Calculate CEPLAN summary statistics
            let totalSubproductos = ceplanSubproductos.length;
            let totalWarnings = 0;

            ceplanSubproductos.forEach(subproducto => {
                if (subproducto.warnings && Array.isArray(subproducto.warnings)) {
                    totalWarnings += subproducto.warnings.length;
                }
            });

            document.getElementById('totalProductos').textContent = '0'; // CEPLAN doesn't have productos in the same way
            document.getElementById('totalActividades').textContent = '0'; // CEPLAN doesn't have actividades in the same way
            document.getElementById('totalSubproductos').textContent = totalSubproductos;
            document.getElementById('totalWarnings').textContent = totalWarnings;

            // Display CEPLAN hierarchical data (converted to PPR-like structure for display)
            const convertedProductos = convertCeplanToProductos(ceplanSubproductos);
            displayHierarchy(convertedProductos);
        } else if (carteraData) {
            // Handle Cartera data
            displayCarteraPreviewData(previewData);
        }

        // Display warnings if any
        if (getTotalWarnings(previewData, dataType) > 0) {
            displayWarnings(previewData, dataType);
        } else {
            document.getElementById('warningsSection').classList.add('d-none');
        }

        // Show the preview container
        document.getElementById('previewContainer').classList.remove('d-none');
    } catch (error) {
        console.error('Error displaying preview data:', error);
        showError('Error al procesar los datos de previsualización: ' + error.message);
    }
}

function displayCarteraPreviewData(previewData) {
    try {
        console.log('Raw previewData:', previewData); // Debug logging
        
        // Handle cartera data structure
        // previewData is the 'data' field from response, which contains {cartera_data, filename, etc}
        let carteraData;
        
        if (previewData.cartera_data) {
            // Use the cartera_data wrapper
            carteraData = previewData.cartera_data;
        } else if (previewData.cartera) {
            // Direct cartera array
            carteraData = previewData;
        } else {
            // Fallback to direct structure
            carteraData = { cartera: previewData };
        }
        
        console.log('Processed carteraData:', carteraData); // Debug logging
        
        if (!carteraData || !carteraData.cartera) {
            throw new Error('No se encontró la estructura de datos de cartera válida');
        }
        
        // Update PPR info section to show Cartera info
        const pprCodigo = document.getElementById('pprCodigo');
        const pprNombre = document.getElementById('pprNombre');
        const pprAnio = document.getElementById('pprAnio');
        
        if (pprCodigo) pprCodigo.textContent = 'CAR';
        if (pprNombre) pprNombre.textContent = 'Cartera de Servicios';
        if (pprAnio) pprAnio.textContent = new Date().getFullYear();

        // Calculate and display summary statistics
        let totalRecords = 0;
        let totalWarnings = 0;

        if (carteraData.cartera && Array.isArray(carteraData.cartera)) {
            totalRecords = carteraData.cartera.length;
            
            // Check for warnings in each record
            carteraData.cartera.forEach(record => {
                if (record.warnings && Array.isArray(record.warnings)) {
                    totalWarnings += record.warnings.length;
                }
            });
        }

        const totalProductos = document.getElementById('totalProductos');
        const totalActividades = document.getElementById('totalActividades');
        const totalSubproductos = document.getElementById('totalSubproductos');
        const totalWarningsEl = document.getElementById('totalWarnings');
        
        if (totalProductos) totalProductos.textContent = '0'; // For cartera we don't have productos
        if (totalActividades) totalActividades.textContent = '0'; // For cartera we don't have actividades
        if (totalSubproductos) totalSubproductos.textContent = totalRecords;
        if (totalWarningsEl) totalWarningsEl.textContent = totalWarnings;

        // Display cartera data in a table format
        displayCarteraData(carteraData.cartera || []);
        
        // Show the preview container
        document.getElementById('previewContainer').classList.remove('d-none');

    } catch (error) {
        console.error('Error displaying cartera preview data:', error);
        showError('Error al procesar los datos de cartera: ' + error.message);
    }
}

function displayCarteraData(records) {
    const container = document.getElementById('hierarchyContainer');
    container.innerHTML = ''; // Clear existing content

    if (!records || !Array.isArray(records) || records.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No se encontraron registros de Cartera de Servicios para mostrar.</div>';
        return;
    }

    // Create a table to display cartera data
    const tableCard = document.createElement('div');
    tableCard.className = 'card mb-3';
    tableCard.innerHTML = `
        <div class="card-header bg-primary text-white">
            <h5 class="mb-0">
                <i class="fas fa-table me-2"></i>Registros de Cartera de Servicios
                <span class="badge bg-light text-dark float-end">${records.length} Registros</span>
            </h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Programa Código</th>
                            <th>Programa Nombre</th>
                            <th>Producto Código</th>
                            <th>Producto Nombre</th>
                            <th>Actividad Código</th>
                            <th>Actividad Nombre</th>
                            <th>Sub Producto Código</th>
                            <th>Sub Producto Nombre</th>
                            <th>Trazador</th>
                            <th>Unidad Medida</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${records.map(record => `
                            <tr>
                                <td><strong>${record.programa_codigo || ''}</strong></td>
                                <td>${record.programa_nombre || ''}</td>
                                <td><strong>${record.producto_codigo || ''}</strong></td>
                                <td>${record.producto_nombre || ''}</td>
                                <td><strong>${record.actividad_codigo || ''}</strong></td>
                                <td>${record.actividad_nombre || ''}</td>
                                <td><strong>${record.sub_producto_codigo || ''}</strong></td>
                                <td>${record.sub_producto_nombre || ''}</td>
                                <td class="text-center">${record.trazador || ''}</td>
                                <td>${record.unidad_medida || ''}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    container.appendChild(tableCard);
}

// Helper function to convert CEPLAN structure to PPR-like structure for display
function convertCeplanToProductos(ceplanSubproductos) {
    if (!ceplanSubproductos || !Array.isArray(ceplanSubproductos)) {
        return [];
    }
    
    // Group CEPLAN subproducts by some logical grouping (or just create a default group)
    const groupedSubproductos = {
        'CEPLAN': ceplanSubproductos
    };
    
    const productos = [];
    let productoIndex = 1;
    
    for (const [groupName, subproductos] of Object.entries(groupedSubproductos)) {
        if (Array.isArray(subproductos) && subproductos.length > 0) {
            const producto = {
                codigo_producto: `CEPLAN${productoIndex}`,
                nombre_producto: groupName,
                actividades: [{
                    codigo_actividad: 'CEPLAN-ACT',
                    nombre_actividad: `Actividad de ${groupName}`,
                    subproductos: subproductos.map(sub => ({
                        codigo_subproducto: sub.codigo_subproducto || 'N/A',
                        nombre_subproducto: sub.nombre_subproducto || 'N/A',
                        unidad_medida: sub.unidad_medida || 'N/A',
                        meta_anual: sub.meta_anual || 0,
                        programado: sub.programado || {},
                        ejecutado: sub.ejecutado || {},
                        warnings: sub.warnings || []
                    }))
                }]
            };
            productos.push(producto);
            productoIndex++;
        }
    }
    
    return productos;
}

// Helper function to get total warnings from PPR, CEPLAN, and Cartera structures
function getTotalWarnings(previewData, dataType = 'ppr') {
    if (dataType === 'cartera') {
        // Handle Cartera data structure
        let carteraData = previewData.cartera_data || previewData.cartera || previewData;
        
        if (carteraData.cartera && Array.isArray(carteraData.cartera)) {
            let totalWarnings = 0;
            carteraData.cartera.forEach(record => {
                if (record.warnings && Array.isArray(record.warnings)) {
                    totalWarnings += record.warnings.length;
                }
            });
            return totalWarnings;
        }
        return 0;
    }
    
    let totalWarnings = 0;
    
    // Check for PPR data structure
    if (previewData.ppr_data && previewData.ppr_data.productos) {
        const productos = previewData.ppr_data.productos;
        productos.forEach(producto => {
            if (producto.actividades && Array.isArray(producto.actividades)) {
                producto.actividades.forEach(actividad => {
                    if (actividad.subproductos && Array.isArray(actividad.subproductos)) {
                        actividad.subproductos.forEach(subproducto => {
                            if (subproducto.warnings && Array.isArray(subproducto.warnings)) {
                                totalWarnings += subproducto.warnings.length;
                            }
                        });
                    }
                });
            }
        });
    } 
    // Check for direct PPR structure
    else if (previewData.productos) {
        const productos = previewData.productos;
        productos.forEach(producto => {
            if (producto.actividades && Array.isArray(producto.actividades)) {
                producto.actividades.forEach(actividad => {
                    if (actividad.subproductos && Array.isArray(actividad.subproductos)) {
                        actividad.subproductos.forEach(subproducto => {
                            if (subproducto.warnings && Array.isArray(subproducto.warnings)) {
                                totalWarnings += subproducto.warnings.length;
                            }
                        });
                    }
                });
            }
        });
    } 
    // Check for CEPLAN data structure
    else if (previewData.ceplan_data && previewData.ceplan_data.subproductos) {
        const subproductos = previewData.ceplan_data.subproductos;
        subproductos.forEach(subproducto => {
            if (subproducto.warnings && Array.isArray(subproducto.warnings)) {
                totalWarnings += subproducto.warnings.length;
            }
        });
    } 
    // Check for direct CEPLAN structure
    else if (previewData.subproductos) {
        const subproductos = previewData.subproductos;
        subproductos.forEach(subproducto => {
            if (subproducto.warnings && Array.isArray(subproducto.warnings)) {
                totalWarnings += subproducto.warnings.length;
            }
        });
    }
    
    return totalWarnings;
}

function displayHierarchy(productos) {
    const container = document.getElementById('hierarchyContainer');
    container.innerHTML = ''; // Clear existing content

    if (!productos || !Array.isArray(productos)) {
        container.innerHTML = '<div class="alert alert-info">No se encontraron productos para mostrar.</div>';
        return;
    }

    productos.forEach((producto, produtoIndex) => {
        // Create producto card
        const produtoCard = createProdutoCard(producto, produtoIndex);
        container.appendChild(produtoCard);
    });
}

function createProdutoCard(producto, produtoIndex) {
    const card = document.createElement('div');
    card.className = 'card mb-3';
    
    const actividades = producto.actividades || [];
    
    card.innerHTML = `
        <div class="card-header bg-secondary text-white">
            <h5 class="mb-0">
                <i class="fas fa-box-open me-2"></i>
                ${produtoIndex + 1}) Producto: ${producto.codigo_producto} - ${producto.nombre_producto}
                <span class="badge bg-light text-dark float-end">${actividades.length} Actividades</span>
            </h5>
        </div>
        <div class="card-body">
            <div id="produto-${produtoIndex}-actividades"></div>
        </div>
    `;

    // Add actividades to the card
    const actividadesContainer = card.querySelector(`#produto-${produtoIndex}-actividades`);
    actividades.forEach((actividad, actividadIndex) => {
        const actividadCard = createActividadCard(actividad, produtoIndex, actividadIndex);
        actividadesContainer.appendChild(actividadCard);
    });

    return card;
}

function createActividadCard(actividad, produtoIndex, actividadIndex) {
    const card = document.createElement('div');
    card.className = 'card mb-2';
    
    const subproductos = actividad.subproductos || [];
    
    card.innerHTML = `
        <div class="card-header bg-info text-white">
            <h6 class="mb-0">
                <i class="fas fa-cogs me-2"></i>
                Actividad: ${actividad.codigo_actividad} - ${actividad.nombre_actividad}
                <span class="badge bg-light text-dark float-end">${subproductos.length} Subproductos</span>
            </h6>
        </div>
        <div class="card-body p-2">
            <div id="atividad-${produtoIndex}-${actividadIndex}-subproductos"></div>
        </div>
    `;

    // Add subproductos to the card
    const subproductosContainer = card.querySelector(`#atividad-${produtoIndex}-${actividadIndex}-subproductos`);
    subproductos.forEach((subproducto, subprodutoIndex) => {
        const subprodutoCard = createSubprodutoCard(subproducto, subprodutoIndex);
        subproductosContainer.appendChild(subprodutoCard);
    });

    return card;
}

function createSubprodutoCard(subproducto, subprodutoIndex) {
    const card = document.createElement('div');
    card.className = 'card mb-2';
    
    card.innerHTML = `
        <div class="card-header bg-light">
            <div class="row">
                <div class="col-md-4">
                    <strong>${subproducto.codigo_subproducto} - ${subproducto.nombre_subproducto}</strong>
                </div>
                <div class="col-md-2">
                    <small>UM: ${subproducto.unidad_medida || 'N/A'}</small>
                </div>
                <div class="col-md-2">
                    <small>Meta: ${subproducto.meta_anual || 0}</small>
                </div>
                <div class="col-md-4">
                    <button class="btn btn-sm btn-outline-primary" type="button" 
                            data-bs-toggle="collapse" 
                            data-bs-target="#subproduto-${subprodutoIndex}-monthly">
                        Mostrar Datos Mensuales
                    </button>
                </div>
            </div>
        </div>
        <div class="collapse" id="subproduto-${subprodutoIndex}-monthly">
            <div class="card-body">
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th>Mes</th>
                            <th>Programado</th>
                            <th>Ejecutado</th>
                            <th>% Cumplimiento</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${generateMonthlyDataRows(subproducto)}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    return card;
}

function generateMonthlyDataRows(subproducto) {
    const months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    let rows = '';
    
    subproducto.programado = subproducto.programado || {};
    subproducto.ejecutado = subproducto.ejecutado || {};
    
    months.forEach(month => {
        const prog = parseFloat(subproducto.programado[month] || 0);
        const ejec = parseFloat(subproducto.ejecutado[month] || 0);
        const cumplimiento = prog > 0 ? ((ejec / prog) * 100).toFixed(1) : 0;
        
        rows += `
            <tr>
                <td>${month.toUpperCase()}</td>
                <td>${prog}</td>
                <td>${ejec}</td>
                <td>${cumplimiento}%</td>
            </tr>
        `;
    });
    
    return rows;
}

function displayWarnings(previewData, dataType = 'ppr') {
    const warningsSection = document.getElementById('warningsSection');
    const warningsList = document.getElementById('warningsList');
    
    warningsList.innerHTML = '';
    
    let warnings = [];
    
    if (dataType === 'cartera') {
        // Handle Cartera data warnings
        let carteraData = previewData.cartera_data || previewData.cartera || previewData;
        
        if (carteraData.cartera && Array.isArray(carteraData.cartera)) {
            carteraData.cartera.forEach(record => {
                if (record.warnings && Array.isArray(record.warnings) && record.warnings.length > 0) {
                    record.warnings.forEach(warning => {
                        warnings.push({
                            type: 'cartera',
                            code: record.programa_codigo || record.producto_codigo || 'N/A',
                            name: record.programa_nombre || record.producto_nombre || 'Registro',
                            message: warning
                        });
                    });
                }
            });
        }
    } else {
        // Check if it's PPR data or CEPLAN data
        let pprData = null;
        let ceplanData = null;
        
        if (previewData.ppr_data) {
            pprData = previewData.ppr_data;
        } else if (previewData.ceplan_data) {
            ceplanData = previewData.ceplan_data;
        } else if (previewData.ppr && previewData.productos) {
            // Direct structure without ppr_data wrapper
            pprData = previewData;
        } else if (previewData.ceplan && previewData.subproductos) {
            // Direct structure for CEPLAN without ceplan_data wrapper
            ceplanData = previewData;
        }
        
        if (pprData) {
            // Handle PPR data structure
            const productos = pprData.productos || pprData;
            
            if (productos && Array.isArray(productos)) {
                productos.forEach(producto => {
                    if (producto.actividades && Array.isArray(producto.actividades)) {
                        producto.actividades.forEach(actividad => {
                            if (actividad.subproductos && Array.isArray(actividad.subproductos)) {
                                actividad.subproductos.forEach(subproducto => {
                                    if (subproducto.warnings && Array.isArray(subproducto.warnings) && subproducto.warnings.length > 0) {
                                        subproducto.warnings.forEach(warning => {
                                            warnings.push({
                                                type: 'subproduct',
                                                code: subproducto.codigo_subproducto,
                                                name: subproducto.nombre_subproducto,
                                                message: warning
                                            });
                                        });
                                    }
                                });
                            }
                        });
                    }
                });
            }
        } else if (ceplanData) {
            // Handle CEPLAN data structure
            const subproductos = ceplanData.subproductos || ceplanData;
            
            if (subproductos && Array.isArray(subproductos)) {
                subproductos.forEach(subproducto => {
                    if (subproducto.warnings && Array.isArray(subproducto.warnings) && subproducto.warnings.length > 0) {
                        subproducto.warnings.forEach(warning => {
                            warnings.push({
                                type: 'subproduct',
                                code: subproducto.codigo_subproducto,
                                name: subproducto.nombre_subproducto,
                                message: warning
                            });
                        });
                    }
                });
            }
        }
    }
    
    if (warnings.length > 0) {
        // Group warnings by type for better organization
        const criticalWarnings = [];
        const infoWarnings = [];
        
        warnings.forEach(warning => {
            if (warning.message.toLowerCase().includes('excede') || 
                warning.message.toLowerCase().includes('negativos') ||
                warning.message.toLowerCase().includes('error')) {
                criticalWarnings.push(warning);
            } else {
                infoWarnings.push(warning);
            }
        });
        
        // Display critical warnings first
        if (criticalWarnings.length > 0) {
            const criticalDiv = document.createElement('div');
            criticalDiv.className = 'mb-3';
            criticalDiv.innerHTML = '<h6><i class="fas fa-exclamation-triangle text-danger me-2"></i>Advertencias Críticas:</h6>';
            warningsList.appendChild(criticalDiv);
            
            criticalWarnings.forEach(warning => {
                const warningDiv = document.createElement('div');
                warningDiv.className = 'alert alert-danger';
                warningDiv.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Crítico:</strong> ${warning.message}
                    <br><small class="text-muted">${warning.type}: ${warning.code} - ${warning.name}</small>
                `;
                warningsList.appendChild(warningDiv);
            });
        }
        
        // Display informational warnings
        if (infoWarnings.length > 0) {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'mb-3';
            infoDiv.innerHTML = '<h6><i class="fas fa-info-circle text-info me-2"></i>Otros Mensajes:</h6>';
            warningsList.appendChild(infoDiv);
            
            infoWarnings.forEach(warning => {
                const warningDiv = document.createElement('div');
                warningDiv.className = 'alert alert-warning';
                warningDiv.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Info:</strong> ${warning.message}
                    <br><small class="text-muted">${warning.type}: ${warning.code} - ${warning.name}</small>
                `;
                warningsList.appendChild(warningDiv);
            });
        }
        
        // Update the total warnings display
        document.getElementById('totalWarnings').textContent = warnings.length;
    } else {
        const noWarningsDiv = document.createElement('div');
        noWarningsDiv.innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>No se encontraron advertencias.</div>';
        warningsList.appendChild(noWarningsDiv);
    }
    
    warningsSection.classList.remove('d-none');
}

function setupEventListeners(previewId) {
    // Confirm and save button
    document.getElementById('confirmBtn').addEventListener('click', function() {
        showConfirmationModal(previewId);
    });
    
    // Cancel button
    document.getElementById('cancelBtn').addEventListener('click', function() {
        // Redirect to previous page or main dashboard
        window.location.href = '/ppr';
    });
    
    // Commit button in modal
    document.getElementById('commitBtn').addEventListener('click', function() {
        commitPreviewData(previewId);
    });
}

function showConfirmationModal(previewId) {
    // Calculate summary for confirmation
    const totalProductos = parseInt(document.getElementById('totalProductos').textContent);
    const totalSubproductos = parseInt(document.getElementById('totalSubproductos').textContent);
    
    document.getElementById('confirmSummary').textContent = 
        `Productos: ${totalProductos}, Subproductos: ${totalSubproductos}`;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    modal.show();
}

function commitPreviewData(previewId) {
    // Hide modal first
    const modal = bootstrap.Modal.getInstance(document.getElementById('confirmationModal'));
    if (modal) {
        modal.hide();
    }
    
    // Show loading
    showLoading(true);
    
    // Need to fetch preview data first to determine if it's PPR, CEPLAN or CARTEGRA
    const token = localStorage.getItem('access_token');
    
    // Get the type from URL parameters to determine the endpoint
    const urlParams = new URLSearchParams(window.location.search);
    const dataType = urlParams.get('type') || 'ppr'; // default to ppr for backward compatibility
    
    let apiUrl;
    if (dataType === 'cartera') {
        apiUrl = `/api/v1/cartera/preview/${previewId}`;
    } else {
        apiUrl = `/api/v1/upload/preview/${previewId}`;
    }
    
    // First, get the preview data to determine the type
    fetch(apiUrl, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error al cargar los datos de previsualización para confirmar');
        }
        return response.json();
    })
    .then(previewResponse => {
        const previewData = previewResponse.data;
        
        // Determine if this is PPR, CEPLAN or CARTEGRA data
        let commitEndpoint;
        if (dataType === 'cartera') {
            commitEndpoint = `/api/v1/cartera/commit/${previewId}`;
        } else {
            let isCeplan = false;
            if (previewData.ceplan_data || (previewData.ceplan && previewData.subproductos)) {
                isCeplan = true;
            }
            commitEndpoint = isCeplan ? 
                `/api/v1/upload/commit-ceplan/${previewId}` : 
                `/api/v1/upload/commit/${previewId}`;
        }
        
        // Now make the commit request
        return fetch(commitEndpoint, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error al confirmar los datos');
        }
        return response.json();
    })
    .then(data => {
        showLoading(false);
        showSuccess('Datos confirmados y guardados exitosamente.');
        
        // Redirect to appropriate page after a short delay
        // For cartera data, redirect to transversal data page which has cartera tab
        if (dataType === 'cartera') {
            setTimeout(() => {
                window.location.href = '/transversal_data';
            }, 2000);
        } else {
            setTimeout(() => {
                window.location.href = '/ppr';
            }, 2000);
        }
    })
    .catch(error => {
        showLoading(false);
        showError(`Error al confirmar los datos: ${error.message}`);
        console.error('Error committing preview data:', error);
    });
}

function showLoading(show) {
    const loader = document.getElementById('loadingIndicator');
    const container = document.getElementById('previewContainer');
    
    if (show) {
        loader.classList.remove('d-none');
        container.classList.add('d-none');
    } else {
        loader.classList.add('d-none');
        // Don't show container here, only when data is loaded
    }
}

function showError(message) {
    const errorDiv = document.getElementById('errorIndicator');
    const errorMsg = document.getElementById('errorMessage');
    
    errorMsg.textContent = message;
    errorDiv.classList.remove('d-none');
    
    // Hide after 10 seconds
    setTimeout(() => {
        errorDiv.classList.add('d-none');
    }, 10000);
}

function showSuccess(message) {
    Swal.fire({
        title: 'Éxito',
        text: message,
        icon: 'success',
        confirmButtonText: 'Aceptar'
    });
}

// Initialize authentication and user info
initializeAuth();