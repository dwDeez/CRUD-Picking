import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from app.dashboard import get_dataframe_from_db, get_inventario_dataframe
from app import create_app
from app.models import Mercancia

# Simular la lógica del dashboard
app = create_app()

print("Obteniendo datos de la base de datos...")
df = get_dataframe_from_db(app)
df_inv = get_inventario_dataframe(app)

print(f"Filas de pickings: {len(df)}")
print(f"Filas de inventario: {len(df_inv)}")

if df.empty:
    print("ERROR: DataFrame de pickings está vacío.")
    sys.exit(1)

if df_inv.empty:
    print("ADVERTENCIA: DataFrame de inventario está vacío.")

# Procesamiento de datos (similar a create_dashboard)
df.columns = df.columns.str.strip()

for col in ['Picking_ID', 'Fecha', 'Hora_generacion', 'Hora_revision', 'Hora_despacho',
            'Auxiliar', 'Pasillo', 'Estanteria', 'Piso', 'Marca_solicitada', 
            'Referencia_solicitada', 'Categoria_producto']:
    if col not in df.columns:
        df[col] = np.nan

df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
for tcol in ["Hora_generacion", "Hora_revision", "Hora_despacho"]:
    df[tcol] = df[tcol].astype(str).replace({"nan": None, "None": None})

def make_dt(row, date_col, time_col):
    if pd.isna(row[date_col]) or pd.isna(row[time_col]) or not row[time_col]:
        return None
    try:
        dt_str = str(row[date_col]) + " " + str(row[time_col])
        return pd.to_datetime(dt_str, errors="coerce")
    except:
        return None

df["datetime_inicio"] = pd.to_datetime(df.apply(lambda r: make_dt(r, "Fecha", "Hora_generacion"), axis=1), errors="coerce")
df["datetime_revision"] = pd.to_datetime(df.apply(lambda r: make_dt(r, "Fecha", "Hora_revision"), axis=1), errors="coerce")
df["datetime_fin"] = pd.to_datetime(df.apply(lambda r: make_dt(r, "Fecha", "Hora_despacho"), axis=1), errors="coerce")

df["tiempo_proceso"] = (df["datetime_fin"] - df["datetime_inicio"]).dt.total_seconds() / 60.0
df["tiempo_proceso"] = df["tiempo_proceso"].fillna(df["tiempo_proceso"].median(skipna=True))

df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
df["Error_porcentaje"] = pd.to_numeric(df["Error_porcentaje"], errors="coerce").fillna(0)

df["Marca_Referencia"] = df["Marca_solicitada"].fillna("").astype(str).str.strip() + " | " + df["Referencia_solicitada"].fillna("").astype(str).str.strip()
df["Marca_Referencia"] = df["Marca_Referencia"].str.strip().replace({"|": ""})

for c in ["Pasillo", "Estanteria", "Piso", "Auxiliar", "Categoria_producto"]:
    df[c] = df[c].fillna("Desconocido").astype(str)

df["fecha_dia"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.floor("D")

# Filtros vacíos (simular estado inicial)
marca_ref_values = None
aux_values = None
pasillo_values = None
categoria_values = None
start_date = df['fecha_dia'].min()
end_date = df['fecha_dia'].max()

print(f"Rango de fechas: {start_date} a {end_date}")

# Aplicar filtros (inicialmente vacíos o todo)
dff = df.copy()
if start_date:
    dff = dff[dff['fecha_dia'] >= pd.to_datetime(start_date)]
if end_date:
    dff = dff[dff['fecha_dia'] <= pd.to_datetime(end_date)]

print(f"Filas tras filtros de fecha: {len(dff)}")

# Generar Top 15
if not dff.empty:
    top = (dff.groupby(['Marca_Referencia','Categoria_producto'], as_index=False)
             .agg(Cantidad_total=('Cantidad','sum'),
                  Error_promedio=('Error_porcentaje','mean'))
             .sort_values('Cantidad_total', ascending=False)
             .head(15))
    print(f"Top 15 generado. Total filas: {len(top)}")
    print(top.head())
else:
    print("No hay datos para los filtros seleccionados (dff vacío)")

# Generar Time Series
if not dff.empty:
    ts_sales = dff.groupby('fecha_dia', as_index=False).agg(Cantidad_diaria=('Cantidad','sum'))
    print(f"Time series generado. Total filas: {len(ts_sales)}")
    print(ts_sales.head())
else:
    print("No hay datos para time series")

# Inventario
with app.app_context():
    mercancias = Mercancia.query.filter(Mercancia.cantidad > 0).all()
    total_unidades = sum(m.cantidad or 0 for m in mercancias)
    print(f"Total unidades en inventario: {total_unidades}")

# Verificar si los dataframes necesarios para los callbacks están vacíos
if df.empty:
    print("ERROR CRITICO: El DataFrame de pickings está vacío después del procesamiento.")
elif len(df) < 5:
    print("ADVERTENCIA: El DataFrame de pickings tiene muy pocas filas.")
else:
    print("El DataFrame de pickings parece correcto.")

if df_inv.empty:
    print("ADVERTENCIA: El DataFrame de inventario está vacío.")
else:
    print("El DataFrame de inventario parece correcto.")

print("Prueba finalizada.")
