import os
import re
import shutil
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from werkzeug.utils import secure_filename

from app import db
from app.models import Picking, PickingItem, Mercancia, PickingCSV, PickingItemCSV, MercanciaCSV


date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
time_re = re.compile(r"^\d{2}:\d{2}:\d{2}$")

COLUMNS_CONFIG_FILE = Path("columns_config.json")

DEFAULT_COLUMNS = {
    "Picking_ID": {"label": "Picking_ID", "visible": True, "order": 1},
    "Fecha": {"label": "Fecha", "visible": True, "order": 2},
    "Hora_gen": {"label": "Hora_gen", "visible": True, "order": 3},
    "Auxiliar": {"label": "Auxiliar", "visible": True, "order": 4},
    "Marca": {"label": "Marca", "visible": True, "order": 5},
    "Referencia": {"label": "Referencia", "visible": True, "order": 6},
    "Pasillo": {"label": "Pasillo", "visible": True, "order": 7},
    "Piso": {"label": "Piso", "visible": True, "order": 8},
    "Cantidad": {"label": "Cantidad", "visible": True, "order": 9},
    "Error": {"label": "Error(%)", "visible": True, "order": 10},
    "modified_at": {"label": "modified_at", "visible": True, "order": 11},
    "acciones": {"label": "acciones", "visible": True, "order": 99},
}

COLUMN_MAPPING = {
    "Picking_ID": ["Picking_ID", "picking_id", "id"],
    "Fecha": ["Fecha", "fecha", "date"],
    "Hora_generacion": ["Hora_generacion", "hora_generacion", "Hora_gen", "hora_gen", "Hora_inicio"],
    "Hora_revision": ["Hora_revision", "hora_revision", "Hora_rev", "hora_rev"],
    "Hora_despacho": ["Hora_despacho", "hora_despacho", "Hora_fin", "hora_fin"],
    "Auxiliar": ["Auxiliar", "auxiliar", "Usuario", "user", "Operario"],
    "Cantidad_pickings_por_auxiliar": ["Cantidad_pickings_por_auxiliar", "cantidad_pickings", "Pickings_auxiliar"],
    "Pasillo": ["Pasillo", "pasillo", "Pasillo_Zona", "zona"],
    "Estanteria": ["Estanteria", "estanteria", "Estante", "rack"],
    "Piso": ["Piso", "piso", "Nivel", "nivel"],
    "Marca_solicitada": ["Marca_solicitada", "Marca", "marca", "marca_solicitada"],
    "Referencia_solicitada": ["Referencia_solicitada", "Referencia", "referencia", "referencia_solicitada", "SKU"],
    "Categoria_producto": ["Categoria_producto", "Categoria", "categoria", "Categoria_producto", "Categoria_vehiculo", "Tipo_producto", "tipo"],
    "Cantidad": ["Cantidad", "cantidad", "qty", "quantity"],
    "Error_porcentaje": ["Error_porcentaje", "Error", "error", "error_porcentaje", "porcentaje_error"],
}


def find_column(csv_columns: list, possible_names: list) -> str | None:
    for name in possible_names:
        for col in csv_columns:
            if col.lower().strip() == name.lower():
                return col
    return None


