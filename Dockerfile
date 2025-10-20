# Dockerfile
# Usar una imagen oficial de Python
FROM python:3.11-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requerimientos e instalarlos
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de tu aplicación
COPY . .

# Comando para ejecutar la aplicación cuando el contenedor inicie
CMD ["python", "src/main.py"]