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
df = pd.read_excel(r'data/Mercado Farmaceutico Fresenius Cierre Abril 2025.xlsx', sheet_name='Data')
# ... resto de tu código ...

# Mapear colores por Grupo Proveedor
color_map = {}
idx = 0
for grp in df['Grupo Proveedor'].unique():
    if grp == 'FRESENIUS CORP':
        color_map[grp] = CORPORATE_BLUE
    elif grp == 'THERAPIA IV':
        color_map[grp] = THERAPIA_COLOR
    else:
        color_map[grp] = OTHER_COLORS[idx % len(OTHER_COLORS)]
        idx += 1


# Convierte duración de contrato a meses con nueva lógica
def convert_to_months(s):
    if pd.isna(s) or str(s).strip() == '':
        return 18  # Si está vacía, asumir 18 meses
    
    s = str(s).strip().lower()
    
    # Extraer número y unidad
    match = re.search(r'(\d+)\s*(meses?|horas?|días?|dia|semanas?)', s)
    if not match:
        return 18  # Si no se puede extraer, asumir 18 meses
    
    valor = int(match.group(1))
    unidad = match.group(2)
    
    # Convertir a meses según la unidad
    if 'mes' in unidad:
        meses = valor
    elif 'hora' in unidad:
        # Convertir horas a meses (asumiendo 30 días/mes, 24 horas/día = 720 horas/mes)
        meses = max(1, round(valor / 720))
    elif 'día' in unidad or 'dia' in unidad:
        # Convertir días a meses (asumiendo 30 días/mes)
        meses = max(1, round(valor / 30))
    elif 'semana' in unidad:
        # Convertir semanas a meses (asumiendo 4.33 semanas/mes)
        meses = max(1, round(valor / 4.33))
    else:
        meses = 18  # Valor por defecto
    
    # Aplicar lógica de redondeo y límites
    if meses < 1:
        return 1  # Mínimo 1 mes
    else:
        return meses

# ¡Aquí debe ir esta línea, antes de inicializar app o definir callbacks!
df['Meses_Contrato'] = df['Duración de Contrato'].apply(convert_to_months)

MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


# ————— Inicializar app —————
app = Dash(__name__,
    external_stylesheets=[
        'https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
    ],
    suppress_callback_exceptions=True
)
server = app.server

# ————— Layout —————
app.layout = html.Div([
    dcc.Store(id='processed-data'),
    html.Div(className='header', id='header', children=html.H1('Dashboard de Ventas y Unidades')),
    html.Div(style={'display':'flex','margin':'1rem'}, children=[
        html.Div(className='sidebar', style={'width':'300px','margin-right':'1rem'}, children=[
            html.Button('Filtros ▼', id='toggle-filters', style={'width':'100%','margin-bottom':'1rem'}),
            html.Div(id='filter-container', className='filter-container visible', children=[
                html.Label('Principio Activo'),
                dcc.Dropdown(
                    id='act-dropdown',
                    options=[{'label':x,'value':x} for x in sorted(df['Principio Activo'].unique())],
                    value=[sorted(df['Principio Activo'].unique())[0]],
                    multi=True,
                    placeholder='Seleccionar principios activos',
                    clearable=False, style=dropdown_style
                ),
                html.Br(),
                html.Label('Organismo'),
                dcc.Dropdown(id='org-dropdown', multi=True, placeholder='Todos', style=dropdown_style),
                html.Br(),
                html.Label('Concentración'),
                dcc.Dropdown(id='conc-dropdown', multi=True, placeholder='Todas', style=dropdown_style),
                html.Br(),
                html.Label('Vista'),
                dcc.RadioItems(
                    id='view-mode',
                    options=[
                        {'label':'Anual','value':'annual'},
                        {'label':'Mensual','value':'monthly'},
                        {'label':'Mensualizado','value':'monthlyavg'}
                    ],
                    value='annual'
                ),
                html.Br(),
                dcc.Checklist(
                    id='current-only',
                    options=[{'label':'Hasta fecha actual','value':'current'}],
                    value=[]
                ),
                html.Br(),
                html.Label('CENABAST'),
                dcc.RadioItems(
                    id='cenabast-filter',
                    options=[
                        {'label':'Con','value':'with'},
                        {'label':'Sin','value':'without'},
                        {'label':'Solo CENABAST','value':'only'},
                        {'label':'Ambos','value':'both'}
                    ],
                    value='with'
                ),
                html.Br(),
                html.Label('Mostrar gráficos'),
                dcc.Checklist(
                    id='chart-select',
                    options=[
                        {'label':'Unidades','value':'units'},
                        {'label':'Ventas','value':'sales'},
                        {'label':'Precio promedio','value':'price'}
                    ],
                    value=['units','sales','price']
                )
            ])
        ]),
        html.Div(className='content', children=[
            dcc.Loading([
                html.Div(id='graphs-container')
            ])
        ], style={'flex':1})
    ])
])

