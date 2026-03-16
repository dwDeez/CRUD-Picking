import os
import random
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import dash

from app import db
from app.models import Picking, PickingItem, Mercancia, PickingCSV, PickingItemCSV
from app import create_app


def get_inventario_dataframe(app=None):
    """Obtiene los datos de inventario desde la tabla Mercancia y Recepciones activas"""
    from app.models import Mercancia, Recepcion, RecepcionItem
    from app import create_app
    if app is None:
        app = create_app()
    with app.app_context():
        mercancias = Mercancia.query.all()
        data = []
        
        for m in mercancias:
            data.append({
                'id': m.id,
                'sku': m.sku or '',
                'marca': m.marca or '',
                'referencia': m.referencia or '',
                'cantidad': m.cantidad or 0,
                'categoria_producto': m.categoria_producto or '',
                'pasillo': m.pasillo or '',
                'estanteria': m.estanteria or '',
                'piso': m.piso or '',
                'ubicacion': f"{m.pasillo or ''}-{m.estanteria or ''}-{m.piso or ''}".strip('-'),
                'fecha_ingreso': m.fecha_ingreso or '',
                'origen': 'Inventario',
            })
        
        recepciones = Recepcion.query.filter(Recepcion.estado.in_(['activa', 'pendiente'])).all()
        for r in recepciones:
            items = RecepcionItem.query.filter_by(recepcion_id=r.id).all()
            for item in items:
                if not item.confirmado:
                    data.append({
                        'id': item.id,
                        'sku': item.sku or '',
                        'marca': item.marca or '',
                        'referencia': item.referencia or '',
                        'cantidad': 1,
                        'categoria_producto': item.categoria or '',
                        'pasillo': item.pasillo or '',
                        'estanteria': item.estanteria or '',
                        'piso': item.piso or '',
                        'ubicacion': f"{item.pasillo or ''}-{item.estanteria or ''}-{item.piso or ''}".strip('-'),
                        'fecha_ingreso': item.timestamp or '',
                        'origen': f'Recepción #{r.id}',
                    })
        
        df_inv = pd.DataFrame(data)
        return df_inv


def get_dataframe_from_db(app=None):
    if app is None:
        app = create_app()
    with app.app_context():
        pickings = Picking.query.all()
        data = []
        for p in pickings:
            row = {
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
                'Error_porcentaje': p.Error_porcentaje,
                'modified_at': p.modified_at,
            }
            if p.items:
                for item in p.items:
                    row_item = row.copy()
                    row_item['Marca_solicitada'] = item.marca
                    row_item['Referencia_solicitada'] = item.referencia
                    row_item['Categoria_producto'] = item.tipo
                    row_item['Cantidad'] = item.cantidad
                    data.append(row_item)
            else:
                data.append(row)
        
        df = pd.DataFrame(data)
        return df


