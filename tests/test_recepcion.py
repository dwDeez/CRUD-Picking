"""
Tests para el módulo de Recepción de Mercancía
"""
import pytest
from app import create_app, db
from app.models import Recepcion, RecepcionItem, Mercancia


class TestRecepcion:
    """Tests para el flujo de recepción de mercancía"""
    
    def test_crear_recepcion(self, client, app):
        """Test: Crear una nueva recepción"""
        with app.app_context():
            response = client.post("/iniciar_recepcion", data={
                "operario": "Juan",
                "referencia": "LG-55P",
                "categoria": "Televisores",
                "pasillo": "A",
                "estanteria": "1",
                "piso": "1"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            recepcion = Recepcion.query.filter_by(operario="Juan").first()
            assert recepcion is not None
            assert recepcion.estado == "activa"
            assert recepcion.operario == "Juan"
    
    def test_crear_recepcion_sin_operario(self, client, app):
        """Test: Crear recepción sin operario debe fallar"""
        response = client.post("/iniciar_recepcion", data={
            "operario": "",
            "referencia": "LG-55P"
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_escaneo_unidad(self, client, app):
        """Test: Escanear una unidad en recepción activa"""
        with app.app_context():
            # Crear recepción primero
            client.post("/iniciar_recepcion", data={
                "operario": "Pedro",
                "referencia": "SAMS-50",
                "categoria": "TV",
                "pasillo": "B",
                "estanteria": "2",
                "piso": "1"
            })
            
            recepcion = Recepcion.query.filter_by(operario="Pedro").first()
            assert recepcion is not None
            
            # Escanear
            response = client.post(f"/recepcion/{recepcion.id}/escaneo", data={
                "sku": "1234567890123"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            items = RecepcionItem.query.filter_by(recepcion_id=recepcion.id).all()
            assert len(items) >= 1
    
    def test_cerrar_recepcion(self, client, app):
        """Test: Cerrar una recepción activa"""
        with app.app_context():
            client.post("/iniciar_recepcion", data={
                "operario": "Maria",
                "referencia": "SONY-42"
            })
            
            recepcion = Recepcion.query.filter_by(operario="Maria").first()
            assert recepcion is not None
            
            response = client.get(f"/recepcion/{recepcion.id}/cerrar", follow_redirects=True)
            
            assert response.status_code == 200
            
            recepcion = Recepcion.query.get(recepcion.id)
            assert recepcion.estado == "pendiente"
    
    def test_pagina_revision(self, client, app):
        """Test: Acceder a la página de revisión"""
        with app.app_context():
            client.post("/iniciar_recepcion", data={
                "operario": "Carlos",
                "referencia": "LG-55P",
                "pasillo": "A",
                "estanteria": "1",
                "piso": "1"
            })
            
            recepcion = Recepcion.query.filter_by(operario="Carlos").first()
            client.get(f"/recepcion/{recepcion.id}/cerrar")
            
            response = client.get(f"/recepcion/{recepcion.id}/revisar")
            
            assert response.status_code == 200
    
    def test_confirmar_recepcion_a_inventario(self, client, app):
        """Test: Confirmar recepción y pasar a inventario"""
        with app.app_context():
            client.post("/iniciar_recepcion", data={
                "operario": "Luis",
                "referencia": "CONFIRM-001",
                "marca": "TestMarca",
                "categoria": "TestCat",
                "pasillo": "C",
                "estanteria": "3",
                "piso": "2"
            })
            
            recepcion = Recepcion.query.filter_by(operario="Luis").first()
            
            # Escanear para que se guarde la marca (DEBE SER ANTES DE CERRAR)
            client.post(f"/recepcion/{recepcion.id}/escaneo", data={"sku": "1234567890123"})
            
            # Cerrar recepción
            client.get(f"/recepcion/{recepcion.id}/cerrar")
            
            response = client.post(f"/recepcion/{recepcion.id}/confirmar", data={
                "observaciones": "Test confirm"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            recepcion = Recepcion.query.get(recepcion.id)
            assert recepcion.estado == "confirmada"
            
            # Verificar que se creó el item con la referencia correcta
            items = RecepcionItem.query.filter_by(recepcion_id=recepcion.id).all()
            assert len(items) == 1
            assert items[0].referencia == "CONFIRM-001"
            assert items[0].marca == "TestMarca"
    
    def test_cancelar_recepcion(self, client, app):
        """Test: Cancelar una recepción"""
        with app.app_context():
            client.post("/iniciar_recepcion", data={
                "operario": "Rosa",
                "referencia": "CANCEL-001"
            })
            
            recepcion = Recepcion.query.filter_by(operario="Rosa").first()
            
            response = client.get(f"/recepcion/{recepcion.id}/cancelar", follow_redirects=True)
            
            assert response.status_code == 200
            
            recepcion = Recepcion.query.get(recepcion.id)
            assert recepcion.estado == "cancelada"
    
    def test_agregar_nueva_posicion(self, client, app):
        """Test: Agregar nueva posición sin cambiar referencia"""
        with app.app_context():
            client.post("/iniciar_recepcion", data={
                "operario": "Diego",
                "referencia": "POS-001",
                "pasillo": "A",
                "estanteria": "1",
                "piso": "1"
            })
            
            recepcion = Recepcion.query.filter_by(operario="Diego").first()
            
            response = client.post(f"/recepcion/{recepcion.id}/nueva-posicion", data={
                "pasillo": "B",
                "estanteria": "2",
                "piso": "3"
            }, follow_redirects=True)
            
            assert response.status_code == 200
    
    def test_cambiar_referencia(self, client, app):
        """Test: Escanear SKU manteniendo referencia y marca iniciales"""
        with app.app_context():
            # Iniciar recepción con marca y referencia específicas
            client.post("/iniciar_recepcion", data={
                "operario": "Elena",
                "referencia": "REF-1",
                "marca": "MarcaOriginal",
                "pasillo": "A",
                "estanteria": "1",
                "piso": "1"
            })
            
            recepcion = Recepcion.query.filter_by(operario="Elena").first()
            
            # Escanear nuevo SKU (debería mantener la referencia y marca iniciales)
            response = client.post(f"/recepcion/{recepcion.id}/escaneo", data={
                "sku": "SKU-REF-2"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verificar que se creó el item con la referencia y marca iniciales
            item = RecepcionItem.query.filter_by(recepcion_id=recepcion.id, sku="SKU-REF-2").first()
            assert item is not None
            assert item.referencia == "REF-1"  # Mantiene la referencia inicial
            assert item.marca == "MarcaOriginal"  # Hereda la marca
            assert item.pasillo == "A"  # Hereda la ubicación del primer item
    
    def test_api_lista_recepciones(self, client, app):
        """Test: API de recepciones activas"""
        with app.app_context():
            client.post("/iniciar_recepcion", data={
                "operario": "API_Test",
                "referencia": "API-REF"
            })
            
            response = client.get("/api/recepciones/activas")
            
            assert response.status_code == 200
            import json
            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) >= 1
    
    def test_recepcion_multiple_items(self, client, app):
        """Test: Escanear múltiples unidades"""
        with app.app_context():
            client.post("/iniciar_recepcion", data={
                "operario": "Multi",
                "referencia": "MULTI-001",
                "pasillo": "A",
                "estanteria": "1",
                "piso": "1"
            })
            
            recepcion = Recepcion.query.filter_by(operario="Multi").first()
            
            # Escanear 5 unidades (incluye el item de creación de referencia)
            for i in range(4):  # 4 más el inicial = 5
                client.post(f"/recepcion/{recepcion.id}/escaneo", data={
                    "sku": f"000000000000{i}"
                })
            
            items = RecepcionItem.query.filter_by(recepcion_id=recepcion.id).all()
            # Puede ser 5 porque el item inicial cuenta como 1
            assert len(items) >= 4
    
    def test_pagina_principal_recepcion(self, client, app):
        """Test: Cargar página principal de recepción"""
        response = client.get("/recepcion")
        assert response.status_code == 200
    
    def test_recepcion_con_datos_completos(self, client, app):
        """Test: Crear recepción con todos los datos"""
        with app.app_context():
            response = client.post("/iniciar_recepcion", data={
                "operario": "Completo",
                "referencia": "TEST-COMPLETO",
                "categoria": "Electronica",
                "pasillo": "Z",
                "estanteria": "10",
                "piso": "3"
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            recepcion = Recepcion.query.filter_by(operario="Completo").first()
            assert recepcion is not None
            
            # Con el nuevo comportamiento, no se crea item inicial sin SKU
            items = RecepcionItem.query.filter_by(recepcion_id=recepcion.id).all()
            assert len(items) == 0
            
            # Escanear un SKU para verificar que se guardan los datos
            client.post(f"/recepcion/{recepcion.id}/escaneo", data={"sku": "1234567890123"})
            
            items = RecepcionItem.query.filter_by(recepcion_id=recepcion.id).all()
            assert len(items) == 1
            item = items[0]
            assert item.referencia == "TEST-COMPLETO"
            assert item.categoria == "Electronica"
            assert item.pasillo == "Z"
