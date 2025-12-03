# Imagen base de Python
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copiar el requirements.txt desde la carpeta app/
COPY app/requirements.txt /app/requirements.txt

# Instalar dependencias
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia el resto del código dentro del contenedor
COPY ./app /app

# Exponer Flask y el puerto del debugger
EXPOSE 5000 5678

# Comando para iniciar con debugpy (modo escucha)
#CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "run.py"]

# Ejecuta la aplicación
CMD ["python", "run.py"]
#CMD ["flask", "run", "--host=0.0.0.0"]

