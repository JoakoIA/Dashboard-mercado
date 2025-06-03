"""
Callbacks para el dashboard farmacéutico
Autor: Sistema automatizado
Fecha: Junio 2025
"""

import dash
from dash import Input, Output, State, callback_context
import plotly.graph_objects as go
from datetime import datetime

from utils import (
    CORPORATE_COLORS, filtrar_datos, agregar_datos_por_vista,
    crear_grafico_unidades, crear_grafico_ventas, crear_grafico_precio,
    crear_grafico_unidades_cenabast, crear_grafico_ventas_cenabast, 
    crear_grafico_precio_cenabast
)


def register_callbacks(app, data_processor):
    """Registra todos los callbacks del dashboard"""

    # Callback para inicializar opciones de filtros al cargar la página
    @app.callback(
        [Output('filtro-principio-activo', 'options'),
         Output('filtro-organismo', 'options'),
         Output('filtro-concentracion', 'options'),
         Output('filtro-grupo-proveedor', 'options')],
        [Input('filtro-cenabast', 'value'),
         Input('opciones-adicionales', 'value')]
    )
    def inicializar_opciones_filtros(cenabast, opciones):
        """Inicializa las opciones de los filtros basado en filtros globales"""
        
        df = data_processor.df
        
        if df is None or len(df) == 0:
            return [], [], [], []
        
        # Aplicar filtros globales
        df_base = df.copy()
        
        # Aplicar filtro CENABAST
        if cenabast == 'sin':
            df_base = df_base[df_base['es_cenabast'] == False]
        elif cenabast == 'solo':
            df_base = df_base[df_base['es_cenabast'] == True]
        
        # Aplicar opciones adicionales
        if opciones and 'truncar_mes' in opciones:
            mes_actual = datetime.now().month
            año_actual = datetime.now().year
            df_base = df_base[
                (df_base['año'] <= año_actual) & 
                ((df_base['año'] < año_actual) | (df_base['mes'] <= mes_actual))
            ]
        
        # Generar opciones para todos los filtros
        opciones_principio = [{'label': p, 'value': p} for p in sorted(df_base['principio_activo'].dropna().unique())]
        opciones_organismo = [{'label': o, 'value': o} for o in sorted(df_base['organismo'].dropna().unique())]
        opciones_concentracion = [{'label': c, 'value': c} for c in sorted(df_base['concentracion'].dropna().unique())]
        opciones_grupo = [{'label': g, 'value': g} for g in sorted(df_base['grupo_proveedor'].dropna().unique())]
        
        return opciones_principio, opciones_organismo, opciones_concentracion, opciones_grupo

    # Callback para filtros dinámicos interdependientes (sin ciclos)
    @app.callback(
        [Output('filtro-organismo', 'options', allow_duplicate=True),
         Output('filtro-concentracion', 'options', allow_duplicate=True),
         Output('filtro-grupo-proveedor', 'options', allow_duplicate=True)],
        [Input('filtro-principio-activo', 'value')],
        [State('filtro-cenabast', 'value'),
         State('opciones-adicionales', 'value')],
        prevent_initial_call=True
    )
    def actualizar_filtros_por_principio(principios, cenabast, opciones):
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
