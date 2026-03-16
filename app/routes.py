import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import (
    Flask, flash, jsonify, redirect, render_template_string, request, url_for, session, send_file
)
from werkzeug.utils import secure_filename

from app import db
from app.models import Picking, PickingItem, Mercancia, PickingCSV, PickingItemCSV, MercanciaCSV, Recepcion, RecepcionItem
from app.utils import (
    allowed_file, backup_csv, backup_db, build_pasillo_alfa_with_positions,
    get_distinct_item_types, get_distinct_values_for_filters, get_pasillo_for_item,
    validate_row_creation, validate_row_edit,
    load_columns_config, save_columns_config, DEFAULT_COLUMNS, import_csv_adaptive,
    get_mercancia_disponible, get_mercancia_by_marca_ref, descontar_mercancia,
    sync_to_pickings
)
from app.pdf_utils import generate_picking_pdf, generate_picking_list_pdf


BASE_HTML = """
<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
<title>CRUD Electro - Sync CSV</title></head><body class="p-4">
<div class="container">
<h3>CRUD - Importadora Electrodomésticos</h3>

<!-- Pestañas Picking / Inventario -->
<ul class="nav nav-tabs mt-3 mb-3">
  <li class="nav-item">
    <a class="nav-link {{ 'active' if request.path == '/' or request.path.startswith('/index') or request.path.startswith('/create') or request.path.startswith('/edit') or request.path.startswith('/delete') or request.path.startswith('/print') else '' }}" href="{{ url_for('index') }}">Picking</a>
  </li>
  <li class="nav-item">
    <a class="nav-link {{ 'active' if request.path == '/inventario' or request.path.startswith('/edit_mercancia') or request.path.startswith('/delete_mercancia') else '' }}" href="{{ url_for('inventario') }}">Inventario</a>
  </li>
</div>

<!-- Barra de herramientas según la pestaña activa -->
{% if request.path == '/' or request.path.startswith('/index') or request.path.startswith('/create') or request.path.startswith('/edit') or request.path.startswith('/delete') or request.path.startswith('/print') %}
<div class="mb-3 d-flex gap-2 flex-wrap">
    <a class="btn btn-primary" href="{{ url_for('create') }}">➕ Generar Picking</a>
    <a class="btn btn-secondary" href="{{ url_for('agregar_mercancia') }}">📦 Agregar mercancía</a>
    <a class="btn btn-success" href="{{ url_for('recepcion') }}">🚚 Recepción</a>
    <a class="btn btn-success" href="{{ url_for('export_csv') }}">📥 Exportar/Actualizar CSV</a>
    <a class="btn btn-info text-white" href="{{ url_for('upload_csv') }}">📤 Cargar CSV</a>
    <a class="btn btn-warning" href="#" data-bs-toggle="modal" data-bs-target="#columnsModal">⚙️ Columnas</a>
    <a class="btn btn-dark" href="http://localhost:8051/dashboard/" target="_blank">📊 Dashboard</a>
    <a class="btn btn-secondary" href="{{ url_for('download_csv') }}">💾 Descargar todo</a>
    <a class="btn btn-outline-primary" href="{{ url_for('download_csv', filter_Picking_ID=request.args.get('filter_Picking_ID', ''), filter_Fecha=request.args.get('filter_Fecha', ''), filter_Auxiliar=request.args.get('filter_Auxiliar', ''), filter_Marca=request.args.get('filter_Marca', ''), filter_Referencia=request.args.get('filter_Referencia', ''), filter_Pasillo=request.args.get('filter_Pasillo', ''), filter_Piso=request.args.get('filter_Piso', ''), filter_Categoria=request.args.get('filter_Categoria', '')) }}">🔍 Descargar filtrado</a>
    <form method="get" action="{{ url_for('print_all_pickings') }}" style="display:inline;">
        <input type="hidden" name="filter_Picking_ID" value="{{ request.args.get('filter_Picking_ID', '') }}">
        <input type="hidden" name="filter_Fecha" value="{{ request.args.get('filter_Fecha', '') }}">
        <input type="hidden" name="filter_Auxiliar" value="{{ request.args.get('filter_Auxiliar', '') }}">
        <input type="hidden" name="filter_Marca" value="{{ request.args.get('filter_Marca', '') }}">
        <input type="hidden" name="filter_Referencia" value="{{ request.args.get('filter_Referencia', '') }}">
        <input type="hidden" name="filter_Pasillo" value="{{ request.args.get('filter_Pasillo', '') }}">
        <input type="hidden" name="filter_Piso" value="{{ request.args.get('filter_Piso', '') }}">
        <input type="hidden" name="filter_Categoria" value="{{ request.args.get('filter_Categoria', '') }}">
        <button type="submit" class="btn btn-danger">🖨️ Imprimir filtro</button>
    </form>
    <a class="btn btn-secondary" href="{{ url_for('index') }}">🔄 Limpiar filtros</a>
</div>
{% endif %}

{% if request.path == '/inventario' or request.path.startswith('/edit_mercancia') or request.path.startswith('/delete_mercancia') %}
<div class="mb-3 d-flex gap-2 flex-wrap">
    <a class="btn btn-success" href="{{ url_for('recepcion') }}">🚚 Recepción</a>
    <a class="btn btn-success" href="{{ url_for('export_csv') }}">📥 Exportar/Actualizar CSV</a>
    <a class="btn btn-info text-white" href="{{ url_for('upload_csv') }}">📤 Cargar CSV</a>
    <a class="btn btn-warning" href="#" data-bs-toggle="modal" data-bs-target="#columnsModal">⚙️ Columnas</a>
    <a class="btn btn-dark" href="http://localhost:8051/dashboard/" target="_blank">📊 Dashboard</a>
    <a class="btn btn-secondary" href="{{ url_for('download_csv') }}">💾 Descargar todo</a>
    <a class="btn btn-secondary" href="{{ url_for('inventario') }}">🔄 Limpiar filtros</a>
</div>
{% endif %}

{% with messages = get_flashed_messages() %}
{% if messages %}<div class="alert alert-info">{{ messages[0] }}</div>{% endif %}
{% endwith %}
{{ body|safe }}
</div>

<div class="modal fade" id="columnsModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Configurar Columnas</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <form id="columnsForm">
            <div class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="selectAllColumns">
                    <label class="form-check-label fw-bold" for="selectAllColumns">Seleccionar todas</label>
                </div>
            </div>
            <hr>
            <div id="columnsList">
            {% for col_key, col_config in columns_config.items() %}
                <div class="mb-2">
                    <div class="form-check">
                        <input class="form-check-input column-checkbox" type="checkbox" 
                               name="columns" value="{{ col_key }}" 
                               id="col_{{ col_key }}"
                               {% if col_config.visible %}checked{% endif %}>
                        <label class="form-check-label" for="col_{{ col_key }}">{{ col_config.label }}</label>
                    </div>
                </div>
            {% endfor %}
            </div>
        </form>
      </div>
      <div class="modal-footer">
        <a href="{{ url_for('reset_columns') }}" class="btn btn-outline-secondary">Restablecer</a>
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
        <button type="button" class="btn btn-primary" id="saveColumnsBtn">Guardar</button>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script>
document.getElementById('selectAllColumns').addEventListener('change', function() {
    document.querySelectorAll('.column-checkbox').forEach(cb => cb.checked = this.checked);
});

document.getElementById('saveColumnsBtn').addEventListener('click', function() {
    const checked = Array.from(document.querySelectorAll('.column-checkbox:checked')).map(cb => cb.value);
    const allCols = Array.from(document.querySelectorAll('.column-checkbox')).map(cb => cb.value);
    
    fetch('{{ url_for("save_columns") }}', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({visible: checked})
    }).then(r => r.json()).then(data => {
        if (data.ok) {
            location.reload();
        }
    });
});
</script>
</body></html>
"""

CREATE_FORM = """
<form method="post" id="createForm">
<div class="row">
<div class="col-md-2 mb-2"><label>Tipo (filtrar)</label>
<select class="form-select" id="Tipo_selector" name="Tipo_selector">
<option value="">-- todos --</option>
{% for t in tipos %}<option value="{{ t }}">{{ t }}</option>{% endfor %}
</select>
</div>
<div class="col-md-4 mb-2"><label>Marca | Referencia (selector)</label>
<select class="form-select" id="Marca_ref_selector" name="Marca_ref_selector">
<option value="">-- seleccionar --</option>
</select>
</div>
<div class="col-md-2 mb-2"><label>Picking_ID</label><input class="form-control" name="Picking_ID" id="Picking_ID" readonly></div>
<div class="col-md-2 mb-2"><label>Fecha</label><input class="form-control" type="date" name="Fecha" id="Fecha"></div>
<div class="col-md-2 mb-2"><label>Hora generación</label><input class="form-control" type="time" step="1" name="Hora_generacion" id="Hora_generacion"></div>
</div>
<div class="row mt-2">
<div class="col-md-3 mb-2"><label>Marca (manual)</label><input class="form-control" name="Marca_solicitada" id="Marca_solicitada"></div>
<div class="col-md-3 mb-2"><label>Referencia (manual)</label><input class="form-control" name="Referencia_solicitada" id="Referencia_solicitada"></div>
<div class="col-md-3 mb-2"><label>Auxiliar</label>
<select class="form-select" name="Auxiliar" id="Auxiliar">
<option value="">-- seleccionar --</option>
{% for a in aux_opts %}<option value="{{ a }}">{{ a }}</option>{% endfor %}
</select>
</div>
</div>
<hr>
<div class="card bg-light mb-3">
<div class="card-body">
<h5>Calculadora FIFO</h5>
<div class="row align-items-end">
<div class="col-md-3">
<label class="form-label">Cantidad a picking:</label>
<input type="number" class="form-control" id="fifo_cantidad" min="1" value="1">
</div>
<div class="col-md-3">
<button type="button" class="btn btn-primary" id="calcular_fifo_btn">Calcular FIFO</button>
</div>
<div class="col-md-6">
<div id="fifo_resultado" class="alert alert-info d-none"></div>
</div>
</div>
</div>
</div>
<hr>
<h5>Ítems del Picking</h5>
<div id="items_container"></div>
<div class="mb-3">
<button type="button" class="btn btn-sm btn-outline-secondary" id="add_item_btn">Agregar ítem</button>
</div>
<div class="mt-3">
<button type="submit" id="saveBtn" class="btn btn-primary">Guardar</button>
<a class="btn btn-secondary" href="{{ url_for('index') }}">Cancelar</a>
</div>
</form>
<template id="item_row_template">
<div class="row item-row mb-2" data-locked="false">
<div class="col-md-2"><input class="form-control" name="item_tipo[]" placeholder="Tipo"></div>
<div class="col-md-2"><input class="form-control" name="item_marca[]" placeholder="Marca"></div>
<div class="col-md-3"><input class="form-control" name="item_referencia[]" placeholder="Referencia"></div>
<div class="col-md-1"><input class="form-control" name="item_cantidad[]" type="number" min="1" value="1"></div>
<div class="col-md-2"><input class="form-control" name="item_ubicacion[]" placeholder="Ubicación (FIFO)" readonly></div>
<div class="col-md-1 d-flex align-items-center">
<div class="form-check">
<input class="form-check-input item-lock" type="checkbox" name="item_locked[]" value="1" title="Fijar ítem">
<label class="form-check-label small">Fijar</label>
</div>
</div>
<div class="col-md-1"><button type="button" class="btn btn-danger btn-sm remove-item-btn">X</button></div>
</div>
</template>
<script>
document.addEventListener('DOMContentLoaded', function(){
let currentMarcaRef = '';

function actualizarMarcaRef() {
    const tipo = document.getElementById('Tipo_selector') ? document.getElementById('Tipo_selector').value : '';
    const marcaSel = document.getElementById('Marca_ref_selector');
    if (!marcaSel) return;
    
    if (!tipo) {
        marcaSel.innerHTML = '<option value="">-- seleccionar --</option>';
        return;
    }
    
    fetch('{{ url_for("marca_refs_for_type") }}?tipo=' + encodeURIComponent(tipo))
    .then(r => r.json())
    .then(j => {
        if(j.ok && Array.isArray(j.marca_refs)){
            marcaSel.innerHTML = '<option value="">-- seleccionar --</option>';
            j.marca_refs.forEach(mr => {
                const o = document.createElement('option');
                o.value = mr;
                o.text = mr;
                marcaSel.appendChild(o);
            });
        }
    })
    .catch(err => console.log('Error:', err));
}

const tipoSel = document.getElementById('Tipo_selector');
if(tipoSel) {
    tipoSel.addEventListener('change', actualizarMarcaRef);
}

const marcaSel = document.getElementById('Marca_ref_selector');
if(marcaSel) {
    marcaSel.addEventListener('change', function(){
        const val = this.value;
        currentMarcaRef = val;
        if(!val) return;
        
        // Update marca and referencia fields
        const parts = val.split('|').map(s => s.trim());
        if(parts[0]) document.getElementById('Marca_solicitada').value = parts[0];
        if(parts[1]) document.getElementById('Referencia_solicitada').value = parts[1];
        
        // Get FIFO positions
        const cantidad = parseInt(document.getElementById('fifo_cantidad').value) || 1;
        calcularFIFO(val, cantidad);
    });
}

// Calcular FIFO button
document.getElementById('calcular_fifo_btn').addEventListener('click', function(){
    if(!currentMarcaRef) {
        alert('Seleccione una Marca | Referencia primero');
        return;
    }
    const cantidad = parseInt(document.getElementById('fifo_cantidad').value) || 1;
    calcularFIFO(currentMarcaRef, cantidad);
});

function calcularFIFO(marcaRef, cantidad) {
    if(!marcaRef) return;
    
    fetch('/fifo_posiciones?marca_ref=' + encodeURIComponent(marcaRef) + '&cantidad=' + cantidad)
    .then(r => r.json())
    .then(j => {
        if(j.ok) {
            // Show result
            const resultDiv = document.getElementById('fifo_resultado');
            let html = '<strong>Stock disponible: ' + j.total_disponible + '</strong><br>';
            html += '<small>Posiciones FIFO:</small><ul class="mb-0">';
            j.posiciones_fifo.forEach(pos => {
                html += '<li>' + pos.pasillo + '-' + pos.estanteria + '-' + pos.piso + ': <strong>' + pos.cantidad + '</strong> unidades</li>';
            });
            if(!j.puede_completar) {
                html += '<li class="text-warning">Faltan ' + j.restante + ' unidades</li>';
            }
            html += '</ul>';
            resultDiv.innerHTML = html;
            resultDiv.classList.remove('d-none');
            
            // Add items with positions
            agregarItemsFIFO(j.posiciones_fifo);
        }
    })
    .catch(err => console.log('Error FIFO:', err));
}

function agregarItemsFIFO(posiciones) {
    const tipo = document.getElementById('Tipo_selector') ? document.getElementById('Tipo_selector').value : '';
    const marcaRef = currentMarcaRef || '';
    const parts = marcaRef.split('|').map(s => s.trim());
    const marca = parts[0] || '';
    const referencia = parts[1] || '';
    
    // Clear existing items (optional - keep if user wants to add more)
    // document.getElementById('items_container').innerHTML = '';
    
    posiciones.forEach(pos => {
        if(pos.cantidad > 0) {
            const ubicacion = pos.pasillo + '-' + pos.estanteria + '-' + pos.piso;
            addItemRow(tipo, marca, referencia, pos.cantidad, ubicacion);
        }
    });
    
    updateTotal();
}

function addItemRow(tipo='', marca='', referencia='', cantidad=1, ubicacion=''){
    const tpl = document.getElementById('item_row_template');
    const clone = tpl.content.cloneNode(true);
    const row = clone.querySelector('.item-row');
    if(tipo) row.querySelector('input[name="item_tipo[]"]').value = tipo;
    if(marca) row.querySelector('input[name="item_marca[]"]').value = marca;
    if(referencia) row.querySelector('input[name="item_referencia[]"]').value = referencia;
    if(cantidad) row.querySelector('input[name="item_cantidad[]"]').value = cantidad;
    if(ubicacion) row.querySelector('input[name="item_ubicacion[]"]').value = ubicacion;
    
    document.getElementById('items_container').appendChild(clone);
    attachRemoveHandlers();
    attachLockHandlers();
}

function attachRemoveHandlers(){
    document.querySelectorAll('.remove-item-btn').forEach(btn => {
        btn.onclick = function(){ this.closest('.item-row').remove(); updateTotal(); };
    });
}

function attachLockHandlers(){
    document.querySelectorAll('.item-lock').forEach(chk => {
        chk.onchange = function(){
            const row = this.closest('.item-row');
            row.dataset.locked = this.checked ? 'true' : 'false';
        };
    });
}

function updateTotal(){
    const qtyInputs = document.querySelectorAll('input[name="item_cantidad[]"]');
    let total = 0;
    qtyInputs.forEach(i => {
        const v = parseInt(i.value) || 0;
        total += v;
    });
    let totalField = document.querySelector('input[name="Cantidad"]');
    if(!totalField){
        totalField = document.createElement('input');
        totalField.type = 'hidden';
        totalField.name = 'Cantidad';
        document.getElementById('createForm').appendChild(totalField);
    }
    totalField.value = total;
}

fetch('{{ url_for("next_picking_id") }}')
.then(r => r.json())
.then(j => { if(j.next_id) document.getElementById('Picking_ID').value = j.next_id; })
.catch(e => console.log('Error:', e));

// Add empty row initially
if (document.getElementById('items_container').children.length === 0) {
    addItemRow();
}

document.getElementById('add_item_btn').addEventListener('click', function(){ 
    addItemRow(); 
});

updateTotal();
});
</script>
"""

