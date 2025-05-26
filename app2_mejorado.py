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


# Extrae meses del string "18 Meses" -> 18
def extract_months(s):
    m = re.search(r'(\d+)', str(s))
    return int(m.group(1)) if m else 12

# ¡Aquí debe ir esta línea, antes de inicializar app o definir callbacks!
df['Meses_Contrato'] = df['Duración de Contrato'].apply(extract_months)

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
                    value=sorted(df['Principio Activo'].unique())[0],
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
    Output('org-dropdown','options'),
    Output('org-dropdown','value'),
    Input('act-dropdown','value')
)
def set_org_options(active):
    df2 = df[df['Principio Activo']==active]
    opts = [{'label':o,'value':o} for o in sorted(df2['Organismo'].unique())]
    return opts, []

@app.callback(
    Output('conc-dropdown','options'),
    Output('conc-dropdown','value'),
    Input('act-dropdown','value'),
    Input('org-dropdown','value')
)
def set_conc_options(active, orgs):
    # 1) Filtrar
    df2 = df[df['Principio Activo'] == active]
    if orgs:
        df2 = df2[df2['Organismo'].isin(orgs)]
    # 2) Combinar y quedarnos sólo con únicos
    combos = df2['Forma'].astype(str) + ' - ' + df2['Concentration'].astype(str)
    unique_combos = sorted(combos.unique())
    options = [{'label': c, 'value': c} for c in unique_combos]
    # 3) Reiniciar selección
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
def process_data(active, orgs, concs, view, current):
    t0 = time.time()
    # — filtros básicos —
    dff = df[df['Principio Activo']==active].copy()
    if orgs:
        dff = dff[dff['Organismo'].isin(orgs)]
    if concs:
        dff['FC'] = dff['Forma'].astype(str)+' - '+dff['Concentration'].astype(str)
        dff = dff[dff['FC'].isin(concs)]
    # anualize / mensualize
    if view=='annual':
        factor = 12/dff['Meses_Contrato']
        mask = dff['Meses_Contrato']!=12
        dff.loc[mask,'Cantidad'] *= factor[mask]
        dff.loc[mask,'Total']    *= factor[mask]
    else:
        records=[]
        for _,row in dff.iterrows():
            m = int(row['Meses_Contrato'])
            for i in range(m):
                r = row.copy()
                if view=='monthlyavg':
                    r['Cantidad'] = round(r['Cantidad']/m)
                    r['Total']    =       r['Total']/m
                a = int(r['Año de emision'])
                mes0 = int(r['N Mes de emision'])
                new_mes = (mes0-1+i)%12+1
                new_ano = a + (mes0-1+i)//12
                r['Año de emision']=new_ano
                r['N Mes de emision']=new_mes
                records.append(r)
        if records:
            dff = pd.DataFrame(records)
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
        xcol = 'Label'

    agg['Cantidad'] = agg['Cantidad'].round().astype(int)
    agg['Total']    = agg['Total'].round().astype(int)
    no_agg['Cantidad'] = no_agg['Cantidad'].round().astype(int)
    no_agg['Total']    = no_agg['Total'].round().astype(int)


    # — preparar output —
    return {
        'agg'   : agg.to_dict('records'),
        'no'    : no_agg.to_dict('records'),
        'xcol'  : xcol,
        'view'  : view,
        'orders': labels
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
    xcol   = data['xcol']
    orders = data['orders']    # ← ahora 'orders' existe
    view   = data['view']      # ← ahora 'view' existe

    figs = []

    # 2) Helper que usa 'orders' y 'view' desde el closure
    def make_bar(df_, ycol, mscol, title, graph_id):
        hover = (
            f"%{{x}}<br>"
            f"{ycol}: %{{y:,.0f}}<br>"                # y sin decimales, con separador de miles
            f"Market Share: %{{customdata[1]:.1f}}%<extra></extra>"
        )
        #fig = annotate_totals(fig, is_sales=(ycol=='Total'))
        fig = px.bar(
            df_, x=xcol, y=ycol, color='Grupo Proveedor',
            barmode='stack',
            category_orders={xcol: orders},
            color_discrete_map=color_map,
            custom_data=['Grupo Proveedor', mscol],
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
    if 'sales' in charts:
        if cenabast in ['with','both']:
            figs.append(make_bar(dfagg, 'Total', 'SMS', 'Ventas por Grupo', 'sales-chart'))
        if cenabast in ['without','both']:
            figs.append(make_bar(dfno,  'Total', 'SMS', "Ventas sin CENABAST", 'sales-chart-no-cenabast'))
    if 'price' in charts:
        dfno['Precio'] = dfno['Total'] / dfno['Cantidad']
        hover = f"%{{x}}<br>Precio: $%{{y:,.2f}}<extra></extra>"
        fig = go.Figure()
        for grp in dfno['Grupo Proveedor'].unique():
            sub = dfno[dfno['Grupo Proveedor']==grp]
            fig.add_trace(go.Scatter(
                x=sub[xcol], y=sub['Precio'], mode='lines+markers',
                name=grp, line=dict(color=color_map.get(grp)), marker=dict(size=6)
            ))
        fig.update_traces(hovertemplate=hover)
        fig.update_layout(title='Tendencia Precio Promedio', margin=dict(l=20, r=20, t=30, b=20))
        figs.append(dcc.Graph(
            id = 'price-chart',
            figure=fig,
            config={'modeBarButtonsToAdd':['toImage'], 'displaylogo':False}
        ))

    return figs

@app.callback(
    Output('units-chart', 'figure'),
    Input('units-chart', 'restyleData'),
    State('units-chart', 'figure')
)
def update_units_annotations(restyle, existing_fig):
    fig = go.Figure(existing_fig)
    x_vals = list(fig.data[0].x)

    # inicializamos totales a 0
    totals = [0]*len(x_vals)
    for trace in fig.data:
        if trace.visible is None or trace.visible:
            # convertimos cada punto y a float antes de sumar
            new_totals = []
            for t, y in zip(totals, trace.y):
                try:
                    y_val = float(y)
                except Exception:
                    y_val = 0
                new_totals.append(t + y_val)
            totals = new_totals

    # construimos las anotaciones
    ann = [
        dict(
            x=x_vals[i],
            y=int(totals[i]),
            text=f"{int(totals[i]):,}",
            showarrow=False,
            yshift=10,
            font=dict(size=11, color='black')
        )
        for i in range(len(x_vals))
    ]
    fig.update_layout(annotations=ann)
    return fig


@app.callback(
    Output('sales-chart','figure'),
    Input('sales-chart','restyleData'),
    State('sales-chart','figure')
)
def update_sales_annotations(restyle, existing_fig):
    fig = go.Figure(existing_fig)
    x_vals = list(fig.data[0].x)

    totals = [0]*len(x_vals)
    for trace in fig.data:
        if trace.visible is None or trace.visible:
            new_totals = []
            for t, y in zip(totals, trace.y):
                try:
                    y_val = float(y)
                except Exception:
                    y_val = 0
                new_totals.append(t + y_val)
            totals = new_totals

    ann = [
        dict(
            x=x_vals[i],
            y=int(totals[i]),
            text=f"${int(totals[i]):,}",
            showarrow=False,
            yshift=10,
            font=dict(size=11, color='black')
        )
        for i in range(len(x_vals))
    ]
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
if __name__=='__main__':
    app.run(debug=True, port=8050)
