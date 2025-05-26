import os

elementos = os.listdir()
#ver elementos dentro de la carpeta data
if 'data' in elementos:
    elementos = os.listdir('data')
else:
    print("La carpeta 'data' no existe en el directorio actual.")
    elementos = []
    
print(elementos)

import re
import time
import datetime
import numpy as np
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go

# ————— Configuración de colores y estilos —————
CORPORATE_BLUE = '#0063BE'
DARK_BLUE      = '#0C2863'
COOL_GRAY      = '#9BAEBE'
WARM_WHITE     = '#F3F2F1'
BLACK          = '#000000'
WHITE          = '#FFFFFF'
THERAPIA_COLOR = '#d62728'
OTHER_COLORS   = ['#3D95F4', '#C9C5BE', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

dropdown_style = {
    'backgroundColor': WHITE,
    'color': BLACK,
    'border': f'1px solid {COOL_GRAY}',
    'borderRadius': '4px',
    'maxHeight': '300px',
}

# ————— Carga y preprocesamiento estático —————
df = pd.read_excel(r'data\Mercado Farmaceutico Fresenius Cierre Abril 2025.xlsx', sheet_name='Data')
# ... resto de tu código ...
print(df)