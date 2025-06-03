# PROMPT DE INSTRUCCIONES: Dashboard de Mercado Farmacéutico

## CONTEXTO Y OBJETIVO
Eres un desarrollador Python experto especializado en Dash y análisis de datos. Tu tarea es crear un dashboard interactivo para análisis de mercado farmacéutico que procese datos de Excel y proporcione visualizaciones dinámicas con filtros específicos para el sistema CENABAST chileno.

## ESPECIFICACIONES TÉCNICAS

### STACK TECNOLÓGICO REQUERIDO
- **Framework**: Dash (Python web framework)
- **Visualizaciones**: Plotly
- **Procesamiento de datos**: Pandas
- **Lectura de archivos**: openpyxl
- **Interfaz**: HTML/CSS con componentes Dash

### ESTRUCTURA DE DATOS DE ENTRADA
Archivo Excel con las siguientes columnas esperadas:
- `Producto` (str): Nombres de medicamentos
- `Precio` (float): Valores unitarios
- `Cantidad` (int): Unidades vendidas  
- `CENABAST` (bool/str): Indicador de participación en sistema público
- `Fecha` (datetime): Fechas de transacciones
- `Categoría` (str): Clasificaciones de productos

## REQUERIMIENTOS FUNCIONALES

### 1. SISTEMA DE FILTROS
Implementa los siguientes controles interactivos:

**A) Modo de Visualización (RadioItems)**
- Opción "Anual": Agrupa datos por año
- Opción "Mensual": Distribución mensual con promedios móviles

**B) Filtro CENABAST (RadioItems)**
- "Con CENABAST": Incluye todos los datos
- "Sin CENABAST": Excluye datos del sistema público
- "Solo CENABAST": Muestra únicamente datos públicos

**C) Selector de Productos (Dropdown)**
- Multi-selección de productos específicos
- Opción "Todos" por defecto

**D) Filtro de Fechas (DatePickerRange)**
- Selector de rango de fechas
- Validación de rangos válidos

### 2. VISUALIZACIONES REQUERIDAS

**A) Gráfico Principal (Líneas de Tiempo)**
```
Especificaciones:
- Tipo: plotly.graph_objects.Scatter con mode='lines+markers'
- Eje X: Fechas (mensual o anual según filtro)
- Eje Y: Precios promedio
- Series múltiples: Una línea por producto seleccionado
- Tooltips: Incluir fecha, producto, precio, cantidad
- Colores: Paleta diferente por producto
```

**B) Gráfico de Barras Comparativo**
```
Especificaciones:
- Tipo: plotly.graph_objects.Bar
- Eje X: Nombres de productos
- Eje Y: Totales agregados (suma de precios × cantidades)
- Ordenamiento: Descendente por valor
- Colores: Consistentes con gráfico principal
```

**C) Tabla de Datos**
```
Especificaciones:
- Componente: dash_table.DataTable
- Paginación: 10 filas por página
- Ordenamiento: Por todas las columnas
- Filtrado: Búsqueda por texto
- Formato: Números con separadores de miles, fechas DD/MM/YYYY
```

### 3. LAYOUT DE LA INTERFAZ

**Estructura HTML requerida:**
```
Container principal
├── Header con título
├── Panel de controles (4 columnas)
│   ├── Modo de visualización
│   ├── Filtro CENABAST  
│   ├── Selector productos
│   └── Selector fechas
├── Fila de totales dinámicos
├── Fila de gráficos (2 columnas)
│   ├── Gráfico de líneas (8 col)
│   └── Gráfico de barras (4 col)
└── Tabla de datos (ancho completo)
```

## LÓGICA DE PROCESAMIENTO DE DATOS

### ALGORITMO PRINCIPAL DEL CALLBACK
```python
def procesar_datos(modo, cenabast_filter, productos, fecha_inicio, fecha_fin):
    # 1. CARGA Y VALIDACIÓN
    datos = cargar_excel()
    validar_columnas_requeridas(datos)
    
    # 2. FILTRADO POR FECHAS
    datos_filtrados = filtrar_por_fechas(datos, fecha_inicio, fecha_fin)
    
    # 3. APLICAR FILTRO CENABAST
    if cenabast_filter == "sin_cenabast":
        datos_filtrados = datos_filtrados[datos_filtrados['CENABAST'] == False]
    elif cenabast_filter == "solo_cenabast":
        datos_filtrados = datos_filtrados[datos_filtrados['CENABAST'] == True]
    # "con_cenabast" no filtra nada
    
    # 4. FILTRAR PRODUCTOS
    if productos != ["Todos"]:
        datos_filtrados = datos_filtrados[datos_filtrados['Producto'].isin(productos)]
    
    # 5. AGREGACIÓN SEGÚN MODO
    if modo == "anual":
        datos_agregados = agrupar_por_año(datos_filtrados)
    else:  # mensual
        datos_agregados = distribuir_mensualmente(datos_filtrados)
    
    # 6. VALIDACIÓN DE DATOS VACÍOS
    if datos_agregados.empty:
        return graficos_vacios(), tabla_vacia(), totales_cero()
    
    # 7. GENERAR VISUALIZACIONES
    grafico_lineas = crear_grafico_lineas(datos_agregados)
    grafico_barras = crear_grafico_barras(datos_agregados)
    tabla = formatear_tabla(datos_filtrados)
    totales = calcular_totales(datos_filtrados)
    
    return grafico_lineas, grafico_barras, tabla, totales
```

