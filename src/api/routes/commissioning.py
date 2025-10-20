"""
API Routes - Commissioning
Endpoints para añadir (comisionar) nuevos dispositivos Matter.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from loguru import logger

from matter.controller import MatterController
from dependencies import get_controller

router = APIRouter()

# ========== MODELO PYDANTIC ==========


class CommissionRequest(BaseModel):
    """Request para iniciar el comisionamiento de un dispositivo."""

    setup_code: str = Field(
        ...,
        description="El código de configuración numérico de 11 dígitos del dispositivo Matter.",
        examples=["20522600020"],
    )


# ========== ENDPOINTS ==========


@router.post("/start")
async def start_commissioning(
    request: CommissionRequest,
    background_tasks: BackgroundTasks,
    controller: MatterController = Depends(get_controller),
):
    """
    Iniciar el proceso de comisionamiento de un nuevo dispositivo.

    Este proceso puede tardar hasta un minuto. La API responderá inmediatamente
    y el comisionamiento se ejecutará en segundo plano.
    """
    if not controller.is_initialized:
        raise HTTPException(
            status_code=503, detail="El controlador Matter no está listo."
        )

    try:
        logger.info(
            f"API: Solicitud de comisionamiento recibida con código: {request.setup_code}"
        )

        # El comisionamiento puede tardar, así que lo ejecutamos en segundo plano
        # para no bloquear la API.
        background_tasks.add_task(controller.commission_device, request.setup_code)

        return {
            "success": True,
            "message": "Proceso de comisionamiento iniciado en segundo plano. "
            "Revisa los logs para ver el progreso y la lista de dispositivos para ver el resultado.",
        }
    except Exception as e:
        logger.error(f"Error al iniciar el comisionamiento: {e}")
        raise HTTPException(status_code=500, detail=str(e))
