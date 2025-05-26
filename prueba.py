import os

elementos = os.listdir()
#ver elementos dentro de la carpeta data
if 'data' in elementos:
    elementos = os.listdir('data')
else:
    print("La carpeta 'data' no existe en el directorio actual.")
    elementos = []
    
print(elementos)