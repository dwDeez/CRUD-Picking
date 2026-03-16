
from datetime import datetime
from app import db
from sqlalchemy import UniqueConstraint


class Mercancia(db.Model):
    __tablename__ = "mercancia"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku = db.Column(db.String)
    marca = db.Column(db.String)
    referencia = db.Column(db.String)
    cantidad = db.Column(db.Integer, default=0)
    categoria_producto = db.Column(db.String)
    pasillo = db.Column(db.String)
    estanteria = db.Column(db.String)
    piso = db.Column(db.String)
    fecha_ingreso = db.Column(db.String)
    hora_ingreso = db.Column(db.String)
    modified_by = db.Column(db.String)
    modified_at = db.Column(db.String)


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
    Unidades_erradas = db.Column(db.Integer, default=0)
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


class PickingCSV(db.Model):
    __tablename__ = "pickings_csv"
    __table_args__ = (
        UniqueConstraint('Picking_ID', name='uix_picking_csv'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Picking_ID = db.Column(db.String)
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


class PickingItemCSV(db.Model):
    __tablename__ = "picking_items_csv"
    __table_args__ = (
        UniqueConstraint('Picking_ID', 'marca', 'referencia', 'tipo', 'cantidad', name='uix_picking_item_csv'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Picking_ID = db.Column(db.String, index=True)
    tipo = db.Column(db.String)
    marca = db.Column(db.String)
    referencia = db.Column(db.String)
    cantidad = db.Column(db.Integer)
    Pasillo = db.Column(db.String)
    Estanteria = db.Column(db.String)
    Piso = db.Column(db.String)


class MercanciaCSV(db.Model):
    __tablename__ = "mercancia_csv"
    __table_args__ = (
        UniqueConstraint('marca', 'referencia', 'pasillo', 'estanteria', 'piso', name='uix_mercancia_csv'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku = db.Column(db.String)
    marca = db.Column(db.String)
    referencia = db.Column(db.String)
    cantidad = db.Column(db.Integer, default=0)
    categoria_producto = db.Column(db.String)
    pasillo = db.Column(db.String)
    estanteria = db.Column(db.String)
    piso = db.Column(db.String)
    fecha_ingreso = db.Column(db.String)
    hora_ingreso = db.Column(db.String)
    modified_by = db.Column(db.String)
    modified_at = db.Column(db.String)


class Recepcion(db.Model):
    __tablename__ = "recepcion"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    operario = db.Column(db.String)
    fecha_inicio = db.Column(db.String)
    fecha_fin = db.Column(db.String)
    estado = db.Column(db.String, default="activa")
    observaciones = db.Column(db.Text)
    items = db.relationship("RecepcionItem", backref="recepcion", cascade="all, delete-orphan")


class RecepcionItem(db.Model):
    __tablename__ = "recepcion_item"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recepcion_id = db.Column(db.Integer, db.ForeignKey("recepcion.id"))
    sku = db.Column(db.String)
    marca = db.Column(db.String)
    referencia = db.Column(db.String)
    categoria = db.Column(db.String)
    pasillo = db.Column(db.String)
    estanteria = db.Column(db.String)
    piso = db.Column(db.String)
    unidad_numero = db.Column(db.Integer)
    timestamp = db.Column(db.String)
    confirmado = db.Column(db.Boolean, default=False)
