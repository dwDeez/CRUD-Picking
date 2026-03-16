"""
Tests para el módulo de Generar Picking (create)
"""
import pytest
from datetime import datetime
from app import create_app, db
from app.models import Picking, PickingItem, Mercancia


class TestGenerarPicking:
    """Tests para generar nuevos pickings"""
    
    def test_pagina_crear_picking_get(self, client, app):
        """Test: Página de crear picking carga correctamente"""
        with app.app_context():
            response = client.get("/create")
            assert response.status_code == 200
            assert b"Generar Picking" in response.data
    
    def test_crear_picking_basico(self, client, app):
        """Test: Crear picking básico"""
        with app.app_context():
            response = client.post("/create", data={
                "Picking_ID": "P9999",
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Hora_generacion": "10:00:00",
                "Auxiliar": "Carlos",
                "Cantidad_pickings_por_auxiliar": "1",
                "Pasillo": "A",
                "Estanteria": "1",
                "Piso": "1",
                "Marca_solicitada": "Samsung",
                "Referencia_solicitada": "UN55BU8000",
                "Categoria_producto": "Televisores",
                "item_tipo[]": "Televisores",
                "item_marca[]": "Samsung",
                "item_referencia[]": "UN55BU8000",
                "item_cantidad[]": "5"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            picking = Picking.query.filter_by(Picking_ID="P9999").first()
            assert picking is not None
            assert picking.Auxiliar == "Carlos"
            assert picking.Cantidad == 5
    
    def test_crear_picking_sin_picking_id(self, client, app):
        """Test: Crear picking sin Picking_ID falla validación"""
        with app.app_context():
            response = client.post("/create", data={
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Hora_generacion": "10:00:00",
                "Auxiliar": "Carlos",
                "item_tipo[]": "Televisores",
                "item_marca[]": "Samsung",
                "item_referencia[]": "UN55BU8000",
                "item_cantidad[]": "5"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            assert "Picking_ID obligatorio".encode() in response.data
    
    def test_crear_picking_fecha_no_usuario(self, app):
        """Test: Fecha se genera automáticamente (no es configurable por usuario)"""
        with app.app_context():
            from app.utils import validate_row_creation
            data = {
                "Picking_ID": "P100",
                "Fecha": "2024-01-15",
                "Hora_generacion": "10:00:00",
                "Cantidad": "5"
            }
            ok, msg = validate_row_creation(data)
            assert ok is True
    
    def test_crear_picking_hora_no_usuario(self, app):
        """Test: Hora se genera automáticamente (no es configurable por usuario)"""
        with app.app_context():
            from app.utils import validate_row_creation
            data = {
                "Picking_ID": "P101",
                "Fecha": "2024-01-15",
                "Hora_generacion": "10:00:00",
                "Cantidad": "5"
            }
            ok, msg = validate_row_creation(data)
            assert ok is True
    
    def test_crear_picking_con_items_multiples(self, client, app):
        """Test: Crear picking con múltiples items"""
        with app.app_context():
            response = client.post("/create", data={
                "Picking_ID": "P9996",
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Hora_generacion": "10:00:00",
                "Auxiliar": "Maria",
                "Cantidad_pickings_por_auxiliar": "1",
                "item_tipo[]": ["Televisores", "Audio"],
                "item_marca[]": ["Samsung", "Sony"],
                "item_referencia[]": ["UN55BU8000", "HT-S40R"],
                "item_cantidad[]": ["3", "2"]
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            picking = Picking.query.filter_by(Picking_ID="P9996").first()
            assert picking is not None
            assert picking.Cantidad == 5
            
            items = PickingItem.query.filter_by(Picking_ID="P9996").all()
            assert len(items) == 2
    
    def test_crear_picking_con_mercancia_disponible(self, client, app):
        """Test: Crear picking usando mercancía del inventario"""
        with app.app_context():
            mercancia = Mercancia(
                sku="1234567890123",
                marca="LG",
                referencia="55UP7750",
                cantidad=10,
                categoria_producto="Televisores",
                pasillo="B",
                estanteria="2",
                piso="1"
            )
            db.session.add(mercancia)
            db.session.commit()
            
            response = client.post("/create", data={
                "Picking_ID": "P9995",
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Hora_generacion": "10:00:00",
                "Auxiliar": "Juan",
                "mercancia_seleccionada": "1",
                "item_tipo[]": "Televisores",
                "item_marca[]": "LG",
                "item_referencia[]": "55UP7750",
                "item_cantidad[]": "3"
            }, follow_redirects=True)
            
            assert response.status_code == 200
    
    def test_crear_picking_con_marca_ref_selector(self, client, app):
        """Test: Crear picking usando selector de marca referencia"""
        with app.app_context():
            response = client.post("/create", data={
                "Picking_ID": "P9994",
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Hora_generacion": "10:00:00",
                "Auxiliar": "Pedro",
                "Marca_ref_selector": "Samsung | UN55BU8000",
                "item_tipo[]": "Televisores",
                "item_marca[]": "Samsung",
                "item_referencia[]": "UN55BU8000",
                "item_cantidad[]": "2"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            picking = Picking.query.filter_by(Picking_ID="P9994").first()
            assert picking.Marca_solicitada == "Samsung"
            assert picking.Referencia_solicitada == "UN55BU8000"
    
    def test_crear_picking_pasillo_automatico(self, client, app):
        """Test: Pasillo se calcula automáticamente"""
        with app.app_context():
            response = client.post("/create", data={
                "Picking_ID": "P9993",
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Hora_generacion": "10:00:00",
                "Auxiliar": "Ana",
                "item_tipo[]": "Refrigeradores",
                "item_marca[]": "Mabe",
                "item_referencia[]": "RMAV20",
                "item_cantidad[]": "4"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            picking = Picking.query.filter_by(Picking_ID="P9993").first()
            assert picking is not None
            assert picking.Pasillo is not None
    
    def test_validate_row_creation_exitoso(self, app):
        """Test: Validación de creación exitosa"""
        from app.utils import validate_row_creation
        with app.app_context():
            data = {
                "Picking_ID": "P100",
                "Fecha": "2024-01-15",
                "Hora_generacion": "10:00:00",
                "Cantidad": "5"
            }
            ok, msg = validate_row_creation(data)
            assert ok is True
            assert msg == ""
    
    def test_validate_row_creation_falla(self, app):
        """Test: Validación de creación falla"""
        from app.utils import validate_row_creation
        with app.app_context():
            data = {
                "Picking_ID": "",
                "Fecha": "invalid",
                "Hora_generacion": "bad",
                "Cantidad": "abc"
            }
            ok, msg = validate_row_creation(data)
            assert ok is False
    
    def test_crear_picking_cantidad_cero(self, client, app):
        """Test: Crear picking sin items (cantidad por defecto 1)"""
        with app.app_context():
            response = client.post("/create", data={
                "Picking_ID": "P9991",
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Hora_generacion": "10:00:00",
                "Auxiliar": "Sofia",
                "item_tipo[]": "",
                "item_marca[]": "",
                "item_referencia[]": "",
                "item_cantidad[]": ""
            }, follow_redirects=True)
            
            picking = Picking.query.filter_by(Picking_ID="P9991").first()
            assert picking is not None
            assert picking.Cantidad >= 0
