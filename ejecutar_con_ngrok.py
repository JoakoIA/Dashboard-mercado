"""
Ejecuta el dashboard con un túnel ngrok para acceso externo.
"""

# Importamos app2_corregido_final sin ejecutarlo
import sys
import os
from importlib.util import spec_from_file_location, module_from_spec

# Ruta al archivo principal
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_final copy 9.py")

# Cargar el módulo sin ejecutarlo
spec = spec_from_file_location("dashboard_app", app_path)
dashboard_app = module_from_spec(spec)
sys.modules["dashboard_app"] = dashboard_app
spec.loader.exec_module(dashboard_app)

# Importamos las bibliotecas necesarias
from pyngrok import ngrok
from threading import Thread
import time

# Obtenemos la app de Dash del módulo importado
app = dashboard_app.app

def main():
    try:
        # Definir el puerto a utilizar
        puerto = 8050
        
        # Iniciar la aplicación Dash en modo accesible externamente
        def run_app():
            app.run(debug=False, host='0.0.0.0', port=puerto)
        
        print("\n* Iniciando el Dashboard...")
        # Ejecutar la app en un hilo separado
        Thread(target=run_app).start()
        
        print("* Creando túnel ngrok...")
        # Crear un túnel HTTP con ngrok al puerto de la aplicación
        public_url = ngrok.connect(puerto)
        
        # Mostrar la URL pública
        print(f"\n✅ ¡DASHBOARD LISTO!")
        print(f"* URL EXTERNA: {public_url}")
        print("* Comparte esta URL con las personas que necesiten acceder al dashboard")
        print("* Para detener, presiona Ctrl+C en esta terminal\n")
        
        # Mantener el programa en ejecución
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        # Desconectar el túnel cuando se interrumpe el programa
        print("\n* Cerrando el túnel ngrok y deteniendo la aplicación...")
        ngrok.kill()
    except Exception as e:
        print(f"\n❌ Error al ejecutar con ngrok: {e}")
        print("\nPosibles soluciones:")
        print("1. Asegúrate de haber configurado tu token de autenticación con 'python configurar_ngrok.py'")
        print("2. Verifica tu conexión a internet")
        print("3. Asegúrate de que el puerto 8050 no esté siendo utilizado por otra aplicación\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