# ————— Callbacks de filtros dependientes —————
@app.callback(
    Output('act-dropdown','options'),
    Input('cenabast-filter','value')
)
def update_act_options(cenabast):
    """Actualizar opciones de Principio Activo según filtro CENABAST"""
    if cenabast == 'without':
        df_filtered = df[~df['Organismo'].str.contains('CENABAST', case=False, na=False)]
    elif cenabast == 'only':
        df_filtered = df[df['Organismo'].str.contains('CENABAST', case=False, na=False)]
    else:  # 'with' o 'both'
        df_filtered = df
    
    options = [{'label':x,'value':x} for x in sorted(df_filtered['Principio Activo'].unique())]
    return options

@app.callback(
    Output('org-dropdown','options'),
    Output('org-dropdown','value'),
    Input('act-dropdown','value'),
    Input('cenabast-filter','value')
)
def set_org_options(actives, cenabast):
    """Actualizar opciones de Organismo según Principio Activo y filtro CENABAST"""
    if not actives:
        return [], []
    
    # Filtrar por principios activos seleccionados
    df2 = df[df['Principio Activo'].isin(actives)]
    
    # Aplicar filtro CENABAST
    if cenabast == 'without':
        df2 = df2[~df2['Organismo'].str.contains('CENABAST', case=False, na=False)]
    elif cenabast == 'only':
        df2 = df2[df2['Organismo'].str.contains('CENABAST', case=False, na=False)]
    # Para 'with' y 'both' no filtramos
    
    opts = [{'label':o,'value':o} for o in sorted(df2['Organismo'].unique())]
    return opts, []

@app.callback(
    Output('conc-dropdown','options'),
    Output('conc-dropdown','value'),
    Input('act-dropdown','value'),
    Input('org-dropdown','value'),
    Input('cenabast-filter','value')
)
def set_conc_options(actives, orgs, cenabast):
    """Actualizar opciones de Concentración según filtros seleccionados"""
    if not actives:
        return [], []
    
    # Filtrar por principios activos
    df2 = df[df['Principio Activo'].isin(actives)]
    
    # Filtrar por organismos si están seleccionados
    if orgs:
        df2 = df2[df2['Organismo'].isin(orgs)]
    
    # Aplicar filtro CENABAST
    if cenabast == 'without':
        df2 = df2[~df2['Organismo'].str.contains('CENABAST', case=False, na=False)]
    elif cenabast == 'only':
        df2 = df2[df2['Organismo'].str.contains('CENABAST', case=False, na=False)]
    
    # Combinar forma y concentración
    combos = df2['Forma'].astype(str) + ' - ' + df2['Concentration'].astype(str)
    unique_combos = sorted(combos.unique())
    options = [{'label': c, 'value': c} for c in unique_combos]
    return options, []