EDIT_FORM = """
<form method="post" id="editForm">
<div class="row">
<div class="col-md-2 mb-2"><label>Tipo (filtrar)</label>
<select class="form-select" id="Tipo_selector" name="Tipo_selector">
<option value="">-- todos --</option>
{% for t in tipos %}<option value="{{ t }}">{{ t }}</option>{% endfor %}
</select>
</div>
<div class="col-md-4 mb-2"><label>Marca | Referencia (selector)</label>
<select class="form-select" id="Marca_ref_selector" name="Marca_ref_selector">
<option value="">-- seleccionar --</option>
{% for mr in marca_opts %}<option value="{{ mr }}" {% if mr == (p.Marca_solicitada + ' | ' + p.Referencia_solicitada).strip(' |') %}selected{% endif %}>{{ mr }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2 mb-2"><label>Picking_ID</label><input class="form-control" name="Picking_ID" value="{{ p.Picking_ID }}" readonly></div>
<div class="col-md-2 mb-2"><label>Fecha</label><input class="form-control" type="date" name="Fecha" value="{{ p.Fecha }}"></div>
<div class="col-md-2 mb-2"><label>Hora generación</label><input class="form-control" type="time" step="1" name="Hora_generacion" value="{{ p.Hora_generacion }}"></div>
</div>
<div class="row mt-2">
<div class="col-md-3 mb-2"><label>Marca (manual)</label><input class="form-control" name="Marca_solicitada" id="Marca_solicitada" value="{{ p.Marca_solicitada or '' }}"></div>
<div class="col-md-3 mb-2"><label>Referencia (manual)</label><input class="form-control" name="Referencia_solicitada" id="Referencia_solicitada" value="{{ p.Referencia_solicitada or '' }}"></div>
<div class="col-md-3 mb-2"><label>Auxiliar</label>
<select class="form-select" name="Auxiliar" id="Auxiliar">
<option value="">-- seleccionar --</option>
{% for a in aux_opts %}<option value="{{ a }}" {% if a == p.Auxiliar %}selected{% endif %}>{{ a }}</option>{% endfor %}
</select>
</div>
<div class="col-md-3 mb-2"><label>Pasillo</label>
<input class="form-control" name="Pasillo" id="Pasillo" list="pasillos_list" value="{{ p.Pasillo or '' }}">
<datalist id="pasillos_list">{% for pa in pas_opts %}<option value="{{ pa }}">{% endfor %}</datalist>
</div>
</div>
<hr>
<h5>Ítems del Picking</h5>
<div id="items_container">
{{ items_html|safe }}
</div>
<div class="mb-3">
<button type="button" class="btn btn-sm btn-outline-secondary" id="add_item_btn">Agregar ítem</button>
<small class="text-muted ms-2">Marque "Fijar" para evitar que el autocompletado sobrescriba ese ítem.</small>
</div>
<div class="row mt-2">
<div class="col-md-3 mb-2"><label>Unidades Erradas</label><input class="form-control" type="number" id="unidades_erradas" min="0" value="{{ p.Unidades_erradas if p.Unidades_erradas is not none else 0 }}"></div>
<div class="col-md-3 mb-2"><label>% Error</label><input class="form-control" type="number" step="0.1" id="Error_porcentaje_display" value="{{ p.Error_porcentaje if p.Error_porcentaje is not none else 0 }}" readonly></div>
<div class="col-md-2 mb-2"><label>&nbsp;</label><button type="button" class="btn btn-secondary" id="calcular_error_btn">Calcular % Error</button></div>
<div class="col-md-2 mb-2"><label>Cantidad total</label><input class="form-control" type="number" name="Cantidad" id="Cantidad_total" value="{{ p.Cantidad or 0 }}" readonly></div>
</div>
<div class="row mt-2">
<div class="col-md-3 mb-2 d-none"><label>Error % (hidden)</label><input class="form-control" type="number" step="0.1" name="Error_porcentaje" id="Error_porcentaje" value="{{ p.Error_porcentaje if p.Error_porcentaje is not none else '' }}"></div>
</div>
<div class="mt-3">
<button type="submit" id="saveBtn" class="btn btn-primary">Guardar</button>
<a class="btn btn-secondary" href="{{ url_for('index') }}">Cancelar</a>
</div>
</form>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const unidadesErradasInput = document.getElementById('unidades_erradas');
    const errorPorcentajeDisplay = document.getElementById('Error_porcentaje_display');
    const errorPorcentajeHidden = document.getElementById('Error_porcentaje');
    const cantidadTotalInput = document.getElementById('Cantidad_total');
    const calcularBtn = document.getElementById('calcular_error_btn');
    
    function calcularError() {
        const unidadesErradas = parseFloat(unidadesErradasInput.value) || 0;
        const cantidadTotal = parseFloat(cantidadTotalInput.value) || 0;
        
        if (cantidadTotal > 0) {
            const porcentajeError = (unidadesErradas / cantidadTotal) * 100;
            errorPorcentajeDisplay.value = porcentajeError.toFixed(2);
            errorPorcentajeHidden.value = porcentajeError.toFixed(2);
        } else {
            errorPorcentajeDisplay.value = 0;
            errorPorcentajeHidden.value = 0;
        }
    }
    
    calcularBtn.addEventListener('click', calcularError);
    
    // Calcular automáticamente cuando cambian las unidades erradas o la cantidad total
    unidadesErradasInput.addEventListener('input', calcularError);
    cantidadTotalInput.addEventListener('change', calcularError);
});
</script>
"""


