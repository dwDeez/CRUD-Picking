# Guía de Plantillas Excel

Esta carpeta contiene plantillas de Excel para importar datos en la aplicación WMS.

## Archivos Disponibles

### 1. plantilla_picking.xlsx
Plantilla para importar datos de picking en la tabla `pickings`.

**Columnas:**
- `Picking_ID` (String): Identificador único del picking (ej: "P-70001")
- `Fecha` (String): Fecha en formato YYYY-MM-DD
- `Hora_generacion` (String): Hora de generación en formato HH:MM:SS
- `Hora_revision` (String): Hora de revisión en formato HH:MM:SS
- `Hora_despacho` (String): Hora de despacho en formato HH:MM:SS
- `Auxiliar` (String): Nombre del auxiliar
- `Cantidad_pickings_por_auxiliar` (Integer): Cantidad de pickings por auxiliar
- `Pasillo` (String): Pasillo del almacén (ej: "A", "B", "C")
- `Estanteria` (String): Número de estantería (ej: "1", "2", "3")
- `Piso` (String): Número de piso (ej: "1", "2")
- `Marca_solicitada` (String): Marca solicitada
- `Referencia_solicitada` (String): Referencia solicitada
- `Categoria_producto` (String): Categoría del producto (ej: "Televisores", "Lavadoras")
- `Cantidad` (Integer): Cantidad total de unidades
- `Unidades_erradas` (Integer): Cantidad de unidades erradas (para cálculo de porcentaje de error)
- `Error_porcentaje` (Float): Porcentaje de error calculado
- `modified_by` (String): Usuario que modificó el registro
- `modified_at` (String): Fecha y hora de última modificación en formato YYYY-MM-DD HH:MM:SS

**Notas:**
- El campo `Unidades_erradas` se usa para calcular el porcentaje de error automáticamente en el editor de picking.
- El campo `Error_porcentaje` puede calcularse automáticamente usando el botón "Calcular % Error".

### 2. plantilla_mercancia.xlsx
Plantilla para importar datos de mercancía en la tabla `mercancia`.

**Columnas:**
- `id` (Integer): Identificador único (auto-generado, puede dejarse vacío)
- `sku` (String): Código SKU del producto
- `marca` (String): Marca del producto
- `referencia` (String): Referencia del producto
- `cantidad` (Integer): Cantidad en stock
- `categoria_producto` (String): Categoría del producto
- `pasillo` (String): Pasillo del almacén
- `estanteria` (String): Número de estantería
- `piso` (String): Número de piso
- `ubicacion` (String): Ubicación completa (ej: "A-1-1")
- `fecha_ingreso` (String): Fecha de ingreso en formato YYYY-MM-DD
- `origen` (String): Origen de la mercancía

**Notas:**
- El campo `ubicacion` se calcula automáticamente como `pasillo-estanteria-piso`.
- El campo `id` se genera automáticamente en la base de datos.

## Uso de las Plantillas

### Importar Datos en la Aplicación

1. **Descargar la plantilla**: Descarga el archivo Excel correspondiente a tu necesidad.
2. **Completar los datos**: Llena las filas con los datos que deseas importar.
3. **Importar en la aplicación**:
   - Ve a la sección correspondiente en la aplicación (ej: "Agregar Mercancía" o "Importar Picking").
   - Usa la función de importación de Excel (si está disponible) o copia y pega los datos.

### Formatos de Fecha y Hora

- **Fecha**: Siempre en formato YYYY-MM-DD (ej: "2024-01-15")
- **Hora**: Siempre en formato HH:MM:SS (ej: "10:00:00")
- **Fecha y hora completa**: YYYY-MM-DD HH:MM:SS (ej: "2024-01-15 10:00:00")

### Ejemplos de Datos

#### Picking
| Picking_ID | Fecha       | Hora_generacion | Auxiliar | Pasillo | Estanteria | Piso | Marca_solicitada | Referencia_solicitada | Cantidad | Unidades_erradas |
|------------|-------------|-----------------|----------|---------|------------|------|------------------|-----------------------|----------|------------------|
| P-70001    | 2024-01-15  | 10:00:00        | Carlos   | A       | 1          | 1    | Sony             | TV-55UHD              | 5        | 1                |

#### Mercancía
| id | sku    | marca | referencia | cantidad | categoria_producto | pasillo | estanteria | piso | ubicacion | fecha_ingreso | origen      |
|----|--------|-------|------------|----------|--------------------|---------|------------|------|-----------|---------------|-------------|
|    | SKU001 | Sony  | TV-55UHD   | 10       | Televisores        | A       | 1          | 1    | A-1-1     | 2024-01-15    | Proveedor A |

## Notas Importantes

1. **Validación de Datos**: La aplicación validará los datos antes de importarlos.
2. **Formato de Columnas**: Asegúrate de que las columnas tengan el formato correcto (texto, número, fecha).
3. **Datos Vacíos**: Algunos campos son obligatorios (ej: `Picking_ID`, `marca`, `referencia`).
4. **Codificación**: Los archivos Excel deben estar codificados en UTF-8.

## Soporte

Si tienes problemas con las plantillas, contacta al administrador del sistema.
