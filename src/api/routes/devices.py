"""
API Routes - Dispositivos
Endpoints para listar, controlar y gestionar dispositivos Matter
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict
from loguru import logger

from matter.controller import MatterController
from dependencies import get_controller  # ← Importamos la función del main
from storage.database import get_database

router = APIRouter()


# ========== MODELO PYDANTIC ==========


class CommandRequest(BaseModel):
    """Request para enviar comando a un dispositivo"""

    command: str = Field(..., description="Comando: on, off, toggle, level")
    params: Dict = Field(default_factory=dict, description="Parámetros adicionales")


# ========== ENDPOINTS ==========


@router.get("/")
async def list_devices(controller: MatterController = Depends(get_controller)):
    """
    Listar todos los dispositivos comisionados.
    """
    try:
        devices = controller.list_devices()

        return [
            {
                "node_id": device.node_id,
                "name": device.name,
                "type": device.device_type,
                "online": device.is_online,
                "endpoint": device.endpoint_id,
            }
            for device in devices
        ]
    except Exception as e:
        logger.error(f"Error listando dispositivos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{node_id}")
async def get_device(
    node_id: int, controller: MatterController = Depends(get_controller)
):
    """
    Obtener información completa de un dispositivo.
    Incluye el estado actual.
    """
    try:
        if node_id not in controller.devices:
            raise HTTPException(
                status_code=404, detail=f"Dispositivo {node_id} no encontrado"
            )

        device = controller.devices[node_id]

        return {
            "node_id": device.node_id,
            "name": device.name,
            "type": device.device_type,
            "online": device.is_online,
            "endpoint": device.endpoint_id,
            "state": device.state,  # Estado completo
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo dispositivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{node_id}/command")
async def send_command(
    node_id: int,
    request: CommandRequest,
    controller: MatterController = Depends(get_controller),
):
    """
    Enviar comando a un dispositivo.

    Comandos disponibles:
    - on: Encender
    - off: Apagar
    - toggle: Cambiar estado
    - level: Cambiar brillo (params: {"level": 0-100})

    Ejemplos:
        {"command": "on"}
        {"command": "level", "params": {"level": 80}}
    """
    try:
        result = await controller.send_command(
            node_id=node_id, command=request.command, **request.params
        )

        return {
            "success": True,
            "node_id": node_id,
            "command": request.command,
            "result": result,
        }

    except ValueError as e:
        print(e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error enviando comando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{node_id}")
async def update_device(
    node_id: int,
    name: Optional[str] = None,
    controller: MatterController = Depends(get_controller),
):
    """
    Actualizar nombre del dispositivo.
    """
    try:
        db = get_database()
        if node_id not in controller.devices:
            raise HTTPException(
                status_code=404, detail=f"Dispositivo {node_id} no encontrado"
            )
            
        device = controller.devices[node_id]

        if name:
            device.name = name
            logger.info(f"Dispositivo {node_id} renombrado a: {name}")

        db.save_device(device)  # Guardar cambios
        return {
            "success": True,
            "device": {
                "node_id": device.node_id,
                "name": device.name,
                "type": device.device_type,
                "online": device.is_online,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando dispositivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{node_id}")
async def remove_device(
    node_id: int, controller: MatterController = Depends(get_controller)
):
    """
    Eliminar dispositivo del sistema.
    """
    try:
        await controller.remove_device(node_id)

        return {"success": True, "message": f"Dispositivo {node_id} eliminado"}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error eliminando dispositivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