### MANEJO DE ERRORES CRÍTICOS
```python
# Error 1: División por cero en cálculos CENABAST
if cenabast_filter == "solo_cenabast":
    datos_cenabast = datos_filtrados[datos_filtrados['CENABAST'] == True]
    if len(datos_cenabast) == 0:
        return mostrar_mensaje_sin_datos_cenabast()

# Error 2: DataFrame vacío después de distribución mensual  
if modo == "mensual":
    datos_mensuales = distribuir_por_meses(datos_filtrados)
    if datos_mensuales.empty:
        datos_mensuales = pd.DataFrame(columns=['Fecha', 'Producto', 'Precio'])
        
# Error 3: Validación de archivos Excel
try:
    datos = pd.read_excel(ruta_archivo)
except FileNotFoundError:
    return mostrar_error_archivo_no_encontrado()
except Exception as e:
    return mostrar_error_lectura_archivo(str(e))
```

## CONFIGURACIONES ESPECÍFICAS

### CALLBACK PRINCIPAL
```python
@app.callback(
    [Output('grafico-principal', 'figure'),
     Output('grafico-barras', 'figure'), 
     Output('tabla-datos', 'data'),
     Output('tabla-datos', 'columns'),
     Output('total-productos', 'children'),
     Output('total-precio', 'children'),
     Output('total-cantidad', 'children')],
    [Input('modo-selector', 'value'),
     Input('cenabast-filter', 'value'),
     Input('producto-selector', 'value'),
     Input('fecha-picker', 'start_date'),
     Input('fecha-picker', 'end_date')]
)
```

### ESTILOS CSS REQUERIDOS
```css
/* Container principal */
.main-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

/* Panel de controles */
.controls-panel {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
}

/* Gráficos */
.graph-container {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 20px;
}

/* Totales dinámicos */
.totals-row {
    background-color: #e9ecef;
    padding: 10px;
    border-radius: 5px;
    margin: 15px 0;
    text-align: center;
}
```

## FUNCIONES AUXILIARES REQUERIDAS

### 1. PROCESAMIENTO DE FECHAS
```python
def distribuir_mensualmente(df):
    """Distribuye datos por meses con promedios móviles"""
    df_monthly = df.groupby([pd.Grouper(key='Fecha', freq='M'), 'Producto']).agg({
        'Precio': 'mean',
        'Cantidad': 'sum'
    }).reset_index()
    return df_monthly

def agrupar_por_año(df):
    """Agrupa datos por año"""
    df_yearly = df.groupby([df['Fecha'].dt.year, 'Producto']).agg({
        'Precio': 'mean', 
        'Cantidad': 'sum'
    }).reset_index()
    return df_yearly
```

### 2. GENERACIÓN DE GRÁFICOS
```python
def crear_grafico_lineas(df):
    """Crea gráfico de líneas temporal"""
    fig = go.Figure()
    productos = df['Producto'].unique()
    
    for i, producto in enumerate(productos):
        data_producto = df[df['Producto'] == producto]
        fig.add_trace(go.Scatter(
            x=data_producto['Fecha'],
            y=data_producto['Precio'],
            mode='lines+markers',
            name=producto,
            line=dict(color=COLORES[i % len(COLORES)]),
            hovertemplate='<b>%{fullData.name}</b><br>Fecha: %{x}<br>Precio: $%{y:,.0f}<extra></extra>'
        ))
    
    fig.update_layout(
        title='Evolución de Precios por Producto',
        xaxis_title='Fecha',
        yaxis_title='Precio Promedio',
        hovermode='x unified'
    )
    return fig

def crear_grafico_barras(df):
    """Crea gráfico de barras comparativo"""
    totales = df.groupby('Producto').agg({
        'Precio': lambda x: (x * df.loc[x.index, 'Cantidad']).sum()
    }).reset_index()
    totales = totales.sort_values('Precio', ascending=False)
    
    fig = go.Figure([go.Bar(
        x=totales['Producto'],
        y=totales['Precio'],
        marker_color='lightblue'
    )])
    
    fig.update_layout(
        title='Total por Producto',
        xaxis_title='Producto',
        yaxis_title='Total ($)'
    )
    return fig
```