def import_csv_adaptive(csv_path: str) -> tuple[str, list, list, list]:
    import_log = {
        "loaded": [],
        "skipped": [],
        "warnings": []
    }
    
    if not os.path.exists(csv_path):
        return "CSV no encontrado.", [], [], []
    
    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except Exception as e:
        try:
            df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="latin-1")
        except Exception as e2:
            return f"Error leyendo CSV: {e2}", [], [], []
    
    csv_columns = list(df.columns)
    
    mapping = {}
    for model_col, possible_names in COLUMN_MAPPING.items():
        found_col = find_column(csv_columns, possible_names)
        if found_col:
            mapping[model_col] = found_col
            import_log["loaded"].append(f"{model_col} <- {found_col}")
        else:
            import_log["skipped"].append(f"{model_col} (no encontrado en CSV)")
    
    for col in csv_columns:
        if col not in mapping.values() and col not in ["modified_by", "modified_at"]:
            import_log["warnings"].append(f"Columna '{col}' ignorada (no mapeada)")
    
    if "Picking_ID" not in mapping:
        return "Error: Columna 'Picking_ID' no encontrada en el CSV", [], [], []
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    audit_user = get_audit_user()
    
    imported_count = 0
    error_count = 0
    
    try:
        PickingCSV.query.delete()
        PickingItemCSV.query.delete()
        db.session.commit()
        
        for _, r in df.iterrows():
            try:
                pick_id = str(r.get(mapping.get("Picking_ID"), "")).strip()
                if not pick_id:
                    continue
                
                p = PickingCSV(
                    Picking_ID=pick_id,
                    Fecha=str(r.get(mapping.get("Fecha"), "")).strip() if mapping.get("Fecha") else "",
                    Hora_generacion=str(r.get(mapping.get("Hora_generacion"), "")).strip() if mapping.get("Hora_generacion") else "",
                    Hora_revision=str(r.get(mapping.get("Hora_revision"), "")).strip() if mapping.get("Hora_revision") else "",
                    Hora_despacho=str(r.get(mapping.get("Hora_despacho"), "")).strip() if mapping.get("Hora_despacho") else "",
                    Auxiliar=str(r.get(mapping.get("Auxiliar"), "")).strip() if mapping.get("Auxiliar") else "",
                    Cantidad_pickings_por_auxiliar=int(r.get(mapping.get("Cantidad_pickings_por_auxiliar")) or 0) if mapping.get("Cantidad_pickings_por_auxiliar") else 0,
                    Pasillo=str(r.get(mapping.get("Pasillo"), "")).strip() if mapping.get("Pasillo") else "",
                    Estanteria=str(r.get(mapping.get("Estanteria"), "")).strip() if mapping.get("Estanteria") else "",
                    Piso=str(r.get(mapping.get("Piso"), "")).strip() if mapping.get("Piso") else "",
                    Marca_solicitada=str(r.get(mapping.get("Marca_solicitada"), "")).strip() if mapping.get("Marca_solicitada") else "",
                    Referencia_solicitada=str(r.get(mapping.get("Referencia_solicitada"), "")).strip() if mapping.get("Referencia_solicitada") else "",
                    Categoria_producto=str(r.get(mapping.get("Categoria_producto"), "")).strip() if mapping.get("Categoria_producto") else "",
                    Cantidad=int(r.get(mapping.get("Cantidad")) or 0) if mapping.get("Cantidad") else 0,
                    Error_porcentaje=float(r.get(mapping.get("Error_porcentaje")) or 0.0) if mapping.get("Error_porcentaje") else 0.0,
                    modified_by=audit_user,
                    modified_at=now
                )
                db.session.merge(p)
                
                if p.Marca_solicitada or p.Referencia_solicitada:
                    try:
                        item = PickingItemCSV(
                            Picking_ID=pick_id,
                            tipo=p.Categoria_producto or "Item",
                            marca=p.Marca_solicitada,
                            referencia=p.Referencia_solicitada,
                            cantidad=p.Cantidad or 1,
                            Pasillo=p.Pasillo,
                            Estanteria=p.Estanteria,
                            Piso=p.Piso
                        )
                        db.session.add(item)
                        db.session.flush()
                    except Exception:
                        db.session.rollback()
                
                imported_count += 1
            except Exception as row_error:
                error_count += 1
                if error_count <= 5:
                    import_log["warnings"].append(f"Error en fila {imported_count + error_count}: {row_error}")
        
        db.session.commit()
        
        result_msg = f"Análisis CSV: {imported_count} filas importadas para análisis."
        if error_count > 0:
            result_msg += f" ({error_count} errores)"
        
        return result_msg, import_log["loaded"], import_log["skipped"], import_log["warnings"]
        
    except Exception as e:
        db.session.rollback()
        return f"Error importando CSV: {e}", [], [], []


def load_columns_config() -> dict:
    if COLUMNS_CONFIG_FILE.exists():
        try:
            with open(COLUMNS_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_COLUMNS.copy()


def save_columns_config(config: dict) -> None:
    with open(COLUMNS_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_csv_columns() -> list:
    csv_path = get_csv_path()
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, nrows=1, encoding="utf-8-sig")
            return list(df.columns)
        except Exception:
            pass
    return []


def get_backup_dir():
    from flask import current_app
    return current_app.config.get("BACKUP_DIR", str(Path("backups")))


def ensure_backup_dir() -> None:
    backup_dir = get_backup_dir()
    Path(backup_dir).mkdir(parents=True, exist_ok=True)


def get_audit_user() -> str:
    from flask import current_app
    return current_app.config.get("AUDIT_USER", "ui_user")


def get_csv_path() -> Path:
    from flask import current_app
    csv_file = current_app.config.get("CSV_FILE", "datos.csv")
    base_dir = current_app.config.get("BASE_DIR", ".")
    return Path(base_dir) / csv_file


def get_db_path() -> Path:
    from flask import current_app
    db_file = current_app.config.get("DB_NAME", "wms_data.db")
    base_dir = current_app.config.get("DATA_DIR", ".")
    return Path(base_dir) / db_file


def allowed_file(filename: str) -> bool:
    from flask import current_app
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"csv"})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def backup_db() -> str | None:
    db_path = get_db_path()
    if os.path.exists(db_path):
        ensure_backup_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(get_backup_dir())
        dest = backup_dir / f"db_backup_{ts}.db"
        shutil.copy2(db_path, dest)
        return str(dest)
    return None