def create_dashboard(server=None):
    # Use the server's app context if available
    app = server if server else None
    df = get_dataframe_from_db(app)
    df_inv = get_inventario_dataframe(app)
    print(f"DEBUG create_dashboard: df shape: {df.shape}, df_inv shape: {df_inv.shape}")
    
    if df_inv.empty:
        df_inv = pd.DataFrame(columns=['id', 'sku', 'marca', 'referencia', 'cantidad', 'categoria_producto', 'pasillo', 'estanteria', 'piso', 'ubicacion', 'fecha_ingreso'])
    
    # Initialize options from current data
    inv_categoria_options = [{'label': c, 'value': c} for c in sorted(df_inv['categoria_producto'].dropna().unique())] if not df_inv.empty else []
    inv_marca_options = [{'label': m, 'value': m} for m in sorted(df_inv['marca'].dropna().unique())] if not df_inv.empty else []
    
    if df.empty:
        df = pd.DataFrame(columns=[
            'Picking_ID', 'Fecha', 'Hora_generacion', 'Hora_revision', 'Hora_despacho',
            'Auxiliar', 'Cantidad_pickings_por_auxiliar', 'Pasillo', 'Estanteria', 'Piso',
            'Marca_solicitada', 'Referencia_solicitada', 'Categoria_producto', 'Cantidad', 
            'Error_porcentaje', 'modified_at'
        ])
    
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

    marca_ref_options = [{'label': mr, 'value': mr} for mr in sorted(df['Marca_Referencia'].dropna().unique())]
    aux_options = [{'label': a, 'value': a} for a in sorted(df['Auxiliar'].dropna().unique())]
    pasillo_options = [{'label': p, 'value': p} for p in sorted(df['Pasillo'].dropna().unique())]
    categoria_options = [{'label': c, 'value': c} for c in sorted(df['Categoria_producto'].dropna().unique())]

    min_date = df['fecha_dia'].min()
    max_date = df['fecha_dia'].max()

    def empty_figure(message="No hay datos para los filtros seleccionados"):
        fig = go.Figure()
        fig.add_annotation(text=message, xref="paper", yref="paper", showarrow=False, font=dict(size=14))
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(margin=dict(t=40, b=40, l=40, r=40))
        return fig

    if server:
        dash_app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP], url_base_pathname='/dashboard/')
    else:
        dash_app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    app = dash_app

    app.layout = dbc.Container([
        html.H3("Dashboard Operativo - Importadora Electrodomésticos", style={'marginTop': 10}),
        dbc.Row([
            dbc.Col([html.Label("Marca + Referencia"), dcc.Dropdown(id='marca_ref_dropdown', options=marca_ref_options, multi=True)], md=3),
            dbc.Col([html.Label("Auxiliar"), dcc.Dropdown(id='aux_dropdown', options=aux_options, multi=True)], md=2),
            dbc.Col([html.Label("Pasillo"), dcc.Dropdown(id='pasillo_dropdown', options=pasillo_options, multi=True)], md=2),
            dbc.Col([html.Label("Categoría producto"), dcc.Dropdown(id='categoria_dropdown', options=categoria_options, multi=True)], md=2),
            dbc.Col([html.Label("Rango de fechas"), dcc.DatePickerRange(id='date_picker', start_date=min_date, end_date=max_date, display_format='YYYY-MM-DD')], md=3),
        ], align='center', className='mb-2'),

        dcc.Interval(id='interval_refresh', interval=60*1000, n_intervals=1),
        dcc.Store(id='store_selected_picking', storage_type='session'),
        
        dcc.Tabs(id='tabs', value='tab_general', children=[
            dcc.Tab(label='General', value='tab_general'),
            dcc.Tab(label='Ventas', value='tab_ventas'),
            dcc.Tab(label='Inventario', value='tab_inventario'),
            dcc.Tab(label='Métricas', value='tab_ubicacion'),
            dcc.Tab(label='Auxiliares', value='tab_auxiliares'),
        ], persistence=True),

        html.Div(id='graphs_container', children=[
            dbc.Row([
                dbc.Col(dcc.Graph(id='top15_bar'), id='col_top15', className='col-md-6'),
                dbc.Col(dcc.Graph(id='timeseries_sales'), id='col_ts_sales', className='col-md-6'),
            ], className='mb-3'),
            dbc.Row([
                dbc.Col(dcc.Graph(id='inventory_gauge'), id='col_inventory', className='col-md-6'),
                dbc.Col(dcc.Graph(id='scatter_error_time'), id='col_scatter', className='col-md-6'),
            ], className='mb-3'),
            dbc.Row([
                dbc.Col(dcc.Graph(id='heatmap_bodega'), id='col_heat', className='col-md-6'),
                dbc.Col(dcc.Graph(id='aux_comparison'), id='col_aux', className='col-md-6'),
            ], className='mb-3'),
            dbc.Row([
                dbc.Col(dcc.Graph(id='scatter_error_time_aux'), id='col_scatter_aux', className='col-md-12'),
            ], className='mb-3'),
            dbc.Row([
                dbc.Col(
                    html.Div([
                        html.Label("Picking (selección única)"),
                        dcc.Dropdown(id='picking_dropdown', options=[], placeholder="Selecciona un Picking_ID", multi=False)
                    ]),
                    id='col_pickings_dropdown',
                    className='col-md-8'
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(html.B("Detalle del Picking seleccionado")),
                        dbc.CardBody([
                            html.Div(id='picking_detail', children="Selecciona un picking en el dropdown para ver detalles.")
                        ])
                    ]),
                    id='col_picking_detail',
                    className='col-md-4'
                )
            ], className='mb-3'),
        ]),

        html.Hr(),
        
        html.Div(id='inventory_footer', children=[
            html.Hr(),
            html.H5("Control de Inventario", className="mt-3"),
            dbc.Row([
                dbc.Col([html.Label("Categoría"), dcc.Dropdown(id='inv_cat_dropdown', options=inv_categoria_options, multi=True, placeholder="Filtrar por categoría")], md=2),
                dbc.Col([html.Label("Marca"), dcc.Dropdown(id='inv_marca2_dropdown', options=inv_marca_options, multi=True, placeholder="Filtrar por marca")], md=2),
                dbc.Col([html.Label("Referencia"), dcc.Input(id='inv_ref_input', placeholder="Buscar referencia...", type='text')], md=2),
                dbc.Col([html.Label("Posición"), dcc.Dropdown(id='inv_posicion_dropdown', options=[], multi=True, placeholder="Filtrar por posición")], md=3),
                dbc.Col([dbc.Button("🔄 Actualizar", id='inv_refresh_btn', color='primary', className='mt-4')], md=3),
            ], className='mb-2'),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(id='inv_total_unidades', className="text-primary"),
                            html.P("Total Unidades")
                        ])
                    ])
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(id='inv_total_skus', className="text-success"),
                            html.P("SKUs Diferentes")
                        ])
                    ])
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(id='inv_total_categorias', className="text-info"),
                            html.P("Categorías")
                        ])
                    ])
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(id='inv_total_ubicaciones', className="text-warning"),
                            html.P("Ubicaciones")
                        ])
                    ])
                ], md=3),
            ], className='mb-2'),
            html.Div(id='inv_detalle_tabla')
        ]),
        
        html.Div(id='diagnostic', style={'fontFamily': 'monospace', 'whiteSpace': 'pre-wrap'}),
        dcc.Store(id='store_filtered_df')
    ], fluid=True)

    @dash_app.callback(
        Output('col_top15', 'className'),
        Output('col_ts_sales', 'className'),
        Output('col_inventory', 'className'),
        Output('col_scatter', 'className'),
        Output('col_heat', 'className'),
        Output('col_aux', 'className'),
        Output('col_scatter_aux', 'className'),
        Output('col_pickings_dropdown', 'className'),
        Output('col_picking_detail', 'className'),
        Input('tabs', 'value')
    )
    def layout_by_tab(tab_value):
        if tab_value == 'tab_general':
            return ('col-md-6','col-md-6','col-md-6','col-md-6','col-md-6','col-md-6','d-none','col-md-8','col-md-4')
        if tab_value == 'tab_ventas':
            return ('d-none','col-12','d-none','d-none','d-none','d-none','d-none','d-none','d-none')
        if tab_value == 'tab_inventario':
            return ('d-none','d-none','col-12','d-none','d-none','d-none','d-none','d-none','d-none')
        if tab_value == 'tab_ubicacion':
            return ('d-none','d-none','d-none','d-none','col-12','d-none','d-none','d-none','d-none')
        if tab_value == 'tab_auxiliares':
            return ('d-none','d-none','d-none','d-none','d-none','col-12','col-12','d-none','d-none')
        return ('col-md-6','col-md-6','col-md-6','col-md-6','col-md-6','col-md-6','d-none','col-md-8','col-md-4')

    @dash_app.callback(
        Output('top15_bar','figure'),
        Output('timeseries_sales','figure'),
        Output('inventory_gauge','figure'),
        Output('scatter_error_time','figure'),
        Output('heatmap_bodega','figure'),
        Output('aux_comparison','figure'),
        Output('scatter_error_time_aux','figure'),
        Output('picking_dropdown','options'),
        Output('picking_dropdown','value'),
        Output('marca_ref_dropdown','options'),
        Output('marca_ref_dropdown','value'),
        Output('diagnostic','children'),
        Output('store_filtered_df','data'),
        Input('marca_ref_dropdown','value'),
        Input('aux_dropdown','value'),
        Input('pasillo_dropdown','value'),
        Input('categoria_dropdown','value'),
        Input('date_picker','start_date'),
        Input('date_picker','end_date'),
        Input('interval_refresh','n_intervals'),
        Input('top15_bar','clickData'),
        State('store_selected_picking','data'),
        State('marca_ref_dropdown','options')
    )
    def update_all(marca_ref_values, aux_values, pasillo_values, categoria_values, start_date, end_date, n_intervals, bar_click, store_selected_picking_data, marca_ref_options_state):
        # Debug: print callback invocation
        print(f"DEBUG update_all called: n_intervals={n_intervals}, marca_ref_values={marca_ref_values}, aux_values={aux_values}")
        # Ensure we're in the correct app context
        with dash_app.server.app_context():
            # Reload data from database on each callback execution
            df_current = get_dataframe_from_db(dash_app.server)
            print(f"DEBUG: df shape: {df_current.shape}")
            
            # Process the dataframe to add required columns
            df_current["Fecha"] = pd.to_datetime(df_current["Fecha"], errors="coerce")
            df_current["Marca_Referencia"] = df_current["Marca_solicitada"].fillna("").astype(str).str.strip() + " | " + df_current["Referencia_solicitada"].fillna("").astype(str).str.strip()
            df_current["Marca_Referencia"] = df_current["Marca_Referencia"].str.strip().replace({"|": ""})
            df_current["fecha_dia"] = pd.to_datetime(df_current["Fecha"], errors="coerce").dt.floor("D")
            
            # Add tiempo_proceso calculation (needed for scatter plot)
            # Use Hora_revision if Hora_despacho is not available
            def make_dt(row, date_col, time_col):
                if pd.isna(row[date_col]) or pd.isna(row[time_col]) or not row[time_col]:
                    return None
                try:
                    dt_str = str(row[date_col]) + " " + str(row[time_col])
                    return pd.to_datetime(dt_str, errors="coerce")
                except:
                    return None
            
            df_current["datetime_inicio"] = pd.to_datetime(df_current.apply(lambda r: make_dt(r, "Fecha", "Hora_generacion"), axis=1), errors="coerce")
            # Try Hora_despacho first, then Hora_revision
            df_current["datetime_fin"] = pd.to_datetime(df_current.apply(lambda r: make_dt(r, "Fecha", "Hora_despacho"), axis=1), errors="coerce")
            if df_current["datetime_fin"].isna().all():
                df_current["datetime_fin"] = pd.to_datetime(df_current.apply(lambda r: make_dt(r, "Fecha", "Hora_revision"), axis=1), errors="coerce")
            
            df_current["tiempo_proceso"] = (df_current["datetime_fin"] - df_current["datetime_inicio"]).dt.total_seconds() / 60.0
            # If still all NaN, generate random times between 10 and 120 minutes
            if df_current["tiempo_proceso"].isna().all():
                df_current["tiempo_proceso"] = random.uniform(10, 120)
            else:
                df_current["tiempo_proceso"] = df_current["tiempo_proceso"].fillna(df_current["tiempo_proceso"].median(skipna=True))
            
            dff = df_current.copy()
            print(f"DEBUG: dff shape before filters: {dff.shape}")
        
        # Apply filters outside the app context (dff is already a copy)
        if start_date:
            dff = dff[dff['fecha_dia'] >= pd.to_datetime(start_date)]
        if end_date:
            dff = dff[dff['fecha_dia'] <= pd.to_datetime(end_date)]
        if aux_values:
            dff = dff[dff['Auxiliar'].isin(aux_values)]
        if pasillo_values:
            dff = dff[dff['Pasillo'].isin(pasillo_values)]
        if categoria_values:
            dff = dff[dff['Categoria_producto'].isin(categoria_values)]
        if aux_values:
            dff = dff[dff['Auxiliar'].isin(aux_values)]
        if pasillo_values:
            dff = dff[dff['Pasillo'].isin(pasillo_values)]
        if categoria_values:
            dff = dff[dff['Categoria_producto'].isin(categoria_values)]

        clicked_mr = None
        if bar_click and isinstance(bar_click, dict):
            try:
                clicked_mr = bar_click['points'][0].get('x')
            except:
                clicked_mr = None

        if marca_ref_values:
            dff = dff[dff['Marca_Referencia'].isin(marca_ref_values)]
        elif clicked_mr:
            dff = dff[dff['Marca_Referencia'] == clicked_mr]
            marca_ref_values = [clicked_mr]

        diag_lines = [
            f"Filas totales: {df_current.shape[0]}",
            f"Filas tras filtros: {dff.shape[0]}",
            f"Rango de fechas datos: {str(df_current['fecha_dia'].min())} -> {str(df_current['fecha_dia'].max())}",
            f"Filtros aplicados -> Marca_ref: {marca_ref_values}, Auxiliar: {aux_values}, Pasillo: {pasillo_values}, Categoria: {categoria_values}"
        ]
        diagnostic_text = "\n".join(diag_lines)

        if dff.empty:
            empty_fig = empty_figure("No hay datos para los filtros seleccionados")
            all_mr = sorted(df_current['Marca_Referencia'].dropna().unique())
            options_mr = [{'label': mr, 'value': mr} for mr in all_mr]
            value_mr = marca_ref_values if marca_ref_values else []
            picking_options = []
            picking_value = None
            store_filtered = []
            
            # Generate inventory figure even when picking data is empty
            mercancias = Mercancia.query.filter(Mercancia.cantidad > 0).all()
            total_unidades = sum(m.cantidad or 0 for m in mercancias)
            # Count unique SKUs (SKU + reference) instead of total rows
            skus_unicos = set()
            for m in mercancias:
                # Use SKU if available, otherwise use reference
                sku_value = m.sku.strip() if m.sku else None
                ref_value = m.referencia.strip() if m.referencia else None
                
                # Prefer SKU for uniqueness, but use reference if SKU is empty
                unique_key = sku_value or ref_value
                if unique_key:
                    skus_unicos.add(unique_key)
            
            total_productos = len(skus_unicos)
            categorias_inv = {}
            for m in mercancias:
                cat = m.categoria_producto or "Sin categoría"
                categorias_inv[cat] = categorias_inv.get(cat, 0) + (m.cantidad or 0)
            
            fig_inventory = make_subplots(
                rows=1, cols=3,
                specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "pie"}]],
                subplot_titles=["Total Unidades en Inventario", "SKUs Únicos", "Distribución por Categoría"]
            )
            
            fig_inventory.add_trace(go.Indicator(
                mode = "number+gauge",
                value = total_unidades,
                title = {"text": "Unidades"},
                gauge = {
                    'axis': {'range': [0, max(total_unidades * 1.2, 100)]},
                    'bar': {'color': "steelblue"}
                }
            ), row=1, col=1)
            
            fig_inventory.add_trace(go.Indicator(
                mode = "number",
                value = total_productos,
                title = {"text": "SKUs"}
            ), row=1, col=2)
            
            if categorias_inv:
                fig_inventory.add_trace(go.Pie(
                    labels=list(categorias_inv.keys()),
                    values=list(categorias_inv.values()),
                    textinfo='percent+label',
                    hole=0.3
                ), row=1, col=3)
            else:
                fig_inventory.add_trace(go.Pie(
                    labels=["Sin datos"],
                    values=[1],
                    marker=dict(colors=["lightgray"])
                ), row=1, col=3)
            
            fig_inventory.update_layout(height=400, margin=dict(t=80, b=40), template='plotly_white')
            
            return empty_fig, empty_fig, fig_inventory, empty_fig, empty_fig, empty_fig, empty_fig, picking_options, picking_value, options_mr, value_mr, diagnostic_text, store_filtered

        else:
            top = (dff.groupby(['Marca_Referencia','Categoria_producto'], as_index=False)
                 .agg(Cantidad_total=('Cantidad','sum'),
                      Error_promedio=('Error_porcentaje','mean'))
                 .sort_values('Cantidad_total', ascending=False)
                 .head(15))
            fig_top = px.bar(top, x='Marca_Referencia', y='Cantidad_total', color='Categoria_producto',
                             hover_data={'Error_promedio':':.2f'}, labels={'Cantidad_total':'Cantidad total'}, title='Top 15 productos por cantidad')
            fig_top.update_layout(xaxis_tickangle=-45, margin=dict(t=50, b=150))

            ts_sales = dff.groupby('fecha_dia', as_index=False).agg(Cantidad_diaria=('Cantidad','sum'))
            fig_sales_ts = go.Figure()
            fig_sales_ts.add_trace(go.Scatter(x=ts_sales['fecha_dia'], y=ts_sales['Cantidad_diaria'], name='Cantidad despachada diaria'))
            fig_sales_ts.update_layout(title='Evolución diaria: Cantidad despachada', xaxis_title='Fecha', yaxis_title='Cantidad', margin=dict(t=50))

            mercancias = Mercancia.query.filter(Mercancia.cantidad > 0).all()
            total_unidades = sum(m.cantidad or 0 for m in mercancias)
            # Count unique SKUs (SKU + reference) instead of total rows
            skus_unicos = set()
            for m in mercancias:
                # Use SKU if available, otherwise use reference
                sku_value = m.sku.strip() if m.sku else None
                ref_value = m.referencia.strip() if m.referencia else None
            
                # Prefer SKU for uniqueness, but use reference if SKU is empty
                unique_key = sku_value or ref_value
                if unique_key:
                    skus_unicos.add(unique_key)
        
            total_productos = len(skus_unicos)
            categorias_inv = {}
            for m in mercancias:
                cat = m.categoria_producto or "Sin categoría"
                categorias_inv[cat] = categorias_inv.get(cat, 0) + (m.cantidad or 0)
        
            fig_inventory = make_subplots(
                rows=1, cols=3,
                specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "pie"}]],
                subplot_titles=["Total Unidades en Inventario", "SKUs Únicos", "Distribución por Categoría"]
            )
        
            fig_inventory.add_trace(go.Indicator(
                mode = "number+gauge",
                value = total_unidades,
                title = {"text": "Unidades"},
                gauge = {
                    'axis': {'range': [0, max(total_unidades * 1.2, 100)]},
                    'bar': {'color': "steelblue"}
                }
            ), row=1, col=1)
        
            fig_inventory.add_trace(go.Indicator(
                mode = "number",
                value = total_productos,
                title = {"text": "SKUs"}
            ), row=1, col=2)
        
            if categorias_inv:
                fig_inventory.add_trace(go.Pie(
                    labels=list(categorias_inv.keys()),
                    values=list(categorias_inv.values()),
                    textinfo='percent+label',
                    hole=0.3
                ), row=1, col=3)
            else:
                fig_inventory.add_trace(go.Pie(
                    labels=["Sin datos"],
                    values=[1],
                    marker=dict(colors=["lightgray"])
                ), row=1, col=3)
        
            fig_inventory.update_layout(height=400, margin=dict(t=50, b=40), template='plotly_white')
            
            print(f"DEBUG: Creating scatter plot with {len(dff)} rows")
            if dff.empty:
                print("DEBUG: dff is empty, creating empty scatter plot")
                fig_scatter = empty_figure("No hay datos para el gráfico de dispersión")
            else:
                fig_scatter = px.scatter(dff, x='tiempo_proceso', y='Error_porcentaje', color='Categoria_producto',
                                     hover_data=['Marca_Referencia','Cantidad','Auxiliar','Picking_ID'],
                                     labels={'tiempo_proceso':'Tiempo de proceso (min)','Error_porcentaje':'Error (%)'},
                                     title='Error (%) vs Tiempo de proceso (min)')
                fig_scatter.update_traces(marker=dict(size=8, opacity=0.75))
                fig_scatter.update_layout(margin=dict(t=40))

            group = (dff.groupby(['Pasillo','Estanteria','Piso','Marca_Referencia'], as_index=False)
                       .agg(Cantidad_total=('Cantidad','sum'),
                            Error_promedio=('Error_porcentaje','mean')))
            if group.empty:
                fig_heat = empty_figure("No hay datos para la métrica")
            else:
                error_promedio = dff['Error_porcentaje'].mean()
                cantidad_total = dff['Cantidad'].sum()
                pickings_count = dff['Picking_ID'].nunique()
            
                fig_heat = make_subplots(
                    rows=1, cols=3,
                    specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
                    subplot_titles=["Error Promedio (%)", "Total Unidades", "Total Pickings"]
                )
            
                fig_heat.add_trace(go.Indicator(
                    mode = "gauge+number",
                    value = error_promedio,
                    title = {"text": "Error %"},
                    gauge = {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "darkred" if error_promedio > 10 else "green"},
                        'steps': [
                            {'range': [0, 5], 'color': "lightgreen"},
                            {'range': [5, 10], 'color': "yellow"},
                            {'range': [10, 100], 'color': "lightcoral"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 2},
                            'thickness': 0.75,
                            'value': 10
                        }
                    }
                ), row=1, col=1)
            
                fig_heat.add_trace(go.Indicator(
                    mode = "number+gauge",
                    value = cantidad_total,
                    title = {"text": "Unidades"},
                    gauge = {
                        'axis': {'range': [0, cantidad_total * 1.2]},
                        'bar': {'color': "steelblue"}
                    }
                ), row=1, col=2)
            
                fig_heat.add_trace(go.Indicator(
                    mode = "number+gauge",
                    value = pickings_count,
                    title = {"text": "Pickings"},
                    gauge = {
                        'axis': {'range': [0, pickings_count * 1.2]},
                        'bar': {'color': "purple"}
                    }
                ), row=1, col=3)
            
                fig_heat.update_layout(height=400, margin=dict(t=90, b=40), template='plotly_white')

            visible_pickings = dff['Picking_ID'].dropna().astype(str).unique()
            picking_options = [{'label': pid, 'value': pid} for pid in sorted(visible_pickings)]

            picking_value = None
            if store_selected_picking_data:
                if str(store_selected_picking_data) in visible_pickings:
                    picking_value = str(store_selected_picking_data)
                else:
                    picking_value = None

            aux_agg = (dff.groupby('Auxiliar', as_index=False)
                         .agg(Cantidad_promedio=('Cantidad','mean'),
                              Error_promedio=('Error_porcentaje','mean'),
                              Total_pickings=('Picking_ID', 'count')))
            aux_agg = aux_agg.sort_values('Cantidad_promedio', ascending=False).head(40)
            fig_aux = go.Figure()
            fig_aux.add_trace(go.Bar(x=aux_agg['Auxiliar'], y=aux_agg['Cantidad_promedio'], name='Cantidad promedio'))
            fig_aux.add_trace(go.Bar(x=aux_agg['Auxiliar'], y=aux_agg['Error_promedio'], name='Error promedio (%)'))
            fig_aux.update_layout(barmode='group', title='Comparación de auxiliares', xaxis_tickangle=-45,
                                  margin=dict(t=50, b=150))

            all_mr = sorted(df_current['Marca_Referencia'].dropna().unique())
            options_mr = [{'label': mr, 'value': mr} for mr in all_mr]
            value_mr = marca_ref_values if marca_ref_values else []

            store_filtered = dff[["Picking_ID","Fecha","Auxiliar"]].copy()
            store_filtered["Picking_ID"] = store_filtered["Picking_ID"].astype(str)
            store_filtered = store_filtered.to_dict('records')

            return fig_top, fig_sales_ts, fig_inventory, fig_scatter, fig_heat, fig_aux, fig_scatter, picking_options, picking_value, options_mr, value_mr, diagnostic_text, store_filtered

    @dash_app.callback(
        Output('store_selected_picking','data'),
        Input('picking_dropdown','value'),
        State('store_selected_picking','data'),
        prevent_initial_call=True
    )
    def persist_selected_picking(picking_value, current_store):
        if not picking_value:
            return dash.no_update
        return str(picking_value)

    @dash_app.callback(
        Output('picking_detail','children'),
        Input('store_selected_picking','data')
    )
    def show_picking_detail_from_store(selected_pid):
        if not selected_pid:
            return "Selecciona un picking en el dropdown para ver detalles."
        full = df[df["Picking_ID"] == str(selected_pid)]
        if full.empty:
            return "No se encontró información completa para el picking seleccionado."
        r = full.iloc[0]
        details = [
            html.P([html.B("Picking_ID: "), str(r.get("Picking_ID", ""))]),
            html.P([html.B("Fecha: "), str(r.get("Fecha"))]),
            html.P([html.B("Hora generación: "), str(r.get("Hora_generacion"))]),
            html.P([html.B("Auxiliar: "), str(r.get("Auxiliar"))]),
            html.P([html.B("Pasillo: "), str(r.get("Pasillo"))]),
            html.P([html.B("Piso: "), str(r.get("Piso"))]),
            html.P([html.B("Marca: "), str(r.get("Marca_solicitada"))]),
            html.P([html.B("Referencia: "), str(r.get("Referencia_solicitada"))]),
            html.P([html.B("Cantidad: "), str(r.get("Cantidad"))]),
            html.P([html.B("Error %: "), f"{r.get('Error_porcentaje'):.1f}" if pd.notna(r.get('Error_porcentaje')) else "0"]),
        ]
        return details

    @dash_app.callback(
        Output('inv_total_unidades', 'children'),
        Output('inv_total_skus', 'children'),
        Output('inv_total_categorias', 'children'),
        Output('inv_total_ubicaciones', 'children'),
        Output('inv_detalle_tabla', 'children'),
        Output('inv_marca2_dropdown', 'options'),
        Output('inv_cat_dropdown', 'options'),
        Output('inv_posicion_dropdown', 'options'),
        Input('inv_cat_dropdown', 'value'),
        Input('inv_marca2_dropdown', 'value'),
        Input('inv_ref_input', 'value'),
        Input('inv_posicion_dropdown', 'value'),
        Input('inv_refresh_btn', 'n_clicks'),
        Input('interval_refresh', 'n_intervals'),
        State('inv_marca2_dropdown', 'options'),
        State('inv_posicion_dropdown', 'options')
    )
    def update_inventory_footer(cat_val, marca_val, ref_val, posicion_val, n_clicks, n_intervals, current_marca_opts, current_posicion_opts):
        # Recargar datos desde la base de datos cada vez que se actualiza
        # Use the server app from dash_app
        app = dash_app.server
        dff = get_inventario_dataframe(app)
        print(f"DEBUG update_inventory_footer: {len(dff)} rows, cat={cat_val}, marca={marca_val}, ref={ref_val}, posicion={posicion_val}")
        
        if dff.empty:
            dff = pd.DataFrame(columns=['id', 'sku', 'marca', 'referencia', 'cantidad', 'categoria_producto', 'pasillo', 'estanteria', 'piso', 'ubicacion', 'fecha_ingreso'])
        
        # Get all options before filtering
        all_marcas = sorted(dff['marca'].dropna().unique()) if not dff.empty else []
        all_categorias = sorted(dff['categoria_producto'].dropna().unique()) if not dff.empty else []
        all_posiciones = sorted(dff['ubicacion'].dropna().unique()) if not dff.empty else []
        
        if cat_val:
            if isinstance(cat_val, list):
                dff = dff[dff['categoria_producto'].isin(cat_val)]
            else:
                dff = dff[dff['categoria_producto'] == cat_val]
        
        if marca_val:
            if isinstance(marca_val, list):
                dff = dff[dff['marca'].isin(marca_val)]
            else:
                dff = dff[dff['marca'] == marca_val]
        
        if ref_val:
            dff = dff[dff['referencia'].str.contains(ref_val, case=False, na=False)]
        
        if posicion_val:
            if isinstance(posicion_val, list):
                dff = dff[dff['ubicacion'].isin(posicion_val)]
            else:
                dff = dff[dff['ubicacion'] == posicion_val]
        
        if dff.empty:
            return "0", "0", "0", "0", html.P("No hay mercancía en inventario con los filtros seleccionados.", className="text-muted"), [{'label': m, 'value': m} for m in all_marcas], [{'label': c, 'value': c} for c in all_categorias], [{'label': p, 'value': p} for p in []]
        
        total_unidades = int(dff['cantidad'].sum())
        # Count unique SKUs (referencias) instead of rows
        total_skus = len(dff['referencia'].unique())
        total_categorias = int(dff['categoria_producto'].nunique())
        total_ubicaciones = len(dff['ubicacion'].unique())
        
        print(f"DEBUG: Calculated totals - unidades={total_unidades}, skus={total_skus}, categorias={total_categorias}, ubicaciones={total_ubicaciones}")
        
        table_rows = []
        for _, row in dff.head(50).iterrows():
            table_rows.append(html.Tr([
                html.Td(row.get('categoria_producto', '')),
                html.Td(row.get('marca', '')),
                html.Td(row.get('referencia', '')),
                html.Td(str(row.get('cantidad', 0))),
                html.Td(row.get('pasillo', '')),
                html.Td(row.get('estanteria', '')),
                html.Td(row.get('piso', '')),
                html.Td(row.get('ubicacion', '')),
            ]))
        
        table = dbc.Table([
            html.Thead(html.Tr([
                html.Th("Categoría"),
                html.Th("Marca"),
                html.Th("Referencia"),
                html.Th("Cantidad"),
                html.Th("Pasillo"),
                html.Th("Estant."),
                html.Th("Piso"),
                html.Th("Ubicación"),
            ])),
            html.Tbody(table_rows)
        ], responsive=True, striped=True, hover=True, size="sm")
        
        if len(dff) > 50:
            table = html.Div([table, html.P(f"Mostrando los primeros 50 de {len(dff)} registros", className="text-muted mt-2")])
        
        # Calculate options based on filtered data to avoid redundancies
        # This ensures that when a filter is applied, the other filters only show relevant options
        updated_marcas = [{'label': m, 'value': m} for m in sorted(dff['marca'].dropna().unique())]
        updated_categorias = [{'label': c, 'value': c} for c in sorted(dff['categoria_producto'].dropna().unique())]
        updated_posiciones = [{'label': p, 'value': p} for p in sorted(dff['ubicacion'].dropna().unique())]
        
        return f"{total_unidades:,}", f"{total_skus:,}", f"{total_categorias}", f"{total_ubicaciones}", table, updated_marcas, updated_categorias, updated_posiciones

    return app


def run_dashboard():
    import sys
    from app import create_app
    
    # Disable Flask reloader to avoid issues
    sys.argv = ['']
    
    # Create Flask app first
    flask_app = create_app()
    
    # Then create Dash app with Flask server
    dash_app = create_dashboard(server=flask_app)
    
    # Disable debug to avoid reloader issues
    flask_app.debug = False
    
    print("Dashboard disponible en: http://localhost:8051/dashboard/")
    print("Presiona Ctrl+C para detener")
    
    # Run with Flask app directly (since dash_app uses flask_app as server)
    flask_app.run(debug=False, port=8051, use_reloader=False)


if __name__ == '__main__':
    run_dashboard()
