#!/usr/bin/env python3
"""
Script para generar 3000 pickings basándose en la mercancía actual en la base de datos.
Descuenta la cantidad de la mercancía cuando se genera un picking.
"""

import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd

# Añadir el directorio app al path para importar los modelos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Picking, PickingItem, Mercancia

def generate_pickings(num_pickings=3000):
    """Genera pickings basados en la mercancía actual"""
    
    app = create_app()
    
    with app.app_context():
        # Obtener mercancía disponible
        mercancias = Mercancia.query.filter(Mercancia.cantidad > 0).all()
        
        if not mercancias:
            print("Error: No hay mercancía disponible en la base de datos")
            return
        
        print(f"Mercancía disponible: {len(mercancias)} registros")
        
        # Agrupar mercancía por referencia para evitar duplicados
        mercancia_por_ref = {}
        for m in mercancias:
            ref = m.referencia
            if ref not in mercancia_por_ref:
                mercancia_por_ref[ref] = []
            mercancia_por_ref[ref].append(m)
        
        print(f"Referencias únicas: {len(mercancia_por_ref)}")
        
        # Generar pickings
        pickings = []
        
        # Find the maximum Picking_ID to avoid conflicts
        max_id = db.session.query(db.func.max(Picking.Picking_ID)).scalar()
        if max_id:
            # Extract numeric part from ID (e.g., "P-70001" -> 70001)
            try:
                if '-' in max_id:
                    numeric_part = max_id.split('-')[1]
                else:
                    numeric_part = max_id
                picking_id_counter = int(numeric_part) + 1
            except:
                picking_id_counter = 70001
        else:
            picking_id_counter = 70001
        
        for i in range(num_pickings):
            # Seleccionar una referencia aleatoria con mercancía disponible
            ref = random.choice(list(mercancia_por_ref.keys()))
            items_mercancia = mercancia_por_ref[ref]
            
            # Seleccionar un item de mercancía aleatorio
            m = random.choice(items_mercancia)
            
            # Calcular cantidad máxima disponible (máximo 50% de lo disponible)
            max_cantidad = max(1, int(m.cantidad * 0.5))
            cantidad_solicitada = random.randint(1, min(max_cantidad, 50))
            
            # Generar picking
            picking = {
                'Picking_ID': f"P-{picking_id_counter + i:05d}",
                'Fecha': m.fecha_ingreso,
                'Hora_generacion': f"{random.randint(6, 18):02d}:{random.randint(0, 59):02d}:00",
                'Auxiliar': random.choice(['Luis', 'Andrés', 'Sofía', 'Pedro', 'Laura', 'Carlos', 'María', 'Camila']),
                'Pasillo': m.pasillo,
                'Estanteria': m.estanteria,
                'Piso': m.piso,
                'Marca_solicitada': m.marca,
                'Referencia_solicitada': ref,
                'Categoria_producto': m.categoria_producto,
                'Cantidad': cantidad_solicitada,
                'Error_porcentaje': round(random.uniform(0, 5), 1),
                'modified_by': 'script_generacion',
                'modified_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            pickings.append({
                'picking': picking,
                'mercancia': m,
                'cantidad_solicitada': cantidad_solicitada
            })
        
        return pickings

def save_to_database(pickings):
    """Guarda los pickings en la base de datos y descuenta la mercancía"""
    app = create_app()
    
    with app.app_context():
        print("\nGuardando pickings en la base de datos...")
        
        for idx, picking_data in enumerate(pickings):
            picking_info = picking_data['picking']
            mercancia = picking_data['mercancia']
            cantidad_solicitada = picking_data['cantidad_solicitada']
            
            # Crear picking
            picking = Picking(
                Picking_ID=picking_info['Picking_ID'],
                Fecha=picking_info['Fecha'],
                Hora_generacion=picking_info['Hora_generacion'],
                Auxiliar=picking_info['Auxiliar'],
                Pasillo=picking_info['Pasillo'],
                Estanteria=picking_info['Estanteria'],
                Piso=picking_info['Piso'],
                Marca_solicitada=picking_info['Marca_solicitada'],
                Referencia_solicitada=picking_info['Referencia_solicitada'],
                Categoria_producto=picking_info['Categoria_producto'],
                Cantidad=cantidad_solicitada,
                Error_porcentaje=picking_info['Error_porcentaje'],
                modified_by=picking_info['modified_by'],
                modified_at=picking_info['modified_at']
            )
            db.session.add(picking)
            
            # Crear item de picking
            picking_item = PickingItem(
                Picking_ID=picking_info['Picking_ID'],
                tipo=picking_info['Categoria_producto'],
                marca=picking_info['Marca_solicitada'],
                referencia=picking_info['Referencia_solicitada'],
                cantidad=cantidad_solicitada,
                Pasillo=picking_info['Pasillo'],
                Estanteria=picking_info['Estanteria'],
                Piso=picking_info['Piso']
            )
            db.session.add(picking_item)
            
            # Descuentar de la mercancía
            mercancia.cantidad -= cantidad_solicitada
            
            # Guardar cada 1000 pickings
            if (idx + 1) % 1000 == 0:
                db.session.commit()
                print(f"  Guardados {idx + 1} pickings...")
        
        db.session.commit()
        print(f"Total de pickings guardados: {len(pickings)}")

def main():
    """Función principal"""
    print("=" * 60)
    print("GENERADOR DE PICKINGS")
    print("=" * 60)
    
    # Generar pickings
    num_pickings = 3000
    print(f"\nGenerando {num_pickings} pickings basados en mercancía actual...")
    pickings = generate_pickings(num_pickings)
    
    if pickings is None:
        return
    
    # Guardar en base de datos
    save_to_database(pickings)
    
    # Mostrar estadísticas
    print("\n" + "=" * 60)
    print("ESTADÍSTICAS")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        total_pickings = Picking.query.count()
        total_items = PickingItem.query.count()
        total_mercancia = Mercancia.query.count()
        mercancia_con_cero = Mercancia.query.filter(Mercancia.cantidad == 0).count()
        mercancia_con_stock = Mercancia.query.filter(Mercancia.cantidad > 0).count()
        
        print(f"Total de pickings: {total_pickings}")
        print(f"Total de items en pickings: {total_items}")
        print(f"Total de entradas en Mercancia: {total_mercancia}")
        print(f"Mercancia con stock: {mercancia_con_stock}")
        print(f"Mercancia sin stock (agotada): {mercancia_con_cero}")
        
        # Mostrar algunos ejemplos
        print("\nEjemplos de pickings generados:")
        pickings_ejemplo = Picking.query.limit(3).all()
        for p in pickings_ejemplo:
            print(f"  - ID: {p.Picking_ID}, Ref: {p.Referencia_solicitada}, Cantidad: {p.Cantidad}")
        
        # Mostrar mercancia con bajo stock
        print("\nMercancia con bajo stock (<10 unidades):")
        baja_stock = Mercancia.query.filter(Mercancia.cantidad > 0, Mercancia.cantidad < 10).limit(5).all()
        for m in baja_stock:
            print(f"  - SKU: {m.sku}, Ref: {m.referencia}, Stock: {m.cantidad}")
    
    print("\n¡Generación completada exitosamente!")
    print(f"\nAhora puedes ejecutar el dashboard:")
    print("  python -m app.dashboard")
    print("  y visitar http://localhost:8051/dashboard/")

if __name__ == "__main__":
    main()
