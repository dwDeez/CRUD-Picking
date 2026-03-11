# Sistema de Gestión de Pickings - CRUD Electrodomésticos

> Sistema de gestión de operaciones de picking para almacenes de importación de electrodomésticos y llantas.

## Descripción

Plataforma web Flask para la gestión integral de operaciones de picking en logística WMS. Permite administrar órdenes de picking, generar documentos PDF para distribución en bodega, visualizar estadísticas operativas y gestionar inventarios por ubicación.

### Funcionalidades Principales

- **CRUD de Pickings**: Crear, leer, actualizar y eliminar órdenes de picking
- **Gestión de Inventario**: Control de productos por pasillo, estantería y piso
- **Generación de PDFs**: Documentos de picking optimizados para distribución en bodega
- **Dashboard Analítico**: Visualizaciones de ventas, errores y métricas operativas
- **Filtros Avanzados**: Filtrar por categoría, auxiliar, ubicación, fecha y más
- **Importación de Datos**: Carga masiva desde archivos CSV con mapeo automático de columnas
- **Configuración de Vistas**: Personalización de columnas visibles en la tabla

---

## Tecnologías

```python
# Backend
Flask==3.0.0           # Framework web
Flask-SQLAlchemy==3.1.1 # ORM
SQLAlchemy==2.0.36     # Base de datos
pandas==2.2.3          # Procesamiento de datos

# Dashboard Analítico
dash==2.18.2                    # Framework Dash
dash-bootstrap-components==1.6.0 # Componentes Bootstrap
plotly==5.24.1                   # Visualizaciones

# PDF
reportlab==4.2.5  # Generación de PDFs

# Utilidades
gunicorn==23.0.0        # Servidor producción
python-dotenv==1.0.1    # Variables de entorno
```

---

## Requisitos del Sistema

### Entorno de Ejecución

- **Sistema Operativo**: Windows 10+ / Linux (Ubuntu 20.04+)
- **Python**: Versión 3.10 o superior
- **Memoria RAM**: Mínimo 4GB (recomendado 8GB)
- **Espacio en Disco**: 500MB para aplicación + backups

### Dependencias

```bash
# Crear entorno virtual (Linux/macOS)
python -m venv venv
source venv/bin/activate

# Crear entorno virtual (Windows)
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Instalación

### Clonar el Repositorio

```bash
# TODO: Añadir URL del repositorio
git clone https://github.com/dwDeez/WMS-CRUD.git
cd WMS-CRUD
```

### Configuración Inicial

1. **Copiar archivo de entorno**:

   ```bash
   # Linux/macOS
   cp .env.example .env

   # Windows
   copy .env.example .env
   ```

2. **Editar configuración** (opcional):

   ```bash
   # Editar variables de entorno
   nano .env
   ```

   Variables disponibles:
   ```env
   FLASK_ENV=development
   SECRET_KEY=tu-secret-key-aqui
   AUDIT_USER=ui_user
   ```

---

## Ejecución

### Desarrollo

#### Linux / macOS

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar aplicación Flask
python run.py
```

La aplicación estará disponible en: `http://localhost:8050`

#### Windows

```cmd
:: Activar entorno virtual
venv\Scripts\activate

:: Ejecutar aplicación Flask
python run.py
```

La aplicación estará disponible en: `http://localhost:8050`

### Dashboard Analítico

El dashboard Dash se ejecuta en un puerto separado:

```bash
# En otra terminal (con venv activado)
python -m app.dashboard
```

Dashboard disponible en: `http://localhost:8051/dashboard/`

### Producción

```bash
# Usando Gunicorn
gunicorn --bind 0.0.0.0:8050 --workers 4 run:app

# O con Docker
docker-compose up --build
```

---

## Uso del Sistema

### Cargar Datos desde CSV

1. Ir a **"📤 Cargar CSV"**
2. Seleccionar archivo CSV
3. El sistema detectará automáticamente las columnas disponibles

Columnas soportadas:
- Picking_ID, Fecha, Hora_generacion, Hora_revision, Hora_despacho
- Auxiliar, Cantidad_pickings_por_auxiliar
- Pasillo, Estanteria, Piso
- Marca_solicitada, Referencia_solicitada
- Categoria_producto, Cantidad, Error_porcentaje

### Generar PDFs de Picking

1. Aplicar filtros deseados (por categoría, auxiliar, pasillo, etc.)
2. Click en **"🖨️ Imprimir filtro"**
3. El PDF generado incluirá:
   - Encabezado con ID, fecha y horas
   - Items agrupados por categoría
   - Ubicación específica de cada producto
   - Totales por picking
   - Pie de página con auxiliar y paginación

### Configurar Columnas

1. Click en **"⚙️ Columnas"**
2. Seleccionar/deseleccionar columnas a mostrar
3. Guardar configuración

### Dashboard

El dashboard incluye:
- Top 15 productos por cantidad
- Serie temporal de despachos
- Distribución de errores
- Mapa de calor de bodega
- Comparación de auxiliares

---

## Estructura del Proyecto

```
CRUD/
├── app/
│   ├── __init__.py          # Factory de Flask
│   ├── config.py            # Configuración
│   ├── models.py            # Modelos SQLAlchemy
│   ├── routes.py           # Rutas y vistas
│   ├── utils.py           # Utilidades
│   ├── pdf_utils.py      # Generación de PDFs
│   └── dashboard.py       # Dashboard Dash
├── backups/               # Backups automáticos
├── tests/                 # Pruebas
├── .github/workflows/     # CI/CD
├── run.py                # Punto de entrada
├── requirements.txt       # Dependencias
├── Dockerfile            # Contenedor Docker
├── docker-compose.yml    # Orquestación
└── dataset_importadora_electrodomesticos_4000.csv
```

---

## Configuración de Production

### Variables de Entorno

```env
FLASK_ENV=production
SECRET_KEY=<generar-key-segura>
AUDIT_USER=usuario_produccion
```

### Base de Datos

Para producción se recomienda PostgreSQL:

```python
# En app/config.py
SQLALCHEMY_DATABASE_URI = "postgresql://user:pass@localhost/dbname"
```

---

## Licencia

MIT License - Ver archivo LICENSE para más detalles.

---





