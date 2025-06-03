"""
Funciones auxiliares para el dashboard farmacéutico
Autor: Sistema automatizado
Fecha: Junio 2025
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime


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
        labels={'ventas': 'Ventas ($)', 'periodo': 'Período'},
        color_discrete_map=color_map,
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