### 3. VALIDACIONES Y FORMATEO
```python
def validar_datos_entrada(df):
    """Valida estructura del DataFrame"""
    columnas_requeridas = ['Producto', 'Precio', 'Cantidad', 'CENABAST', 'Fecha']
    missing_cols = [col for col in columnas_requeridas if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Columnas faltantes: {missing_cols}")
    
    # Convertir tipos
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce')
    df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce')
    
    return df

def formatear_tabla(df):
    """Formatea datos para la tabla"""
    df_table = df.copy()
    df_table['Precio'] = df_table['Precio'].apply(lambda x: f"${x:,.0f}")
    df_table['Cantidad'] = df_table['Cantidad'].apply(lambda x: f"{x:,}")
    df_table['Fecha'] = df_table['Fecha'].dt.strftime('%d/%m/%Y')
    return df_table.to_dict('records')
```

## INSTRUCCIONES DE IMPLEMENTACIÓN

### PASO 1: ESTRUCTURA BÁSICA
1. Crear aplicación Dash con `app = dash.Dash(__name__)`
2. Configurar layout principal con componentes HTML y dcc
3. Implementar estructura de carpetas: `assets/`, `data/`

### PASO 2: COMPONENTES DE INTERFAZ
1. Crear controles de filtros con IDs específicos
2. Implementar gráficos vacíos iniciales
3. Configurar tabla con paginación y ordenamiento

### PASO 3: LÓGICA DE DATOS
1. Implementar función de carga de Excel
2. Crear funciones de filtrado y agregación
3. Desarrollar generadores de gráficos

### PASO 4: CALLBACK PRINCIPAL  
1. Definir callback con todos los inputs y outputs
2. Implementar lógica de procesamiento paso a paso
3. Agregar manejo de errores y casos especiales

### PASO 5: VALIDACIONES Y OPTIMIZACIÓN
1. Agregar validaciones de datos de entrada
2. Implementar manejo de errores específicos
3. Optimizar rendimiento para datasets grandes

## CASOS DE PRUEBA OBLIGATORIOS

### DATOS DE PRUEBA
```python
# Caso 1: Datos normales con CENABAST mixto
test_data_1 = pd.DataFrame({
    'Producto': ['MedA', 'MedB', 'MedA', 'MedB'],
    'Precio': [100, 200, 150, 250],
    'Cantidad': [10, 5, 8, 12],
    'CENABAST': [True, False, True, False],
    'Fecha': ['2024-01-15', '2024-01-20', '2024-02-10', '2024-02-15']
})

# Caso 2: Solo datos CENABAST
test_data_2 = pd.DataFrame({
    'Producto': ['MedC'],
    'Precio': [300],
    'Cantidad': [7],
    'CENABAST': [True],
    'Fecha': ['2024-01-10']
})

# Caso 3: Sin datos CENABAST
test_data_3 = pd.DataFrame({
    'Producto': ['MedD'],
    'Precio': [400],
    'Cantidad': [3],
    'CENABAST': [False],
    'Fecha': ['2024-01-05']
})
```

### PRUEBAS REQUERIDAS
1. **Filtro "Solo CENABAST"** con datos mixtos → Debe mostrar solo filas con CENABAST=True
2. **Filtro "Sin CENABAST"** con datos mixtos → Debe excluir filas con CENABAST=True  
3. **Modo mensual** con datos vacíos → Debe mostrar gráfico vacío sin errores
4. **Selección de productos** específicos → Debe filtrar correctamente
5. **Rango de fechas** que no incluye datos → Debe manejar caso vacío
6. **División por cero** en cálculos → Debe validar antes de dividir

## MENSAJE DE ÉXITO
Una vez implementado correctamente, el dashboard debe:
- ✅ Cargar datos Excel automáticamente
- ✅ Responder a todos los filtros sin errores
- ✅ Mostrar visualizaciones coherentes y actualizadas
- ✅ Manejar casos vacíos graciosamente  
- ✅ Calcular totales dinámicos correctamente
- ✅ Funcionar en modo mensual y anual
- ✅ Distinguir correctamente datos CENABAST vs no-CENABAST

**RESULTADO ESPERADO**: Dashboard funcional que permita análisis interactivo completo del mercado farmacéutico con funcionalidades específicas para el sistema público chileno CENABAST.