def register_routes(app: Flask) -> None:
    
    @app.route("/")
    def index():
        f_pid = request.args.get("filter_Picking_ID", "")
        f_fecha = request.args.get("filter_Fecha", "")
        f_aux = request.args.get("filter_Auxiliar", "")
        f_marca = request.args.get("filter_Marca", "")
        f_ref = request.args.get("filter_Referencia", "")
        f_pas = request.args.get("filter_Pasillo", "")
        f_piso = request.args.get("filter_Piso", "")
        f_cat = request.args.get("filter_Categoria", "")
        
        q = Picking.query
        if f_pid:
            q = q.filter(Picking.Picking_ID == f_pid)
        if f_fecha:
            q = q.filter(Picking.Fecha == f_fecha)
        if f_aux:
            q = q.filter(Picking.Auxiliar == f_aux)
        if f_marca:
            parts = [p.strip() for p in f_marca.split("|")]
            marca = parts[0] if parts else ""
            ref = parts[1] if len(parts) > 1 else None
            if marca and ref:
                q = q.filter(Picking.Marca_solicitada == marca, Picking.Referencia_solicitada == ref)
            elif marca:
                q = q.filter(Picking.Marca_solicitada == marca)
        if f_ref:
            q = q.filter(Picking.Referencia_solicitada == f_ref)
        if f_pas:
            q = q.filter(Picking.Pasillo == f_pas)
        if f_piso:
            q = q.filter(Picking.Piso == f_piso)
        if f_cat:
            q = q.filter(Picking.Categoria_producto == f_cat)
        
        try:
            rows = q.all()
        except Exception:
            rows = []
        
        def key_fn(r):
            pid = (r.Picking_ID or "").strip()
            return (int(pid) if pid.isdigit() else float("inf"), pid)
        
        rows_sorted = sorted(rows, key=key_fn)
        distincts = get_distinct_values_for_filters()
        
        columns_config = load_columns_config()
        visible_cols = [k for k, v in columns_config.items() if v.get("visible", True)]
        visible_cols = sorted(visible_cols, key=lambda k: columns_config[k].get("order", 99))
        
        form = render_template_string("""
<form method="get" class="row g-2 mb-3">
<div class="col-md-2"><label>Picking_ID</label>
<select class="form-select" name="filter_Picking_ID"><option value="">-- todos --</option>
{% for v in distincts.Picking_ID %}<option value="{{ v }}" {% if v==f_pid %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2"><label>Fecha</label>
<select class="form-select" name="filter_Fecha"><option value="">-- todas --</option>
{% for v in distincts.Fecha %}<option value="{{ v }}" {% if v==f_fecha %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2"><label>Auxiliar</label>
<select class="form-select" name="filter_Auxiliar"><option value="">-- todos --</option>
{% for v in distincts.Auxiliar %}<option value="{{ v }}" {% if v==f_aux %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-3"><label>Marca | Referencia</label>
<select class="form-select" name="filter_Marca"><option value="">-- todas --</option>
{% for v in distincts.Marca %}<option value="{{ v }}" {% if v==f_marca %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-3"><label>Referencia</label>
<select class="form-select" name="filter_Referencia"><option value="">-- todas --</option>
{% for v in distincts.Referencia %}<option value="{{ v }}" {% if v==f_ref %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-3 mt-2"><label>Pasillo</label>
<select class="form-select" name="filter_Pasillo"><option value="">-- todos --</option>
{% for v in distincts.Pasillo %}<option value="{{ v }}" {% if v==f_pas %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-3 mt-2"><label>Piso</label>
<select class="form-select" name="filter_Piso"><option value="">-- todas --</option>
{% for v in distincts.Piso %}<option value="{{ v }}" {% if v==f_piso %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-3 mt-2"><label>Categoria</label>
<select class="form-select" name="filter_Categoria"><option value="">-- todas --</option>
{% for v in distincts.Categoria %}<option value="{{ v }}" {% if v==f_cat %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-3 d-flex align-items-end mt-2">
<div>
<button class="btn btn-primary me-2" type="submit">Aplicar filtros</button>
<a class="btn btn-outline-secondary" href="{{ url_for('index') }}">Limpiar</a>
</div>
</div>
</form>
        """, distincts=type("D", (), distincts)(), f_pid=f_pid, f_fecha=f_fecha, f_aux=f_aux, f_marca=f_marca, f_ref=f_ref, f_pas=f_pas, f_piso=f_piso, f_cat=f_cat)
        
        table_rows = []
        for r in rows_sorted:
            table_rows.append({
                "Picking_ID": r.Picking_ID,
                "Fecha": r.Fecha,
                "Hora_gen": r.Hora_generacion,
                "Auxiliar": r.Auxiliar,
                "Marca": r.Marca_solicitada,
                "Referencia": r.Referencia_solicitada,
                "Pasillo": r.Pasillo,
                "Piso": r.Piso,
                "Cantidad": r.Cantidad,
                "Error": r.Error_porcentaje if r.Error_porcentaje is not None else "",
                "modified_at": r.modified_at,
                "edit_url": url_for("edit", pid=r.Picking_ID) if r.Picking_ID else None,
                "print_url": url_for("print_picking", pid=r.Picking_ID) if r.Picking_ID else None,
                "delete_url": url_for("delete", pid=r.Picking_ID) if r.Picking_ID else None
            })
        
        table_html = render_template_string("""
<table id="pickings_table" class="display table table-sm table-striped" style="width:100%">
<thead><tr>
{% if 'Picking_ID' in visible_cols %}<th>Picking_ID</th>{% endif %}
{% if 'Fecha' in visible_cols %}<th>Fecha</th>{% endif %}
{% if 'Hora_gen' in visible_cols %}<th>Hora_gen</th>{% endif %}
{% if 'Auxiliar' in visible_cols %}<th>Auxiliar</th>{% endif %}
{% if 'Marca' in visible_cols %}<th>Marca</th>{% endif %}
{% if 'Referencia' in visible_cols %}<th>Referencia</th>{% endif %}
{% if 'Pasillo' in visible_cols %}<th>Pasillo</th>{% endif %}
{% if 'Piso' in visible_cols %}<th>Piso</th>{% endif %}
{% if 'Cantidad' in visible_cols %}<th>Cantidad</th>{% endif %}
{% if 'Error' in visible_cols %}<th>Error(%)</th>{% endif %}
{% if 'modified_at' in visible_cols %}<th>modified_at</th>{% endif %}
{% if 'acciones' in visible_cols %}<th>acciones</th>{% endif %}
</tr></thead>
<tbody>
{% for r in rows %}
<tr>
{% if 'Picking_ID' in visible_cols %}<td>{{ r.Picking_ID }}</td>{% endif %}
{% if 'Fecha' in visible_cols %}<td>{{ r.Fecha }}</td>{% endif %}
{% if 'Hora_gen' in visible_cols %}<td>{{ r.Hora_gen }}</td>{% endif %}
{% if 'Auxiliar' in visible_cols %}<td>{{ r.Auxiliar }}</td>{% endif %}
{% if 'Marca' in visible_cols %}<td>{{ r.Marca }}</td>{% endif %}
{% if 'Referencia' in visible_cols %}<td>{{ r.Referencia }}</td>{% endif %}
{% if 'Pasillo' in visible_cols %}<td>{{ r.Pasillo }}</td>{% endif %}
{% if 'Piso' in visible_cols %}<td>{{ r.Piso }}</td>{% endif %}
{% if 'Cantidad' in visible_cols %}<td>{{ r.Cantidad }}</td>{% endif %}
{% if 'Error' in visible_cols %}<td>{{ r.Error }}</td>{% endif %}
{% if 'modified_at' in visible_cols %}<td>{{ r.modified_at }}</td>{% endif %}
{% if 'acciones' in visible_cols %}
<td>
{% if r.edit_url %}
<a class="btn btn-sm btn-outline-primary" href="{{ r.edit_url }}">Editar</a>
{% else %}
<button class="btn btn-sm btn-outline-secondary" disabled>Editar</button>
{% endif %}
{% if r.print_url %}
<a class="btn btn-sm btn-outline-dark" href="{{ r.print_url }}" target="_blank">🖨️</a>
{% endif %}
{% if r.delete_url %}
<a class="btn btn-sm btn-outline-danger" href="#" onclick="if(confirm('¿Estás seguro de eliminar este registro?')) { window.location.href='{{ r.delete_url }}'; }">Eliminar</a>
{% else %}
<button class="btn btn-sm btn-outline-secondary" disabled>Eliminar</button>
{% endif %}
</td>
{% endif %}
</tr>
{% endfor %}
</tbody>
</table>
<script>
$(document).ready(function() {
$('#pickings_table').DataTable({
order: [[0, 'asc']],
columnDefs: [{ targets: 0, type: 'num' }],
pageLength: 25,
lengthMenu: [10,25,50,100]
});
});
</script>
        """, rows=table_rows, visible_cols=visible_cols)
        
        body = form + table_html
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/inventario", methods=["GET"])
    def inventario():
        # Filtros para inventario
        f_sku = request.args.get("filter_SKU", "")
        f_marca = request.args.get("filter_Marca", "")
        f_ref = request.args.get("filter_Referencia", "")
        f_pas = request.args.get("filter_Pasillo", "")
        f_est = request.args.get("filter_Estanteria", "")
        f_piso = request.args.get("filter_Piso", "")
        
        # Query para Mercancia
        q = Mercancia.query
        if f_sku:
            q = q.filter(Mercancia.sku == f_sku)
        if f_marca:
            q = q.filter(Mercancia.marca == f_marca)
        if f_ref:
            q = q.filter(Mercancia.referencia == f_ref)
        if f_pas:
            q = q.filter(Mercancia.pasillo == f_pas)
        if f_est:
            q = q.filter(Mercancia.estanteria == f_est)
        if f_piso:
            q = q.filter(Mercancia.piso == f_piso)
        
        try:
            rows = q.all()
        except Exception:
            rows = []
        
        # Obtener valores distintos para filtros
        distincts = {
            "SKU": sorted(set([r.sku for r in Mercancia.query.with_entities(Mercancia.sku).distinct().all() if r.sku])),
            "Marca": sorted(set([r.marca for r in Mercancia.query.with_entities(Mercancia.marca).distinct().all() if r.marca])),
            "Referencia": sorted(set([r.referencia for r in Mercancia.query.with_entities(Mercancia.referencia).distinct().all() if r.referencia])),
            "Pasillo": sorted(set([r.pasillo for r in Mercancia.query.with_entities(Mercancia.pasillo).distinct().all() if r.pasillo])),
            "Estanteria": sorted(set([r.estanteria for r in Mercancia.query.with_entities(Mercancia.estanteria).distinct().all() if r.estanteria]), key=lambda x: int(x) if x.isdigit() else float('inf')),
            "Piso": sorted(set([r.piso for r in Mercancia.query.with_entities(Mercancia.piso).distinct().all() if r.piso])),
        }
        
        # Formulario de filtros
        form = render_template_string("""
<form method="get" class="row g-2 mb-3">
<div class="col-md-2"><label>SKU</label>
<select class="form-select" name="filter_SKU"><option value="">-- todos --</option>
{% for v in distincts.SKU %}<option value="{{ v }}" {% if v==f_sku %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2"><label>Marca</label>
<select class="form-select" name="filter_Marca"><option value="">-- todas --</option>
{% for v in distincts.Marca %}<option value="{{ v }}" {% if v==f_marca %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2"><label>Referencia</label>
<select class="form-select" name="filter_Referencia"><option value="">-- todas --</option>
{% for v in distincts.Referencia %}<option value="{{ v }}" {% if v==f_ref %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2"><label>Pasillo</label>
<select class="form-select" name="filter_Pasillo"><option value="">-- todos --</option>
{% for v in distincts.Pasillo %}<option value="{{ v }}" {% if v==f_pas %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2"><label>Estantería</label>
<select class="form-select" name="filter_Estanteria"><option value="">-- todas --</option>
{% for v in distincts.Estanteria %}<option value="{{ v }}" {% if v==f_est %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2"><label>Piso</label>
<select class="form-select" name="filter_Piso"><option value="">-- todos --</option>
{% for v in distincts.Piso %}<option value="{{ v }}" {% if v==f_piso %}selected{% endif %}>{{ v }}</option>{% endfor %}
</select>
</div>
<div class="col-md-3 d-flex align-items-end mt-2">
<div>
<button class="btn btn-primary me-2" type="submit">Aplicar filtros</button>
<a class="btn btn-outline-secondary" href="{{ url_for('inventario') }}">Limpiar</a>
</div>
</div>
</form>
        """, distincts=type("D", (), distincts)(), f_sku=f_sku, f_marca=f_marca, f_ref=f_ref, f_pas=f_pas, f_est=f_est, f_piso=f_piso)
        
        # Preparar datos para la tabla
        table_rows = []
        for r in rows:
            ubicacion = f"{r.pasillo or ''}-{r.estanteria or ''}-{r.piso or ''}".strip("-")
            table_rows.append({
                "SKU": r.sku,
                "Marca": r.marca,
                "Referencia": r.referencia,
                "Cantidad": r.cantidad,
                "Ubicacion": ubicacion,
                "modified_at": r.modified_at,
                "edit_url": url_for("edit_mercancia", mid=r.id) if r.id else None,
                "delete_url": url_for("delete_mercancia", mid=r.id) if r.id else None
            })
        
        # Tabla HTML
        table_html = render_template_string("""
<table id="inventario_table" class="display table table-sm table-striped" style="width:100%">
<thead><tr>
<th>SKU</th>
<th>Marca</th>
<th>Referencia</th>
<th>Cantidad</th>
<th>Ubicación</th>
<th>modified_at</th>
<th>acciones</th>
</tr></thead>
<tbody>
{% for r in rows %}
<tr>
<td>{{ r.SKU }}</td>
<td>{{ r.Marca }}</td>
<td>{{ r.Referencia }}</td>
<td>{{ r.Cantidad }}</td>
<td>{{ r.Ubicacion }}</td>
<td>{{ r.modified_at }}</td>
<td>
{% if r.edit_url %}
<a class="btn btn-sm btn-outline-primary" href="{{ r.edit_url }}">Editar</a>
{% endif %}
{% if r.delete_url %}
<a class="btn btn-sm btn-outline-danger" href="#" onclick="if(confirm('¿Estás seguro de eliminar esta mercancía?')) { window.location.href='{{ r.delete_url }}'; }">Eliminar</a>
{% endif %}
</td>
</tr>
{% endfor %}
</tbody>
</table>
<script>
$(document).ready(function() {
$('#inventario_table').DataTable({
order: [[0, 'asc']],
pageLength: 25,
lengthMenu: [10,25,50,100]
});
});
</script>
        """, rows=table_rows)
        
        body = form + table_html
        return render_template_string(BASE_HTML, body=body, columns_config=load_columns_config())

    @app.route("/create", methods=["GET", "POST"])
    def create():
        distincts = get_distinct_values_for_filters()
        marca_opts = distincts["Marca"]
        aux_opts = distincts["Auxiliar"]
        pas_opts = distincts["Pasillo"]
        cat_opts = distincts["Categoria"]
        piso_opts = distincts["Piso"]
        tipos = get_distinct_item_types()
        all_categories = sorted(set(list(cat_opts) + tipos))
        
        # Get estanteria options from Mercancia
        try:
            estanteria_rows = db.session.query(Mercancia.estanteria).distinct().filter(Mercancia.estanteria != None).all()
            est_opts = sorted([r[0] for r in estanteria_rows if r[0]])
        except Exception:
            est_opts = []
        
        # Create posicion options (combination of pasillo-estanteria-piso)
        try:
            posicion_rows = db.session.query(Mercancia.pasillo, Mercancia.estanteria, Mercancia.piso).distinct().all()
            posicion_opts = []
            for pas, est, pis in posicion_rows:
                if pas or est or pis:
                    parts = []
                    if pas: parts.append(pas)
                    if est: parts.append(est)
                    if pis: parts.append(pis)
                    if parts:
                        posicion_opts.append("-".join(parts))
            posicion_opts = sorted(set(posicion_opts))
        except Exception:
            posicion_opts = []
        
        mercancia_opts = get_mercancia_disponible()
        mercancia_select = []
        for m in mercancia_opts:
            ubicacion = ""
            if m.get('pasillo'):
                ubicacion = f"Pas: {m['pasillo']}"
            if m.get('estanteria'):
                ubicacion += f" Est: {m['estanteria']}"
            if m.get('piso'):
                ubicacion += f" Piso: {m['piso']}"
            ubicacion = ubicacion.strip() or "Sin ubicación"
            label = f"{m['marca']} | {m['referencia']} (Stock: {m['cantidad']}) - {ubicacion}"
            mercancia_select.append({'label': label, 'value': str(m['id'])})
        
        if request.method == "POST":
            data = request.form.to_dict()
            marca_ref = data.get("Marca_ref_selector")
            if marca_ref:
                parts = [p.strip() for p in marca_ref.split("|")]
                data["Marca_solicitada"] = parts[0] if parts else ""
                data["Referencia_solicitada"] = parts[1] if len(parts) > 1 else ""
            
            mercancia_seleccionada = data.get("mercancia_seleccionada")
            
            now_dt = datetime.now()
            data["Fecha"] = now_dt.strftime("%Y-%m-%d")
            data["Hora_generacion"] = now_dt.strftime("%H:%M:%S")
            
            tipos_list = request.form.getlist("item_tipo[]")
            marcas = request.form.getlist("item_marca[]")
            referencias = request.form.getlist("item_referencia[]")
            cantidades = request.form.getlist("item_cantidad[]")
            locked_flags = request.form.getlist("item_locked[]")
            
            items_data = []
            total_qty = 0
            pasillos_ordered = []
            
            for i in range(len(tipos_list)):
                t = tipos_list[i].strip() if i < len(tipos_list) else ""
                m = marcas[i].strip() if i < len(marcas) else ""
                rref = referencias[i].strip() if i < len(referencias) else ""
                try:
                    cqty = int(cantidades[i]) if i < len(cantidades) and cantidades[i] != "" else 1
                except (ValueError, TypeError):
                    cqty = 1
                locked = i < len(locked_flags)
                items_data.append({"tipo": t, "marca": m, "referencia": rref, "cantidad": cqty, "locked": locked})
                total_qty += cqty
                pas = get_pasillo_for_item(m, rref)
                pasillos_ordered.append(pas if pas else "")
            
            data["Cantidad"] = str(total_qty)
            ok, msg = validate_row_creation(data)
            if not ok:
                flash(msg)
                return redirect(url_for("create"))
            
            backup_db()
            pasillo_field = build_pasillo_alfa_with_positions(pasillos_ordered)
            audit_user = app.config.get("AUDIT_USER", "ui_user")
            
            p = Picking(
                Picking_ID=str(data.get("Picking_ID", "")).strip(),
                Fecha=str(data.get("Fecha", "")).strip(),
                Hora_generacion=str(data.get("Hora_generacion", "")).strip(),
                Hora_revision=str(data.get("Hora_revision", "")).strip(),
                Hora_despacho=str(data.get("Hora_despacho", "")).strip(),
                Auxiliar=str(data.get("Auxiliar", "")).strip(),
                Cantidad_pickings_por_auxiliar=int(data.get("Cantidad_pickings_por_auxiliar") or 0),
                Pasillo=pasillo_field,
                Estanteria=str(data.get("Estanteria", "")).strip(),
                Piso=str(data.get("Piso", "")).strip(),
                Marca_solicitada=str(data.get("Marca_solicitada", "")).strip(),
                Referencia_solicitada=str(data.get("Referencia_solicitada", "")).strip(),
                Categoria_producto=str(data.get("Categoria_producto", "")).strip(),
                Cantidad=total_qty,
                Error_porcentaje=None,
                modified_by=audit_user,
                modified_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            db.session.add(p)
            db.session.flush()
            
            for it in items_data:
                if it["tipo"] or it["marca"] or it["referencia"]:
                    try:
                        item = PickingItem(
                            Picking_ID=p.Picking_ID,
                            tipo=it["tipo"] or (p.Categoria_producto or "Item"),
                            marca=it["marca"],
                            referencia=it["referencia"],
                            cantidad=it["cantidad"]
                        )
                        db.session.add(item)
                        db.session.flush()
                        
                        descontar_mercancia(it["marca"], it["referencia"], it["cantidad"])
                    except Exception:
                        db.session.rollback()
            
            db.session.commit()
            flash("Creado (Pasillo y Cantidad total calculados automáticamente). Mercanía descontada del inventario.")
            return redirect(url_for("index"))
        
        body = render_template_string(CREATE_FORM, marca_opts=marca_opts, aux_opts=aux_opts, pas_opts=pas_opts, est_opts=est_opts, cat_opts=all_categories, piso_opts=piso_opts, posicion_opts=posicion_opts, tipos=tipos, mercancia_opts=mercancia_select)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/get_marcas_por_categoria")
    def get_marcas_por_categoria():
        categoria = request.args.get("categoria", "").strip()
        if not categoria:
            return jsonify({"ok": False, "msg": "Categoría vacía"}), 400
        
        try:
            marcas = sorted([m.marca for m in Mercancia.query.filter(Mercancia.categoria_producto == categoria).with_entities(Mercancia.marca).distinct().all() if m.marca])
        except Exception:
            marcas = []
        
        return jsonify({"ok": True, "marcas": marcas})
    
    @app.route("/get_posiciones_por_categoria")
    def get_posiciones_por_categoria():
        categoria = request.args.get("categoria", "").strip()
        if not categoria:
            return jsonify({"ok": False, "msg": "Categoría vacía"}), 400
        
        try:
            posiciones = sorted(set([f"{m.pasillo}-{m.estanteria}-{m.piso}" for m in Mercancia.query.filter(Mercancia.categoria_producto == categoria).distinct().all() if m.pasillo and m.estanteria and m.piso]))
        except Exception:
            posiciones = []
        
        return jsonify({"ok": True, "posiciones": posiciones})
    
    @app.route("/get_all_marcas")
    def get_all_marcas():
        try:
            marcas = sorted([m.marca for m in Mercancia.query.with_entities(Mercancia.marca).distinct().all() if m.marca])
        except Exception:
            marcas = []
        
        return jsonify({"ok": True, "marcas": marcas})
    
    @app.route("/get_all_posiciones")
    def get_all_posiciones():
        try:
            posiciones = sorted(set([f"{m.pasillo}-{m.estanteria}-{m.piso}" for m in Mercancia.query.with_entities(Mercancia.pasillo, Mercancia.estanteria, Mercancia.piso).distinct().all() if m.pasillo and m.estanteria and m.piso]))
        except Exception:
            posiciones = []
            
        return jsonify({"ok": True, "posiciones": posiciones})
    
    @app.route("/agregar_mercancia", methods=["GET", "POST"])
    def agregar_mercancia():
        distincts = get_distinct_values_for_filters()
        marca_opts = distincts["Marca"]
        
        mercancia_marcas = sorted([m.marca for m in Mercancia.query.with_entities(Mercancia.marca).distinct().all() if m.marca])
        marca_opts = sorted(set(list(marca_opts) + mercancia_marcas))
        
        pas_opts = distincts["Pasillo"]
        mercancia_pasillos = sorted([m.pasillo for m in Mercancia.query.with_entities(Mercancia.pasillo).distinct().all() if m.pasillo])
        pas_opts = sorted(set(list(pas_opts) + mercancia_pasillos))
        
        est_opts = sorted(set([p.Estanteria for p in Picking.query.with_entities(Picking.Estanteria).distinct().all() if p.Estanteria]))
        mercancia_est = sorted([m.estanteria for m in Mercancia.query.with_entities(Mercancia.estanteria).distinct().all() if m.estanteria])
        est_opts = sorted(set(list(est_opts) + mercancia_est))
        
        piso_opts = distincts["Piso"]
        mercancia_pisos = sorted([m.piso for m in Mercancia.query.with_entities(Mercancia.piso).distinct().all() if m.piso])
        piso_opts = sorted(set(list(piso_opts) + mercancia_pisos))
        
        cat_opts = distincts["Categoria"]
        mercancia_cats = sorted([m.categoria_producto for m in Mercancia.query.with_entities(Mercancia.categoria_producto).distinct().all() if m.categoria_producto])
        cat_opts = sorted(set(list(cat_opts) + mercancia_cats))
        
        tipos = get_distinct_item_types()
        
        all_categories = sorted(set(list(cat_opts) + tipos))
        
        if request.method == "POST":
            data = request.form.to_dict()
            
            now_dt = datetime.now()
            fecha_ingreso = now_dt.strftime("%Y-%m-%d")
            hora_ingreso = now_dt.strftime("%H:%M:%S")
            
            try:
                cantidad = int(data.get("Cantidad", 0))
            except (ValueError, TypeError):
                cantidad = 0
            
            if cantidad <= 0:
                flash("La cantidad debe ser mayor a 0")
                return redirect(url_for("agregar_mercancia"))
            
            pasillo = str(data.get("Pasillo", "")).strip()
            estanteria = str(data.get("Estanteria", "")).strip()
            piso = str(data.get("Piso", "")).strip()
            marca = str(data.get("Marca_solicitada", "")).strip()
            referencia = str(data.get("Referencia_solicitada", "")).strip()
            sku = str(data.get("SKU", "")).strip()
            
            if not marca and not referencia and not sku:
                flash("Debe agregar al menos un SKU, marca o referencia")
                return redirect(url_for("agregar_mercancia"))
            
            audit_user = app.config.get("AUDIT_USER", "ui_user")
            
            categoria = str(data.get("Categoria_producto", "")).strip()
            
            marca_lower = marca.strip().lower() if marca else ""
            referencia_lower = referencia.strip().lower() if referencia else ""
            
            if marca_lower and referencia_lower:
                existing = Mercancia.query.filter(
                    db.func.lower(Mercancia.marca) == marca_lower,
                    db.func.lower(Mercancia.referencia) == referencia_lower
                ).first()
            else:
                existing = None
            
            if existing:
                existing.cantidad = (existing.cantidad or 0) + cantidad
                if sku:
                    existing.sku = sku
                if categoria:
                    existing.categoria_producto = categoria
                if pasillo:
                    existing.pasillo = pasillo
                if estanteria:
                    existing.estanteria = estanteria
                if piso:
                    existing.piso = piso
                existing.modified_by = audit_user
                existing.modified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = "Mercancía actualizada (sumada)."
            else:
                m = Mercancia(
                    sku=sku,
                    marca=marca,
                    referencia=referencia,
                    cantidad=cantidad,
                    categoria_producto=categoria,
                    pasillo=pasillo,
                    estanteria=estanteria,
                    piso=piso,
                    fecha_ingreso=fecha_ingreso,
                    hora_ingreso=hora_ingreso,
                    modified_by=audit_user,
                    modified_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                db.session.add(m)
                msg = "Mercancía agregada correctamente."
            
            db.session.commit()
            flash(msg)
            return redirect(url_for("agregar_mercancia"))
        
        # Get initial options for marca and posicion (filtered by category if any)
        initial_categoria = request.args.get("categoria", "")
        if initial_categoria:
            initial_marca_opts = sorted([m.marca for m in Mercancia.query.filter(Mercancia.categoria_producto == initial_categoria).with_entities(Mercancia.marca).distinct().all() if m.marca])
            initial_posicion_opts = sorted(set([f"{m.pasillo}-{m.estanteria}-{m.piso}" for m in Mercancia.query.filter(Mercancia.categoria_producto == initial_categoria).distinct().all() if m.pasillo and m.estanteria and m.piso]))
        else:
            initial_marca_opts = marca_opts
            initial_posicion_opts = sorted(set([f"{m.pasillo}-{m.estanteria}-{m.piso}" for m in Mercancia.query.with_entities(Mercancia.pasillo, Mercancia.estanteria, Mercancia.piso).distinct().all() if m.pasillo and m.estanteria and m.piso]))
        
        mercancia_form = """
<form method="post">
<div class="row">
    <div class="col-md-6 mb-2">
        <label>SKU (código único del producto)</label>
        <input class="form-control" name="SKU" id="SKU" placeholder="Ingrese o escanee el SKU" autofocus>
    </div>
    <div class="col-md-3 mb-2">
        <label>Categoría producto</label>
        <select class="form-select" name="Categoria_producto" id="Categoria_producto">
            <option value="">-- seleccionar --</option>
            {% for c in all_categories %}<option value="{{ c }}" {% if c==initial_categoria %}selected{% endif %}>{{ c }}</option>{% endfor %}
        </select>
    </div>
    <div class="col-md-3 mb-2">
        <label>Marca</label>
        <select class="form-select" name="Marca_solicitada" id="Marca_solicitada">
            <option value="">-- seleccionar --</option>
            {% for m in initial_marca_opts %}<option value="{{ m }}">{{ m }}</option>{% endfor %}
        </select>
    </div>
</div>
<div class="row">
    <div class="col-md-4 mb-2">
        <label>Referencia</label>
        <input class="form-control" name="Referencia_solicitada" id="Referencia_solicitada">
    </div>
    <div class="col-md-2 mb-2">
        <label>Cantidad</label>
        <input class="form-control" type="number" name="Cantidad" id="Cantidad" min="1" value="1" required>
    </div>
    <div class="col-md-2 mb-2">
        <label>Posición</label>
        <select class="form-select" name="Posicion" id="Posicion">
            <option value="">-- seleccionar --</option>
            {% for p in initial_posicion_opts %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
        </select>
    </div>
</div>
<div class="mt-3">
    <button type="submit" class="btn btn-primary">Guardar</button>
    <a class="btn btn-secondary" href="{{ url_for('index') }}">Cancelar</a>
</div>
</form>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const categoriaSel = document.getElementById('Categoria_producto');
    const marcaSel = document.getElementById('Marca_solicitada');
    const posicionSel = document.getElementById('Posicion');
    
    function updateMarcaAndPosicion() {
        const categoria = categoriaSel.value;
        
        // Clear current options
        marcaSel.innerHTML = '<option value="">-- seleccionar --</option>';
        posicionSel.innerHTML = '<option value="">-- seleccionar --</option>';
        
        if (!categoria) {
            // Load all options if no category selected
            fetch('/get_all_marcas')
                .then(r => r.json())
                .then(data => {
                    data.marcas.forEach(m => {
                        const opt = document.createElement('option');
                        opt.value = m;
                        opt.text = m;
                        marcaSel.appendChild(opt);
                    });
                });
            
            fetch('/get_all_posiciones')
                .then(r => r.json())
                .then(data => {
                    data.posiciones.forEach(p => {
                        const opt = document.createElement('option');
                        opt.value = p;
                        opt.text = p;
                        posicionSel.appendChild(opt);
                    });
                });
        } else {
            // Load filtered options
            fetch('/get_marcas_por_categoria?categoria=' + encodeURIComponent(categoria))
                .then(r => r.json())
                .then(data => {
                    data.marcas.forEach(m => {
                        const opt = document.createElement('option');
                        opt.value = m;
                        opt.text = m;
                        marcaSel.appendChild(opt);
                    });
                });
            
            fetch('/get_posiciones_por_categoria?categoria=' + encodeURIComponent(categoria))
                .then(r => r.json())
                .then(data => {
                    data.posiciones.forEach(p => {
                        const opt = document.createElement('option');
                        opt.value = p;
                        opt.text = p;
                        posicionSel.appendChild(opt);
                    });
                });
        }
    }
    
    categoriaSel.addEventListener('change', updateMarcaAndPosicion);
    
    document.getElementById('SKU').addEventListener('change', function() {
        var sku = this.value.trim();
        if(sku) {
            fetch('/buscar_sku/' + encodeURIComponent(sku))
                .then(response => response.json())
                .then(data => {
                    if(data.encontrado) {
                        document.getElementById('Marca_solicitada').value = data.marca || '';
                        document.getElementById('Referencia_solicitada').value = data.referencia || '';
                        document.getElementById('Categoria_producto').value = data.categoria || '';
                        updateMarcaAndPosicion();
                    }
                })
                .catch(err => console.error('Error buscando SKU:', err));
        }
    });
    
    document.getElementById('SKU').addEventListener('keypress', function(e) {
        if(e.key === 'Enter') {
            e.preventDefault();
            var sku = this.value.trim();
            if(sku) {
                fetch('/buscar_sku/' + encodeURIComponent(sku))
                    .then(response => response.json())
                    .then(data => {
                        if(data.encontrado) {
                            document.getElementById('Marca_solicitada').value = data.marca || '';
                            document.getElementById('Referencia_solicitada').value = data.referencia || '';
                            document.getElementById('Categoria_producto').value = data.categoria || '';
                            updateMarcaAndPosicion();
                        }
                    });
            }
        }
    });
});
</script>
"""
        body = render_template_string(mercancia_form, marca_opts=marca_opts, pas_opts=pas_opts, est_opts=est_opts, piso_opts=piso_opts, cat_opts=cat_opts, tipos=tipos, all_categories=all_categories)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/buscar_sku/<sku>")
    def buscar_sku(sku):
        mercancia = Mercancia.query.filter(Mercancia.sku == sku).first()
        if mercancia:
            return jsonify({
                "encontrado": True,
                "marca": mercancia.marca,
                "referencia": mercancia.referencia,
                "categoria": mercancia.categoria_producto,
                "cantidad": mercancia.cantidad,
                "pasillo": mercancia.pasillo,
                "estanteria": mercancia.estanteria,
                "piso": mercancia.piso
            })
        return jsonify({"encontrado": False})

    @app.route("/buscar_mercancia_id/<int:mercancia_id>")
    def buscar_mercancia_id(mercancia_id):
        mercancia = db.session.get(Mercancia, mercancia_id)
        if mercancia:
            return jsonify({
                "marca": mercancia.marca,
                "referencia": mercancia.referencia,
                "categoria": mercancia.categoria_producto,
                "cantidad": mercancia.cantidad,
                "pasillo": mercancia.pasillo,
                "estanteria": mercancia.estanteria,
                "piso": mercancia.piso
            })
        return jsonify({})

    @app.route("/edit/<pid>", methods=["GET", "POST"])
    def edit(pid):
        p = Picking.query.get(pid)
        if not p:
            flash("No encontrado")
            return redirect(url_for("index"))
        
        distincts = get_distinct_values_for_filters()
        marca_opts = distincts["Marca"]
        aux_opts = distincts["Auxiliar"]
        pas_opts = distincts["Pasillo"]
        cat_opts = distincts["Categoria"]
        piso_opts = distincts["Piso"]
        tipos = get_distinct_item_types()
        
        if request.method == "POST":
            data = request.form.to_dict()
            marca_ref = data.get("Marca_ref_selector")
            if marca_ref:
                parts = [x.strip() for x in marca_ref.split("|")]
                data["Marca_solicitada"] = parts[0] if parts else ""
                data["Referencia_solicitada"] = parts[1] if len(parts) > 1 else ""
            
            now_dt = datetime.now()
            data["Fecha"] = now_dt.strftime("%Y-%m-%d")
            data["Hora_generacion"] = now_dt.strftime("%H:%M:%S")
            
            tipos_list = request.form.getlist("item_tipo[]")
            marcas = request.form.getlist("item_marca[]")
            referencias = request.form.getlist("item_referencia[]")
            cantidades = request.form.getlist("item_cantidad[]")
            locked_flags = request.form.getlist("item_locked[]")
            
            items_data = []
            total_qty = 0
            pasillos_ordered = []
            
            for i in range(len(tipos_list)):
                t = tipos_list[i].strip() if i < len(tipos_list) else ""
                m = marcas[i].strip() if i < len(marcas) else ""
                rref = referencias[i].strip() if i < len(referencias) else ""
                try:
                    cqty = int(cantidades[i]) if i < len(cantidades) and cantidades[i] != "" else 1
                except (ValueError, TypeError):
                    cqty = 1
                locked = i < len(locked_flags)
                items_data.append({"tipo": t, "marca": m, "referencia": rref, "cantidad": cqty, "locked": locked})
                total_qty += cqty
                pas = get_pasillo_for_item(m, rref)
                pasillos_ordered.append(pas if pas else "")
            
            data["Cantidad"] = str(total_qty)
            ok, msg = validate_row_edit(data)
            if not ok:
                flash(msg)
                return redirect(url_for("edit", pid=pid))
            
            backup_db()
            
            for field in ["Fecha", "Hora_generacion", "Hora_revision", "Hora_despacho", "Auxiliar", "Cantidad_pickings_por_auxiliar", "Estanteria", "Piso", "Marca_solicitada", "Referencia_solicitada", "Categoria_producto"]:
                if field in data:
                    val = data[field]
                    setattr(p, field, val)
            
            p.Pasillo = build_pasillo_alfa_with_positions(pasillos_ordered)
            p.Cantidad = total_qty
            if "Unidades_erradas" in data:
                p.Unidades_erradas = int(data["Unidades_erradas"]) if data["Unidades_erradas"] != "" else 0
            if "Error_porcentaje" in data:
                p.Error_porcentaje = float(data["Error_porcentaje"]) if data["Error_porcentaje"] != "" else None
            
            audit_user = app.config.get("AUDIT_USER", "ui_user")
            p.modified_by = audit_user
            p.modified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            PickingItem.query.filter_by(Picking_ID=pid).delete()
            db.session.flush()
            
            for it in items_data:
                if it["tipo"] or it["marca"] or it["referencia"]:
                    try:
                        item = PickingItem(
                            Picking_ID=pid,
                            tipo=it["tipo"] or (p.Categoria_producto or "Item"),
                            marca=it["marca"],
                            referencia=it["referencia"],
                            cantidad=it["cantidad"]
                        )
                        db.session.add(item)
                        db.session.flush()
                    except Exception:
                        db.session.rollback()
            
            db.session.commit()
            flash("Actualizado (Pasillo y Cantidad total recalculados).")
            return redirect(url_for("index"))
        
        items_html = ""
        for it in p.items:
            items_html += render_template_string("""
<div class="row item-row mb-2" data-locked="false">
<div class="col-md-2"><input class="form-control" name="item_tipo[]" value="{{ it.tipo or '' }}" placeholder="Tipo"></div>
<div class="col-md-3"><input class="form-control" name="item_marca[]" value="{{ it.marca or '' }}" placeholder="Marca"></div>
<div class="col-md-4"><input class="form-control" name="item_referencia[]" value="{{ it.referencia or '' }}" placeholder="Referencia"></div>
<div class="col-md-1"><input class="form-control" name="item_cantidad[]" type="number" min="1" value="{{ it.cantidad or 1 }}"></div>
<div class="col-md-1 d-flex align-items-center">
<div class="form-check">
<input class="form-check-input item-lock" type="checkbox" name="item_locked[]" value="1" title="Fijar ítem">
<label class="form-check-label small">Fijar</label>
</div>
</div>
<div class="col-md-1"><button type="button" class="btn btn-danger btn-sm remove-item-btn">X</button></div>
</div>
            """, it=it)
        
        body = render_template_string(EDIT_FORM, p=p, marca_opts=marca_opts, aux_opts=aux_opts, pas_opts=pas_opts, cat_opts=cat_opts, piso_opts=piso_opts, items_html=items_html, tipos=tipos)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/edit_mercancia/<int:mid>", methods=["GET", "POST"])
    def edit_mercancia(mid):
        m = Mercancia.query.get(mid)
        if not m:
            flash("Mercancía no encontrada")
            return redirect(url_for("inventario"))
        
        if request.method == "POST":
            data = request.form.to_dict()
            
            backup_db()
            
            # Actualizar campos
            m.sku = data.get("sku", "")
            m.marca = data.get("marca", "")
            m.referencia = data.get("referencia", "")
            m.cantidad = int(data.get("cantidad", 0)) or 0
            m.categoria_producto = data.get("categoria_producto", "")
            m.pasillo = data.get("pasillo", "")
            m.estanteria = data.get("estanteria", "")
            m.piso = data.get("piso", "")
            
            audit_user = app.config.get("AUDIT_USER", "ui_user")
            m.modified_by = audit_user
            m.modified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            db.session.commit()
            flash("Mercancía actualizada")
            return redirect(url_for("inventario"))
        
        # Formulario de edición
        form_html = """
<style>
.edit-form { max-width: 800px; margin: 0 auto; }
.form-label { font-weight: bold; }
</style>
<div class="edit-form">
<h4>Editar Mercancía #{{ m.id }}</h4>
<form method="post">
    <div class="row">
        <div class="col-md-4">
            <label class="form-label">SKU</label>
            <input type="text" class="form-control" name="sku" value="{{ m.sku or '' }}">
        </div>
        <div class="col-md-4">
            <label class="form-label">Marca</label>
            <input type="text" class="form-control" name="marca" value="{{ m.marca or '' }}">
        </div>
        <div class="col-md-4">
            <label class="form-label">Referencia</label>
            <input type="text" class="form-control" name="referencia" value="{{ m.referencia or '' }}">
        </div>
    </div>
    <div class="row mt-2">
        <div class="col-md-4">
            <label class="form-label">Cantidad</label>
            <input type="number" class="form-control" name="cantidad" value="{{ m.cantidad or 0 }}">
        </div>
        <div class="col-md-4">
            <label class="form-label">Categoría</label>
            <input type="text" class="form-control" name="categoria_producto" value="{{ m.categoria_producto or '' }}">
        </div>
        <div class="col-md-4">
            <label class="form-label">Ubicación</label>
            <div class="input-group">
                <input type="text" class="form-control" name="pasillo" value="{{ m.pasillo or '' }}" placeholder="Pasillo" style="width: 33%;">
                <input type="text" class="form-control" name="estanteria" value="{{ m.estanteria or '' }}" placeholder="Estantería" style="width: 33%;">
                <input type="text" class="form-control" name="piso" value="{{ m.piso or '' }}" placeholder="Piso" style="width: 33%;">
            </div>
        </div>
    </div>
    <div class="mt-3">
        <button type="submit" class="btn btn-success">Guardar</button>
        <a href="{{ url_for('inventario') }}" class="btn btn-secondary">Cancelar</a>
    </div>
</form>
</div>
        """
        
        body = render_template_string(form_html, m=m)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/delete_mercancia/<int:mid>")
    def delete_mercancia(mid):
        m = Mercancia.query.get(mid)
        if not m:
            flash("Mercancía no encontrada")
            return redirect(url_for("inventario"))
        
        backup_db()
        db.session.delete(m)
        db.session.commit()
        flash("Mercancía eliminada")
        return redirect(url_for("inventario"))

    @app.route("/delete/<pid>")
    def delete(pid):
        p = Picking.query.get(pid)
        if not p:
            flash("No encontrado")
            return redirect(url_for("index"))
        backup_db()
        db.session.delete(p)
        db.session.commit()
        flash("Eliminado")
        return redirect(url_for("index"))

    @app.route("/upload_csv", methods=["GET", "POST"])
    def upload_csv():
        import_log_html = ""
        
        if request.method == "POST":
            if 'file' not in request.files:
                flash("No se seleccionó archivo")
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':
                flash("Nombre de archivo vacío")
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                import_dir = Path(app.config.get("IMPORT_DIR", "Data/import"))
                import_dir.mkdir(parents=True, exist_ok=True)
                upload_path = import_dir / filename
                file.save(upload_path)
                
                try:
                    PickingCSV.query.delete()
                    PickingItemCSV.query.delete()
                    db.session.commit()
                    
                    msg, loaded, skipped, warnings = import_csv_adaptive(str(upload_path))
                    
                    log_parts = [f"✅ {msg}"]
                    
                    if loaded:
                        log_parts.append("<br><strong>Columnas cargadas:</strong>")
                        for l in loaded:
                            log_parts.append(f"<br>✓ {l}")
                    
                    if skipped:
                        log_parts.append("<br><strong>Columnas no encontradas:</strong>")
                        for s in skipped:
                            log_parts.append(f"<br>✗ {s}")
                    
                    if warnings:
                        log_parts.append("<br><strong>Advertencias:</strong>")
                        for w in warnings[:10]:
                            log_parts.append(f"<br>⚠ {w}")
                        if len(warnings) > 10:
                            log_parts.append(f"<br>... y {len(warnings) - 10} más")
                    
                    flash("".join(log_parts))
                    
                    sync_to_pickings()
                except Exception as e:
                    flash(f"❌ Error importando CSV: {e}")
                    db.session.rollback()
                return redirect(url_for('index'))
            else:
                flash("❌ Solo se permiten archivos .csv")
                return redirect(request.url)
        
        body = render_template_string("""
<div class="card mt-4">
    <div class="card-header bg-info text-white">📤 Cargar Nuevo CSV</div>
    <div class="card-body">
        <form method="post" enctype="multipart/form-data">
            <div class="mb-3">
                <label class="form-label">Seleccionar archivo CSV</label>
                <input type="file" class="form-control" name="file" accept=".csv" required>
                <small class="text-muted">El sistema detectará automáticamente las columnas disponibles</small>
            </div>
            <div class="alert alert-secondary">
                <strong>Columnas soportadas:</strong><br>
                Picking_ID, Fecha, Hora_generacion, Hora_revision, Hora_despacho, Auxiliar, 
                Cantidad_pickings_por_auxiliar, Pasillo, Estanteria, Piso, Marca_solicitada, 
                Referencia_solicitada, Categoria (producto/vehiculo), Cantidad, Error_porcentaje
            </div>
            <button type="submit" class="btn btn-success">Cargar CSV</button>
            <a class="btn btn-secondary" href="{{ url_for('index') }}">Cancelar</a>
        </form>
        <div class="mt-4 alert alert-warning">
            <strong>⚠️ Advertencia:</strong> Esto reemplazará TODOS los datos actuales en la base de datos.
            Se crearán backups automáticos de DB y CSV antes de continuar.
        </div>
    </div>
</div>
        """)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/export_csv")
    def export_csv():
        try:
            backup_db()
            backup_csv()
            
            all_pickings = Picking.query.all()
            rows = []
            
            for p in all_pickings:
                if p.items:
                    for item in p.items:
                        rows.append({
                            'Picking_ID': p.Picking_ID,
                            'Fecha': p.Fecha,
                            'Hora_generacion': p.Hora_generacion,
                            'Hora_revision': p.Hora_revision,
                            'Hora_despacho': p.Hora_despacho,
                            'Auxiliar': p.Auxiliar,
                            'Cantidad_pickings_por_auxiliar': p.Cantidad_pickings_por_auxiliar,
                            'Pasillo': p.Pasillo,
                            'Estanteria': p.Estanteria,
                            'Piso': p.Piso,
                            'Marca_solicitada': item.marca,
                            'Referencia_solicitada': item.referencia,
                            'Categoria_producto': item.tipo,
                            'Cantidad': item.cantidad,
                            'Error_porcentaje': p.Error_porcentaje if p.Error_porcentaje is not None else '',
                            'modified_by': p.modified_by,
                            'modified_at': p.modified_at
                        })
                else:
                    rows.append({
                        'Picking_ID': p.Picking_ID,
                        'Fecha': p.Fecha,
                        'Hora_generacion': p.Hora_generacion,
                        'Hora_revision': p.Hora_revision,
                        'Hora_despacho': p.Hora_despacho,
                        'Auxiliar': p.Auxiliar,
                        'Cantidad_pickings_por_auxiliar': p.Cantidad_pickings_por_auxiliar,
                        'Pasillo': p.Pasillo,
                        'Estanteria': p.Estanteria,
                        'Piso': p.Piso,
                        'Marca_solicitada': p.Marca_solicitada,
                        'Referencia_solicitada': p.Referencia_solicitada,
                        'Categoria_producto': p.Categoria_producto,
                        'Cantidad': p.Cantidad,
                        'Error_porcentaje': p.Error_porcentaje if p.Error_porcentaje is not None else '',
                        'modified_by': p.modified_by,
                        'modified_at': p.modified_at
                    })
            
            df = pd.DataFrame(rows)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            base_dir = Path(app.config.get("BASE_DIR", "."))
            export_path = base_dir / f"dataset_exportado_{ts}.csv"
            df.to_csv(export_path, index=False, encoding='utf-8-sig')
            
            csv_path = app.config.get("CSV_FILE")
            if csv_path:
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            flash(f"✅ CSV exportado: {len(rows)} filas. Backup creado en /backups/")
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f"❌ Error exportando CSV: {e}")
            db.session.rollback()
            return redirect(url_for('index'))

    @app.route("/download_csv")
    def download_csv():
        try:
            f_pid = request.args.get("filter_Picking_ID", "")
            f_fecha = request.args.get("filter_Fecha", "")
            f_aux = request.args.get("filter_Auxiliar", "")
            f_marca = request.args.get("filter_Marca", "")
            f_ref = request.args.get("filter_Referencia", "")
            f_pas = request.args.get("filter_Pasillo", "")
            f_piso = request.args.get("filter_Piso", "")
            f_cat = request.args.get("filter_Categoria", "")
            
            q = Picking.query
            if f_pid:
                q = q.filter(Picking.Picking_ID == f_pid)
            if f_fecha:
                q = q.filter(Picking.Fecha == f_fecha)
            if f_aux:
                q = q.filter(Picking.Auxiliar == f_aux)
            if f_marca:
                parts = [p.strip() for p in f_marca.split("|")]
                marca = parts[0] if parts else ""
                ref = parts[1] if len(parts) > 1 else None
                if marca and ref:
                    q = q.filter(Picking.Marca_solicitada == marca, Picking.Referencia_solicitada == ref)
                elif marca:
                    q = q.filter(Picking.Marca_solicitada == marca)
            if f_ref:
                q = q.filter(Picking.Referencia_solicitada == f_ref)
            if f_pas:
                q = q.filter(Picking.Pasillo == f_pas)
            if f_piso:
                q = q.filter(Picking.Piso == f_piso)
            if f_cat:
                q = q.filter(Picking.Categoria_producto == f_cat)
            
            all_pickings = q.all()
            rows = []
            
            for p in all_pickings:
                if p.items:
                    for item in p.items:
                        rows.append({
                            'Picking_ID': p.Picking_ID,
                            'Fecha': p.Fecha,
                            'Hora_generacion': p.Hora_generacion,
                            'Hora_revision': p.Hora_revision,
                            'Hora_despacho': p.Hora_despacho,
                            'Auxiliar': p.Auxiliar,
                            'Cantidad_pickings_por_auxiliar': p.Cantidad_pickings_por_auxiliar,
                            'Pasillo': p.Pasillo,
                            'Estanteria': p.Estanteria,
                            'Piso': p.Piso,
                            'Marca_solicitada': item.marca,
                            'Referencia_solicitada': item.referencia,
                            'Categoria_producto': item.tipo,
                            'Cantidad': item.cantidad,
                            'Error_porcentaje': p.Error_porcentaje if p.Error_porcentaje is not None else '',
                            'modified_by': p.modified_by,
                            'modified_at': p.modified_at
                        })
                else:
                    rows.append({
                        'Picking_ID': p.Picking_ID,
                        'Fecha': p.Fecha,
                        'Hora_generacion': p.Hora_generacion,
                        'Hora_revision': p.Hora_revision,
                        'Hora_despacho': p.Hora_despacho,
                        'Auxiliar': p.Auxiliar,
                        'Cantidad_pickings_por_auxiliar': p.Cantidad_pickings_por_auxiliar,
                        'Pasillo': p.Pasillo,
                        'Estanteria': p.Estanteria,
                        'Piso': p.Piso,
                        'Marca_solicitada': p.Marca_solicitada,
                        'Referencia_solicitada': p.Referencia_solicitada,
                        'Categoria_producto': p.Categoria_producto,
                        'Cantidad': p.Cantidad,
                        'Error_porcentaje': p.Error_porcentaje if p.Error_porcentaje is not None else '',
                        'modified_by': p.modified_by,
                        'modified_at': p.modified_at
                    })
            
            df = pd.DataFrame(rows)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            has_filters = any([f_pid, f_fecha, f_aux, f_marca, f_ref, f_pas, f_piso, f_cat])
            if has_filters:
                filename = f"pickings_filtrados_{ts}.csv"
            else:
                filename = f"pickings_completo_{ts}.csv"
            
            import io
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            flash(f"❌ Error descargando CSV: {e}")
            return redirect(url_for('index'))

    @app.route("/get_marcas_y_refs_por_categoria")
    def get_marcas_y_refs_por_categoria():
        """Obtiene marcas y referencias disponibles para una categoría específica"""
        categoria = request.args.get("categoria", "").strip()
        if not categoria:
            return jsonify({"ok": False, "msg": "Categoría vacía"}), 400
        
        try:
            # Obtener marcas únicas para la categoría
            marcas = sorted(set([m.marca for m in Mercancia.query.filter(Mercancia.categoria_producto == categoria).with_entities(Mercancia.marca).distinct().all() if m.marca]))
            
            # Obtener referencias únicas para la categoría
            referencias = sorted(set([r.referencia for r in Mercancia.query.filter(Mercancia.categoria_producto == categoria).with_entities(Mercancia.referencia).distinct().all() if r.referencia]))
            
            return jsonify({"ok": True, "marcas": marcas, "referencias": referencias})
        except Exception as e:
            return jsonify({"ok": False, "msg": f"Error: {str(e)}"}), 500
    
    @app.route("/get_refs_por_marca_categoria")
    def get_refs_por_marca_categoria():
        """Obtiene referencias disponibles para una marca y categoría específica"""
        marca = request.args.get("marca", "").strip()
        categoria = request.args.get("categoria", "").strip()
        
        if not marca and not categoria:
            return jsonify({"ok": False, "msg": "Marca o categoría vacía"}), 400
        
        try:
            q = Mercancia.query
            if categoria:
                q = q.filter(Mercancia.categoria_producto == categoria)
            if marca:
                q = q.filter(Mercancia.marca == marca)
            
            referencias = sorted(set([r.referencia for r in q.with_entities(Mercancia.referencia).distinct().all() if r.referencia]))
            
            return jsonify({"ok": True, "referencias": referencias})
        except Exception as e:
            return jsonify({"ok": False, "msg": f"Error: {str(e)}"}), 500
    
    @app.route("/meta_for_marca")
    def meta_for_marca():
        marca_ref = request.args.get("marca_ref", "").strip()
        if not marca_ref:
            return jsonify({"ok": False, "msg": "marca_ref vacío"}), 400
        parts = [p.strip() for p in marca_ref.split("|")]
        marca = parts[0] if parts else ""
        referencia = parts[1] if len(parts) > 1 else ""
        try:
            q = Picking.query.filter(
                Picking.Marca_solicitada == marca,
                Picking.Referencia_solicitada == referencia
            ).first()
            if not q:
                q = Picking.query.filter(
                    (Picking.Marca_solicitada == marca) | (Picking.Referencia_solicitada == referencia)
                ).first()
        except:
            return jsonify({"ok": False, "msg": "tabla faltante"}), 404
        if not q:
            return jsonify({"ok": False, "msg": "No encontrado"}), 404
        return jsonify({
            "ok": True,
            "pasillo": q.Pasillo or "",
            "categoria": q.Categoria_producto or "",
            "piso": q.Piso or "",
            "estanteria": q.Estanteria or ""
        })

    @app.route("/fifo_posiciones")
    def fifo_posiciones():
        """Returns all positions for a marca/referencia with FIFO calculation"""
        marca_ref = request.args.get("marca_ref", "").strip()
        cantidad = request.args.get("cantidad", type=int, default=1)
        
        if not marca_ref:
            return jsonify({"ok": False, "msg": "marca_ref vacío"}), 400
        
        parts = [p.strip() for p in marca_ref.split("|")]
        marca = parts[0] if parts else ""
        referencia = parts[1] if len(parts) > 1 else ""
        
        try:
            # Get all mercancia for this marca/referencia ordered by fecha_ingreso (FIFO)
            mercancias = Mercancia.query.filter(
                Mercancia.marca == marca,
                Mercancia.referencia == referencia
            ).order_by(Mercancia.fecha_ingreso.asc()).all()
            
            posiciones = []
            total_disponible = 0
            
            for m in mercancias:
                if m.cantidad and m.cantidad > 0:
                    posiciones.append({
                        "id": m.id,
                        "pasillo": m.pasillo or "",
                        "estanteria": m.estanteria or "",
                        "piso": m.piso or "",
                        "cantidad": m.cantidad,
                        "fecha_ingreso": m.fecha_ingreso or ""
                    })
                    total_disponible += m.cantidad
            
            # Calculate how much to take from each position (FIFO)
            posiciones_fifo = []
            restante = cantidad
            
            for pos in posiciones:
                if restante <= 0:
                    break
                cantidad_tomar = min(restante, pos["cantidad"])
                posiciones_fifo.append({
                    "pasillo": pos["pasillo"],
                    "estanteria": pos["estanteria"],
                    "piso": pos["piso"],
                    "cantidad": cantidad_tomar
                })
                restante -= cantidad_tomar
            
            return jsonify({
                "ok": True,
                "posiciones": posiciones,
                "posiciones_fifo": posiciones_fifo,
                "total_disponible": total_disponible,
                "puede_completar": restante <= 0,
                "restante": restante
            })
        except Exception as e:
            return jsonify({"ok": False, "msg": str(e)}), 500

    @app.route("/items_for_marca")
    def items_for_marca():
        marca_ref = request.args.get("marca_ref", "").strip()
        if not marca_ref:
            return jsonify({"ok": False, "msg": "marca_ref vacío"}), 400
        parts = [p.strip() for p in marca_ref.split("|")]
        marca = parts[0] if parts else ""
        referencia = parts[1] if len(parts) > 1 else ""
        
        try:
            items = PickingItem.query.filter(
                PickingItem.marca == marca,
                PickingItem.referencia == referencia
            ).all()
            if not items:
                items = PickingItem.query.filter(PickingItem.marca == marca).limit(10).all()
            if not items:
                items = PickingItem.query.filter(PickingItem.referencia == referencia).limit(10).all()
        except Exception:
            return jsonify({"ok": False, "items": []}), 404
        
        result = []
        for it in items:
            result.append({
                "tipo": it.tipo or "",
                "marca": it.marca or "",
                "referencia": it.referencia or "",
                "cantidad": it.cantidad or 1
            })
        return jsonify({"ok": True, "items": result})

    @app.route("/marca_refs_for_type")
    def marca_refs_for_type():
        tipo = request.args.get("tipo", "").strip()
        if not tipo:
            return jsonify({"ok": False, "msg": "tipo vacío"}), 400
        try:
            # Use Mercancia table for correct filtering
            rows = db.session.query(Mercancia.marca, Mercancia.referencia).filter(Mercancia.categoria_producto == tipo).distinct().all()
        except Exception:
            return jsonify({"ok": True, "marca_refs": []})
        marca_refs = []
        for m, r in rows:
            if m or r:
                marca_refs.append(f"{m} | {r}".strip(" |"))
        return jsonify({"ok": True, "marca_refs": sorted(marca_refs)})

    @app.route("/next_picking_id")
    def next_picking_id():
        try:
            all_ids = [r[0] for r in db.session.query(Picking.Picking_ID).all()]
        except Exception:
            return jsonify({"next_id": "60001"})
        numeric_ids = [int(x) for x in all_ids if x and x.isdigit()]
        if numeric_ids:
            next_id = max(numeric_ids) + 1
        else:
            next_id = 60001
        return jsonify({"next_id": str(next_id)})

    @app.route("/save_columns", methods=["POST"])
    def save_columns():
        try:
            data = request.get_json()
            visible_cols = data.get("visible", [])
            
            config = load_columns_config()
            for col_key in config:
                config[col_key]["visible"] = col_key in visible_cols
            
            save_columns_config(config)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/reset_columns")
    def reset_columns():
        save_columns_config(DEFAULT_COLUMNS.copy())
        flash("Columnas restablecidas a valores por defecto")
        return redirect(url_for("index"))

    @app.route("/print_picking/<pid>")
    def print_picking(pid):
        from io import BytesIO
        try:
            pdf_data = generate_picking_pdf(pid)
            buffer = BytesIO(pdf_data)
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'picking_{pid}.pdf'
            )
        except Exception as e:
            flash(f"Error generando PDF: {e}")
            return redirect(url_for("index"))

    @app.route("/print_all")
    def print_all_pickings():
        from io import BytesIO
        try:
            f_pid = request.args.get("filter_Picking_ID", "")
            f_fecha = request.args.get("filter_Fecha", "")
            f_aux = request.args.get("filter_Auxiliar", "")
            f_marca = request.args.get("filter_Marca", "")
            f_ref = request.args.get("filter_Referencia", "")
            f_pas = request.args.get("filter_Pasillo", "")
            f_piso = request.args.get("filter_Piso", "")
            f_cat = request.args.get("filter_Categoria", "")
            
            q = Picking.query
            if f_pid:
                q = q.filter(Picking.Picking_ID == f_pid)
            if f_fecha:
                q = q.filter(Picking.Fecha == f_fecha)
            if f_aux:
                q = q.filter(Picking.Auxiliar == f_aux)
            if f_marca:
                parts = [p.strip() for p in f_marca.split("|")]
                marca = parts[0] if parts else ""
                ref = parts[1] if len(parts) > 1 else None
                if marca and ref:
                    q = q.filter(Picking.Marca_solicitada == marca, Picking.Referencia_solicitada == ref)
                elif marca:
                    q = q.filter(Picking.Marca_solicitada == marca)
            if f_ref:
                q = q.filter(Picking.Referencia_solicitada == f_ref)
            if f_pas:
                q = q.filter(Picking.Pasillo == f_pas)
            if f_piso:
                q = q.filter(Picking.Piso == f_piso)
            if f_cat:
                q = q.filter(Picking.Categoria_producto == f_cat)
            
            pickings = q.all()
            if not pickings:
                flash("No hay pickings para imprimir con los filtros seleccionados")
                return redirect(url_for("index"))
            
            picking_ids = [p.Picking_ID for p in pickings if p.Picking_ID]
            pdf_data = generate_picking_list_pdf(picking_ids)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            buffer = BytesIO(pdf_data)
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'pickings_{ts}.pdf'
            )
        except Exception as e:
            flash(f"Error generando PDF: {e}")
            return redirect(url_for("index"))

    @app.route("/recepcion", methods=["GET"])
    def recepcion():
        distincts = get_distinct_values_for_filters()
        recepciones_activas = Recepcion.query.filter_by(estado="activa").all()
        recepciones_pendientes = Recepcion.query.filter_by(estado="pendiente").all()
        
        # Generate options for pasillo (A-Z)
        pasillo_options = ''.join([f'<option value="{chr(65+i)}">{chr(65+i)}</option>' for i in range(26)])
        
        # Generate options for estanteria (1-15)
        estanteria_options = ''.join([f'<option value="{i}">{i}</option>' for i in range(1, 16)])
        
        # Generate options for piso (1-4)
        piso_options = ''.join([f'<option value="{i}">{i}</option>' for i in range(1, 5)])
        
        recepcion_html = """
<style>
.recepcion-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
.recepcion-activa { border-left: 4px solid #28a745; }
.recepcion-pendiente { border-left: 4px solid #ffc107; }
.scanner-input { font-size: 24px; padding: 10px; letter-spacing: 2px; }
.escaneo-box { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
.contador-display { font-size: 48px; font-weight: bold; color: #28a745; }
.ubicacion-box { background: #e7f1ff; padding: 15px; border-radius: 8px; }
</style>
<div class="row">
    <div class="col-md-8">
        <h4>📦 Recepción de Mercancía</h4>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-info">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <div class="recepcion-card recepcion-activa">
            <h5>Nueva Recepción</h5>
            <form method="post" action="{{ url_for('iniciar_recepcion') }}">
                <div class="row">
                    <div class="col-md-3">
                        <label>Operario *</label>
                        <input type="text" class="form-control" name="operario" required placeholder="Nombre del operario">
                    </div>
                    <div class="col-md-3">
                        <label>Marca</label>
                        <input type="text" class="form-control" name="marca" placeholder="Marca del producto" list="marcas_list">
                        <datalist id="marcas_list">
                        {% for m in marca_opts %}<option value="{{ m }}">{% endfor %}
                        </datalist>
                    </div>
                    <div class="col-md-3">
                        <label>Referencia</label>
                        <input type="text" class="form-control" name="referencia" placeholder="Referencia del producto">
                    </div>
                    <div class="col-md-3">
                        <label>Categoría</label>
                        <input type="text" class="form-control" name="categoria" list="categorias_list" placeholder="Categoría">
                        <datalist id="categorias_list">
                        {% for c in cat_opts %}<option value="{{ c }}">{% endfor %}
                        </datalist>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-md-3">
                        <label>Pasillo</label>
                        <select class="form-select" name="pasillo">
                            <option value="">Seleccione pasillo...</option>
                            """ + pasillo_options + """
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label>Estantería</label>
                        <select class="form-select" name="estanteria">
                            <option value="">Seleccione estantería...</option>
                            """ + estanteria_options + """
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label>Piso</label>
                        <select class="form-select" name="piso">
                            <option value="">Seleccione piso...</option>
                            """ + piso_options + """
                        </select>
                    </div>
                    <div class="col-md-3 d-flex align-items-end">
                        <button type="submit" class="btn btn-success w-100">▶ Iniciar Recepción</button>
                    </div>
                </div>
            </form>
        </div>
        <h5 class="mt-4">Recepciones Activas</h5>
        {% for r in recepciones_activas %}
        <div class="recepcion-card recepcion-activa">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>Recepción #{{ r.id }}</strong> - Operario: {{ r.operario }}
                    <br><small>Inicio: {{ r.fecha_inicio }}</small>
                </div>
                <div>
                    <a href="{{ url_for('recepcion_activa', recepcion_id=r.id) }}" class="btn btn-primary btn-sm">Continuar</a>
                    <a href="{{ url_for('cerrar_recepcion', recepcion_id=r.id) }}" class="btn btn-warning btn-sm">Cerrar</a>
                </div>
            </div>
        </div>
        {% else %}
        <p class="text-muted">No hay recepciones activas</p>
        {% endfor %}
    </div>
    <div class="col-md-4">
        <h5>📋 Recepciones Pendientes</h5>
        {% for r in recepciones_pendientes %}
        <div class="recepcion-card recepcion-pendiente">
            <strong>#{{ r.id }}</strong> - {{ r.operario }}
            <br><small>{{ r.fecha_fin or r.fecha_inicio }}</small>
            <br><a href="{{ url_for('revisar_recepcion', recepcion_id=r.id) }}" class="btn btn-warning btn-sm mt-2">Revisar</a>
        </div>
        {% else %}
        <p class="text-muted">No hay recepciones pendientes</p>
        {% endfor %}
    </div>
</div>
"""
        cat_opts = distincts.get("Categoria", [])
        marca_opts = distincts.get("Marca", [])
        body = render_template_string(recepcion_html, recepciones_activas=recepciones_activas, recepciones_pendientes=recepciones_pendientes, cat_opts=cat_opts, marca_opts=marca_opts)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/iniciar_recepcion", methods=["POST"])
    def iniciar_recepcion():
        operario = request.form.get("operario", "").strip()
        if not operario:
            flash("El operario es obligatorio")
            return redirect(url_for("recepcion"))
        
        now = datetime.now()
        recepcion = Recepcion(
            operario=operario,
            fecha_inicio=now.strftime("%Y-%m-%d %H:%M:%S"),
            estado="activa"
        )
        db.session.add(recepcion)
        
        # Store initial data in session for use when first SKU is scanned
        session['recepcion_id'] = recepcion.id
        session['recepcion_ref'] = request.form.get("referencia", "").strip()
        session['recepcion_marca'] = request.form.get("marca", "").strip()
        session['recepcion_categoria'] = request.form.get("categoria", "").strip()
        session['recepcion_pasillo'] = request.form.get("pasillo", "").strip()
        session['recepcion_estanteria'] = request.form.get("estanteria", "").strip()
        session['recepcion_piso'] = request.form.get("piso", "").strip()
        
        db.session.commit()
        return redirect(url_for("recepcion_activa", recepcion_id=recepcion.id))

    @app.route("/recepcion/<int:recepcion_id>")
    def recepcion_activa(recepcion_id):
        recepcion = Recepcion.query.get_or_404(recepcion_id)
        if recepcion.estado != "activa":
            flash("Esta recepción no está activa")
            return redirect(url_for("recepcion"))
        
        items_agrupados = {}
        for item in recepcion.items:
            key = f"{item.referencia}|{item.pasillo}|{item.estanteria}|{item.piso}"
            if key not in items_agrupados:
                items_agrupados[key] = {
                    "referencia": item.referencia,
                    "marca": item.marca,
                    "categoria": item.categoria,
                    "pasillo": item.pasillo,
                    "estanteria": item.estanteria,
                    "piso": item.piso,
                    "cantidad": 0
                }
            items_agrupados[key]["cantidad"] += 1
        
        activa_html = """
<style>
.scanner-input { font-size: 28px; padding: 15px; letter-spacing: 3px; text-align: center; }
.escaneo-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
.contador-display { font-size: 72px; font-weight: bold; color: #28a745; }
.ubicacion-box { background: #e7f1ff; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
.item-card { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
.referencia-actual { background: #28a745; color: white; padding: 15px; border-radius: 8px; font-size: 24px; text-align: center; }
</style>
<div class="row">
    <div class="col-md-8">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4>📦 Recepción #{{ recepcion.id }} - {{ recepcion.operario }}</h4>
            <a href="{{ url_for('recepcion') }}" class="btn btn-secondary">← Volver</a>
        </div>
        
        <div class="referencia-actual mb-3">
            <strong>Referencia:</strong> {{ items[0].referencia if items else 'Sin referencia' }}
            {% if items and items[0].sku %}
            <br><small>{{ items[0].categoria or '' }}</small>
            {% endif %}
        </div>
        
        <div class="escaneo-box">
            <h5 class="text-white">📱 ESCÁNER / INPUT</h5>
            <form method="post" action="{{ url_for('escaneo_recepcion', recepcion_id=recepcion.id) }}" id="scannerForm">
                <input type="text" class="form-control scanner-input" name="sku" id="skuInput" 
                       placeholder="Escanee código o escriba SKU" autofocus
                       onkeypress="if(event.key==='Enter'){event.preventDefault(); this.form.submit();}">
            </form>
            <div class="contador-display mt-3">
                {{ total_unidades }}
            </div>
            <small class="text-white">unidades escaneadas</small>
        </div>
        
        <div class="row">
            <div class="col-md-12">
                <a href="{{ url_for('nueva_posicion_recepcion', recepcion_id=recepcion.id) }}" class="btn btn-outline-primary w-100">➕ Nueva Posición</a>
            </div>
        </div>
        <div class="mt-3">
            <a href="{{ url_for('cerrar_recepcion', recepcion_id=recepcion.id) }}" class="btn btn-warning w-100">📋 Finalizar Recepción</a>
        </div>
    </div>
    
    <div class="col-md-4">
        <h5>📍 Ubicación Actual</h5>
        {% if items %}
        <div class="ubicacion-box">
            <div class="row text-center">
                <div class="col-4">
                    <strong>Pasillo</strong><br>{{ items[-1].pasillo or '-' }}
                </div>
                <div class="col-4">
                    <strong>Est.</strong><br>{{ items[-1].estanteria or '-' }}
                </div>
                <div class="col-4">
                    <strong>Piso</strong><br>{{ items[-1].piso or '-' }}
                </div>
            </div>
        </div>
        {% endif %}
        
        <h5 class="mt-3">📊 Resumen</h5>
        {% for key, item in items_agrupados.items() %}
        <div class="item-card">
            <strong>{{ item.referencia }}</strong><br>
            <small>{{ item.categoria or '' }}</small>
            <span class="badge bg-primary float-end">{{ item.cantidad }} uds</span>
            <br><small class="text-muted">{{ item.pasillo or '' }}-{{ item.estanteria or '' }}-{{ item.piso or '' }}</small>
        </div>
        {% endfor %}
    </div>
</div>
<script>
document.getElementById('skuInput').focus();
</script>
"""
        items = recepcion.items or []
        # Count only items with SKU
        total_unidades = len([item for item in items if item.sku])
        
        # Get new location from session if it exists
        nueva_posicion_pasillo = session.get('nueva_posicion_pasillo')
        nueva_posicion_estanteria = session.get('nueva_posicion_estanteria')
        nueva_posicion_piso = session.get('nueva_posicion_piso')
        
        # If there's a new location in session, show it instead of last item
        if nueva_posicion_pasillo or nueva_posicion_estanteria or nueva_posicion_piso:
            # Create a dummy item with the new location
            from types import SimpleNamespace
            location_item = SimpleNamespace(
                pasillo=nueva_posicion_pasillo or items[-1].pasillo if items else "",
                estanteria=nueva_posicion_estanteria or items[-1].estanteria if items else "",
                piso=nueva_posicion_piso or items[-1].piso if items else ""
            )
            items_for_display = items + [location_item]
        else:
            items_for_display = items
        
        body = render_template_string(activa_html, recepcion=recepcion, items=items_for_display, items_agrupados=items_agrupados, total_unidades=total_unidades)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/recepcion/<int:recepcion_id>/escaneo", methods=["POST"])
    def escaneo_recepcion(recepcion_id):
        recepcion = Recepcion.query.get_or_404(recepcion_id)
        if recepcion.estado != "activa":
            return jsonify({"error": "Recepción no activa"}), 400
        
        sku = request.form.get("sku", "").strip()
        if not sku:
            flash("SKU es obligatorio")
            return redirect(url_for("recepcion_activa", recepcion_id=recepcion_id))
        
        now = datetime.now()
        
        # Get items with SKU only (exclude items without SKU)
        items_with_sku = RecepcionItem.query.filter(
            RecepcionItem.recepcion_id == recepcion_id,
            RecepcionItem.sku.isnot(None),
            RecepcionItem.sku != ""
        ).order_by(RecepcionItem.id.asc()).all()
        
        # Get the first item with SKU to inherit reference and brand
        first_item_with_sku = items_with_sku[0] if items_with_sku else None
        
        # Check if there's a new location in session
        nueva_posicion_pasillo = session.get('nueva_posicion_pasillo')
        nueva_posicion_estanteria = session.get('nueva_posicion_estanteria')
        nueva_posicion_piso = session.get('nueva_posicion_piso')
        
        # Get the last item to inherit location (including items from "nueva posicion")
        last_item = RecepcionItem.query.filter_by(recepcion_id=recepcion_id).order_by(RecepcionItem.id.desc()).first()
        
        # Determine location source: use new location from session if exists, otherwise use last item
        if nueva_posicion_pasillo or nueva_posicion_estanteria or nueva_posicion_piso:
            # Create a temporary object with the new location
            class Location:
                def __init__(self, pasillo, estanteria, piso):
                    self.pasillo = pasillo
                    self.estanteria = estanteria
                    self.piso = piso
            
            location_source = Location(
                nueva_posicion_pasillo or (last_item.pasillo if last_item else ""),
                nueva_posicion_estanteria or (last_item.estanteria if last_item else ""),
                nueva_posicion_piso or (last_item.piso if last_item else "")
            )
            # Clear session variables
            session.pop('nueva_posicion_pasillo', None)
            session.pop('nueva_posicion_estanteria', None)
            session.pop('nueva_posicion_piso', None)
        else:
            location_source = last_item
        
        mercancia = Mercancia.query.filter(Mercancia.sku == sku).first()
        
        # Determine the reference and marca for the new item
        if mercancia:
            # If we have mercancia data, use it
            if first_item_with_sku:
                referencia = first_item_with_sku.referencia
                marca = first_item_with_sku.marca
                categoria = first_item_with_sku.categoria
                pasillo = location_source.pasillo if location_source else (mercancia.pasillo or "")
                estanteria = location_source.estanteria if location_source else (mercancia.estanteria or "")
                piso = location_source.piso if location_source else (mercancia.piso or "")
            else:
                # Use data from session if no items with SKU yet
                referencia = session.get('recepcion_ref', mercancia.referencia)
                marca = session.get('recepcion_marca', mercancia.marca)
                categoria = session.get('recepcion_categoria', mercancia.categoria_producto)
                pasillo = session.get('recepcion_pasillo', mercancia.pasillo or "")
                estanteria = session.get('recepcion_estanteria', mercancia.estanteria or "")
                piso = session.get('recepcion_piso', mercancia.piso or "")
        else:
            # No mercancia found for SKU
            # Try to find existing mercancia by reference to get category/location
            mercancia_by_ref = Mercancia.query.filter(Mercancia.referencia == sku).first()
            if mercancia_by_ref:
                if first_item_with_sku:
                    referencia = first_item_with_sku.referencia
                    marca = first_item_with_sku.marca
                    categoria = first_item_with_sku.categoria
                    pasillo = location_source.pasillo if location_source else (mercancia_by_ref.pasillo or "")
                    estanteria = location_source.estanteria if location_source else (mercancia_by_ref.estanteria or "")
                    piso = location_source.piso if location_source else (mercancia_by_ref.piso or "")
                else:
                    # Use data from session if no items with SKU yet
                    referencia = session.get('recepcion_ref', sku)
                    marca = session.get('recepcion_marca', mercancia_by_ref.marca)
                    categoria = session.get('recepcion_categoria', mercancia_by_ref.categoria_producto)
                    pasillo = session.get('recepcion_pasillo', mercancia_by_ref.pasillo or "")
                    estanteria = session.get('recepcion_estanteria', mercancia_by_ref.estanteria or "")
                    piso = session.get('recepcion_piso', mercancia_by_ref.piso or "")
            else:
                # Use data from session or SKU as reference
                if first_item_with_sku:
                    referencia = first_item_with_sku.referencia
                    marca = first_item_with_sku.marca
                    categoria = first_item_with_sku.categoria
                    pasillo = location_source.pasillo if location_source else ""
                    estanteria = location_source.estanteria if location_source else ""
                    piso = location_source.piso if location_source else ""
                else:
                    # Use data from session if no items with SKU yet
                    referencia = session.get('recepcion_ref', sku)
                    marca = session.get('recepcion_marca', "")
                    categoria = session.get('recepcion_categoria', "")
                    pasillo = session.get('recepcion_pasillo', "")
                    estanteria = session.get('recepcion_estanteria', "")
                    piso = session.get('recepcion_piso', "")
        
        # Calculate unit count based ONLY on items with SKU in the same location
        unidad_count = RecepcionItem.query.filter(
            RecepcionItem.recepcion_id == recepcion_id,
            RecepcionItem.sku.isnot(None),
            RecepcionItem.sku != "",
            RecepcionItem.pasillo == pasillo,
            RecepcionItem.estanteria == estanteria,
            RecepcionItem.piso == piso
        ).count() + 1
        
        item = RecepcionItem(
            recepcion_id=recepcion_id,
            sku=sku,
            marca=marca,
            referencia=referencia,
            categoria=categoria,
            pasillo=pasillo,
            estanteria=estanteria,
            piso=piso,
            unidad_numero=unidad_count,
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(item)
        db.session.commit()
        
        flash(f"Unidad {unidad_count} escaneada correctamente")
        return redirect(url_for("recepcion_activa", recepcion_id=recepcion_id))

    @app.route("/recepcion/<int:recepcion_id>/nueva-posicion", methods=["GET", "POST"])
    def nueva_posicion_recepcion(recepcion_id):
        recepcion = Recepcion.query.get_or_404(recepcion_id)
        if recepcion.estado != "activa":
            flash("Recepción no activa")
            return redirect(url_for("recepcion"))
        
        if request.method == "POST":
            pasillo = request.form.get("pasillo", "").strip()
            estanteria = request.form.get("estanteria", "").strip()
            piso = request.form.get("piso", "").strip()
            
            # Store new location in session for the next scan
            session['nueva_posicion_pasillo'] = pasillo
            session['nueva_posicion_estanteria'] = estanteria
            session['nueva_posicion_piso'] = piso
            
            return redirect(url_for("recepcion_activa", recepcion_id=recepcion_id))
        
        # Generate options for pasillo (A-Z)
        pasillo_options = ''.join([f'<option value="{chr(65+i)}">{chr(65+i)}</option>' for i in range(26)])
        
        # Generate options for estanteria (1-15)
        estanteria_options = ''.join([f'<option value="{i}">{i}</option>' for i in range(1, 16)])
        
        # Generate options for piso (1-4)
        piso_options = ''.join([f'<option value="{i}">{i}</option>' for i in range(1, 5)])
        
        form_html = """
<h4>Nueva Posición - Recepción #{{ recepcion.id }}</h4>
<form method="post">
    <div class="row">
        <div class="col-md-4">
            <label>Pasillo *</label>
            <select class="form-select" name="pasillo" required>
                <option value="">Seleccione pasillo...</option>
                """ + pasillo_options + """
            </select>
        </div>
        <div class="col-md-4">
            <label>Estantería *</label>
            <select class="form-select" name="estanteria" required>
                <option value="">Seleccione estantería...</option>
                """ + estanteria_options + """
            </select>
        </div>
        <div class="col-md-4">
            <label>Piso *</label>
            <select class="form-select" name="piso" required>
                <option value="">Seleccione piso...</option>
                """ + piso_options + """
            </select>
        </div>
    </div>
    <div class="mt-3">
        <button type="submit" class="btn btn-success">Agregar Posición</button>
        <a href="{{ url_for('recepcion_activa', recepcion_id=recepcion.id) }}" class="btn btn-secondary">Cancelar</a>
    </div>
</form>
"""
        body = render_template_string(form_html, recepcion=recepcion)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)


    @app.route("/recepcion/<int:recepcion_id>/cerrar")
    def cerrar_recepcion(recepcion_id):
        recepcion = Recepcion.query.get_or_404(recepcion_id)
        if recepcion.estado != "activa":
            flash("Recepción no activa")
            return redirect(url_for("recepcion"))
        
        recepcion.estado = "pendiente"
        recepcion.fecha_fin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.session.commit()
        flash("Recepción cerrada. Pendiente de revisión.")
        return redirect(url_for("recepcion"))

    @app.route("/recepcion/<int:recepcion_id>/revisar")
    def revisar_recepcion(recepcion_id):
        recepcion = Recepcion.query.get_or_404(recepcion_id)
        
        items_agrupados = {}
        total = 0
        for item in recepcion.items:
            key = f"{item.referencia}|{item.pasillo}|{item.estanteria}|{item.piso}"
            if key not in items_agrupados:
                items_agrupados[key] = {
                    "referencia": item.referencia,
                    "marca": item.marca,
                    "categoria": item.categoria,
                    "pasillo": item.pasillo,
                    "estanteria": item.estanteria,
                    "piso": item.piso,
                    "cantidad": 0,
                    "items": []
                }
            items_agrupados[key]["cantidad"] += 1
            items_agrupados[key]["items"].append(item)
            total += 1
        
        categorias_count = {}
        for item in recepcion.items:
            cat = item.categoria or "Sin categoría"
            categorias_count[cat] = categorias_count.get(cat, 0) + 1
        
        revisar_html = """
<style>
.resumen-box { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
.item-card { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
.cat-badge { background: #17a2b8; color: white; padding: 5px 10px; border-radius: 15px; margin: 2px; display: inline-block; }
</style>
<div class="row">
    <div class="col-md-12">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4>📋 Revisión - Recepción #{{ recepcion.id }}</h4>
            <a href="{{ url_for('recepcion') }}" class="btn btn-secondary">← Volver</a>
        </div>
        
        <div class="resumen-box">
            <div class="row">
                <div class="col-md-3">
                    <strong>Operario:</strong> {{ recepcion.operario }}
                </div>
                <div class="col-md-3">
                    <strong>Inicio:</strong> {{ recepcion.fecha_inicio }}
                </div>
                <div class="col-md-3">
                    <strong>Total Unidades:</strong> {{ total }}
                </div>
                <div class="col-md-3">
                    <strong>Estado:</strong> <span class="badge bg-warning">{{ recepcion.estado }}</span>
                </div>
            </div>
            <div class="mt-2">
                <strong>Por Categoría:</strong><br>
                {% for cat, count in categorias.items() %}
                    <span class="cat-badge">{{ cat }}: {{ count }}</span>
                {% endfor %}
            </div>
        </div>
        
        <h5>Detalle por Referencia</h5>
        {% for key, item in items_agrupados.items() %}
        <div class="item-card">
            <div class="d-flex justify-content-between">
                <div>
                    <strong>{{ item.referencia }}</strong> - {{ item.marca or '' }}
                    <br><small class="text-muted">{{ item.categoria or '' }}</small>
                    <br><small>📍 {{ item.pasillo or '' }}-{{ item.estanteria or '' }}-{{ item.piso or '' }}</small>
                </div>
                <div class="text-end">
                    <span class="badge bg-primary" style="font-size: 18px;">{{ item.cantidad }} unidades</span>
                    <br>
                    <form method="post" action="{{ url_for('corregir_cantidad_recepcion', recepcion_id=recepcion.id) }}" class="d-inline">
                        <input type="hidden" name="referencia" value="{{ item.referencia }}">
                        <input type="hidden" name="pasillo" value="{{ item.pasillo }}">
                        <input type="hidden" name="estanteria" value="{{ item.estanteria }}">
                        <input type="hidden" name="piso" value="{{ item.piso }}">
                        <button type="submit" name="accion" value="-1" class="btn btn-outline-danger btn-sm">-1</button>
                        <button type="submit" name="accion" value="+1" class="btn btn-outline-success btn-sm">+1</button>
                    </form>
                </div>
            </div>
        </div>
        {% endfor %}
        
        <form method="post" action="{{ url_for('confirmar_recepcion', recepcion_id=recepcion.id) }}">
            <div class="mt-3">
                <label>Observaciones</label>
                <textarea class="form-control" name="observaciones" rows="2" placeholder="Notas adicionales..."></textarea>
            </div>
            <div class="mt-3">
                <a href="{{ url_for('cancelar_recepcion', recepcion_id=recepcion.id) }}" class="btn btn-danger" onclick="return confirm('¿Cancelar recepción?')">Cancelar</a>
                <button type="submit" class="btn btn-success float-end">✅ Confirmar a Inventario</button>
            </div>
        </form>
    </div>
</div>
"""
        body = render_template_string(revisar_html, recepcion=recepcion, items_agrupados=items_agrupados, total=total, categorias=categorias_count)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

    @app.route("/recepcion/<int:recepcion_id>/corregir", methods=["POST"])
    def corregir_cantidad_recepcion(recepcion_id):
        recepcion = Recepcion.query.get_or_404(recepcion_id)
        if recepcion.estado not in ["activa", "pendiente"]:
            flash("Recepción no editable")
            return redirect(url_for("recepcion"))
        
        referencia = request.form.get("referencia", "").strip()
        pasillo = request.form.get("pasillo", "").strip()
        estanteria = request.form.get("estanteria", "").strip()
        piso = request.form.get("piso", "").strip()
        accion = request.form.get("accion", "+1")
        
        items = RecepcionItem.query.filter_by(
            recepcion_id=recepcion_id,
            referencia=referencia,
            pasillo=pasillo,
            estanteria=estanteria,
            piso=piso
        ).all()
        
        if accion == "-1" and items:
            item_to_remove = items[-1]
            db.session.delete(item_to_remove)
        elif accion == "+1":
            if items:
                last = items[0]
                new_item = RecepcionItem(
                    recepcion_id=recepcion_id,
                    sku=last.sku,
                    marca=last.marca,
                    referencia=last.referencia,
                    categoria=last.categoria,
                    pasillo=last.pasillo,
                    estanteria=last.estanteria,
                    piso=last.piso,
                    unidad_numero=len(items) + 1,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                db.session.add(new_item)
        
        db.session.commit()
        return redirect(url_for("revisar_recepcion", recepcion_id=recepcion_id))

    @app.route("/recepcion/<int:recepcion_id>/confirmar", methods=["POST"])
    def confirmar_recepcion(recepcion_id):
        recepcion = Recepcion.query.get_or_404(recepcion_id)
        if recepcion.estado != "pendiente":
            flash("La recepción debe estar en estado pendiente")
            return redirect(url_for("recepcion"))
        
        observaciones = request.form.get("observaciones", "").strip()
        recepcion.observaciones = observaciones
        
        # Agrupar por SKU + ubicación para guardar todas las ubicaciones
        items_agrupados = {}
        for item in recepcion.items:
            key = f"{item.referencia}|{item.pasillo}|{item.estanteria}|{item.piso}"  # SKU + ubicación
            if key not in items_agrupados:
                items_agrupados[key] = {
                    "referencia": item.referencia,
                    "marca": item.marca,
                    "categoria": item.categoria,
                    "pasillo": item.pasillo,
                    "estanteria": item.estanteria,
                    "piso": item.piso,
                    "cantidad": 0
                }
            items_agrupados[key]["cantidad"] += 1
        
        for key, data in items_agrupados.items():
            # Buscar mercancia existente por marca, referencia Y ubicación
            existente = Mercancia.query.filter(
                Mercancia.marca == data["marca"],
                Mercancia.referencia == data["referencia"],
                Mercancia.pasillo == data["pasillo"],
                Mercancia.estanteria == data["estanteria"],
                Mercancia.piso == data["piso"]
            ).first()
            
            if existente:
                existente.cantidad = (existente.cantidad or 0) + data["cantidad"]
                # Actualizar SKU si no existe
                if not existente.sku:
                    # Buscar el SKU del primer item en esta ubicación
                    primer_item = RecepcionItem.query.filter(
                        RecepcionItem.referencia == data["referencia"],
                        RecepcionItem.pasillo == data["pasillo"],
                        RecepcionItem.estanteria == data["estanteria"],
                        RecepcionItem.piso == data["piso"]
                    ).first()
                    if primer_item:
                        existente.sku = primer_item.sku
            else:
                # Buscar el primer item en esta ubicación para obtener el SKU
                primer_item = RecepcionItem.query.filter(
                    RecepcionItem.referencia == data["referencia"],
                    RecepcionItem.pasillo == data["pasillo"],
                    RecepcionItem.estanteria == data["estanteria"],
                    RecepcionItem.piso == data["piso"]
                ).first()
                
                # Crear nueva entrada con esta ubicación específica
                nueva = Mercancia(
                    sku=primer_item.sku if primer_item else "",
                    marca=data["marca"] or "",
                    referencia=data["referencia"],
                    cantidad=data["cantidad"],
                    categoria_producto=data["categoria"],
                    pasillo=data["pasillo"],
                    estanteria=data["estanteria"],
                    piso=data["piso"],
                    fecha_ingreso=datetime.now().strftime("%Y-%m-%d"),
                    hora_ingreso=datetime.now().strftime("%H:%M:%S"),
                    modified_by=recepcion.operario,
                    modified_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                db.session.add(nueva)
            
            # Marcar todos los items con esta referencia como confirmados
            for item in recepcion.items:
                if item.referencia == data["referencia"]:
                    item.confirmado = True
        
        recepcion.estado = "confirmada"
        db.session.commit()
        flash("Recección confirmada. Mercancía agregada al inventario.")
        return redirect(url_for("recepcion"))

    @app.route("/recepcion/<int:recepcion_id>/cancelar")
    def cancelar_recepcion(recepcion_id):
        recepcion = Recepcion.query.get_or_404(recepcion_id)
        recepcion.estado = "cancelada"
        db.session.commit()
        flash("Recepción cancelada")
        return redirect(url_for("recepcion"))

    @app.route("/api/recepciones/activas")
    def api_recepciones_activas():
        recepciones = Recepcion.query.filter(Recepcion.estado.in_(["activa", "pendiente"])).all()
        result = []
        for r in recepciones:
            total = len(r.items or [])
            items_unicos = len(set((i.referencia or "") for i in (r.items or [])))
            result.append({
                "id": r.id,
                "operario": r.operario,
                "estado": r.estado,
                "fecha_inicio": r.fecha_inicio,
                "total_unidades": total,
                "referencias_unicas": items_unicos
            })
        return jsonify(result)
