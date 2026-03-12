import os
from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app import db
from app.models import Picking, PickingItem, Mercancia


def generate_picking_pdf(picking_id: str) -> bytes:
    p = Picking.query.get(picking_id)
    if not p:
        raise ValueError(f"Picking {picking_id} no encontrado")
    
    items = PickingItem.query.filter_by(Picking_ID=picking_id).all()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=25*mm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    
    category_style = ParagraphStyle(
        'CategoryStyle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_LEFT,
        spaceBefore=10,
        spaceAfter=3,
    )
    
    product_style = ParagraphStyle(
        'ProductStyle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_LEFT,
        spaceAfter=2,
    )
    
    location_style = ParagraphStyle(
        'LocationStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.darkblue,
        spaceAfter=8,
    )
    
    total_style = ParagraphStyle(
        'TotalStyle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_RIGHT,
        spaceBefore=15,
    )
    
    story = []
    
    story.append(Paragraph(f"PICKING ORDER", title_style))
    story.append(Spacer(1, 10))
    
    header_data = [
        [Paragraph(f"<b>Picking ID:</b> {p.Picking_ID or '-'}", header_style), 
         Paragraph(f"<b>Fecha:</b> {p.Fecha or '-'}", header_style)],
        [Paragraph(f"<b>Hora Generación:</b> {p.Hora_generacion or '-'}", header_style),
         Paragraph(f"<b>Hora Revisión:</b> {p.Hora_revision or '-'}", header_style)],
    ]
    
    header_table = Table(header_data, colWidths=[100*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    def get_item_location(marca: str, referencia: str):
        if not marca:
            return None, None, None
        mercancia = Mercancia.query.filter(
            Mercancia.marca == marca,
            Mercancia.referencia == referencia
        ).first()
        if mercancia:
            return mercancia.pasillo, mercancia.estanteria, mercancia.piso
        other = Picking.query.filter(
            Picking.Marca_solicitada == marca,
            Picking.Referencia_solicitada == referencia
        ).first()
        if other:
            return other.Pasillo, other.Estanteria, other.Piso
        other2 = Picking.query.filter(Picking.Marca_solicitada == marca).first()
        if other2:
            return other2.Pasillo, other2.Estanteria, other2.Piso
        return None, None, None
    
    def extract_first_pasillo(pasillo_str):
        if not pasillo_str:
            return ""
        pasillo_str = pasillo_str.strip()
        if not pasillo_str:
            return ""
        first_char = pasillo_str[0].upper()
        if 'A' <= first_char <= 'Z':
            return first_char
        return ""
    
    def sort_key(item):
        pasillo_raw = item.Pasillo if item.Pasillo else ""
        estanteria = item.Estanteria if item.Estanteria else ""
        
        pasillo = extract_first_pasillo(pasillo_raw)
        
        if not pasillo:
            pasillo, estanteria_fallback, piso = get_item_location(item.marca, item.referencia)
            if pasillo:
                pasillo = extract_first_pasillo(pasillo)
        
        if not pasillo and item.Picking_ID:
            picking = Picking.query.get(item.Picking_ID)
            if picking:
                pasillo = extract_first_pasillo(picking.Pasillo)
        
        try:
            est_num = int(estanteria) if estanteria else 0
        except:
            est_num = 0
        return (pasillo.lower(), est_num)
    
    sorted_items = sorted(items, key=sort_key)
    
    items_by_category = {}
    for item in sorted_items:
        cat = item.tipo or "Sin categoría"
        if cat not in items_by_category:
            items_by_category[cat] = []
        items_by_category[cat].append(item)
    
    for category, category_items in items_by_category.items():
        story.append(Paragraph(f"Categoría: {category}", category_style))
        story.append(Spacer(1, 3))
        
        for item in category_items:
            product_text = f"{item.marca or ''} {item.referencia or ''}".strip()
            if not product_text:
                product_text = "Sin producto"
            
            story.append(Paragraph(f"Producto: {product_text}", product_style))
            
            pasillo_raw = item.Pasillo if item.Pasillo else None
            estanteria = item.Estanteria if item.Estanteria else None
            piso = item.Piso if item.Piso else None
            
            if not pasillo_raw:
                pasillo_raw, estanteria, piso = get_item_location(item.marca, item.referencia)
            
            if not pasillo_raw:
                pasillo_raw = p.Pasillo
                estanteria = p.Estanteria
                piso = p.Piso
            
            pasillo_display = extract_first_pasillo(pasillo_raw) if pasillo_raw else ""
            
            location_info = []
            if pasillo_display:
                location_info.append(f"Pasillo: {pasillo_display}")
            if estanteria:
                location_info.append(f"Estantería: {estanteria}")
            if piso:
                location_info.append(f"Piso: {piso}")
            
            location_text = " | ".join(location_info) if location_info else "Ubicación no especificada"
            story.append(Paragraph(f"<b>Ubicación:</b> {location_text}", location_style))
            
            story.append(Paragraph(f"<b>Cantidad:</b> {item.cantidad or 1}", product_style))
            
            line_data = [['', '']]
            line_table = Table(line_data, colWidths=[180*mm])
            line_table.setStyle(TableStyle([
                ('LINEABOVE', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(line_table)
        
        story.append(Spacer(1, 5))
    
    total_items = sum(item.cantidad or 1 for item in items)
    total_unique = len(items)
    
    story.append(Paragraph(f"Total de ítems: {total_unique} | Cantidad total: {total_items}", total_style))
    
    def footer(canvas, doc):
        canvas.saveState()
        P = Paragraph(
            f"<b>Auxiliar:</b> {p.Auxiliar or '-'} | Página {doc.page} ",
            styles['Normal']
        )
        w, h = P.wrap(doc.width, doc.bottomMargin)
        P.drawOn(canvas, doc.leftMargin, h + 10)
        canvas.restoreState()
    
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    
    buffer.seek(0)
    return buffer.getvalue()


def generate_picking_list_pdf(picking_ids: list = None) -> bytes:
    if picking_ids is None:
        pickings = Picking.query.all()
        picking_ids = [p.Picking_ID for p in pickings]
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=25*mm
    )
    
    styles = getSampleStyleSheet()
    story = []
    picking_auxiliares = {}
    current_page = 1
    
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10,
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle', parent=styles['Normal'], fontSize=12, alignment=TA_LEFT, spaceAfter=5,
    )
    
    category_style = ParagraphStyle(
        'CategoryStyle', parent=styles['Heading2'], fontSize=14, alignment=TA_LEFT, spaceBefore=10, spaceAfter=3,
    )
    
    product_style = ParagraphStyle(
        'ProductStyle', parent=styles['Normal'], fontSize=12, alignment=TA_LEFT, spaceAfter=2,
    )
    
    location_style = ParagraphStyle(
        'LocationStyle', parent=styles['Normal'], fontSize=11, textColor=colors.darkblue, spaceAfter=8,
    )
    
    total_style = ParagraphStyle(
        'TotalStyle', parent=styles['Heading2'], fontSize=14, alignment=TA_RIGHT, spaceBefore=15,
    )
    
    def get_item_location_for_list(marca: str, referencia: str):
        if not marca:
            return None, None, None
        mercancia = Mercancia.query.filter(
            Mercancia.marca == marca,
            Mercancia.referencia == referencia
        ).first()
        if mercancia:
            return mercancia.pasillo, mercancia.estanteria, mercancia.piso
        other = Picking.query.filter(
            Picking.Marca_solicitada == marca,
            Picking.Referencia_solicitada == referencia
        ).first()
        if other:
            return other.Pasillo, other.Estanteria, other.Piso
        other2 = Picking.query.filter(Picking.Marca_solicitada == marca).first()
        if other2:
            return other2.Pasillo, other2.Estanteria, other2.Piso
        return None, None, None
    
    def extract_first_pasillo_list(pasillo_str):
        if not pasillo_str:
            return ""
        pasillo_str = pasillo_str.strip()
        if not pasillo_str:
            return ""
        first_char = pasillo_str[0].upper()
        if 'A' <= first_char <= 'Z':
            return first_char
        return ""
    
    def sort_key_for_list(item):
        pasillo_raw = item.Pasillo if item.Pasillo else ""
        estanteria = item.Estanteria if item.Estanteria else ""
        pasillo = extract_first_pasillo_list(pasillo_raw)
        if not pasillo:
            pasillo, estanteria_fallback, piso = get_item_location_for_list(item.marca, item.referencia)
            if pasillo:
                pasillo = extract_first_pasillo_list(pasillo)
        if not pasillo and item.Picking_ID:
            picking = Picking.query.get(item.Picking_ID)
            if picking:
                pasillo = extract_first_pasillo_list(picking.Pasillo)
        try:
            est_num = int(estanteria) if estanteria else 0
        except:
            est_num = 0
        return (pasillo.lower() if pasillo else "", est_num)
    
    page_count_per_picking = []
    is_first = True
    
    for picking_id in picking_ids:
        p = Picking.query.get(picking_id)
        if not p:
            continue
        
        if not is_first:
            story.append(PageBreak())
        is_first = False
        
        items = PickingItem.query.filter_by(Picking_ID=picking_id).all()
        
        picking_start_page = len(page_count_per_picking) + 1
        page_count_per_picking.append({
            'picking_id': picking_id,
            'auxiliar': p.Auxiliar or '-',
            'start_page': picking_start_page
        })
        
        items = PickingItem.query.filter_by(Picking_ID=picking_id).all()
        
        story.append(Paragraph(f"PICKING ORDER", title_style))
        story.append(Spacer(1, 10))
        
        header_data = [
            [Paragraph(f"<b>Picking ID:</b> {p.Picking_ID or '-'}", header_style), 
             Paragraph(f"<b>Fecha:</b> {p.Fecha or '-'}", header_style)],
            [Paragraph(f"<b>Hora Generación:</b> {p.Hora_generacion or '-'}", header_style),
             Paragraph(f"<b>Hora Revisión:</b> {p.Hora_revision or '-'}", header_style)],
        ]
        
        header_table = Table(header_data, colWidths=[100*mm, 80*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))
        
        sorted_items = sorted(items, key=sort_key_for_list)
        
        items_by_category = {}
        for item in sorted_items:
            cat = item.tipo or "Sin categoría"
            if cat not in items_by_category:
                items_by_category[cat] = []
            items_by_category[cat].append(item)
        
        for category, category_items in items_by_category.items():
            story.append(Paragraph(f"Categoría: {category}", category_style))
            story.append(Spacer(1, 3))
            
            for item in category_items:
                product_text = f"{item.marca or ''} {item.referencia or ''}".strip()
                if not product_text:
                    product_text = "Sin producto"
                
                story.append(Paragraph(f"Producto: {product_text}", product_style))
                
                pasillo_raw = item.Pasillo if item.Pasillo else None
                estanteria = item.Estanteria if item.Estanteria else None
                piso = item.Piso if item.Piso else None
                
                if not pasillo_raw:
                    pasillo_raw, estanteria, piso = get_item_location_for_list(item.marca, item.referencia)
                
                if not pasillo_raw:
                    pasillo_raw = p.Pasillo
                    estanteria = p.Estanteria
                    piso = p.Piso
                
                pasillo_display = extract_first_pasillo_list(pasillo_raw) if pasillo_raw else ""
                
                location_info = []
                if pasillo_display:
                    location_info.append(f"Pasillo: {pasillo_display}")
                if estanteria:
                    location_info.append(f"Estantería: {estanteria}")
                if piso:
                    location_info.append(f"Piso: {piso}")
                
                location_text = " | ".join(location_info) if location_info else "Ubicación no especificada"
                story.append(Paragraph(f"<b>Ubicación:</b> {location_text}", location_style))
                
                story.append(Paragraph(f"<b>Cantidad:</b> {item.cantidad or 1}", product_style))
                
                line_data = [['', '']]
                line_table = Table(line_data, colWidths=[180*mm])
                line_table.setStyle(TableStyle([
                    ('LINEABOVE', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(line_table)
            
            story.append(Spacer(1, 5))
        
        total_items = sum(item.cantidad or 1 for item in items)
        total_unique = len(items)
        
        story.append(Paragraph(f"Total de ítems: {total_unique} | Cantidad total: {total_items}", total_style))
    
    def footer(canvas, doc):
        page_num = doc.page
        current_aux = '-'
        current_picking_num = '-'
        
        for i, pick_info in enumerate(page_count_per_picking):
            start = pick_info['start_page']
            if i + 1 < len(page_count_per_picking):
                end = page_count_per_picking[i + 1]['start_page']
            else:
                end = page_num + 1
            
            if start <= page_num < end:
                current_aux = pick_info['auxiliar']
                current_picking_num = i + 1
                relative_page = page_num - start + 1
                break
        
        canvas.saveState()
        P = Paragraph(
            f"<b>Picking:</b> {current_picking_num} | <b>Auxiliar:</b> {current_aux} | <b>Página</b> {page_num} ",
            styles['Normal']
        )
        w, h = P.wrap(doc.width, doc.bottomMargin)
        P.drawOn(canvas, doc.leftMargin, h + 10)
        canvas.restoreState()
    
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    
    buffer.seek(0)
    return buffer.getvalue()