# ————— Callbacks de datos procesados —————
@app.callback(
    Output('processed-data','data'),
    Input('act-dropdown','value'),
    Input('org-dropdown','value'),
    Input('conc-dropdown','value'),
    Input('view-mode','value'),
    Input('current-only','value')
)
def process_data(actives, orgs, concs, view, current):
    t0 = time.time()
    
    # Validar que hay principios activos seleccionados
    if not actives:
        return {
            'agg': [], 'no': [], 'only': [], 'xcol': 'Año de emision', 
            'view': view, 'orders': [], 'filters_info': {}
        }
    
    # — filtros básicos —
    dff = df[df['Principio Activo'].isin(actives)].copy()
    if orgs:
        dff = dff[dff['Organismo'].isin(orgs)]
    if concs:
        dff['FC'] = dff['Forma'].astype(str)+' - '+dff['Concentration'].astype(str)
        dff = dff[dff['FC'].isin(concs)]
    
    # Guardar información de filtros para hover
    filters_info = {
        'principios_activos': ', '.join(actives),
        'organismos': ', '.join(orgs) if orgs else 'Todos',
        'concentraciones': ', '.join(concs) if concs else 'Todas'
    }
    
    # Lógica para anual, mensual y mensualizado
    if view == 'annual':
        # Anualizar: convertir todo a base anual
        factor = 12/dff['Meses_Contrato']
        mask = dff['Meses_Contrato'] != 12
        dff.loc[mask, 'Cantidad'] *= factor[mask]
        dff.loc[mask, 'Total'] *= factor[mask]
    elif view == 'monthly':
        # Mensual: mostrar valor total en el mes de licitación, sin distribuir
        pass  # No necesitamos hacer nada, los datos ya están en el mes correcto
    else:  # monthlyavg (mensualizado)
        # Mensualizado: distribuir el valor total a lo largo de los meses del contrato
        records = []
        for _, row in dff.iterrows():
            m = int(row['Meses_Contrato'])
            for i in range(m):
                r = row.copy()
                # Dividir cantidad y total entre los meses del contrato
                r['Cantidad'] = round(r['Cantidad'] / m)
                r['Total'] = r['Total'] / m
                
                # Calcular nuevo año y mes
                a = int(r['Año de emision'])
                mes0 = int(r['N Mes de emision'])
                new_mes = (mes0 - 1 + i) % 12 + 1
                new_ano = a + (mes0 - 1 + i) // 12
                r['Año de emision'] = new_ano
                r['N Mes de emision'] = new_mes
                records.append(r)
        
        if records:
            dff = pd.DataFrame(records)
        else:
            # Si no hay registros después de la distribución mensual, crear DataFrame vacío
            dff = pd.DataFrame(columns=dff.columns)
    # truncar
    if 'current' in current:
        now = datetime.datetime.now()
        if view=='annual':
            dff = dff[dff['Año de emision']<=now.year]
        else:
            dff = dff[ (dff['Año de emision']< now.year) |
                       ((dff['Año de emision']==now.year)&(dff['N Mes de emision']<=now.month)) ]
    # — definir columna de período y orders —
    if view!='annual':
        dff['Periodo'] = (
            dff['Año de emision'].astype(str)+'-'+
            dff['N Mes de emision'].astype(str).str.zfill(2)
        )
        xcol = 'Periodo'
    else:
        xcol = 'Año de emision'

    # — agrupación TODOS los datos —
    agg = (
      dff.groupby([xcol,'Grupo Proveedor'])[['Cantidad','Total']]
         .sum()
         .reset_index()
    )

    # — cálculo de market shares —
    tot_cant = agg.groupby(xcol)['Cantidad'].sum().to_dict()
    tot_vent = agg.groupby(xcol)['Total'].sum().to_dict()
    agg['MS']  = agg.apply(lambda r:100*r['Cantidad']/tot_cant[r[xcol]] if tot_cant[r[xcol]]>0 else 0, axis=1)
    agg['SMS'] = agg.apply(lambda r:100*r['Total']/tot_vent[r[xcol]]   if tot_vent[r[xcol]]>0 else 0, axis=1)

    # — agrupación SIN CENABAST (filtrar por Organismo) —
    dff_no = dff[ ~dff['Organismo'].str.contains('CENABAST', case=False, na=False) ]
    no_agg = (
      dff_no.groupby([xcol,'Grupo Proveedor'])[['Cantidad','Total']]
         .sum()
         .reset_index()
    )
    tot_cant_no = no_agg.groupby(xcol)['Cantidad'].sum().to_dict()
    tot_vent_no = no_agg.groupby(xcol)['Total'].sum().to_dict()
    no_agg['MS']  = no_agg.apply(lambda r:100*r['Cantidad']/tot_cant_no[r[xcol]] if tot_cant_no[r[xcol]]>0 else 0, axis=1)
    no_agg['SMS'] = no_agg.apply(lambda r:100*r['Total']/tot_vent_no[r[xcol]]   if tot_vent_no[r[xcol]]>0 else 0, axis=1)

    # — agrupación SOLO CENABAST —
    dff_only = dff[ dff['Organismo'].str.contains('CENABAST', case=False, na=False) ]
    only_agg = (
      dff_only.groupby([xcol,'Grupo Proveedor'])[['Cantidad','Total']]
         .sum()
         .reset_index()
    )
    if not only_agg.empty:
        tot_cant_only = only_agg.groupby(xcol)['Cantidad'].sum().to_dict()
        tot_vent_only = only_agg.groupby(xcol)['Total'].sum().to_dict()
        
        # Calcular MS (Market Share) de forma más robusta
        ms_values = []
        for _, row in only_agg.iterrows():
            xcol_val = row[xcol]
            if xcol_val in tot_cant_only and tot_cant_only[xcol_val] > 0:
                ms_values.append(100 * row['Cantidad'] / tot_cant_only[xcol_val])
            else:
                ms_values.append(0)
        only_agg['MS'] = ms_values
        
        # Calcular SMS (Sales Market Share) de forma más robusta
        sms_values = []
        for _, row in only_agg.iterrows():
            xcol_val = row[xcol]
            if xcol_val in tot_vent_only and tot_vent_only[xcol_val] > 0:
                sms_values.append(100 * row['Total'] / tot_vent_only[xcol_val])
            else:
                sms_values.append(0)
        only_agg['SMS'] = sms_values
    else:
        # Si no hay datos de CENABAST, crear DataFrame vacío con las columnas necesarias
        only_agg = pd.DataFrame(columns=[xcol, 'Grupo Proveedor', 'Cantidad', 'Total', 'MS', 'SMS'])

    # — si es mensual, traducir labels a español —
    orders = sorted(agg[xcol].unique().tolist())
    labels = orders
    if xcol=='Periodo':
        # orders = ['2025-01', '2025-02', …]
        labels = []
        for p in orders:
            año, mes = p.split('-')
            mes_i = int(mes)-1
            labels.append(f"{MESES_ES[mes_i]} {año}")
        # para usar directamente los labels en lugar de las keys:
        agg['Label']   = agg[xcol].apply(lambda p: labels[orders.index(p)])
        no_agg['Label']= no_agg[xcol].apply(lambda p: labels[orders.index(p)])
        if not only_agg.empty:
            only_agg['Label']= only_agg[xcol].apply(lambda p: labels[orders.index(p)] if p in orders else p)
        xcol = 'Label'

    agg['Cantidad'] = agg['Cantidad'].round().astype(int)
    agg['Total']    = agg['Total'].round().astype(int)
    no_agg['Cantidad'] = no_agg['Cantidad'].round().astype(int)
    no_agg['Total']    = no_agg['Total'].round().astype(int)
    if not only_agg.empty:
        only_agg['Cantidad'] = only_agg['Cantidad'].round().astype(int)
        only_agg['Total']    = only_agg['Total'].round().astype(int)


    # — preparar output —
    return {
        'agg'   : agg.to_dict('records'),
        'no'    : no_agg.to_dict('records'),
        'only'  : only_agg.to_dict('records'),
        'xcol'  : xcol,
        'view'  : view,
        'orders': labels,
        'filters_info': filters_info
    }