def backup_csv() -> str | None:
    csv_path = get_csv_path()
    if os.path.exists(csv_path):
        ensure_backup_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(get_backup_dir())
        dest = backup_dir / f"csv_backup_{ts}_{csv_path.name}"
        shutil.copy2(csv_path, dest)
        return str(dest)
    return None


def validate_row_creation(data: dict) -> tuple[bool, str]:
    if not data.get("Picking_ID"):
        return False, "Picking_ID obligatorio"
    if not date_re.match(data.get("Fecha", "")):
        return False, "Fecha inválida (YYYY-MM-DD)"
    if not time_re.match(data.get("Hora_generacion", "")):
        return False, "Hora_generacion inválida (HH:MM:SS)"
    try:
        int(data.get("Cantidad", 0))
    except (ValueError, TypeError):
        return False, "Cantidad debe ser entero"
    return True, ""


def validate_row_edit(data: dict) -> tuple[bool, str]:
    ok, msg = validate_row_creation(data)
    if not ok:
        return ok, msg
    try:
        v = float(data.get("Error_porcentaje", 0.0))
        if not (0.0 <= v <= 100.0):
            return False, "Error_porcentaje fuera de rango"
    except (ValueError, TypeError):
        return False, "Error_porcentaje inválido"
    return True, ""


def build_pasillo_alfa_with_positions(pasillos_ordered: list) -> str:
    positions = {}
    for idx, pas in enumerate(pasillos_ordered, start=1):
        key = pas.strip() if pas else ""
        if key == "":
            continue
        positions.setdefault(key, []).append(idx)
    sorted_pas = sorted(positions.keys(), key=lambda s: s.lower())
    parts = []
    for pas in sorted_pas:
        pos_list = positions[pas]
        parts.append(f"{pas} (pos:{','.join(str(x) for x in pos_list)})")
    return "; ".join(parts)


def get_distinct_values_for_filters() -> dict:
    cols = {
        "Picking_ID": set(),
        "Fecha": set(),
        "Auxiliar": set(),
        "Marca": set(),
        "Referencia": set(),
        "Pasillo": set(),
        "Piso": set(),
        "Categoria": set()
    }
    try:
        rows = Picking.query.with_entities(
            Picking.Picking_ID, Picking.Fecha, Picking.Auxiliar,
            Picking.Marca_solicitada, Picking.Referencia_solicitada,
            Picking.Pasillo, Picking.Piso, Picking.Categoria_producto
        ).all()
    except Exception:
        rows = []
    
    for pid, fecha, aux, marca, ref, pas, piso, cat in rows:
        if pid:
            cols["Picking_ID"].add(pid)
        if fecha:
            cols["Fecha"].add(fecha)
        if aux:
            cols["Auxiliar"].add(aux)
        if marca:
            marca_ref = f"{marca} | {ref}".strip(" |")
            cols["Marca"].add(marca_ref)
        if ref:
            cols["Referencia"].add(ref)
        if pas:
            cols["Pasillo"].add(pas)
        if piso:
            cols["Piso"].add(piso)
        if cat:
            cols["Categoria"].add(cat)
    
    try:
        mercancias = Mercancia.query.all()
        for m in mercancias:
            if m.marca:
                cols["Marca"].add(m.marca)
            if m.referencia:
                cols["Referencia"].add(m.referencia)
            if m.pasillo:
                cols["Pasillo"].add(m.pasillo)
            if m.piso:
                cols["Piso"].add(m.piso)
            if m.categoria_producto:
                cols["Categoria"].add(m.categoria_producto)
    except Exception:
        pass
    
    return {k: sorted(list(v)) for k, v in cols.items()}


def get_distinct_item_types() -> list:
    try:
        rows = db.session.query(PickingItem.tipo).distinct().all()
        types = sorted([r[0] for r in rows if r[0]])
        return types
    except Exception:
        return []


def get_pasillo_for_item(marca: str, referencia: str) -> str:
    try:
        q = Picking.query.filter(
            Picking.Marca_solicitada == (marca or ""),
            Picking.Referencia_solicitada == (referencia or "")
        ).first()
        if q and q.Pasillo:
            return q.Pasillo
        q2 = Picking.query.filter(Picking.Marca_solicitada == (marca or "")).first()
        if q2 and q2.Pasillo:
            return q2.Pasillo
    except Exception:
        return ""
    return ""


