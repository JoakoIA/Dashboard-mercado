window.onload = function() {
    // Función para actualizar los totales en las gráficas
    function updateTotals(graphDiv) {
        // Verificar si es una gráfica de barras
        if (!graphDiv || !graphDiv.data || graphDiv.data.length === 0 || 
            (graphDiv.data[0].type !== 'bar' && graphDiv.data[0].type !== 'scatter')) {
            return;
        }
        
        // Obtener los datos visibles
        const visibleData = graphDiv.data.filter(trace => trace.visible !== 'legendonly');
        
        if (visibleData.length === 0) return;
        
        // Eliminar anotaciones existentes
        let layout = graphDiv.layout;
        let updatedAnnotations = [];
        
        // Mantener solo anotaciones que no sean de totales
        if (layout.annotations) {
            updatedAnnotations = layout.annotations.filter(ann => 
                !ann.text || !ann.text.includes(',') || ann.yshift !== 10);
        }
        
        // Si es una gráfica de barras apiladas
        if (graphDiv.data[0].type === 'bar') {
            // Calcular totales por cada valor de x
            const totals = {};
            
            visibleData.forEach(trace => {
                if (trace.x && trace.y) {
                    trace.x.forEach((x, i) => {
                        if (!totals[x]) totals[x] = 0;
                        totals[x] += trace.y[i] || 0;
                    });
                }
            });
            
            // Crear anotaciones para los totales
            Object.keys(totals).forEach(x => {
                updatedAnnotations.push({
                    x: x,
                    y: totals[x],
                    text: `${parseInt(totals[x]).toLocaleString('es-ES')}`,
                    font: {size: 10, color: 'black'},
                    showarrow: false,
                    yshift: 10
                });
            });
        }
        
        // Actualizar las anotaciones
        Plotly.relayout(graphDiv, {annotations: updatedAnnotations});
    }
    
    // Conectar a eventos de redibujo de Plotly
    const graphIds = ['units-all-chart', 'units-no-cenabast-chart', 
                     'sales-all-chart', 'sales-no-cenabast-chart'];
    
    graphIds.forEach(id => {
        const graphDiv = document.getElementById(id);
        if (graphDiv) {
            graphDiv.on('plotly_afterplot', function() {
                updateTotals(this);
            });
            
            // Evento para click en la leyenda
            graphDiv.on('plotly_legendclick', function() {
                setTimeout(() => updateTotals(this), 100);
            });
            
            // Evento para doble click en la leyenda
            graphDiv.on('plotly_legenddoubleclick', function() {
                setTimeout(() => updateTotals(this), 100);
            });
        }
    });
};
