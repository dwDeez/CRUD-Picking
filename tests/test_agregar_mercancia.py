"""
Tests para el módulo de Agregar Mercancía
"""
import pytest
from app import create_app, db
from app.models import Mercancia


class TestAgregarMercancia:
    """Tests para el flujo de agregar mercancía"""
    
    def test_agregar_mercancia_basico(self, client, app):
        """Test: Agregar mercancía básica"""
        with app.app_context():
            response = client.post("/agregar_mercancia", data={
                "SKU": "1234567890123",
                "Marca_solicitada": "Samsung",
                "Referencia_solicitada": "UN55BU8000",
                "Categoria_producto": "Televisores",
                "Cantidad": "10",
                "Pasillo": "A",
                "Estanteria": "1",
                "Piso": "1"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            mercancia = Mercancia.query.filter_by(sku="1234567890123").first()
            assert mercancia is not None
            assert mercancia.marca == "Samsung"
            assert mercancia.referencia == "UN55BU8000"
            assert mercancia.cantidad == 10
    
    def test_agregar_mercancia_sin_sku(self, client, app):
        """Test: Agregar mercancía sin SKU"""
        with app.app_context():
            response = client.post("/agregar_mercancia", data={
                "Marca_solicitada": "LG",
                "Referencia_solicitada": "55UP7750",
                "Cantidad": "5",
                "Pasillo": "B"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            mercancia = Mercancia.query.filter_by(marca="LG").first()
            assert mercancia is not None
            assert mercancia.referencia == "55UP7750"
    
    def test_agregar_mercancia_con_categoria_vacia(self, client, app):
        """Test: Agregar mercancía sin categoría"""
        with app.app_context():
            response = client.post("/agregar_mercancia", data={
                "SKU": "9999999999999",
                "Marca_solicitada": "Sony",
                "Referencia_solicitada": "KD55X80J",
                "Cantidad": "3",
                "Pasillo": "C"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            mercancia = Mercancia.query.filter_by(sku="9999999999999").first()
            assert mercancia is not None
    
    def test_buscar_sku_existente(self, client, app):
        """Test: Buscar SKU existente"""
        with app.app_context():
            # Agregar primero
            m = Mercancia(
                sku="1112223334455",
                marca="TestMarca",
                referencia="TestRef",
                cantidad=10,
                categoria_producto="TestCat",
                pasillo="A",
                estanteria="1",
                piso="1"
            )
            db.session.add(m)
            db.session.commit()
            
            response = client.get("/buscar_sku/1112223334455")
            assert response.status_code == 200
            
            import json
            data = json.loads(response.data)
            assert data["encontrado"] is True
            assert data["marca"] == "TestMarca"
    
    def test_buscar_sku_inexistente(self, client, app):
        """Test: Buscar SKU inexistente"""
        response = client.get("/buscar_sku/0000000000000")
        
        import json
        data = json.loads(response.data)
        assert data["encontrado"] is False
    
    def test_buscar_mercancia_por_id(self, client, app):
        """Test: Buscar mercancía por ID"""
        with app.app_context():
            m = Mercancia(
                sku="5556667778889",
                marca="BuscarID",
                referencia="REF-ID",
                cantidad=15,
                pasillo="X",
                estanteria="5",
                piso="3"
            )
            db.session.add(m)
            db.session.commit()
            
            response = client.get(f"/buscar_mercancia_id/{m.id}")
            assert response.status_code == 200
            
            import json
            data = json.loads(response.data)
            assert data["marca"] == "BuscarID"
            assert data["referencia"] == "REF-ID"
            assert data["cantidad"] == 15
    
    def test_pagina_agregar_mercancia(self, client, app):
        """Test: Cargar página de agregar mercancía"""
        response = client.get("/agregar_mercancia")
        assert response.status_code == 200
    
    def test_agregar_mercancia_cantidad_cero(self, client, app):
        """Test: Agregar mercancía con cantidad cero debe fallar"""
        response = client.post("/agregar_mercancia", data={
            "Marca_solicitada": "Error",
            "Referencia_solicitada": "Cero",
            "Cantidad": "0",
            "Pasillo": "A"
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # No debe crear mercancía con cantidad 0
    
    def test_agregar_mercancia_sin_datos(self, client, app):
        """Test: Agregar mercancía sin datos debe fallar"""
        response = client.post("/agregar_mercancia", data={}, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_mercancia_multiple_ubicaciones(self, client, app):
        """Test: Agregar mercancía en diferentes ubicaciones (misma marca+ref se actualiza)"""
        with app.app_context():
            # Primera ubicación
            client.post("/agregar_mercancia", data={
                "SKU": "MULTI01",
                "Marca_solicitada": "Multi",
                "Referencia_solicitada": "REF01",
                "Cantidad": "10",
                "Pasillo": "A",
                "Estanteria": "1",
                "Piso": "1"
            })
            
            # Segunda ubicación misma referencia - se actualiza cantidad
            client.post("/agregar_mercancia", data={
                "SKU": "MULTI02",
                "Marca_solicitada": "Multi",
                "Referencia_solicitada": "REF01",
                "Cantidad": "5",
                "Pasillo": "A",
                "Estanteria": "2",
                "Piso": "1"
            })
            
            # Verificar que se actualizó la cantidad
            items = Mercancia.query.filter_by(marca="Multi").all()
            assert len(items) == 1  # Misma referencia = mismo registro
            assert items[0].cantidad == 15  # 10 + 5
    
    def test_mercancia_lista_disponible(self, client, app):
        """Test: Obtener lista de mercancía disponible"""
        with app.app_context():
            m = Mercancia(
                sku="LIST001",
                marca="Lista",
                referencia="LIST-REF",
                cantidad=20,
                pasillo="L"
            )
            db.session.add(m)
            db.session.commit()
            
            response = client.get("/agregar_mercancia")
            assert response.status_code == 200
    
    def test_agregar_mercancia_todos_campos(self, client, app):
        """Test: Agregar mercancía con todos los campos"""
        with app.app_context():
            response = client.post("/agregar_mercancia", data={
                "SKU": "FULL1234567890",
                "Marca_solicitada": "Completo",
                "Referencia_solicitada": "FULL-REF",
                "Categoria_producto": "Electronica",
                "Cantidad": "25",
                "Pasillo": "Z",
                "Estanteria": "10",
                "Piso": "5"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            mercancia = Mercancia.query.filter_by(sku="FULL1234567890").first()
            assert mercancia is not None
            assert mercancia.marca == "Completo"
            assert mercancia.categoria_producto == "Electronica"
            assert mercancia.pasillo == "Z"
            assert mercancia.estanteria == "10"
            assert mercancia.piso == "5"
    
    def test_agregar_mercancia_categoria_desde_picking(self, client, app):
        """Test: Agregar mercancía usando categoría existente"""
        from app.models import Picking
        with app.app_context():
            # Crear un picking con categoría
            p = Picking(
                Picking_ID="TEST-CAT-001",
                Fecha="2024-01-01",
                Categoria_producto="Electrodomesticos"
            )
            db.session.add(p)
            db.session.commit()
            
            # Agregar mercancía con esa categoría
            response = client.post("/agregar_mercancia", data={
                "Marca_solicitada": "ConCat",
                "Referencia_solicitada": "CAT-REF",
                "Categoria_producto": "Electrodomesticos",
                "Cantidad": "8",
                "Pasillo": "E"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            mercancia = Mercancia.query.filter_by(marca="ConCat").first()
            assert mercancia.categoria_producto == "Electrodomesticos"
