"""
Dashboard de Mercado Farmacéutico - Versión Final Modularizada
Autor: Sistema automatizado
Fecha: Junio 2025

Características principales:
- 4 filtros multi-select: Principio Activo, Organismo, Concentración, Grupo Proveedor
- 3 vistas: Anual, Mensual, Mensualizado
- Filtros adicionales: truncar al mes actual, mostrar solo gráficos seleccionados, CENABAST
- 6 gráficos: 3 básicos + 3 separados por CENABAST cuando se selecciona "Con y Sin"
"""

import dash
from dash import dcc, html
import warnings
warnings.filterwarnings('ignore')

# Importar módulos locales
from data_processor import OptimizedDataProcessor
from callbacks import register_callbacks
from utils import CORPORATE_COLORS

# Configuración de la aplicación
app = dash.Dash(__name__)
app.title = "Dashboard Mercado Farmacéutico - Final"

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

# Registrar todos los callbacks
register_callbacks(app, data_processor)

if __name__ == '__main__':
    app.run(debug=True, port=8052, host='127.0.0.1')
