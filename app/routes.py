import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import (
    Flask, flash, jsonify, redirect, render_template_string, request, url_for, session, send_file
)
from werkzeug.utils import secure_filename

from app import db
from app.models import Picking, PickingItem, Mercancia, PickingCSV, PickingItemCSV, MercanciaCSV
from app.utils import (
    allowed_file, backup_csv, backup_db, build_pasillo_alfa_with_positions,
    get_distinct_item_types, get_distinct_values_for_filters, get_pasillo_for_item,
    validate_row_creation, validate_row_edit,
    load_columns_config, save_columns_config, DEFAULT_COLUMNS, import_csv_adaptive,
    get_mercancia_disponible, get_mercancia_by_marca_ref, descontar_mercancia
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
<div class="mb-3 d-flex gap-2 flex-wrap">
    <a class="btn btn-primary" href="{{ url_for('create') }}">➕ Agregar nuevo</a>
    <a class="btn btn-secondary" href="{{ url_for('agregar_mercancia') }}">📦 Agregar mercancía</a>
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
<div class="col-md-3 mb-2"><label>Tipo (filtrar)</label>
<select class="form-select" id="Tipo_selector" name="Tipo_selector">
<option value="">-- todos --</option>
{% for t in tipos %}<option value="{{ t }}">{{ t }}</option>{% endfor %}
</select>
</div>
<div class="col-md-4 mb-2"><label>Marca | Referencia (selector)</label>
<select class="form-select" id="Marca_ref_selector" name="Marca_ref_selector">
<option value="">-- seleccionar --</option>
{% for mr in marca_opts %}<option value="{{ mr }}">{{ mr }}</option>{% endfor %}
</select>
</div>
<div class="col-md-5 mb-2"><label>Seleccionar del Inventario</label>
<select class="form-select" id="mercancia_selector" name="mercancia_selector">
<option value="">-- seleccionar mercancía --</option>
{% for m in mercancia_opts %}<option value="{{ m.value }}">{{ m.label }}</option>{% endfor %}
</select>
</div>
</div>
<div class="row">
<div class="col-md-2 mb-2"><label>Picking_ID</label><input class="form-control" name="Picking_ID" id="Picking_ID" readonly></div>
<div class="col-md-2 mb-2"><label>Fecha</label><input class="form-control" type="date" name="Fecha" id="Fecha"></div>
<div class="col-md-2 mb-2"><label>Hora generación</label><input class="form-control" type="time" step="1" name="Hora_generacion" id="Hora_generacion"></div>
<div class="col-md-2 mb-2"><label>Auxiliar</label>
<select class="form-select" name="Auxiliar" id="Auxiliar">
<option value="">-- seleccionar --</option>
{% for a in aux_opts %}<option value="{{ a }}">{{ a }}</option>{% endfor %}
</select>
</div>
<div class="col-md-2 mb-2"><label>Pasillo</label>
<input class="form-control" name="Pasillo" id="Pasillo" list="pasillos_list">
<datalist id="pasillos_list">{% for p in pas_opts %}<option value="{{ p }}">{% endfor %}</datalist>
</div>
<div class="col-md-2 mb-2"><label>Categoría</label>
<input class="form-control" name="Categoria_producto" id="Categoria_producto" list="categorias_list">
<datalist id="categorias_list">{% for c in cat_opts %}<option value="{{ c }}">{% endfor %}</datalist>
</div>
</div>
<div class="row mt-2">
<div class="col-md-3 mb-2"><label>Marca (manual)</label><input class="form-control" name="Marca_solicitada" id="Marca_solicitada"></div>
<div class="col-md-3 mb-2"><label>Referencia (manual)</label><input class="form-control" name="Referencia_solicitada" id="Referencia_solicitada"></div>
</div>
<hr>
<h5>Ítems del Picking (se rellenan automáticamente al seleccionar Marca | Referencia o Mercancía del Inventario)</h5>
<div id="items_container"></div>
<div class="mb-3">
<button type="button" class="btn btn-sm btn-outline-secondary" id="add_item_btn">Agregar ítem</button>
<small class="text-muted ms-2">Marque "Fijar" para evitar que el autocompletado sobrescriba ese ítem.</small>
</div>
<div class="mt-3">
<button type="submit" id="saveBtn" class="btn btn-primary">Guardar</button>
<a class="btn btn-secondary" href="{{ url_for('index') }}">Cancelar</a>
</div>
</form>
<template id="item_row_template">
<div class="row item-row mb-2" data-locked="false">
<div class="col-md-2"><input class="form-control" name="item_tipo[]" placeholder="Tipo"></div>
<div class="col-md-3"><input class="form-control" name="item_marca[]" placeholder="Marca"></div>
<div class="col-md-4"><input class="form-control" name="item_referencia[]" placeholder="Referencia"></div>
<div class="col-md-1"><input class="form-control" name="item_cantidad[]" type="number" min="1" value="1"></div>
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
let marcaUserInteracted = false;
const marcaSel = document.getElementById('Marca_ref_selector');
const initialMarcaValue = marcaSel ? marcaSel.value : '';
if (marcaSel) {
marcaSel.addEventListener('focus', () => { marcaUserInteracted = true; });
marcaSel.addEventListener('click', () => { marcaUserInteracted = true; });
marcaSel.addEventListener('keydown', () => { marcaUserInteracted = true; });
}
fetch('{{ url_for("next_picking_id") }}')
.then(r => r.json())
.then(j => { if(j.next_id) document.getElementById('Picking_ID').value = j.next_id; })
.catch(e => console.log('next_id error', e));
if (document.getElementById('items_container').children.length === 0) {
addItemRow();
}
document.getElementById('add_item_btn').addEventListener('click', function(){ addItemRow(); });
function addItemRow(tipo='', marca='', referencia='', cantidad=1, locked=false){
const tpl = document.getElementById('item_row_template');
const clone = tpl.content.cloneNode(true);
const row = clone.querySelector('.item-row');
if(tipo) row.querySelector('input[name="item_tipo[]"]').value = tipo;
if(marca) row.querySelector('input[name="item_marca[]"]').value = marca;
if(referencia) row.querySelector('input[name="item_referencia[]"]').value = referencia;
if(cantidad) row.querySelector('input[name="item_cantidad[]"]').value = cantidad;
const lockCheckbox = row.querySelector('.item-lock');
if(locked){
lockCheckbox.checked = true;
row.dataset.locked = 'true';
row.style.backgroundColor = '#f8f9fa';
row.style.borderLeft = '4px solid #0d6efd';
} else {
row.dataset.locked = 'false';
}
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
if(this.checked){
row.style.backgroundColor = '#f8f9fa';
row.style.borderLeft = '4px solid #0d6efd';
} else {
row.style.backgroundColor = '';
row.style.borderLeft = '';
}
};
const row = chk.closest('.item-row');
if(chk.checked){
row.dataset.locked = 'true';
row.style.backgroundColor = '#f8f9fa';
row.style.borderLeft = '4px solid #0d6efd';
} else {
row.dataset.locked = 'false';
}
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
const tipoSel = document.getElementById('Tipo_selector');
if(tipoSel){
tipoSel.addEventListener('change', function(){
const tipo = this.value;
marcaSel.innerHTML = '<option value="">-- seleccionar --</option>';
if(!tipo) return;
fetch('{{ url_for("marca_refs_for_type") }}?tipo=' + encodeURIComponent(tipo))
.then(r => r.json())
.then(j => {
if(j.ok && Array.isArray(j.marca_refs)){
j.marca_refs.forEach(mr => {
const o = document.createElement('option');
o.value = mr;
o.text = mr;
marcaSel.appendChild(o);
});
}
})
.catch(err => console.log('marca_refs_for_type error', err));
});
}
if(marcaSel){
marcaSel.addEventListener('change', function(){
if (!marcaUserInteracted && this.value === initialMarcaValue) {
return;
}
const val = this.value;
if(!val) return;
fetch('{{ url_for("meta_for_marca") }}?marca_ref=' + encodeURIComponent(val))
.then(r => { if(!r.ok) throw r; return r.json(); })
.then(j => {
if(j.ok){
if(j.pasillo) document.getElementById('Pasillo').value = j.pasillo;
if(j.piso) document.getElementById('Piso') && (document.getElementById('Piso').value = j.piso);
const parts = val.split('|').map(s => s.trim());
if(parts[0]) document.getElementById('Marca_solicitada').value = parts[0];
if(parts[1]) document.getElementById('Referencia_solicitada').value = parts[1];
}
})
.catch(err => console.log('meta fetch error', err));
fetch('{{ url_for("items_for_marca") }}?marca_ref=' + encodeURIComponent(val))
.then(r => {
if(!r.ok) return {ok: false, items: []};
return r.json();
})
.then(j => {
if(!(j && j.ok && Array.isArray(j.items))) {
if(document.getElementById('items_container').children.length === 0) addItemRow();
return;
}
const returned = j.items;
returned.forEach(it => {
const rows = Array.from(document.querySelectorAll('.item-row'));
let matched = false;
for (const row of rows) {
const rowMarca = (row.querySelector('input[name="item_marca[]"]').value || '').trim();
const rowRef = (row.querySelector('input[name="item_referencia[]"]').value || '').trim();
const locked = row.dataset.locked === 'true';
if (rowMarca === (it.marca || '') && rowRef === (it.referencia || '')) {
matched = true;
if (!locked) {
row.querySelector('input[name="item_tipo[]"]').value = it.tipo || '';
row.querySelector('input[name="item_marca[]"]').value = it.marca || '';
row.querySelector('input[name="item_referencia[]"]').value = it.referencia || '';
row.querySelector('input[name="item_cantidad[]"]').value = it.cantidad || 1;
updateTotal();
}
break;
}
}
if (!matched) {
let filled = false;
for (const row of rows) {
const rowMarca = (row.querySelector('input[name="item_marca[]"]').value || '').trim();
const rowRef = (row.querySelector('input[name="item_referencia[]"]').value || '').trim();
const locked = row.dataset.locked === 'true';
if (!locked && rowMarca === '' && rowRef === '') {
row.querySelector('input[name="item_tipo[]"]').value = it.tipo || '';
row.querySelector('input[name="item_marca[]"]').value = it.marca || '';
row.querySelector('input[name="item_referencia[]"]').value = it.referencia || '';
row.querySelector('input[name="item_cantidad[]"]').value = it.cantidad || 1;
filled = true;
updateTotal();
break;
}
}
if (!filled) {
addItemRow(tipo || '', it.marca || '', it.referencia || '', it.cantidad || 1, false);
updateTotal();
}
}
});
})
.catch(err => {
console.log('items fetch error', err);
if(document.getElementById('items_container').children.length === 0) addItemRow();
});
});
}
updateTotal();
});
const mercanciaSel = document.getElementById('mercancia_selector');
if(mercanciaSel){
mercanciaSel.addEventListener('change', function(){
const mercanciaId = this.value;
if(!mercanciaId) return;
fetch('/buscar_mercancia_id/' + mercanciaId)
.then(r => r.json())
.then(data => {
if(data && data.marca){
const firstRow = document.querySelector('.item-row');
if(firstRow && firstRow.dataset.locked === 'false'){
firstRow.querySelector('input[name="item_marca[]"]').value = data.marca || '';
firstRow.querySelector('input[name="item_referencia[]"]').value = data.referencia || '';
firstRow.querySelector('input[name="item_cantidad[]"]').value = data.cantidad || 1;
firstRow.querySelector('input[name="item_tipo[]"]').value = data.categoria || '';
document.getElementById('Marca_solicitada').value = data.marca || '';
document.getElementById('Referencia_solicitada').value = data.referencia || '';
document.getElementById('Pasillo').value = data.pasillo || '';
updateTotal();
}
}
})
.catch(err => console.log('Error mercancia:', err));
});
}
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
<div class="col-md-3 mb-2"><label>Error % (solo en edición)</label><input class="form-control" type="number" step="0.1" name="Error_porcentaje" value="{{ p.Error_porcentaje if p.Error_porcentaje is not none else '' }}"></div>
<div class="col-md-3 mb-2"><label>Cantidad total</label><input class="form-control" type="number" name="Cantidad" value="{{ p.Cantidad or 0 }}" readonly></div>
</div>
<div class="mt-3">
<button type="submit" id="saveBtn" class="btn btn-primary">Guardar</button>
<a class="btn btn-secondary" href="{{ url_for('index') }}">Cancelar</a>
</div>
</form>
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
<a class="btn btn-sm btn-outline-danger" href="{{ r.delete_url }}">Eliminar</a>
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
        
        body = render_template_string(CREATE_FORM, marca_opts=marca_opts, aux_opts=aux_opts, pas_opts=pas_opts, cat_opts=all_categories, piso_opts=piso_opts, tipos=tipos, mercancia_opts=mercancia_select)
        columns_config = load_columns_config()
        return render_template_string(BASE_HTML, body=body, columns_config=columns_config)

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
        
        mercancia_form = """
<form method="post">
<div class="row">
    <div class="col-md-6 mb-2">
        <label>SKU (código único del producto)</label>
        <input class="form-control" name="SKU" id="SKU" placeholder="Ingrese o escanee el SKU" autofocus>
    </div>
    <div class="col-md-3 mb-2">
        <label>Categoría producto</label>
        <input class="form-control" name="Categoria_producto" id="Categoria_producto" list="categorias_list">
        <datalist id="categorias_list">
        {% for c in all_categories %}<option value="{{ c }}">{% endfor %}
        </datalist>
    </div>
    <div class="col-md-3 mb-2">
        <label>Marca</label>
        <input class="form-control" name="Marca_solicitada" id="Marca_solicitada" list="marcas_list">
        <datalist id="marcas_list">
        {% for m in marca_opts %}<option value="{{ m }}">{% endfor %}
        </datalist>
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
        <label>Pasillo</label>
        <input class="form-control" name="Pasillo" id="Pasillo" list="pasillos_list">
        <datalist id="pasillos_list">
        {% for p in pas_opts %}<option value="{{ p }}">{% endfor %}
        </datalist>
    </div>
    <div class="col-md-2 mb-2">
        <label>Estantería</label>
        <input class="form-control" name="Estanteria" id="Estanteria" list="estanterias_list">
        <datalist id="estanterias_list">
        {% for e in est_opts %}<option value="{{ e }}">{% endfor %}
        </datalist>
    </div>
    <div class="col-md-2 mb-2">
        <label>Piso</label>
        <input class="form-control" name="Piso" id="Piso" list="pisos_list">
        <datalist id="pisos_list">
        {% for p in piso_opts %}<option value="{{ p }}">{% endfor %}
        </datalist>
    </div>
</div>
<div class="mt-3">
    <button type="submit" class="btn btn-primary">Guardar</button>
    <a class="btn btn-secondary" href="{{ url_for('index') }}">Cancelar</a>
</div>
</form>
<script>
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
                    }
                });
        }
    }
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
        mercancia = Mercancia.query.get(mercancia_id)
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
                upload_path = Path(app.config.get("BASE_DIR", ".")) / filename
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
        except Exception:
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
            rows = db.session.query(PickingItem.marca, PickingItem.referencia).filter(PickingItem.tipo == tipo).distinct().all()
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