def dedupe_picking_items() -> str:
    try:
        sql = """
        DELETE FROM picking_items
        WHERE id NOT IN (
        SELECT MIN(id) FROM picking_items
        GROUP BY Picking_ID, marca, referencia, tipo, cantidad
        );
        """
        db.session.execute(db.text(sql))
        db.session.commit()
        return "Dedupe executed."
    except Exception as e:
        db.session.rollback()
        return f"Dedupe error: {e}"


def init_db_from_csv(csv_path: str = None) -> str:
    csv_file = csv_path or str(get_csv_path())
    
    try:
        db.create_all()
    except Exception as e:
        print("Warning creating tables:", e)
    
    try:
        msg = dedupe_picking_items()
        print(msg)
    except Exception as e:
        print("Dedupe failed:", e)
    
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file, dtype=str, keep_default_na=False)
        except Exception as e:
            print("CSV read error:", e)
            return "CSV no pudo leerse."
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        audit_user = get_audit_user()
        
        try:
            for _, r in df.iterrows():
                pid = str(r.get("Picking_ID", "")).strip()
                p = Picking(
                    Picking_ID=pid,
                    Fecha=str(r.get("Fecha", "")).strip(),
                    Hora_generacion=str(r.get("Hora_generacion", "")).strip(),
                    Hora_revision=str(r.get("Hora_revision", "")).strip(),
                    Hora_despacho=str(r.get("Hora_despacho", "")).strip(),
                    Auxiliar=str(r.get("Auxiliar", "")).strip(),
                    Cantidad_pickings_por_auxiliar=int(r.get("Cantidad_pickings_por_auxiliar") or 0),
                    Pasillo=str(r.get("Pasillo", "")).strip(),
                    Estanteria=str(r.get("Estanteria", "")).strip(),
                    Piso=str(r.get("Piso", "")).strip(),
                    Marca_solicitada=str(r.get("Marca_solicitada", "")).strip(),
                    Referencia_solicitada=str(r.get("Referencia_solicitada", "")).strip(),
                    Categoria_producto=str(r.get("Categoria_producto", "")).strip(),
                    Cantidad=int(r.get("Cantidad") or 0),
                    Error_porcentaje=float(r.get("Error_porcentaje") or 0.0),
                    modified_by=audit_user,
                    modified_at=now
                )
                db.session.merge(p)
                if p.Marca_solicitada or p.Referencia_solicitada:
                    try:
                        item = PickingItem(
                            Picking_ID=pid,
                            tipo=p.Categoria_producto or "Item",
                            marca=p.Marca_solicitada,
                            referencia=p.Referencia_solicitada,
                            cantidad=p.Cantidad or 1,
                            Pasillo=p.Pasillo,
                            Estanteria=p.Estanteria,
                            Piso=p.Piso
                        )
                        db.session.add(item)
                        db.session.flush()
                    except Exception:
                        db.session.rollback()
            db.session.commit()
            return f"DB importada desde CSV ({len(df)} filas)."
        except Exception as e:
            db.session.rollback()
            print("init_db_from_csv error:", e)
            return "Error importando CSV."
    return "CSV no encontrado o DB ya existe."


def get_mercancia_disponible():
    try:
        mercancias = Mercancia.query.filter(Mercancia.cantidad > 0).all()
        return [{
            'id': m.id,
            'marca': m.marca,
            'referencia': m.referencia,
            'cantidad': m.cantidad,
            'categoria_producto': m.categoria_producto,
            'pasillo': m.pasillo,
            'estanteria': m.estanteria,
            'piso': m.piso,
            'fecha_ingreso': m.fecha_ingreso,
            'hora_ingreso': m.hora_ingreso
        } for m in mercancias]
    except Exception as e:
        print("Error get_mercancia_disponible:", e)
        return []


def get_mercancia_by_marca_ref(marca: str, referencia: str):
    try:
        return Mercancia.query.filter(
            Mercancia.marca == marca,
            Mercancia.referencia == referencia,
            Mercancia.cantidad > 0
        ).all()
    except Exception as e:
        print("Error get_mercancia_by_marca_ref:", e)
        return []


def descontar_mercancia(marca: str, referencia: str, cantidad: int) -> bool:
    try:
        mercancias = get_mercancia_by_marca_ref(marca, referencia)
        remaining = cantidad
        
        for m in mercancias:
            if remaining <= 0:
                break
            if m.cantidad >= remaining:
                m.cantidad -= remaining
                remaining = 0
            else:
                remaining -= m.cantidad
                m.cantidad = 0
        
        db.session.commit()
        return remaining == 0
    except Exception as e:
        db.session.rollback()
        print("Error descontar_mercancia:", e)
        return False


def get_mercancia_by_sku(sku: str):
    try:
        return Mercancia.query.filter(Mercancia.sku == sku).first()
    except Exception as e:
        print("Error get_mercancia_by_sku:", e)
        return None
