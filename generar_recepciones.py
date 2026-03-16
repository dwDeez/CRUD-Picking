#!/usr/bin/env python3
"""
Script para generar 4000 entradas en la recepción de mercancía
basándose en el dataset_importadora_electrodomesticos_4000.csv
"""

import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd

# Añadir el directorio app al path para importar los modelos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Recepcion, RecepcionItem, Mercancia

def load_csv_data():
    """Carga los datos del CSV"""
    csv_path = os.path.join(os.path.dirname(__file__), 'Data', 'import', 'dataset_importadora_electrodomesticos_4000.csv')
    
    if not os.path.exists(csv_path):
        print(f"Error: No se encontró el archivo {csv_path}")
        return None
    
    df = pd.read_csv(csv_path, encoding='utf-8')
    print(f"Datos cargados: {len(df)} registros")
    return df

def generate_recepciones(df, num_recepciones=4000):
    """Genera entradas de recepción basadas en el CSV"""
    
    # Obtener valores únicos del CSV
    marcas = df['Marca_solicitada'].unique()
    referencias = df['Referencia_solicitada'].unique()
    categorias = df['Categoria_producto'].unique()
    
    print(f"Marcas únicas: {len(marcas)}")
    print(f"Referencias únicas: {len(referencias)}")
    print(f"Categorías únicas: {len(categorias)}")
    
    # Crear un diccionario para mapear referencia -> categoria
    ref_to_cat = {}
    for _, row in df[['Referencia_solicitada', 'Categoria_producto']].iterrows():
        if row['Referencia_solicitada'] not in ref_to_cat:
            ref_to_cat[row['Referencia_solicitada']] = row['Categoria_producto']
    
    # Generar recepciones
    recepciones = []
    for i in range(num_recepciones):
        # Seleccionar valores aleatorios del CSV
        marca = random.choice(marcas)
        ref_idx = random.randint(0, len(referencias) - 1)
        referencia = referencias[ref_idx]
        # Asignar categoría basada en la referencia (no aleatoria)
        categoria = ref_to_cat.get(referencia, random.choice(categorias))
        
        # Generar SKU basado en referencia y índice
        sku = f"SKU-{referencia}-{i:04d}"
        
        # Generar ubicación aleatoria (A-Z, 1-15, 1-4)
        pasillo = random.choice([chr(65 + i) for i in range(26)])
        estanteria = random.randint(1, 15)
        piso = random.randint(1, 4)
        
        # Generar cantidad aleatoria (1-50)
        cantidad = random.randint(1, 50)
        
        # Generar fecha aleatoria en el último año
        fecha_inicio = datetime(2025, 1, 1)
        fecha_fin = datetime(2026, 3, 15)
        dias_aleatorios = random.randint(0, (fecha_fin - fecha_inicio).days)
        fecha = fecha_inicio + timedelta(days=dias_aleatorios)
        
        recepciones.append({
            'sku': sku,
            'marca': marca,
            'referencia': referencia,
            'cantidad': cantidad,
            'categoria': categoria,
            'pasillo': pasillo,
            'estanteria': str(estanteria),
            'piso': str(piso),
            'fecha': fecha.strftime('%Y-%m-%d')
        })
    
    return recepciones

def save_to_database(recepciones):
    """Guarda las recepciones en la base de datos"""
    app = create_app()
    
    with app.app_context():
        print("\nGuardando recepciones en la base de datos...")
        
        # Eliminar datos existentes para empezar limpio
        print("Eliminando datos existentes...")
        db.session.query(RecepcionItem).delete()
        db.session.query(Recepcion).delete()
        db.session.query(Mercancia).delete()
        db.session.commit()
        
        # Crear recepciones y items
        recepcion_actual = None
        items_por_recepcion = random.randint(1, 5)  # 1-5 items por recepción
        
        for idx, item in enumerate(recepciones):
            # Crear nueva recepción cada ciertos items
            if idx % items_por_recepcion == 0:
                # Crear nueva recepción
                recepcion_actual = Recepcion(
                    operario=f"Operario{random.randint(1, 10)}",
                    fecha_inicio=item['fecha'],
                    estado="activa"
                )
                db.session.add(recepcion_actual)
                db.session.flush()
                
                items_por_recepcion = random.randint(1, 5)
            
            # Crear item de recepción
            item_recepcion = RecepcionItem(
                recepcion_id=recepcion_actual.id,
                sku=item['sku'],
                marca=item['marca'],
                referencia=item['referencia'],
                categoria=item['categoria'],
                pasillo=item['pasillo'],
                estanteria=item['estanteria'],
                piso=item['piso'],
                unidad_numero=item['cantidad'],
                timestamp=item['fecha'] + " " + "12:00:00",
                confirmado=True
            )
            db.session.add(item_recepcion)
            
            # Crear entrada en Mercancia
            mercancia = Mercancia(
                sku=item['sku'],
                marca=item['marca'],
                referencia=item['referencia'],
                cantidad=item['cantidad'],
                categoria_producto=item['categoria'],
                pasillo=item['pasillo'],
                estanteria=item['estanteria'],
                piso=item['piso'],
                fecha_ingreso=item['fecha'],
                modified_by="script_generacion",
                modified_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            db.session.add(mercancia)
            
            if (idx + 1) % 1000 == 0:
                print(f"  Guardados {idx + 1} registros...")
        
        db.session.commit()
        print(f"Total de recepciones guardadas: {len(recepciones)}")

def main():
    """Función principal"""
    print("=" * 60)
    print("GENERADOR DE ENTRADAS DE RECEPCIÓN")
    print("=" * 60)
    
    # Cargar datos del CSV
    df = load_csv_data()
    if df is None:
        return
    
    # Generar recepciones
    num_recepciones = 4000
    print(f"\nGenerando {num_recepciones} entradas de recepción...")
    recepciones = generate_recepciones(df, num_recepciones)
    
    # Guardar en base de datos
    save_to_database(recepciones)
    
    # Mostrar estadísticas
    print("\n" + "=" * 60)
    print("ESTADÍSTICAS")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        total_recepciones = Recepcion.query.count()
        total_items = RecepcionItem.query.count()
        total_mercancia = Mercancia.query.count()
        
        print(f"Total de recepciones: {total_recepciones}")
        print(f"Total de items en recepciones: {total_items}")
        print(f"Total de entradas en Mercancia: {total_mercancia}")
        
        # Mostrar algunos ejemplos
        print("\nEjemplos de entradas:")
        items_ejemplo = RecepcionItem.query.limit(5).all()
        for item in items_ejemplo:
            print(f"  - SKU: {item.sku}, Ref: {item.referencia}, Marca: {item.marca}, Unidad: {item.unidad_numero}")
    
    print("\n¡Generación completada exitosamente!")
    print(f"\nAhora puedes ejecutar el dashboard:")
    print("  python -m app.dashboard")
    print("  y visitar http://localhost:8051/dashboard/")

if __name__ == "__main__":
    main()
