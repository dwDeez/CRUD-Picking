"""
Tests para el módulo Dashboard
"""
import pytest
import pandas as pd
from app import create_app, db
from app.models import Picking, PickingItem


class TestDashboard:
    """Tests para el dashboard operativo"""
    
    def test_get_dataframe_from_db_vacio(self, app):
        """Test: DataFrame vacío cuando no hay datos"""
        from app.dashboard import get_dataframe_from_db
        df = get_dataframe_from_db(app)
        assert df.empty, f"Expected empty DataFrame but got {len(df)} rows"
    
    def test_get_dataframe_from_db_con_datos(self, app):
        """Test: DataFrame con pickings en DB"""
        with app.app_context():
            picking = Picking(
                Picking_ID="P001",
                Fecha="2024-01-15",
                Hora_generacion="08:00:00",
                Hora_revision="09:00:00",
                Hora_despacho="10:00:00",
                Auxiliar="Juan",
                Cantidad_pickings_por_auxiliar=1,
                Pasillo="A",
                Estanteria="1",
                Piso="1",
                Marca_solicitada="Samsung",
                Referencia_solicitada="UN55BU8000",
                Categoria_producto="Televisores",
                Cantidad=5,
                Error_porcentaje=0.0,
                modified_by="test",
                modified_at="2024-01-15 10:00:00"
            )
            db.session.add(picking)
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            
            assert not df.empty
            assert len(df) == 1
            assert df.iloc[0]["Picking_ID"] == "P001"
            assert df.iloc[0]["Marca_solicitada"] == "Samsung"
    
    def test_get_dataframe_from_db_con_items(self, app):
        """Test: DataFrame incluye items de picking"""
        with app.app_context():
            picking = Picking(
                Picking_ID="P002",
                Fecha="2024-01-16",
                Hora_generacion="08:00:00",
                modified_by="test",
                modified_at="2024-01-16 10:00:00"
            )
            db.session.add(picking)
            
            item1 = PickingItem(
                Picking_ID="P002",
                tipo="Televisores",
                marca="LG",
                referencia="55UP7750",
                cantidad=3,
                Pasillo="A",
                Estanteria="1",
                Piso="1"
            )
            item2 = PickingItem(
                Picking_ID="P002",
                tipo="Audio",
                marca="Sony",
                referencia="HT-S40R",
                cantidad=2,
                Pasillo="B",
                Estanteria="2",
                Piso="1"
            )
            db.session.add(item1)
            db.session.add(item2)
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            
            assert len(df) == 2
            assert df.iloc[0]["Marca_solicitada"] == "LG"
            assert df.iloc[1]["Marca_solicitada"] == "Sony"
    
    def test_create_dashboard_sin_datos(self, app):
        """Test: Dashboard se crea con DataFrame vacío"""
        with app.app_context():
            from app.dashboard import create_dashboard
            dash_app = create_dashboard()
            assert dash_app is not None
            assert dash_app.layout is not None
    
    def test_create_dashboard_con_datos(self, app):
        """Test: Dashboard se crea correctamente con datos"""
        with app.app_context():
            picking = Picking(
                Picking_ID="P003",
                Fecha="2024-01-17",
                Hora_generacion="08:00:00",
                Hora_revision="09:30:00",
                Hora_despacho="11:00:00",
                Auxiliar="Maria",
                Cantidad_pickings_por_auxiliar=2,
                Pasillo="C",
                Estanteria="3",
                Piso="2",
                Marca_solicitada="Mabe",
                Referencia_solicitada="RMAV20",
                Categoria_producto="Refrigeradores",
                Cantidad=10,
                Error_porcentaje=5.0,
                modified_by="test",
                modified_at="2024-01-17 11:00:00"
            )
            db.session.add(picking)
            db.session.commit()
            
            from app.dashboard import create_dashboard
            dash_app = create_dashboard()
            assert dash_app is not None
            assert dash_app.layout is not None
    
    def test_dashboard_calculo_tiempo_proceso(self, app):
        """Test: Cálculo de tiempo de proceso"""
        with app.app_context():
            picking = Picking(
                Picking_ID="P004",
                Fecha="2024-01-18",
                Hora_generacion="08:00:00",
                Hora_revision="09:00:00",
                Hora_despacho="10:30:00",
                Auxiliar="Pedro",
                Cantidad_pickings_por_auxiliar=1,
                Pasillo="D",
                Estanteria="4",
                Piso="1",
                Marca_solicitada="Whirlpool",
                Referencia_solicitada="WRT311",
                Categoria_producto="Refrigeradores",
                Cantidad=3,
                Error_porcentaje=0.0,
                modified_by="test",
                modified_at="2024-01-18 10:30:00"
            )
            db.session.add(picking)
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
            df["datetime_inicio"] = pd.to_datetime(df["Fecha"].astype(str) + " " + df["Hora_generacion"].astype(str), errors="coerce")
            df["datetime_fin"] = pd.to_datetime(df["Fecha"].astype(str) + " " + df["Hora_despacho"].astype(str), errors="coerce")
            df["tiempo_proceso"] = (df["datetime_fin"] - df["datetime_inicio"]).dt.total_seconds() / 60.0
            
            assert df.iloc[0]["tiempo_proceso"] == 150.0
    
    def test_dashboard_fechas_min_max(self, app):
        """Test: Fechas min y max correctas"""
        with app.app_context():
            p1 = Picking(Picking_ID="P005", Fecha="2024-01-01", modified_by="test", modified_at="2024-01-01 10:00:00")
            p2 = Picking(Picking_ID="P006", Fecha="2024-01-31", modified_by="test", modified_at="2024-01-31 10:00:00")
            db.session.add_all([p1, p2])
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            df["fecha_dia"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.floor("D")
            
            min_date = df["fecha_dia"].min()
            max_date = df["fecha_dia"].max()
            
            assert min_date is not pd.NaT
            assert max_date is not pd.NaT
    
    def test_dashboard_campos_requeridos(self, app):
        """Test: DataFrame tiene todos los campos requeridos"""
        with app.app_context():
            picking = Picking(
                Picking_ID="P_TEST",
                Fecha="2024-01-15",
                Hora_generacion="08:00:00",
                Hora_revision="09:00:00",
                Hora_despacho="10:00:00",
                Auxiliar="Juan",
                Cantidad_pickings_por_auxiliar=1,
                Pasillo="A",
                Estanteria="1",
                Piso="1",
                Marca_solicitada="Samsung",
                Referencia_solicitada="UN55BU8000",
                Categoria_producto="Televisores",
                Cantidad=5,
                Error_porcentaje=0.0,
                modified_by="test",
                modified_at="2024-01-15 10:00:00"
            )
            db.session.add(picking)
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            
            required_cols = [
                'Picking_ID', 'Fecha', 'Hora_generacion', 'Hora_revision', 'Hora_despacho',
                'Auxiliar', 'Cantidad_pickings_por_auxiliar', 'Pasillo', 'Estanteria', 'Piso',
                'Marca_solicitada', 'Referencia_solicitada', 'Categoria_producto', 
                'Cantidad', 'Error_porcentaje', 'modified_at'
            ]
            
            for col in required_cols:
                assert col in df.columns, f"Columna {col} faltante"
    
    def test_dashboard_marca_referencia(self, app):
        """Test: Campo Marca_Referencia generado correctamente"""
        with app.app_context():
            picking = Picking(
                Picking_ID="P007",
                Fecha="2024-02-01",
                Marca_solicitada="Samsung",
                Referencia_solicitada="UN55BU8000",
                modified_by="test",
                modified_at="2024-02-01 10:00:00"
            )
            db.session.add(picking)
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            
            df["Marca_Referencia"] = df["Marca_solicitada"].fillna("").astype(str).str.strip() + " | " + df["Referencia_solicitada"].fillna("").astype(str).str.strip()
            
            assert "Samsung | UN55BU8000" in df.iloc[0]["Marca_Referencia"]
    
    def test_dashboard_cantidad_numerica(self, app):
        """Test: Cantidad convertida a numérico"""
        with app.app_context():
            picking = Picking(
                Picking_ID="P008",
                Fecha="2024-02-02",
                Cantidad="15",
                modified_by="test",
                modified_at="2024-02-02 10:00:00"
            )
            db.session.add(picking)
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            
            df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
            
            assert df.iloc[0]["Cantidad"] == 15
    
    def test_dashboard_error_porcentaje(self, app):
        """Test: Error_porcentaje convertido a numérico"""
        with app.app_context():
            picking = Picking(
                Picking_ID="P009",
                Fecha="2024-02-03",
                Error_porcentaje="12.5",
                modified_by="test",
                modified_at="2024-02-03 10:00:00"
            )
            db.session.add(picking)
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            
            df["Error_porcentaje"] = pd.to_numeric(df["Error_porcentaje"], errors="coerce").fillna(0)
            
            assert df.iloc[0]["Error_porcentaje"] == 12.5
    
    def test_dashboard_multiple_pickings_mismo_dia(self, app):
        """Test: Múltiples pickings mismo día"""
        with app.app_context():
            for i in range(3):
                picking = Picking(
                    Picking_ID=f"P010-{i}",
                    Fecha="2024-02-04",
                    Hora_generacion=f"0{i}:00:00",
                    modified_by="test",
                    modified_at="2024-02-04 10:00:00"
                )
                db.session.add(picking)
            db.session.commit()
            
            from app.dashboard import get_dataframe_from_db
            df = get_dataframe_from_db(app)
            
            assert len(df) == 3
            assert df["Fecha"].nunique() == 1
