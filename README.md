# 📦 Sistema WMS - Importadora Electrodomésticos

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.36-orange?logo=sqlite&logoColor=white)](https://www.sqlalchemy.org/)
[![Dash](https://img.shields.io/badge/Dash-2.18.2-blueviolet?logo=plotly&logoColor=white)](https://dash.plotly.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Sistema de Gestión de Pickings e Inventario** para almacenes de importación de electrodomésticos y llantas.

![Tabla Inventario](./screenshots/tabla_inventario.png)

---

## 📑 Índice de Contenidos

- [🚀 Funcionalidades Principales](#-funcionalidades-principales)
  - [📦 Gestión de Pickings](#-gestión-de-pickings)
  - [📦 Gestión de Inventario](#-gestión-de-inventario)
  - [📊 Dashboard Analítico](#-dashboard-analítico)
- [🛠️ Tecnologías Implementadas](#-tecnologías-implementadas)
  - [⚙️ Python & Frameworks](#-python--frameworks)
  - [📊 Dashboard & Visualización](#-dashboard--visualización)
  - [📄 Generación de Documentos](#-generación-de-documentos)
  - [🔧 Utilidades](#-utilidades)
- [📋 Requisitos del Sistema](#-requisitos-del-sistema)
  - [Entorno de Ejecución](#entorno-de-ejecución)
  - [Dependencias](#dependencias)
- [📥 Instalación](#-instalación)
  - [Clonar el Repositorio](#clonar-el-repositorio)
  - [Configuración Inicial](#configuración-inicial)
- [🚀 Ejecución](#-ejecución)
  - [Desarrollo](#desarrollo)
  - [Dashboard Analítico](#dashboard-analítico-1)
  - [Producción](#producción)
- [📖 Uso del Sistema](#-uso-del-sistema)
  - [📥 Cargar Datos desde CSV](#-cargar-datos-desde-csv)
  - [🖨️ Generar PDFs de Picking](#-generar-pdfs-de-picking)
  - [⚙️ Configurar Columnas](#-configurar-columnas)
  - [📊 Dashboard](#-dashboard)
- [🗂️ Estructura del Proyecto](#-estructura-del-proyecto)
- [📸 Capturas de Pantalla](#-capturas-de-pantalla)
  - [📋 Tabla de Capturas](#-tabla-de-capturas)
  - [📍 Ubicación de Capturas](#-ubicación-de-capturas)
- [🏗️ Estructura de Base de Datos](#-estructura-de-base-de-datos)
  - [Tablas Principales](#tablas-principales)
- [🔧 Configuración de Producción](#-configuración-de-producción)
  - [Variables de Entorno](#variables-de-entorno)
  - [Base de Datos](#base-de-datos)
- [📄 Licencia](#-licencia)
- [📞 Soporte](#-soporte)

---

## 🚀 Funcionalidades Principales

<details>
<summary><b>📦 Gestión de Pickings</b></summary>

- ✅ **CRUD Completo**: Crear, leer, actualizar y eliminar órdenes de picking
- ✅ **Filtros Avanzados**: Filtrar por categoría, auxiliar, ubicación, fecha y más
- ✅ **Generación de PDFs**: Documentos de picking optimizados para distribución en bodega
- ✅ **Importación CSV**: Carga masiva de datos con mapeo automático de columnas

**Capturas:**
- [Crear Picking](./screenshots/crear_picking.png)
- [Listado de Pickings](./screenshots/listado_pickings.png)
- [Generar PDF](./screenshots/generar_pdf.png)

</details>

<details>
<summary><b>📦 Gestión de Inventario</b></summary>

- ✅ **Control por Ubicación**: Gestión de productos por pasillo, estantería y piso
- ✅ **Recepción de Mercancía**: Proceso completo de recepción con escaneo de SKUs
- ✅ **Dashboard Inventario**: Visualización de totales y distribución de productos

**Capturas:**
- [Formulario Recepción](./screenshots/recepcion_mercancia.png)
- [Escaneo Mercancía](./screenshots/escaneo_mercancia.png)
- [Tabla Inventario](./screenshots/tabla_inventario.png)

</details>

<details>
<summary><b>📊 Dashboard Analítico</b></summary>

- ✅ **Top 15 Productos**: Visualización de productos más despachados
- ✅ **Serie Temporal**: Evolución diaria de despachos
- ✅ **Métricas de Error**: Distribución de errores por picking
- ✅ **Mapa de Calor**: Distribución de productos en bodega
- ✅ **Comparación de Auxiliares**: Rendimiento por operario

*Nota: El dashboard se ejecuta en un puerto separado (http://localhost:8051/dashboard/).*

</details>

---

## 🛠️ Tecnologías Implementadas

### Backend
<details>
<summary><b>⚙️ Python & Frameworks</b></summary>

| Tecnología | Versión | Descripción |
|------------|---------|-------------|
| ![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python) | 3.10+ | Lenguaje principal |
| ![Flask](https://img.shields.io/badge/Flask-3.0.0-green?logo=flask) | 3.0.0 | Framework web |
| ![Flask-SQLAlchemy](https://img.shields.io/badge/Flask--SQLAlchemy-3.1.1-orange) | 3.1.1 | ORM para bases de datos |
| ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.36-orange) | 2.0.36 | ORM principal |

</details>

<details>
<summary><b>📊 Dashboard & Visualización</b></summary>

| Tecnología | Versión | Descripción |
|------------|---------|-------------|
| ![Dash](https://img.shields.io/badge/Dash-2.18.2-blueviolet?logo=plotly) | 2.18.2 | Framework para dashboards |
| ![Plotly](https://img.shields.io/badge/Plotly-5.24.1-blue?logo=plotly) | 5.24.1 | Visualizaciones interactivas |
| ![Dash Bootstrap](https://img.shields.io/badge/Dash--Bootstrap--Components-1.6.0-purple) | 1.6.0 | Componentes UI |

</details>

<details>
<summary><b>📄 Generación de Documentos</b></summary>

| Tecnología | Versión | Descripción |
|------------|---------|-------------|
| ![ReportLab](https://img.shields.io/badge/ReportLab-4.2.5-red?logo=pdf) | 4.2.5 | Generación de PDFs |

</details>

<details>
<summary><b>🔧 Utilidades</b></summary>

| Tecnología | Versión | Descripción |
|------------|---------|-------------|
| ![Pandas](https://img.shields.io/badge/Pandas-2.2.3-blue?logo=pandas) | 2.2.3 | Procesamiento de datos |
| ![Gunicorn](https://img.shields.io/badge/Gunicorn-23.0.0-green) | 23.0.0 | Servidor de producción |

</details>

---

## 📋 Requisitos del Sistema

### Entorno de Ejecución
- **Sistema Operativo**: Windows 10+ / Linux (Ubuntu 20.04+) / macOS
- **Python**: Versión 3.10 o superior
- **Memoria RAM**: Mínimo 4GB (recomendado 8GB)
- **Espacio en Disco**: 500MB para aplicación + backups

### Dependencias
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno (Linux/macOS)
source venv/bin/activate

# Activar entorno (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## 📥 Instalación

### Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/WMS-CRUD.git
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
   nano .env
   ```

   Variables disponibles:
   ```env
   FLASK_ENV=development
   SECRET_KEY=tu-secret-key-aqui
   AUDIT_USER=ui_user
   ```

---

## 🚀 Ejecución

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

## 📖 Uso del Sistema

### 📥 Cargar Datos desde CSV
1. Ir a **"📤 Cargar CSV"**
2. Seleccionar archivo CSV
3. El sistema detectará automáticamente las columnas disponibles

### 🖨️ Generar PDFs de Picking
1. Aplicar filtros deseados (por categoría, auxiliar, pasillo, etc.)
2. Click en **"🖨️ Imprimir filtro"**
3. El PDF generado incluirá:
   - Encabezado con ID, fecha y horas
   - Items agrupados por categoría
   - Ubicación específica de cada producto
   - Totales por picking
   - Pie de página con auxiliar y paginación

**Capturas:**
- [Generar PDF](./screenshots/generar_pdf.png)

### ⚙️ Configurar Columnas
1. Click en **"⚙️ Columnas"**
2. Seleccionar/deseleccionar columnas a mostrar
3. Guardar configuración

### 📊 Dashboard
El dashboard incluye:
- Top 15 productos por cantidad
- Serie temporal de despachos
- Distribución de errores
- Mapa de calor de bodega
- Comparación de auxiliares

*Nota: El dashboard se ejecuta en http://localhost:8051/dashboard/*

---

## 🗂️ Estructura del Proyecto

```
WMS-CRUD/
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
├── screenshots/           # Capturas de pantalla ⬅️ Aquí van las capturas
├── .github/workflows/     # CI/CD
├── run.py                # Punto de entrada
├── requirements.txt       # Dependencias
├── Dockerfile            # Contenedor Docker
├── docker-compose.yml    # Orquestación
└── dataset_importadora_electrodomesticos_4000.csv
```

---

## 📸 Capturas de Pantalla

### 📋 Tabla de Capturas

| Funcionalidad | Archivo | Descripción |
|---------------|---------|-------------|
| **Crear Picking** | `crear_picking.png` | Formulario para crear nuevo picking |
| **Listado Pickings** | `listado_pickings.png` | Tabla con listado de pickings |
| **Generar PDF** | `generar_pdf.png` | Proceso de generación de PDF |
| **Recepción Mercancía** | `recepcion_mercancia.png` | Formulario de recepción de mercancía |
| **Escaneo Mercancía** | `escaneo_mercancia.png` | Proceso de escaneo de mercancía |
| **Tabla Inventario** | `tabla_inventario.png` | Tabla de gestión de inventario |

### 📍 Ubicación de Capturas
Todas las capturas se guardan en la carpeta `./screenshots/` del proyecto.

---

## 🏗️ Estructura de Base de Datos

### Tablas Principales
- **Picking**: Órdenes de picking
- **PickingItem**: Items de cada picking
- **Mercancia**: Inventario de productos
- **Recepcion**: Procesos de recepción
- **RecepcionItem**: Items recibidos

---

## 🔧 Configuración de Producción

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

## 📄 Licencia

MIT License - Ver archivo LICENSE para más detalles.

---

## 📞 Soporte

Para reportar problemas o solicitar características, abre un issue en el repositorio.

