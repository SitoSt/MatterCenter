"""
MatterCenter - Servidor Principal
Punto de entrada de la aplicación
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv
from dependencies import get_controller, set_controller
from storage.database import init_database, get_database

# Cargar variables de entorno
load_dotenv()

# Importar el controlador Matter (lo crearemos después)
from matter.controller import MatterController

# Variable global para el controlador
matter_controller = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    
    - ANTES del yield: Se ejecuta al INICIAR el servidor
    - DESPUÉS del yield: Se ejecuta al CERRAR el servidor
    """
    global matter_controller
    
    # ========== INICIO ==========
    logger.info("🚀 Iniciando MatterCenter...")
    
    db_path = os.getenv("DATABASE_PATH", "data/mattercenter.db")
    init_database(db_path)
    logger.success("💾 Base de datos inicializada")
    
    # Crear e inicializar el controlador Matter
    matter_controller = MatterController()
    await matter_controller.initialize()
    set_controller(matter_controller)  # ← Configuramos la dependencia
    
    
    logger.success("✅ MatterCenter listo!")
    
    # yield = La aplicación queda funcionando aquí
    yield
    
    # ========== CIERRE ==========
    logger.info("🛑 Cerrando MatterCenter...")
    if matter_controller:
        await matter_controller.shutdown()
    
    # Cerrar base de datos
    try:
        db = get_database()
        db.close()
    except:
        pass
    
    logger.success("👋 MatterCenter cerrado")


# Crear la aplicación FastAPI
app = FastAPI(
    title="MatterCenter - J Bridge",
    description="Control unificado de dispositivos Matter",
    version="0.1.0",
    lifespan=lifespan  # Conectar el lifecycle
)

# CORS - Permitir peticiones desde cualquier origen (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== RUTAS PÚBLICAS ==========

@app.get("/")
async def root():
    """Health check simple"""
    return {
        "status": "online",
        "service": "MatterCenter",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Estado detallado del sistema"""
    matter_controller = get_controller()
    
    if not matter_controller:
        return {"status": "initializing"}
    
    return {
        "status": "healthy",
        "devices_count": len(matter_controller.devices),
        "devices": [
            {
                "node_id": device.node_id,
                "name": device.name,
                "online": device.is_online
            }
            for device in matter_controller.devices.values()
        ]
    }


## ========== IMPORTAR Y REGISTRAR RUTAS ==========

from api.routes import devices

app.include_router(
    devices.router,
    prefix="/api/devices",
    tags=["devices"]
)

# app.include_router(
#     commissioning.router,
#     prefix="/api/commissioning",
#     tags=["commissioning"]
# )


# ========== EJECUTAR ==========

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "True") == "True"
    
    logger.info(f"🌐 Iniciando servidor en http://localhost:{port}")
    logger.info(f"📚 Documentación en http://localhost:{port}/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=debug  # Hot-reload en desarrollo
    )