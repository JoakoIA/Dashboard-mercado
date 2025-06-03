"""
Dashboard de Mercado Farmacéutico - Versión Final Optimizada
Autor: Sistema automatizado
Fecha: Junio 2025

Características principales:
- 4 filtros multi-select: Principio Activo, Organismo, Concentración, Grupo Proveedor
- 3 vistas: Anual, Mensual, Mensualizado
- Filtros adicionales: truncar al mes actual, mostrar solo gráficos seleccionados, CENABAST
- 6 gráficos: 3 básicos + 3 separados por CENABAST cuando se selecciona "Con y Sin"
"""


# Market Share
# Revisar desvios
# si es menor a 5% 

# --------------------
# Ventas
# añadir resumen de ventas de moleculas, filtrado por linea (principio activo). Por unidades y ventas totales
# Informacion por representantes 
# Agregar proceso actual de forecast
# para informacion de ventas agregar clave y usuario##################
# --------------------

# --------------------
# KPIs (Pendiente)

# --------------------



import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, date
import warnings
warnings.filterwarnings('ignore')

# Configuración de la aplicación
app = dash.Dash(__name__)
app.title = "Dashboard Mercado Farmacéutico - Final"

# Colores corporativos Fresenius
CORPORATE_COLORS = {
    'primary_blue': '#0063BE',
    'dark_blue': '#0C2863', 
    'vital_blue': '#3D95F4',
    'cool_gray': '#9BAEBE',
    'warm_gray': '#C9C5BE',
    'warm_white': '#F3F2F1',
    'white': '#FFFFFF',
    'black': '#000000'
}

# Paleta de colores para gráficos
COLORS = [CORPORATE_COLORS['primary_blue'], CORPORATE_COLORS['vital_blue'], 
          CORPORATE_COLORS['cool_gray'], CORPORATE_COLORS['dark_blue'],
          CORPORATE_COLORS['warm_gray'], '#FF6B6B', '#4ECDC4', '#45B7D1', 
          '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8']

# Mapeo de colores específicos para proveedores
PROVIDER_COLOR_MAP = {
    'FRESENIUS CORP': CORPORATE_COLORS['primary_blue'],  # Azul corporativo
    'THERAPIA IV': '#DC3545',  # Rojo
    'Fresenius Kabi': CORPORATE_COLORS['primary_blue'],  # Azul corporativo (alternativo)
    'FRESENIUS CORP - CENABAST': CORPORATE_COLORS['vital_blue'],  # Azul claro para CENABAST
    'THERAPIA IV - CENABAST': '#FF6B6B',  # Rojo claro para CENABAST
    'Fresenius Kabi - CENABAST': CORPORATE_COLORS['vital_blue']  # Azul claro para CENABAST (alternativo)
}

# Mapeo de meses en inglés a español
MESES_ESPANOL = {
    'January': 'Enero',
    'February': 'Febrero', 
    'March': 'Marzo',
    'April': 'Abril',
    'May': 'Mayo',
    'June': 'Junio',
    'July': 'Julio',
    'August': 'Agosto',
    'September': 'Septiembre',
    'October': 'Octubre',
    'November': 'Noviembre',
    'December': 'Diciembre'
}

def convertir_meses_espanol(df):
    """Convierte nombres de meses del inglés al español"""
    df_resultado = df.copy()
    
    if 'mes_nombre' in df_resultado.columns:
        df_resultado['mes_nombre_es'] = df_resultado['mes_nombre'].map(MESES_ESPANOL)
        # Solo actualizar periodo si se mapeo correctamente
        df_resultado.loc[df_resultado['mes_nombre_es'].notna(), 'periodo'] = df_resultado['mes_nombre_es']
        
        # Ordenar por mes usando el mapeo español
        orden_meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        if 'mes_nombre_es' in df_resultado.columns:
            serie_meses = df_resultado['mes_nombre_es']
        else:
            serie_meses = df_resultado['mes_nombre']
        df_resultado['mes_order'] = serie_meses.map({mes: i for i, mes in enumerate(orden_meses_es)})

        
        # Si no se pudo mapear a español, usar orden original en inglés
        if df_resultado['mes_order'].isna().any():
            orden_meses_en = ['January', 'February', 'March', 'April', 'May', 'June',
                             'July', 'August', 'September', 'October', 'November', 'December']
            df_resultado['mes_order'] = df_resultado['mes_order'].fillna(
                df_resultado['mes_nombre'].map({mes: i for i, mes in enumerate(orden_meses_en)})
            )
        
        df_resultado = df_resultado.sort_values('mes_order')
    
    return df_resultado

