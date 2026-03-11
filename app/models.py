from datetime import datetime
from app import db
from sqlalchemy import UniqueConstraint


class Picking(db.Model):
    __tablename__ = "pickings"
    __table_args__ = (
        UniqueConstraint('Picking_ID', name='uix_picking'),
    )

    Picking_ID = db.Column(db.String, primary_key=True)
    Fecha = db.Column(db.String)
    Hora_generacion = db.Column(db.String)
    Hora_revision = db.Column(db.String)
    Hora_despacho = db.Column(db.String)
    Auxiliar = db.Column(db.String)
    Cantidad_pickings_por_auxiliar = db.Column(db.Integer)
    Pasillo = db.Column(db.String)
    Estanteria = db.Column(db.String)
    Piso = db.Column(db.String)
    Marca_solicitada = db.Column(db.String)
    Referencia_solicitada = db.Column(db.String)
    Categoria_producto = db.Column(db.String)
    Cantidad = db.Column(db.Integer)
    Error_porcentaje = db.Column(db.Float)
    modified_by = db.Column(db.String)
    modified_at = db.Column(db.String)
    items = db.relationship("PickingItem", back_populates="picking", cascade="all, delete-orphan")


class PickingItem(db.Model):
    __tablename__ = "picking_items"
    __table_args__ = (
        UniqueConstraint('Picking_ID', 'marca', 'referencia', 'tipo', 'cantidad', name='uix_picking_item'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Picking_ID = db.Column(db.String, db.ForeignKey("pickings.Picking_ID", ondelete="CASCADE"), index=True)
    tipo = db.Column(db.String)
    marca = db.Column(db.String)
    referencia = db.Column(db.String)
    cantidad = db.Column(db.Integer)
    Pasillo = db.Column(db.String)
    Estanteria = db.Column(db.String)
    Piso = db.Column(db.String)
    picking = db.relationship("Picking", back_populates="items")