def annotate_totals(fig, is_sales=False):
    """
    Añade anotaciones de total sobre cada barra.
    is_sales=False → usa trace.y directamente (Unidades);
    is_sales=True  → convierte a float y añade símbolo $ (Ventas).
    """
    # obtenemos X como lista indexable
    x_vals = list(fig.data[0].x)
    # suma todas las traces visibles
    totals = [0] * len(x_vals)
    for trace in fig.data:
        if trace.visible is None or trace.visible:
            # aseguramos float
            ys = []
            for y in trace.y:
                try: ys.append(float(y))
                except: ys.append(0)
            totals = [t + y for t, y in zip(totals, ys)]

    # construimos las anotaciones
    ann = []
    for i, tot in enumerate(totals):
        text = f"${int(tot):,}" if is_sales else f"{int(tot):,}"
        ann.append(dict(
            x=x_vals[i],
            y=tot,
            text=text,
            showarrow=False,
            yshift=10,
            font=dict(size=11, color='black')
        ))
    fig.update_layout(annotations=ann)
    return fig


# ————— Callback único para renderizar todos los gráficos —————
@app.callback(
    Output('graphs-container','children'),
    Input('processed-data','data'),
    Input('chart-select','value'),
    Input('cenabast-filter','value')
)
def render_graphs(data, charts, cenabast):
    if not data:
        return html.Div("Cargando…")

    # 1) Extraemos todo lo que necesitamos del dict 'data'
    dfagg = pd.DataFrame(data['agg'])
    dfno  = pd.DataFrame(data['no'])
    dfonly = pd.DataFrame(data['only']) if data.get('only') else pd.DataFrame()
    xcol   = data['xcol']
    orders = data['orders']    # ← ahora 'orders' existe
    view   = data['view']      # ← ahora 'view' existe
    filters_info = data.get('filters_info', {})

    figs = []

    # Función para calcular totales por período
    def calculate_totals(df_):
        if df_.empty:
            return {}
        return df_.groupby(xcol)[['Cantidad', 'Total']].sum().to_dict('index')

    # 2) Helper que usa 'orders' y 'view' desde el closure
    def make_bar(df_, ycol, mscol, title, graph_id):
        if df_.empty:
            return html.Div(f"No hay datos para {title}")
        
        # Calcular totales por período
        totals_by_period = calculate_totals(df_)
        
        # Crear datos personalizados para el hover
        custom_data_list = []
        for _, row in df_.iterrows():
            period_totals = totals_by_period.get(row[xcol], {'Cantidad': 0, 'Total': 0})
            custom_data_list.append([
                row['Grupo Proveedor'],
                row[mscol],
                filters_info.get('principios_activos', ''),
                filters_info.get('organismos', ''),
                filters_info.get('concentraciones', ''),
                period_totals['Cantidad'],
                period_totals['Total']
            ])
        
        df_['custom_data'] = custom_data_list
        
        # Template de hover mejorado
        if ycol == 'Total':
            hover = (
                f"<b>%{{x}}</b><br>"
                f"Grupo: %{{customdata[0]}}<br>"
                f"Ventas: $%{{y:,.0f}}<br>"
                f"Market Share: %{{customdata[1]:.1f}}%<br>"
                f"<b>Total período: $%{{customdata[6]:,.0f}}</b><br>"
                f"<br><i>Filtros aplicados:</i><br>"
                f"Principios: %{{customdata[2]}}<br>"
                f"Organismos: %{{customdata[3]}}<br>"
                f"Concentraciones: %{{customdata[4]}}<extra></extra>"
            )
        else:
            hover = (
                f"<b>%{{x}}</b><br>"
                f"Grupo: %{{customdata[0]}}<br>"
                f"Unidades: %{{y:,.0f}}<br>"
                f"Market Share: %{{customdata[1]:.1f}}%<br>"
                f"<b>Total período: %{{customdata[5]:,.0f}}</b><br>"
                f"<br><i>Filtros aplicados:</i><br>"
                f"Principios: %{{customdata[2]}}<br>"
                f"Organismos: %{{customdata[3]}}<br>"
                f"Concentraciones: %{{customdata[4]}}<extra></extra>"
            )
        
        fig = px.bar(
            df_, x=xcol, y=ycol, color='Grupo Proveedor',
            barmode='stack',
            category_orders={xcol: orders},
            color_discrete_map=color_map,
            custom_data='custom_data',
            title=title
        )
        fig.update_traces(hovertemplate=hover)
        if view == 'annual':
            fig.update_xaxes(tickmode='array', tickvals=list(map(int, orders)))
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        return dcc.Graph(
            id = graph_id,
            figure=fig,
            config={'modeBarButtonsToAdd':['toImage'],'displaylogo':False},
            style={'margin-bottom':'2rem'}
        )


    # 3) Construcción de la lista de figuras
    if 'units' in charts:
        if cenabast in ['with','both']:
            figs.append(make_bar(dfagg, 'Cantidad', 'MS', 'Unidades por Grupo', 'units-chart'))
        if cenabast in ['without','both']:
            figs.append(make_bar(dfno,  'Cantidad', 'MS', "Unidades sin CENABAST", 'units-chart-no-cenabast'))
        if cenabast == 'only' and not dfonly.empty:
            figs.append(make_bar(dfonly, 'Cantidad', 'MS', "Unidades solo CENABAST", 'units-chart-only-cenabast'))
    if 'sales' in charts:
        if cenabast in ['with','both']:
            figs.append(make_bar(dfagg, 'Total', 'SMS', 'Ventas por Grupo', 'sales-chart'))
        if cenabast in ['without','both']:
            figs.append(make_bar(dfno,  'Total', 'SMS', "Ventas sin CENABAST", 'sales-chart-no-cenabast'))
        if cenabast == 'only' and not dfonly.empty:
            figs.append(make_bar(dfonly, 'Total', 'SMS', "Ventas solo CENABAST", 'sales-chart-only-cenabast'))
    if 'price' in charts:
        if cenabast in ['with','both'] and not dfagg.empty and 'Total' in dfagg.columns and 'Cantidad' in dfagg.columns:
            # Verificar que no hay división por cero
            dfagg_price = dfagg[dfagg['Cantidad'] > 0].copy()
            if not dfagg_price.empty:
                dfagg_price['Precio'] = dfagg_price['Total'] / dfagg_price['Cantidad']
                hover = (
                    f"<b>%{{x}}</b><br>"
                    f"Grupo: %{{fullData.name}}<br>"
                    f"Precio: $%{{y:,.2f}}<br>"
                    f"<br><i>Filtros aplicados:</i><br>"
                    f"Principios: {filters_info.get('principios_activos', '')}<br>"
                    f"Organismos: {filters_info.get('organismos', '')}<br>"
                    f"Concentraciones: {filters_info.get('concentraciones', '')}<extra></extra>"
                )
                fig = go.Figure()
                for grp in dfagg_price['Grupo Proveedor'].unique():
                    sub = dfagg_price[dfagg_price['Grupo Proveedor']==grp]
                    fig.add_trace(go.Scatter(
                        x=sub[xcol], y=sub['Precio'], mode='lines+markers',
                        name=grp, line=dict(color=color_map.get(grp)), marker=dict(size=6),
                        hovertemplate=hover
                    ))
                fig.update_layout(title='Tendencia Precio Promedio', margin=dict(l=20, r=20, t=30, b=20))
                figs.append(dcc.Graph(figure=fig, config={'modeBarButtonsToAdd':['toImage'],'displaylogo':False}))
        
        if cenabast in ['without','both'] and not dfno.empty and 'Total' in dfno.columns and 'Cantidad' in dfno.columns:
            # Verificar que no hay división por cero
            dfno_price = dfno[dfno['Cantidad'] > 0].copy()
            if not dfno_price.empty:
                dfno_price['Precio'] = dfno_price['Total'] / dfno_price['Cantidad']
                hover = (
                    f"<b>%{{x}}</b><br>"
                    f"Grupo: %{{fullData.name}}<br>"
                    f"Precio: $%{{y:,.2f}}<br>"
                    f"<br><i>Filtros aplicados:</i><br>"
                    f"Principios: {filters_info.get('principios_activos', '')}<br>"
                    f"Organismos: {filters_info.get('organismos', '')}<br>"
                    f"Concentraciones: {filters_info.get('concentraciones', '')}<extra></extra>"
                )
                fig = go.Figure()
                for grp in dfno_price['Grupo Proveedor'].unique():
                    sub = dfno_price[dfno_price['Grupo Proveedor']==grp]
                    fig.add_trace(go.Scatter(
                        x=sub[xcol], y=sub['Precio'], mode='lines+markers',
                        name=grp, line=dict(color=color_map.get(grp)), marker=dict(size=6),
                        hovertemplate=hover
                    ))
                fig.update_layout(title='Tendencia Precio Promedio sin CENABAST', margin=dict(l=20, r=20, t=30, b=20))
                figs.append(dcc.Graph(figure=fig, config={'modeBarButtonsToAdd':['toImage'],'displaylogo':False}))
        
        if cenabast == 'only' and not dfonly.empty and 'Total' in dfonly.columns and 'Cantidad' in dfonly.columns:
            # Verificar que no hay división por cero
            dfonly_price = dfonly[dfonly['Cantidad'] > 0].copy()
            if not dfonly_price.empty:
                dfonly_price['Precio'] = dfonly_price['Total'] / dfonly_price['Cantidad']
                hover = (
                    f"<b>%{{x}}</b><br>"
                    f"Grupo: %{{fullData.name}}<br>"
                    f"Precio: $%{{y:,.2f}}<br>"
                    f"<br><i>Filtros aplicados:</i><br>"
                    f"Principios: {filters_info.get('principios_activos', '')}<br>"
                    f"Organismos: {filters_info.get('organismos', '')}<br>"
                    f"Concentraciones: {filters_info.get('concentraciones', '')}<extra></extra>"
                )
                fig = go.Figure()
                for grp in dfonly_price['Grupo Proveedor'].unique():
                    sub = dfonly_price[dfonly_price['Grupo Proveedor']==grp]
                    fig.add_trace(go.Scatter(
                        x=sub[xcol], y=sub['Precio'], mode='lines+markers',
                        name=grp, line=dict(color=color_map.get(grp)), marker=dict(size=6),
                        hovertemplate=hover
                    ))
                fig.update_layout(title='Tendencia Precio Promedio solo CENABAST', margin=dict(l=20, r=20, t=30, b=20))
                figs.append(dcc.Graph(figure=fig, config={'modeBarButtonsToAdd':['toImage'],'displaylogo':False}))

    return figs