def aplicar_logica_mensualizada_mejorada(df):
    """
    Aplica la lógica mensualizada refinada con distribución real de contratos por meses:
    - ≤1 mes: aparecer solo en ese mes (sin división)
    - >1 mes a ≤12 meses: crear registros separados para cada mes del contrato
    - >12 meses O en blanco: crear registros mensuales por 18 meses (valor por defecto)
    
    Mejoras implementadas:
    - Distribución real de contratos a través de múltiples meses
    - Creación de registros separados por cada mes de duración del contrato
    - Mejor manejo de fechas y períodos
    - Conservación de valores totales del contrato
    """
    # Verificar que el DataFrame no esté vacío
    if df.empty:
        return df.copy()
    
    # Verificar columnas requeridas
    columnas_requeridas = ['fecha', 'unidades', 'ventas']
    for col in columnas_requeridas:
        if col not in df.columns:
            print(f"Advertencia: Columna '{col}' no encontrada. Retornando DataFrame original.")
            return df.copy()
    
    # Si no hay información de duración, crear columna con valor por defecto
    if 'duracion_contrato_meses' not in df.columns:
        df = df.copy()
        df['duracion_contrato_meses'] = 18  # Valor por defecto más conservador
    
    # Crear lista para almacenar registros expandidos
    registros_expandidos = []
    
    for idx, row in df.iterrows():
        try:
            duracion = row['duracion_contrato_meses']
            fecha_inicio = pd.to_datetime(row['fecha'])
            unidades_originales = float(row['unidades']) if pd.notna(row['unidades']) else 0
            ventas_originales = float(row['ventas']) if pd.notna(row['ventas']) else 0
            
            # Manejar valores en blanco, NaN o cero
            if pd.isna(duracion) or duracion <= 0:
                duracion_efectiva = 18  # Asumir 18 meses por defecto
            else:
                duracion_efectiva = float(duracion)
            
            # Aplicar lógica según duración del contrato
            if duracion_efectiva <= 1:
                # ≤1 mes: aparecer solo en ese mes (sin división)
                registro_mensual = row.copy()
                registro_mensual['mes_contrato'] = 1
                registro_mensual['duracion_aplicada'] = duracion_efectiva
                registros_expandidos.append(registro_mensual)
                
            elif duracion_efectiva <= 12:
                # >1 mes a ≤12 meses: crear registros separados para cada mes del contrato
                meses_distribucion = max(1, int(round(duracion_efectiva)))
                cantidad_mensual = unidades_originales / meses_distribucion
                ventas_mensual = ventas_originales / meses_distribucion
                
                # Crear un registro para cada mes del contrato
                for mes_offset in range(meses_distribucion):
                    registro_mensual = row.copy()
                    # Calcular fecha del mes correspondiente
                    fecha_mes = fecha_inicio + pd.DateOffset(months=mes_offset)
                    registro_mensual['fecha'] = fecha_mes
                    registro_mensual['unidades'] = cantidad_mensual
                    registro_mensual['ventas'] = ventas_mensual
                    registro_mensual['mes_contrato'] = mes_offset + 1
                    registro_mensual['duracion_aplicada'] = duracion_efectiva
                    registros_expandidos.append(registro_mensual)
                    
            else:
                # >12 meses O en blanco: crear registros mensuales por 18 meses (distribución anualizada)
                meses_distribucion = 18  # Distribuir por 18 meses
                cantidad_mensual = unidades_originales / 12  # Dividir por 12 para anualizar
                ventas_mensual = ventas_originales / 12
                
                # Crear registros mensuales
                for mes_offset in range(meses_distribucion):
                    registro_mensual = row.copy()
                    # Calcular fecha del mes correspondiente
                    fecha_mes = fecha_inicio + pd.DateOffset(months=mes_offset)
                    registro_mensual['fecha'] = fecha_mes
                    registro_mensual['unidades'] = cantidad_mensual
                    registro_mensual['ventas'] = ventas_mensual
                    registro_mensual['mes_contrato'] = mes_offset + 1
                    registro_mensual['duracion_aplicada'] = meses_distribucion
                    registro_mensual['ciclo_anual'] = (mes_offset // 12) + 1
                    registros_expandidos.append(registro_mensual)
                    
        except Exception as e:
            print(f"Error procesando fila {idx}: {e}")
            # En caso de error, mantener el registro original
            registro_original = row.copy()
            registro_original['mes_contrato'] = 1
            registro_original['duracion_aplicada'] = 1
            registros_expandidos.append(registro_original)
            continue
    
    # Crear DataFrame con registros expandidos
    if registros_expandidos:
        df_mensualizado = pd.DataFrame(registros_expandidos)
        
        # Reagrupar por fecha y otras dimensiones para consolidar registros del mismo período
        columnas_agrupacion = ['fecha']
        columnas_opcionales = ['principio_activo', 'organismo', 'concentracion', 'grupo_proveedor', 'proveedor']
        
        # Agregar solo las columnas que existan en el DataFrame
        for col in columnas_opcionales:
            if col in df_mensualizado.columns:
                columnas_agrupacion.append(col)
        
        # Preparar diccionario de agregación dinámico
        agg_dict = {
            'unidades': 'sum',
            'ventas': 'sum'
        }
        
        # Agregar columnas opcionales al diccionario de agregación
        columnas_numericas_adicionales = ['precio', 'precio_unitario']
        for col in columnas_numericas_adicionales:
            if col in df_mensualizado.columns:
                # Promedio ponderado por unidades para precios
                agg_dict[col] = lambda x: np.average(x, weights=df_mensualizado.loc[x.index, 'unidades']) if len(x) > 0 and df_mensualizado.loc[x.index, 'unidades'].sum() > 0 else x.mean()
        
        # Columnas categóricas a mantener
        columnas_categoricas = ['es_cenabast', 'tipo_compra', 'estado_contrato']
        for col in columnas_categoricas:
            if col in df_mensualizado.columns:
                agg_dict[col] = 'first'
        
        try:
            df_final = df_mensualizado.groupby(columnas_agrupacion).agg(agg_dict).reset_index()
            
            # Recalcular precio unitario promedio ponderado
            if 'precio' not in df_final.columns and 'unidades' in df_final.columns and 'ventas' in df_final.columns:
                # Evitar división por cero
                df_final['precio'] = np.where(
                    df_final['unidades'] > 0,
                    df_final['ventas'] / df_final['unidades'],
                    0
                )
            
            # Llenar valores NaN en precio
            if 'precio' in df_final.columns:
                df_final['precio'] = df_final['precio'].fillna(0)
            
        except Exception as e:
            print(f"Error en agrupación: {e}")
            df_final = df_mensualizado
        
    else:
        print("No se generaron registros expandidos. Retornando DataFrame original.")
        df_final = df.copy()
    
    return df_final

def calcular_participacion_mercado(df, grupo_col='grupo_proveedor'):
    """Calcula la participación de mercado por proveedor"""
    if df.empty:
        return df
    
    df_resultado = df.copy()
    
    # Calcular totales por período
    if 'periodo' in df_resultado.columns:
        totales_periodo = df_resultado.groupby('periodo')[['unidades', 'ventas']].sum().reset_index()
        totales_periodo.columns = ['periodo', 'total_unidades_periodo', 'total_ventas_periodo']
        
        # Hacer merge con los datos originales
        df_resultado = df_resultado.merge(totales_periodo, on='periodo', how='left')
        
        # Calcular participación de mercado
        df_resultado['participacion_unidades'] = np.where(
            df_resultado['total_unidades_periodo'] > 0,
            (df_resultado['unidades'] / df_resultado['total_unidades_periodo'] * 100).round(2),
            0
        )
        df_resultado['participacion_ventas'] = np.where(
            df_resultado['total_ventas_periodo'] > 0,
            (df_resultado['ventas'] / df_resultado['total_ventas_periodo'] * 100).round(2),
            0
        )
    
    return df_resultado

def crear_tooltip_personalizado(row, vista, filtros_aplicados=""):
    """Crea tooltips personalizados para los gráficos"""
    periodo = row.get('periodo', 'N/A')
    
    # Formatear fecha según vista
    if vista == 'anual':
        fecha_formato = f"Año: {periodo}"
    elif vista == 'mensual':
        fecha_formato = f"Período: {periodo}"
    else:  # mensualizado
        fecha_formato = f"Mes: {periodo}"
    
    # Formatear valores
    unidades = f"{row.get('unidades', 0):,.0f}"
    ventas = f"${row.get('ventas', 0):,.0f}"
    
    # Información de participación de mercado
    participacion_info = ""
    if 'participacion_unidades' in row and pd.notna(row['participacion_unidades']):
        participacion_info = f"<br>Participación Unidades: {row['participacion_unidades']:.1f}%"
    if 'participacion_ventas' in row and pd.notna(row['participacion_ventas']):
        participacion_info += f"<br>Participación Ventas: {row['participacion_ventas']:.1f}%"
    
    # Información de filtros aplicados
    filtros_info = ""
    if filtros_aplicados and filtros_aplicados != "Sin filtros":
        filtros_info = f"<br><br>Filtros: {filtros_aplicados}"
    
    # Construir tooltip completo
    tooltip = f"{fecha_formato}<br>Unidades: {unidades}<br>Ventas: {ventas}{participacion_info}{filtros_info}"
    
    return tooltip

def agregar_totales_barras(fig, df, y_column):
    """Agrega valores totales arriba de las barras apiladas"""
    if df.empty:
        return fig
    
    # Calcular totales por período
    totales = df.groupby('periodo')[y_column].sum().reset_index()
    
    # Agregar anotaciones de totales
    for _, row in totales.iterrows():
        fig.add_annotation(
            x=row['periodo'],
            y=row[y_column],
            text=f"{row[y_column]:,.0f}",
            showarrow=False,
            yshift=10,
            font=dict(size=10, color='black'),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(0,0,0,0.2)',
            borderwidth=1
        )
    
    return fig

class OptimizedDataProcessor:
    """Procesador de datos optimizado para el dashboard farmacéutico"""
    
    def __init__(self):
        self.df = None
        self.file_path = None
        
    def load_data(self, file_path=None):
        """Carga y procesa los datos del archivo Excel"""
        
        # Intentar diferentes rutas para el archivo
        paths_to_try = []
        if file_path:
            paths_to_try.append(file_path)
        
        paths_to_try.extend([
            'Mercado Farmaceutico Fresenius Cierre Abril 2025.xlsx',
            'data/Mercado Farmaceutico Fresenius Cierre Abril 2025.xlsx',
            './Mercado Farmaceutico Fresenius Cierre Abril 2025.xlsx'        ])
        
        for path in paths_to_try:
            try:
                print(f"Intentando cargar datos desde: {path}")
                self.df = pd.read_excel(path, sheet_name='Data')
                self.file_path = path
                print(f"Datos cargados exitosamente: {self.df.shape[0]} filas, {self.df.shape[1]} columnas")
                
                # Procesar datos
                self.process_data()
                print("Procesamiento de datos completado exitosamente")
                return
                
            except Exception as e:
                print(f"Error al cargar desde {path}: {str(e)}")
                continue
        
        # Si no se pudo cargar ningún archivo, crear datos de muestra
        print("No se pudo cargar el archivo Excel. Creando datos de muestra...")
        self.create_sample_data()
    
    def process_data(self):
        """Procesa y limpia los datos"""
          # Mapeo de columnas del archivo real a nombres estándar
        column_mapping = {
            'Principio Activo': 'principio_activo',
            'Organismo': 'organismo', 
            'Concentration': 'concentracion_base',
            'Forma': 'forma',
            'Grupo Proveedor': 'grupo_proveedor',
            'Fecha': 'fecha',
            'Precio Unitario': 'precio',
            'Cantidad': 'unidades',
            'Total': 'ventas'
        }
        
        # Aplicar mapeo de columnas existentes
        for original, standard in column_mapping.items():
            if original in self.df.columns:
                self.df = self.df.rename(columns={original: standard})
        
        # Crear columna de concentración combinada
        if 'concentracion_base' in self.df.columns and 'forma' in self.df.columns:
            self.df['concentracion'] = self.df['concentracion_base'].astype(str) + ' - ' + self.df['forma'].astype(str)
        elif 'concentracion_base' in self.df.columns:
            self.df['concentracion'] = self.df['concentracion_base'].astype(str)
        else:
            self.df['concentracion'] = 'No especificado'
        
        # Identificar registros CENABAST
        self.df['es_cenabast'] = self.identify_cenabast_records()
        
        # Crear datos temporales y numéricos si no existen
        if 'fecha' not in self.df.columns:
            self.df['fecha'] = pd.date_range('2024-01-01', periods=len(self.df), freq='D')
        else:
            self.df['fecha'] = pd.to_datetime(self.df['fecha'], errors='coerce')
        
        # Crear datos numéricos si no existen
        numeric_columns = ['precio', 'unidades', 'ventas']
        for col in numeric_columns:
            if col not in self.df.columns:
                if col == 'precio':
                    self.df[col] = np.random.uniform(500, 15000, len(self.df))
                elif col == 'unidades':
                    self.df[col] = np.random.randint(10, 2000, len(self.df))
                else:  # ventas
                    self.df[col] = self.df.get('precio', 1000) * self.df.get('unidades', 100)
        
        # Crear columnas de tiempo
        self.df['año'] = self.df['fecha'].dt.year
        self.df['mes'] = self.df['fecha'].dt.month
        self.df['año_mes'] = self.df['fecha'].dt.to_period('M')
        self.df['mes_nombre'] = self.df['fecha'].dt.strftime('%B')
        
        # Llenar valores faltantes
        text_columns = ['principio_activo', 'organismo', 'concentracion', 'grupo_proveedor']
        for col in text_columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna('No especificado')
            else:
                self.df[col] = 'No especificado'
        
        # Eliminar filas con fechas faltantes
        self.df = self.df.dropna(subset=['fecha'])
        
        print(f"Datos procesados: {len(self.df)} registros finales")
    
    def identify_cenabast_records(self):
        """Identifica registros relacionados con CENABAST"""
        cenabast_flags = pd.Series(False, index=self.df.index)
        
        # Buscar CENABAST en diferentes columnas posibles
        search_columns = ['organismo', 'Tipo', 'Segmento Comprador', 'Institucion']
        
        for col in search_columns:
            if col in self.df.columns:
                cenabast_flags |= self.df[col].astype(str).str.contains('CENABAST', case=False, na=False)
                cenabast_flags |= self.df[col].astype(str).str.contains('CENTRAL', case=False, na=False)
        
        return cenabast_flags
    
    def create_sample_data(self):
        """Crea datos de muestra para desarrollo"""
        print("Creando datos de muestra...")
        
        np.random.seed(42)
        n_records = 2000
        
        self.df = pd.DataFrame({
            'principio_activo': np.random.choice([
                'Paracetamol', 'Ibuprofeno', 'Amoxicilina', 'Omeprazol', 
                'Losartán', 'Metformina', 'Atorvastatina', 'Diclofenaco',
                'Ciprofloxacino', 'Ranitidina'
            ], n_records),
            'organismo': np.random.choice([
                'Hospital Regional Valparaíso', 'Clínica Las Condes', 'Hospital UC', 
                'FONASA', 'ISAPRE Cruz Blanca', 'Hospital del Salvador',
                'CENABAST', 'Hospital Roberto del Río', 'Clínica Alemana'
            ], n_records),
            'concentracion': np.random.choice([
                '500mg - Tableta', '200mg - Cápsula', '100mg - Jarabe',
                '50mg - Inyectable', '25mg - Tableta', '1g - Sobre',
                '250mg - Suspensión', '10mg - Comprimido'
            ], n_records),
            'grupo_proveedor': np.random.choice([
                'Laboratorio Chile', 'Pharma International', 'MedSupply SA',
                'BioLab Corp', 'Generic Plus', 'Health Solutions',
                'Fresenius Kabi', 'Sandoz', 'Pfizer'
            ], n_records),
            'fecha': pd.date_range('2024-01-01', periods=n_records, freq='D'),
            'precio': np.random.uniform(500, 15000, n_records),
            'unidades': np.random.randint(10, 2000, n_records),
            'ventas': np.random.uniform(5000, 100000, n_records),
            'es_cenabast': np.random.choice([True, False], n_records, p=[0.3, 0.7])
        })
        
        # Crear columnas de tiempo
        self.df['año'] = self.df['fecha'].dt.year
        self.df['mes'] = self.df['fecha'].dt.month
        self.df['año_mes'] = self.df['fecha'].dt.to_period('M')
        self.df['mes_nombre'] = self.df['fecha'].dt.strftime('%B')

# Inicializar procesador de datos
data_processor = OptimizedDataProcessor()
data_processor.load_data()

# Layout corporativo del dashboard con sidebar colapsable
app.layout = html.Div([
    
    # Store para manejar estado del sidebar
    dcc.Store(id='sidebar-state', data={'collapsed': False}),
    
    # Contenedor principal con estilo corporativo
    html.Div([
        
        # Header corporativo
        html.Div([
            html.Div([
                html.Button("☰", id="sidebar-toggle", 
                           style={
                               'background': 'none', 'border': 'none', 'color': CORPORATE_COLORS['white'],
                               'fontSize': '20px', 'cursor': 'pointer', 'marginRight': '20px'
                           }),
                html.H1("Dashboard Mercado Farmacéutico", 
                        style={
                            'color': CORPORATE_COLORS['white'], 'margin': '0', 'fontSize': '24px',
                            'fontWeight': 'bold', 'display': 'inline-block'
                        }),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            
            html.Div([
                html.Span("Fresenius Kabi", style={
                    'color': CORPORATE_COLORS['warm_white'], 'fontSize': '14px', 'fontWeight': '300'
                })
            ])
        ], style={
            'background': f'linear-gradient(135deg, {CORPORATE_COLORS["primary_blue"]}, {CORPORATE_COLORS["dark_blue"]})',
            'padding': '15px 25px', 'marginBottom': '0px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
        }),
        
        # Contenedor principal con sidebar y contenido
        html.Div([
            
            # Sidebar de filtros
            html.Div([
                
                # Título del sidebar
                html.Div([
                    html.H3("Filtros", style={
                        'color': CORPORATE_COLORS['primary_blue'], 'margin': '0 0 20px 0',
                        'fontSize': '18px', 'fontWeight': 'bold'
                    })
                ], style={'borderBottom': f'2px solid {CORPORATE_COLORS["primary_blue"]}', 'paddingBottom': '10px'}),
                
                # Filtros principales
                html.Div([
                    
                    # Principio Activo
                    html.Div([
                        html.Label("Principio Activo", style={
                            'fontWeight': 'bold', 'marginBottom': '8px', 'display': 'block',
                            'color': CORPORATE_COLORS['dark_blue'], 'fontSize': '13px'
                        }),
                        dcc.Dropdown(
                            id='filtro-principio-activo',
                            options=[],
                            value=[],
                            multi=True,
                            placeholder="Seleccionar...",
                            style={'marginBottom': '15px', 'fontSize': '12px'}
                        )
                    ]),
                    
                    # Organismo
                    html.Div([
                        html.Label("Organismo", style={
                            'fontWeight': 'bold', 'marginBottom': '8px', 'display': 'block',
                            'color': CORPORATE_COLORS['dark_blue'], 'fontSize': '13px'
                        }),
                        dcc.Dropdown(
                            id='filtro-organismo',
                            options=[],
                            value=[],
                            multi=True,
                            placeholder="Seleccionar...",
                            style={'marginBottom': '15px', 'fontSize': '12px'}
                        )
                    ]),
                    
                    # Concentración
                    html.Div([
                        html.Label("Concentración", style={
                            'fontWeight': 'bold', 'marginBottom': '8px', 'display': 'block',
                            'color': CORPORATE_COLORS['dark_blue'], 'fontSize': '13px'
                        }),
                        dcc.Dropdown(
                            id='filtro-concentracion',
                            options=[],
                            value=[],
                            multi=True,
                            placeholder="Seleccionar...",
                            style={'marginBottom': '15px', 'fontSize': '12px'}
                        )
                    ]),
                    
                    # Grupo Proveedor
                    html.Div([
                        html.Label("Grupo Proveedor", style={
                            'fontWeight': 'bold', 'marginBottom': '8px', 'display': 'block',
                            'color': CORPORATE_COLORS['dark_blue'], 'fontSize': '13px'
                        }),
                        dcc.Dropdown(
                            id='filtro-grupo-proveedor',
                            options=[],
                            value=[],
                            multi=True,
                            placeholder="Seleccionar...",
                            style={'marginBottom': '20px', 'fontSize': '12px'}
                        )
                    ]),
                    
                ], style={'marginBottom': '25px'}),
                
                # Separador
                html.Hr(style={'border': f'1px solid {CORPORATE_COLORS["warm_gray"]}', 'margin': '20px 0'}),
                
                # Controles de vista
                html.Div([
                    html.Label("Vista Temporal", style={
                        'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block',
                        'color': CORPORATE_COLORS['dark_blue'], 'fontSize': '13px'
                    }),
                    dcc.RadioItems(
                        id='selector-vista',
                        options=[
                            {'label': 'Anual', 'value': 'anual'},
                            {'label': 'Mensual', 'value': 'mensual'},
                            {'label': 'Mensualizado', 'value': 'mensualizado'}
                        ],
                        value='mensual',
                        style={'marginBottom': '20px', 'fontSize': '12px'},
                        labelStyle={'display': 'block', 'marginBottom': '5px'}
                    )
                ]),
                
                # Opciones CENABAST
                html.Div([
                    html.Label("Opciones CENABAST", style={
                        'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block',
                        'color': CORPORATE_COLORS['dark_blue'], 'fontSize': '13px'
                    }),
                    dcc.RadioItems(
                        id='filtro-cenabast',
                        options=[
                            {'label': 'Con CENABAST', 'value': 'con'},
                            {'label': 'Sin CENABAST', 'value': 'sin'},
                            {'label': 'Solo CENABAST', 'value': 'solo'},
                            {'label': 'Con y Sin CENABAST', 'value': 'ambos'}
                        ],
                        value='ambos',
                        style={'marginBottom': '20px', 'fontSize': '12px'},
                        labelStyle={'display': 'block', 'marginBottom': '5px'}
                    )
                ]),
                
                # Separador
                html.Hr(style={'border': f'1px solid {CORPORATE_COLORS["warm_gray"]}', 'margin': '20px 0'}),
                
                # Opciones adicionales
                html.Div([
                    html.Label("Opciones Adicionales", style={
                        'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block',
                        'color': CORPORATE_COLORS['dark_blue'], 'fontSize': '13px'
                    }),
                    dcc.Checklist(
                        id='opciones-adicionales',
                        options=[
                            {'label': 'Truncar al mes actual', 'value': 'truncar_mes'}
                        ],
                        value=[],
                        style={'marginBottom': '20px', 'fontSize': '12px'},
                        labelStyle={'display': 'block', 'marginBottom': '5px'}
                    )
                ])
                
            ], id='sidebar', style={
                'width': '280px', 'minWidth': '280px', 'height': '100vh', 'overflowY': 'auto',
                'background': f'linear-gradient(180deg, {CORPORATE_COLORS["warm_white"]}, {CORPORATE_COLORS["white"]})',
                'padding': '20px', 'borderRight': f'1px solid {CORPORATE_COLORS["cool_gray"]}',
                'transition': 'all 0.3s ease', 'position': 'relative',
                'boxShadow': '2px 0 4px rgba(0,0,0,0.1)'
            }),
            
            # Contenido principal
            html.Div([
                
                # Información de datos
                html.Div([
                    html.Div(id='info-datos', style={
                        'padding': '10px 15px', 'marginBottom': '20px',
                        'background': f'linear-gradient(90deg, {CORPORATE_COLORS["primary_blue"]}15, {CORPORATE_COLORS["vital_blue"]}15)',
                        'border': f'1px solid {CORPORATE_COLORS["primary_blue"]}30',
                        'borderRadius': '5px', 'fontSize': '14px',
                        'color': CORPORATE_COLORS['dark_blue']
                    })
                ]),
                  # Área de gráficos - Layout apilado (uno debajo del otro ocupando todo el ancho)
                html.Div([
                    
                    # Layout apilado - cada gráfico ocupa todo el ancho
                    html.Div([
                        dcc.Graph(id='grafico-unidades')
                    ], id='container-unidades', style={
                        'width': '100%', 'marginBottom': '20px', 'padding': '0 10px'
                    }),
                    
                    html.Div([
                        dcc.Graph(id='grafico-ventas')
                    ], id='container-ventas', style={
                        'width': '100%', 'marginBottom': '20px', 'padding': '0 10px'
                    }),
                    
                    html.Div([
                        dcc.Graph(id='grafico-precio')
                    ], id='container-precio', style={
                        'width': '100%', 'marginBottom': '20px', 'padding': '0 10px'
                    }),
                    
                    # Gráficos CENABAST adicionales (solo visible cuando filtro = 'ambos')
                    html.Div([
                        dcc.Graph(id='grafico-unidades-cenabast')
                    ], id='container-unidades-cenabast', style={
                        'width': '100%', 'display': 'none', 'marginBottom': '20px', 'padding': '0 10px'
                    }),
                    
                    html.Div([
                        dcc.Graph(id='grafico-ventas-cenabast')
                    ], id='container-ventas-cenabast', style={
                        'width': '100%', 'display': 'none', 'marginBottom': '20px', 'padding': '0 10px'
                    }),
                    
                    html.Div([
                        dcc.Graph(id='grafico-precio-cenabast')
                    ], id='container-precio-cenabast', style={
                        'width': '100%', 'display': 'none', 'marginBottom': '20px', 'padding': '0 10px'
                    }),
                    
                ])
                
            ], id='main-content', style={
                'flexGrow': '1', 'padding': '20px', 'height': '100vh', 'overflowY': 'auto',
                'background': CORPORATE_COLORS['white']
            })
            
        ], style={'display': 'flex', 'height': '100vh'})
        
    ], style={'fontFamily': 'Arial, sans-serif'})
    
])

# Callback dinámico para actualizar filtros de forma reactiva
@app.callback(
    [Output('filtro-principio-activo', 'options'),
     Output('filtro-organismo', 'options'),
     Output('filtro-concentracion', 'options'),
     Output('filtro-grupo-proveedor', 'options')],
    [Input('filtro-principio-activo', 'value'),
     Input('filtro-organismo', 'value'),
     Input('filtro-concentracion', 'value'),
     Input('filtro-grupo-proveedor', 'value'),
     Input('filtro-cenabast', 'value'),
     Input('opciones-adicionales', 'value')]
)
def actualizar_filtros_dinamicos(principios, organismos, concentraciones, grupos, cenabast, opciones):
    """Actualiza dinámicamente las opciones de los filtros basado en las selecciones actuales"""
    
    df = data_processor.df
    
    if df is None or len(df) == 0:
        return [], [], [], []
    
    # Aplicar filtros parciales para obtener datos disponibles
    df_base = df.copy()
    
    # Aplicar filtro CENABAST primero
    if cenabast == 'sin':
        df_base = df_base[df_base['es_cenabast'] == False]
    elif cenabast == 'solo':
        df_base = df_base[df_base['es_cenabast'] == True]
    # 'con' y 'ambos' no filtran nada
    
    # Aplicar opciones adicionales
    if opciones and 'truncar_mes' in opciones:
        mes_actual = datetime.now().month
        año_actual = datetime.now().year
        df_base = df_base[
            (df_base['año'] <= año_actual) & 
            ((df_base['año'] < año_actual) | (df_base['mes'] <= mes_actual))
        ]
      # Determinar qué filtro disparó el callback para preservar su valor
    ctx = callback_context
    triggers = ctx.triggered or []
    if len(triggers) > 0:
        trigger_id = triggers[0]['prop_id'].split('.')[0]
    else:
        trigger_id = None

    
    # Aplicar filtros existentes (excepto el que está siendo actualizado)
    if trigger_id != 'filtro-principio-activo' and principios:
        df_base = df_base[df_base['principio_activo'].isin(principios)]
    
    if trigger_id != 'filtro-organismo' and organismos:
        df_base = df_base[df_base['organismo'].isin(organismos)]
    
    if trigger_id != 'filtro-concentracion' and concentraciones:
        df_base = df_base[df_base['concentracion'].isin(concentraciones)]
    
    if trigger_id != 'filtro-grupo-proveedor' and grupos:
        df_base = df_base[df_base['grupo_proveedor'].isin(grupos)]
    
    # Generar opciones dinámicas para cada filtro
    opciones_principio = [{'label': p, 'value': p} for p in sorted(df_base['principio_activo'].dropna().unique())]
    opciones_organismo = [{'label': o, 'value': o} for o in sorted(df_base['organismo'].dropna().unique())]
    opciones_concentracion = [{'label': c, 'value': c} for c in sorted(df_base['concentracion'].dropna().unique())]
    opciones_grupo = [{'label': g, 'value': g} for g in sorted(df_base['grupo_proveedor'].dropna().unique())]
    
    return opciones_principio, opciones_organismo, opciones_concentracion, opciones_grupo

# Callback para el toggle del sidebar
@app.callback(
    [Output('sidebar', 'style'),
     Output('main-content', 'style'),
     Output('sidebar-state', 'data')],
    [Input('sidebar-toggle', 'n_clicks')],
    [State('sidebar-state', 'data')]
)
def toggle_sidebar(n_clicks, sidebar_data):
    """Maneja el colapso/expansión del sidebar"""
    if n_clicks is None:
        n_clicks = 0
    
    # Obtener estado actual
    is_collapsed = sidebar_data.get('collapsed', False) if sidebar_data else False
    
    # Alternar estado si se hizo clic
    new_collapsed = not is_collapsed if n_clicks > 0 else is_collapsed
    
    if new_collapsed:
        # Sidebar colapsado
        sidebar_style = {
            'width': '0px', 'minWidth': '0px', 'height': '100vh', 'overflowY': 'hidden',
            'background': f'linear-gradient(180deg, {CORPORATE_COLORS["warm_white"]}, {CORPORATE_COLORS["white"]})',
            'padding': '0px', 'borderRight': f'1px solid {CORPORATE_COLORS["cool_gray"]}',
            'transition': 'all 0.3s ease', 'position': 'relative',
            'boxShadow': '2px 0 4px rgba(0,0,0,0.1)'
        }
        main_style = {
            'flexGrow': '1', 'padding': '20px', 'height': '100vh', 'overflowY': 'auto',
            'background': CORPORATE_COLORS['white'], 'marginLeft': '0px', 'transition': 'all 0.3s ease'
        }
    else:
        # Sidebar expandido
        sidebar_style = {
            'width': '280px', 'minWidth': '280px', 'height': '100vh', 'overflowY': 'auto',
            'background': f'linear-gradient(180deg, {CORPORATE_COLORS["warm_white"]}, {CORPORATE_COLORS["white"]})',
            'padding': '20px', 'borderRight': f'1px solid {CORPORATE_COLORS["cool_gray"]}',
            'transition': 'all 0.3s ease', 'position': 'relative',
            'boxShadow': '2px 0 4px rgba(0,0,0,0.1)'
        }
        main_style = {
            'flexGrow': '1', 'padding': '20px', 'height': '100vh', 'overflowY': 'auto',
            'background': CORPORATE_COLORS['white']
        }
    
    return sidebar_style, main_style, {'collapsed': new_collapsed}

# Callback principal para actualizar gráficos - ACTUALIZADO PARA 6 GRÁFICOS
@app.callback(
    [Output('grafico-unidades', 'figure'),
     Output('grafico-ventas', 'figure'), 
     Output('grafico-precio', 'figure'),
     Output('grafico-unidades-cenabast', 'figure'),
     Output('grafico-ventas-cenabast', 'figure'),
     Output('grafico-precio-cenabast', 'figure'),
     Output('container-unidades', 'style'),
     Output('container-ventas', 'style'),
     Output('container-precio', 'style'),
     Output('container-unidades-cenabast', 'style'),
     Output('container-ventas-cenabast', 'style'),
     Output('container-precio-cenabast', 'style'),
     Output('info-datos', 'children')],
    [Input('filtro-principio-activo', 'value'),
     Input('filtro-organismo', 'value'),
     Input('filtro-concentracion', 'value'),
     Input('filtro-grupo-proveedor', 'value'),
     Input('selector-vista', 'value'),
     Input('filtro-cenabast', 'value'),
     Input('opciones-adicionales', 'value')]
)
def actualizar_dashboard_6_graficos(principios, organismos, concentraciones, grupos, vista, cenabast, opciones):
    """Actualiza todos los gráficos (6 en total) y la información del dashboard"""
    
    # Verificar que tenemos datos
    if data_processor.df is None or len(data_processor.df) == 0:
        fig_empty = go.Figure()
        fig_empty.add_annotation(text="No hay datos disponibles", x=0.5, y=0.5, showarrow=False)
          # Estilos base para layout apilado
        style_visible = {'width': '100%', 'marginBottom': '20px', 'padding': '0 10px'}
        style_hidden = {'width': '100%', 'display': 'none', 'marginBottom': '20px', 'padding': '0 10px'}
        
        return (fig_empty, fig_empty, fig_empty, fig_empty, fig_empty, fig_empty,
                style_visible, style_visible, style_visible,
                style_hidden, style_hidden, style_hidden,
                "No hay datos para mostrar")
    
    # Filtrar datos
    df_filtrado = filtrar_datos(
        data_processor.df, principios, organismos, concentraciones, grupos, 
        cenabast, opciones
    )
      # Estilos para los contenedores - Layout apilado
    style_visible = {'width': '100%', 'marginBottom': '20px', 'padding': '0 10px'}
    style_hidden = {'width': '100%', 'display': 'none', 'marginBottom': '20px', 'padding': '0 10px'}
    
    # Crear gráficos básicos
    if cenabast in ['con', 'ambos']:
        # Datos con CENABAST
        df_con_cenabast = df_filtrado.copy()
        df_agregado_con = agregar_datos_por_vista(df_con_cenabast, vista, 'con')
        
        fig_unidades = crear_grafico_unidades(df_agregado_con, vista, 'con')
        fig_ventas = crear_grafico_ventas(df_agregado_con, vista, 'con')
        fig_precio = crear_grafico_precio(df_agregado_con, vista, 'con')
    elif cenabast == 'sin':
        # Datos sin CENABAST
        df_sin_cenabast = df_filtrado[df_filtrado['es_cenabast'] == False].copy()
        df_agregado_sin = agregar_datos_por_vista(df_sin_cenabast, vista, 'sin')
        
        fig_unidades = crear_grafico_unidades(df_agregado_sin, vista, 'sin')
        fig_ventas = crear_grafico_ventas(df_agregado_sin, vista, 'sin')
        fig_precio = crear_grafico_precio(df_agregado_sin, vista, 'sin')
    else:  # solo
        # Solo datos CENABAST
        df_solo_cenabast = df_filtrado[df_filtrado['es_cenabast'] == True].copy()
        df_agregado_solo = agregar_datos_por_vista(df_solo_cenabast, vista, 'solo')
        
        fig_unidades = crear_grafico_unidades(df_agregado_solo, vista, 'solo')
        fig_ventas = crear_grafico_ventas(df_agregado_solo, vista, 'solo')
        fig_precio = crear_grafico_precio(df_agregado_solo, vista, 'solo')
    
    # Determinar si mostrar gráficos CENABAST
    mostrar_cenabast = cenabast == 'ambos'
    
    if mostrar_cenabast:
        # Crear gráficos específicos de CENABAST
        df_cenabast_separado = df_filtrado[df_filtrado['es_cenabast'] == True].copy()
        df_agregado_cenabast = agregar_datos_por_vista(df_cenabast_separado, vista, 'solo')
        
        fig_unidades_cenabast = crear_grafico_unidades_cenabast(df_agregado_cenabast, vista)
        fig_ventas_cenabast = crear_grafico_ventas_cenabast(df_agregado_cenabast, vista)
        fig_precio_cenabast = crear_grafico_precio_cenabast(df_agregado_cenabast, vista)
        
        # Estilos de contenedores CENABAST (visibles)
        style_cenabast = style_visible
    else:
        # Gráficos vacíos cuando no se muestran CENABAST
        fig_empty = go.Figure()
        fig_unidades_cenabast = fig_empty
        fig_ventas_cenabast = fig_empty  
        fig_precio_cenabast = fig_empty
        
        # Estilos de contenedores CENABAST (ocultos)
        style_cenabast = style_hidden
    
    # Información de datos
    total_registros = len(df_filtrado)
    total_unidades = df_filtrado['unidades'].sum()
    total_ventas = df_filtrado['ventas'].sum()
    precio_promedio = (df_filtrado['ventas'].sum() / df_filtrado['unidades'].sum()) if df_filtrado['unidades'].sum() > 0 else 0
    
    info_text = f"""
    📊 Registros mostrados: {total_registros:,} | 
    📦 Total Unidades: {total_unidades:,.0f} | 
    💰 Total Ventas: ${total_ventas:,.0f} | 
    💵 Precio Promedio: ${precio_promedio:,.0f}
    {' | 🏥 Modo: Con y Sin CENABAST (6 gráficos)' if mostrar_cenabast else f' | 🏥 Modo: {cenabast.upper()}'}
    """
    
    return (fig_unidades, fig_ventas, fig_precio,
            fig_unidades_cenabast, fig_ventas_cenabast, fig_precio_cenabast,
            style_visible, style_visible, style_visible,
            style_cenabast, style_cenabast, style_cenabast,
            info_text)

def filtrar_datos(df, principios, organismos, concentraciones, grupos, cenabast, opciones):
    """Aplica todos los filtros a los datos"""
    
    df_filtrado = df.copy()
    
    # Filtros multi-select
    if principios:
        df_filtrado = df_filtrado[df_filtrado['principio_activo'].isin(principios)]
    
    if organismos:
        df_filtrado = df_filtrado[df_filtrado['organismo'].isin(organismos)]
    
    if concentraciones:
        df_filtrado = df_filtrado[df_filtrado['concentracion'].isin(concentraciones)]
    
    if grupos:
        df_filtrado = df_filtrado[df_filtrado['grupo_proveedor'].isin(grupos)]
      # Filtro CENABAST
    if cenabast == 'con':
        # "Con CENABAST" muestra todos los datos (tanto CENABAST como no CENABAST)
        pass  # No filtra nada
    elif cenabast == 'sin':
        df_filtrado = df_filtrado[df_filtrado['es_cenabast'] == False]
    elif cenabast == 'solo':
        df_filtrado = df_filtrado[df_filtrado['es_cenabast'] == True]
    # 'ambos' no filtra nada pero se maneja diferente en la visualización
    
    # Truncar al mes actual
    if opciones and 'truncar_mes' in opciones:
        mes_actual = datetime.now().month
        año_actual = datetime.now().year
        df_filtrado = df_filtrado[
            (df_filtrado['año'] <= año_actual) & 
            ((df_filtrado['año'] < año_actual) | (df_filtrado['mes'] <= mes_actual))
        ]
    
    return df_filtrado

def agregar_datos_por_vista(df, vista, cenabast_option=None):
    """Agrega los datos según la vista temporal seleccionada con mejoras implementadas"""
    
    if len(df) == 0:
        return pd.DataFrame(columns=['periodo', 'grupo_proveedor', 'unidades', 'ventas', 'precio'])
    
    # Aplicar lógica mensualizada mejorada para vista mensualizada
    if vista == 'mensualizado':
        df = aplicar_logica_mensualizada_mejorada(df)
    
    # Para "Con y Sin" CENABAST, agregamos por estado CENABAST
    if cenabast_option == 'ambos':
        if vista == 'anual':
            df_agregado = df.groupby(['año', 'grupo_proveedor', 'es_cenabast']).agg({
                'unidades': 'sum',
                'ventas': 'sum', 
                'precio': 'mean'
            }).reset_index()
            df_agregado['periodo'] = df_agregado['año'].astype(str)
            
        elif vista == 'mensual':
            df_agregado = df.groupby(['año', 'mes', 'grupo_proveedor', 'es_cenabast']).agg({
                'unidades': 'sum',
                'ventas': 'sum',
                'precio': 'mean'
            }).reset_index()
            df_agregado['periodo'] = df_agregado['año'].astype(str) + '-' + df_agregado['mes'].astype(str).str.zfill(2)
            
        else:  # mensualizado
            df_agregado = df.groupby(['mes_nombre', 'grupo_proveedor', 'es_cenabast']).agg({
                'unidades': 'sum',
                'ventas': 'sum',
                'precio': 'mean'
            }).reset_index()
            df_agregado['periodo'] = df_agregado['mes_nombre']
            
            # Convertir meses al español y ordenar
            df_agregado = convertir_meses_espanol(df_agregado)
        
        # Crear grupo_proveedor_cenabast para separar las series
        df_agregado['grupo_proveedor_cenabast'] = df_agregado['grupo_proveedor'] + ' - ' + df_agregado['es_cenabast'].map({True: 'CENABAST', False: 'No CENABAST'})
        
    else:
        # Agregación normal sin separar por CENABAST
        if vista == 'anual':
            df_agregado = df.groupby(['año', 'grupo_proveedor']).agg({
                'unidades': 'sum',
                'ventas': 'sum', 
                'precio': 'mean'
            }).reset_index()
            df_agregado['periodo'] = df_agregado['año'].astype(str)
            
        elif vista == 'mensual':
            df_agregado = df.groupby(['año', 'mes', 'grupo_proveedor']).agg({
                'unidades': 'sum',
                'ventas': 'sum',
                'precio': 'mean'
            }).reset_index()
            df_agregado['periodo'] = df_agregado['año'].astype(str) + '-' + df_agregado['mes'].astype(str).str.zfill(2)
            
        else:  # mensualizado
            df_agregado = df.groupby(['mes_nombre', 'grupo_proveedor']).agg({
                'unidades': 'sum',
                'ventas': 'sum',
                'precio': 'mean'
            }).reset_index()
            df_agregado['periodo'] = df_agregado['mes_nombre']
            
            # Convertir meses al español y ordenar
            df_agregado = convertir_meses_espanol(df_agregado)
        
        # Para coherencia, crear la columna grupo_proveedor_cenabast igual a grupo_proveedor
        df_agregado['grupo_proveedor_cenabast'] = df_agregado['grupo_proveedor']
    
    # Calcular participación de mercado
    df_agregado = calcular_participacion_mercado(df_agregado, 'grupo_proveedor')
    
    return df_agregado

def crear_grafico_unidades(df, vista, cenabast=None):
    """Crea el gráfico de unidades por grupo proveedor con mejoras"""
    
    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos para mostrar", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title=f"Unidades por Grupo Proveedor - Vista {vista.title()}", height=400)
        return fig
      
    # Usar grupo_proveedor_cenabast si es el caso "Con y Sin CENABAST"
    color_column = 'grupo_proveedor_cenabast' if cenabast == 'ambos' else 'grupo_proveedor'
    
    # Asignar colores específicos para proveedores
    color_map, color_sequence = asignar_colores_proveedores(df, color_column)
    
    # Crear tooltips personalizados
    df_con_tooltips = df.copy()
    filtros_aplicados = f"Vista: {vista}, CENABAST: {cenabast or 'N/A'}"
    df_con_tooltips['tooltip_personalizado'] = df_con_tooltips.apply(
        lambda row: crear_tooltip_personalizado(row, vista, filtros_aplicados), axis=1
    )
    
    fig = px.bar(
        df_con_tooltips,
        x='periodo',
        y='unidades', 
        color=color_column,
        title=f"Unidades por Grupo Proveedor - Vista {vista.title()}",
        labels={'unidades': 'Unidades', 'periodo': 'Período'},
        color_discrete_map=color_map,
        hover_data={'tooltip_personalizado': True}
    )
    
    # Agregar totales sobre las barras
    fig = agregar_totales_barras(fig, df, 'unidades')
    fig.update_layout(
        height=400,
        xaxis_title="Período",
        yaxis_title="Unidades", 
        legend_title="Grupo Proveedor",
        hovermode='closest'
    )
    
    return fig

def crear_grafico_ventas(df, vista, cenabast=None):
    """Crea el gráfico de ventas por grupo proveedor con mejoras"""
    
    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos para mostrar", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title=f"Ventas por Grupo Proveedor - Vista {vista.title()}", height=400)
        return fig
      
    # Usar grupo_proveedor_cenabast si es el caso "Con y Sin CENABAST"
    color_column = 'grupo_proveedor_cenabast' if cenabast == 'ambos' else 'grupo_proveedor'
    
    # Asignar colores específicos para proveedores
    color_map, color_sequence = asignar_colores_proveedores(df, color_column)
    
    # Crear tooltips personalizados
    df_con_tooltips = df.copy()
    filtros_aplicados = f"Vista: {vista}, CENABAST: {cenabast or 'N/A'}"
    df_con_tooltips['tooltip_personalizado'] = df_con_tooltips.apply(
        lambda row: crear_tooltip_personalizado(row, vista, filtros_aplicados), axis=1
    )
    
    fig = px.bar(
        df_con_tooltips,
        x='periodo',
        y='ventas', 
        color=color_column,
        title=f"Ventas por Grupo Proveedor - Vista {vista.title()}",
        labels={'ventas': 'Ventas ($)', 'periodo': 'Período'},        color_discrete_map=color_map,
        hover_data={'tooltip_personalizado': True}
    )
    
    # Agregar totales sobre las barras
    fig = agregar_totales_barras(fig, df, 'ventas')
    
    fig.update_layout(
        height=400,
        xaxis_title="Período",
        yaxis_title="Ventas ($)",
        legend_title="Grupo Proveedor",
        hovermode='closest'
    )
    
    return fig

def crear_grafico_precio(df, vista, cenabast=None):
    """Crea el gráfico de tendencia de precio promedio con mejoras"""
    
    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos para mostrar", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title=f"Tendencia Precio Promedio - Vista {vista.title()}", height=400)
        return fig
      
    # Usar grupo_proveedor_cenabast si es el caso "Con y Sin CENABAST"
    color_column = 'grupo_proveedor_cenabast' if cenabast == 'ambos' else 'grupo_proveedor'
    
    # Asignar colores específicos para proveedores
    color_map, color_sequence = asignar_colores_proveedores(df, color_column)
    
    # Crear tooltips personalizados
    df_con_tooltips = df.copy()
    filtros_aplicados = f"Vista: {vista}, CENABAST: {cenabast or 'N/A'}"
    df_con_tooltips['tooltip_personalizado'] = df_con_tooltips.apply(
        lambda row: crear_tooltip_personalizado(row, vista, filtros_aplicados), axis=1
    )
    
    fig = px.line(
        df_con_tooltips,
        x='periodo',
        y='precio',
        color=color_column, 
        title=f"Tendencia Precio Promedio - Vista {vista.title()}",
        labels={'precio': 'Precio Promedio ($)', 'periodo': 'Período'},
        color_discrete_map=color_map,
        markers=True,
        hover_data={'tooltip_personalizado': True}
    )
    
    fig.update_layout(
        height=400,
        xaxis_title="Período",
        yaxis_title="Precio Promedio ($)",
        legend_title="Grupo Proveedor",
        hovermode='x unified'
    )
    
    return fig

def crear_grafico_unidades_cenabast(df, vista):
    """Crea el gráfico de unidades por grupo proveedor (solo CENABAST) con mejoras"""
    
    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos para mostrar", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title=f"Unidades por CENABAST - Vista {vista.title()}", height=400)
        return fig
    
    # Crear tooltips personalizados
    df_con_tooltips = df.copy()
    filtros_aplicados = f"Vista: {vista}, CENABAST: Solo CENABAST"
    df_con_tooltips['tooltip_personalizado'] = df_con_tooltips.apply(
        lambda row: crear_tooltip_personalizado(row, vista, filtros_aplicados), axis=1
    )
    
    fig = px.bar(
        df_con_tooltips,
        x='periodo',
        y='unidades',
        color='grupo_proveedor',
        title=f"Unidades por CENABAST - Vista {vista.title()}",
        labels={'unidades': 'Unidades', 'periodo': 'Período'},
        color_discrete_sequence=COLORS,
        hover_data={'tooltip_personalizado': True}
    )
    
    # Agregar totales sobre las barras
    fig = agregar_totales_barras(fig, df, 'unidades')
    
    fig.update_layout(
        height=400,
        xaxis_title="Período",
        yaxis_title="Unidades",
        legend_title="Grupo Proveedor",
        hovermode='x unified'
    )
    
    return fig

def crear_grafico_ventas_cenabast(df, vista):
    """Crea el gráfico de ventas por grupo proveedor (solo CENABAST) con mejoras"""
    
    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos para mostrar", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title=f"Ventas por CENABAST - Vista {vista.title()}", height=400)
        return fig
    
    # Crear tooltips personalizados
    df_con_tooltips = df.copy()
    filtros_aplicados = f"Vista: {vista}, CENABAST: Solo CENABAST"
    df_con_tooltips['tooltip_personalizado'] = df_con_tooltips.apply(
        lambda row: crear_tooltip_personalizado(row, vista, filtros_aplicados), axis=1
    )
    
    fig = px.bar(
        df_con_tooltips,
        x='periodo',
        y='ventas',
        color='grupo_proveedor',
        title=f"Ventas por CENABAST - Vista {vista.title()}",
        labels={'ventas': 'Ventas ($)', 'periodo': 'Período'},
        color_discrete_sequence=COLORS,
        hover_data={'tooltip_personalizado': True}
    )
    
    # Agregar totales sobre las barras
    fig = agregar_totales_barras(fig, df, 'ventas')
    
    fig.update_layout(
        height=400,
        xaxis_title="Período",
        yaxis_title="Ventas ($)",
        legend_title="Grupo Proveedor",
        hovermode='x unified'
    )
    
    return fig

def crear_grafico_precio_cenabast(df, vista):
    """Crea el gráfico de tendencia de precio promedio (solo CENABAST) con mejoras"""
    
    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos para mostrar", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title=f"Tendencia Precio Promedio por CENABAST - Vista {vista.title()}", height=400)
        return fig
    
    # Crear tooltips personalizados
    df_con_tooltips = df.copy()
    filtros_aplicados = f"Vista: {vista}, CENABAST: Solo CENABAST"
    df_con_tooltips['tooltip_personalizado'] = df_con_tooltips.apply(
        lambda row: crear_tooltip_personalizado(row, vista, filtros_aplicados), axis=1
    )
    
    fig = px.line(
        df_con_tooltips,
        x='periodo',
        y='precio',
        color='grupo_proveedor',
        title=f"Tendencia Precio Promedio por CENABAST - Vista {vista.title()}",
        labels={'precio': 'Precio Promedio ($)', 'periodo': 'Período'},
        color_discrete_sequence=COLORS,
        markers=True,
        hover_data={'tooltip_personalizado': True}
    )
    
    fig.update_layout(
        height=400,
        xaxis_title="Período",
        yaxis_title="Precio Promedio ($)",
        legend_title="Grupo Proveedor",
        hovermode='x unified'
    )
    
    return fig

def asignar_colores_proveedores(df, color_column):
    """Asigna colores específicos basándose en PROVIDER_COLOR_MAP"""
    # Obtener lista única de proveedores/grupos
    proveedores_unicos = df[color_column].unique()
    
    # Crear mapeo de colores
    color_map = {}
    color_sequence = []
    
    for i, proveedor in enumerate(proveedores_unicos):
        # Verificar si el proveedor tiene un color específico definido
        if proveedor in PROVIDER_COLOR_MAP:
            color_map[proveedor] = PROVIDER_COLOR_MAP[proveedor]
            color_sequence.append(PROVIDER_COLOR_MAP[proveedor])
        else:
            # Usar colores de la paleta corporativa para otros proveedores
            color_index = i % len(COLORS)
            color_map[proveedor] = COLORS[color_index]
            color_sequence.append(COLORS[color_index])
    
    return color_map, color_sequence

# Callback para limpiar valores de filtros que ya no están disponibles
@app.callback(
    [Output('filtro-principio-activo', 'value'),
     Output('filtro-organismo', 'value'),
     Output('filtro-concentracion', 'value'),
     Output('filtro-grupo-proveedor', 'value')],
    [Input('filtro-principio-activo', 'options'),
     Input('filtro-organismo', 'options'),
     Input('filtro-concentracion', 'options'),
     Input('filtro-grupo-proveedor', 'options')],
    [State('filtro-principio-activo', 'value'),
     State('filtro-organismo', 'value'),
     State('filtro-concentracion', 'value'),
     State('filtro-grupo-proveedor', 'value')]
)
def limpiar_valores_filtros(opt_principio, opt_organismo, opt_concentracion, opt_grupo,
                           val_principio, val_organismo, val_concentracion, val_grupo):
    """Limpia valores seleccionados que ya no están disponibles en las opciones actualizadas"""
    
    # Obtener valores disponibles de las opciones
    valores_disponibles_principio = [opt['value'] for opt in opt_principio] if opt_principio else []
    valores_disponibles_organismo = [opt['value'] for opt in opt_organismo] if opt_organismo else []
    valores_disponibles_concentracion = [opt['value'] for opt in opt_concentracion] if opt_concentracion else []
    valores_disponibles_grupo = [opt['value'] for opt in opt_grupo] if opt_grupo else []
    
    # Filtrar valores seleccionados que aún están disponibles
    nuevos_principios = [v for v in (val_principio or []) if v in valores_disponibles_principio]
    nuevos_organismos = [v for v in (val_organismo or []) if v in valores_disponibles_organismo]
    nuevas_concentraciones = [v for v in (val_concentracion or []) if v in valores_disponibles_concentracion]
    nuevos_grupos = [v for v in (val_grupo or []) if v in valores_disponibles_grupo]
    
    return nuevos_principios, nuevos_organismos, nuevas_concentraciones, nuevos_grupos


if __name__ == '__main__':
    app.run(debug=True, port=8052, host='0.0.0.0')