@app.callback(
    Output('units-chart', 'figure'),
    Input('units-chart', 'restyleData'),
    State('units-chart', 'figure')
)
def update_units_annotations(restyle, existing_fig):
    if not existing_fig or not existing_fig.get('data') or len(existing_fig['data']) == 0:
        return existing_fig
    
    fig = go.Figure(existing_fig)
    
    # Verificar que el primer trace tenga datos x válidos
    if not fig.data[0].x or len(fig.data[0].x) == 0:
        return existing_fig
    
    x_vals = list(fig.data[0].x)

    # inicializamos totales a 0
    totals = [0]*len(x_vals)
    for trace in fig.data:
        if trace.visible is None or trace.visible:
            # Verificar que trace.y existe y tiene la misma longitud que x_vals
            if not trace.y or len(trace.y) != len(x_vals):
                continue
                
            # convertimos cada punto y a float antes de sumar
            new_totals = []
            for t, y in zip(totals, trace.y):
                try:
                    y_val = float(y)
                except Exception:
                    y_val = 0
                new_totals.append(t + y_val)
            totals = new_totals

    # construimos las anotaciones, pero solo para valores > 0
    ann = []
    for i in range(min(len(x_vals), len(totals))):
        if totals[i] > 0:  # Solo mostrar anotaciones para valores mayores a 0
            ann.append(dict(
                x=x_vals[i],
                y=int(totals[i]),
                text=f"{int(totals[i]):,}",
                showarrow=False,
                yshift=10,
                font=dict(size=11, color='black')
            ))
    fig.update_layout(annotations=ann)
    return fig


@app.callback(
    Output('sales-chart','figure'),
    Input('sales-chart','restyleData'),
    State('sales-chart','figure')
)
def update_sales_annotations(restyle, existing_fig):
    if not existing_fig or not existing_fig.get('data') or len(existing_fig['data']) == 0:
        return existing_fig
    
    fig = go.Figure(existing_fig)
    
    # Verificar que el primer trace tenga datos x válidos
    if not fig.data[0].x or len(fig.data[0].x) == 0:
        return existing_fig
        
    x_vals = list(fig.data[0].x)

    totals = [0]*len(x_vals)
    for trace in fig.data:
        if trace.visible is None or trace.visible:
            # Verificar que trace.y existe y tiene la misma longitud que x_vals
            if not trace.y or len(trace.y) != len(x_vals):
                continue
                
            new_totals = []
            for t, y in zip(totals, trace.y):
                try:
                    y_val = float(y)
                except Exception:
                    y_val = 0
                new_totals.append(t + y_val)
            totals = new_totals

    # construimos las anotaciones, pero solo para valores > 0
    ann = []
    for i in range(min(len(x_vals), len(totals))):
        if totals[i] > 0:  # Solo mostrar anotaciones para valores mayores a 0
            ann.append(dict(
                x=x_vals[i],
                y=int(totals[i]),
                text=f"${int(totals[i]):,}",
                showarrow=False,
                yshift=10,
                font=dict(size=11, color='black')
            ))
    fig.update_layout(annotations=ann)
    return fig


# ————— Toggle filtros —————
@app.callback(
    Output('filter-container','className'),
    Input('toggle-filters','n_clicks'),
    prevent_initial_call=True
)
def toggle(c):
    return 'filter-container hidden' if c and c%2 else 'filter-container visible'

# ————— Run —————
import os
if __name__=='__main__':
    port = int(os.environ.get("PORT", 8050))
    # En producción usa run_server; debug=True lo puedes dejar en False
    app.run(host='0.0.0.0', port=port, debug=False)