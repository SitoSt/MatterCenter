"""
MatterController - Gestión de dispositivos Matter
Por ahora es un MOCK (simulación) - luego integraremos el SDK real
"""

import asyncio
import json
from typing import Dict, Optional
from dataclasses import dataclass, field, asdict
from loguru import logger

from storage.database import get_database


@dataclass
class Device:
    """Representación de un dispositivo Matter"""
    node_id: int
    name: str
    device_type: str  # "light", "switch", "sensor", etc
    is_online: bool = True
    endpoint_id: int = 1
    
    # Estado actual del dispositivo
    state: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Inicializar estado por defecto según tipo"""
        if self.device_type == "light" and not self.state:
            self.state = {
                "on": False,
                "brightness": 100  # 0-100%
            }


class MatterController:
    """
    Controlador principal para dispositivos Matter.
    
    Responsabilidades:
    - Comisionar (emparejar) nuevos dispositivos
    - Enviar comandos a dispositivos
    - Leer estado de dispositivos
    - Mantener lista de dispositivos
    """
    
    def __init__(self):
        self.devices: Dict[int, Device] = {}
        self.commissioning_in_progress = False
        self.is_initialized = False
    
    async def initialize(self):
        """
        Inicializar el controlador.
        Aquí cargaríamos:
        - SDK Matter real
        - Dispositivos guardados en BD
        - Configuración del Fabric
        """
        logger.info("🔧 Inicializando controlador Matter...")
        
        # TODO: Aquí iría la inicialización real del SDK
        # from chip import ChipDeviceCtrl
        # self.chip_controller = ChipDeviceCtrl.ChipDeviceController()
        
        # Por ahora: modo mock
        logger.warning("⚠️  Modo MOCK - SDK Matter no conectado")
        
        # Cargar dispositivos guardados (simulado)
        await self._load_saved_devices()
        
        self.is_initialized = True
        logger.success(f"✅ Controlador iniciado - {len(self.devices)} dispositivos cargados")
    
    async def shutdown(self):
        """Cerrar controlador y liberar recursos"""
        logger.info("Cerrando controlador Matter...")
        
        # TODO: Cerrar SDK real
        # if self.chip_controller:
        #     self.chip_controller.Shutdown()
        
        self.is_initialized = False
        logger.info("Controlador cerrado")
    
    # ========== COMMISSIONING ==========
    
    async def commission_device(
        self, 
        setup_code: str, 
        name: Optional[str] = None,
        node_id: Optional[int] = None
    ) -> Device:
        """
        Comisionar (emparejar) un nuevo dispositivo.
        
        Args:
            setup_code: Código QR o numérico del dispositivo
            name: Nombre personalizado (opcional)
            node_id: ID personalizado (opcional, se autogenera)
        
        Returns:
            Device: El dispositivo comisionado
        
        Raises:
            Exception: Si ya hay un commissioning en progreso
        """
        if self.commissioning_in_progress:
            raise Exception("Ya hay un commissioning en progreso")
        
        try:
            self.commissioning_in_progress = True
            logger.info(f"🔗 Iniciando commissioning...")
            logger.debug(f"Setup code: {setup_code}")
            
            # Generar node_id si no se proporciona
            if node_id is None:
                node_id = self._get_next_node_id()
            
            # TODO: Commissioning real con SDK
            # self.chip_controller.CommissionWithCode(
            #     setupPayload=setup_code,
            #     nodeid=node_id
            # )
            
            # MOCK: Simular delay de commissioning
            await asyncio.sleep(1)
            
            # Detectar tipo de dispositivo (simulado)
            device_type = "light"  # TODO: Detectar del descriptor real
            
            # Crear dispositivo
            device = Device(
                node_id=node_id,
                name=name or f"Dispositivo {node_id}",
                device_type=device_type,
                is_online=True
            )
            
            # Guardar en memoria
            self.devices[node_id] = device
            
            await self._save_device(device)
            
            logger.success(f"✅ Dispositivo comisionado: Node {node_id} - {device.name}")
            return device
            
        except Exception as e:
            logger.error(f"❌ Error en commissioning: {e}")
            raise
        finally:
            self.commissioning_in_progress = False
    
    # ========== CONTROL DE DISPOSITIVOS ==========
    
    async def send_command(
        self, 
        node_id: int, 
        command: str, 
        **params
    ) -> Dict:
        """
        Enviar comando a un dispositivo.
        
        Args:
            node_id: ID del dispositivo
            command: Comando a enviar ("on", "off", "toggle", "level")
            **params: Parámetros adicionales (ej: level=200)
        
        Returns:
            Dict con resultado de la operación
        
        Raises:
            ValueError: Si el dispositivo no existe
        """
        if node_id not in self.devices:
            raise ValueError(f"Dispositivo {node_id} no encontrado")
        
        device = self.devices[node_id]
        
        logger.info(f"📤 Comando '{command}' → {device.name} (Node {node_id})")
        
        # Despachar según tipo de dispositivo
        if device.device_type == "light":
            return await self._control_light(device, command, **params)
        else:
            raise ValueError(f"Tipo de dispositivo no soportado: {device.device_type}")
    
    async def _control_light(self, device: Device, command: str, **params) -> Dict:
        """Comandos específicos para luces"""
        
        # TODO: Enviar comandos reales al SDK
        # from chip.clusters import OnOff, LevelControl
        
        if command == "on":
            # TODO: Real
            # await self.chip_controller.SendCommand(
            #     device.node_id,
            #     device.endpoint_id,
            #     OnOff.Commands.On()
            # )
            
            # MOCK
            device.state["on"] = True
            logger.info(f"💡 {device.name} → ENCENDIDA")
            
        elif command == "off":
            device.state["on"] = False
            logger.info(f"💡 {device.name} → APAGADA")
            
        elif command == "toggle":
            device.state["on"] = not device.state["on"]
            estado = "ENCENDIDA" if device.state["on"] else "APAGADA"
            logger.info(f"💡 {device.name} → {estado}")
            
        elif command == "level":
            # Brightness: 0-100 en API, 0-254 en Matter
            brightness = params.get("level", 100)
            if not 0 <= brightness <= 100:
                raise ValueError("Brightness debe estar entre 0-100")
            
            device.state["brightness"] = brightness
            device.state["on"] = brightness > 0  # Auto-encender si brightness > 0
            
            logger.info(f"💡 {device.name} → Brillo {brightness}%")
        else:
            raise ValueError(f"Comando no reconocido: {command}")
        
        return {
            "success": True,
            "node_id": device.node_id,
            "command": command,
            "new_state": device.state.copy()
        }
    
    # ========== LECTURA DE ESTADO ==========
    
    async def get_device_state(self, node_id: int) -> Dict:
        """
        Obtener estado actual de un dispositivo.
        
        Args:
            node_id: ID del dispositivo
        
        Returns:
            Dict con el estado del dispositivo
        """
        if node_id not in self.devices:
            raise ValueError(f"Dispositivo {node_id} no encontrado")
        
        device = self.devices[node_id]
        
        # TODO: Leer estado real del dispositivo
        # state = await self.chip_controller.ReadAttribute(
        #     node_id,
        #     [(device.endpoint_id, OnOff.Attributes.OnOff)]
        # )
        
        # MOCK: Devolver estado en memoria
        return {
            "node_id": device.node_id,
            "name": device.name,
            "type": device.device_type,
            "online": device.is_online,
            "state": device.state.copy()
        }
    
    # ========== GESTIÓN DE DISPOSITIVOS ==========
    
    async def remove_device(self, node_id: int):
        """
        Eliminar dispositivo del sistema.
        
        Args:
            node_id: ID del dispositivo a eliminar
        """
        if node_id not in self.devices:
            raise ValueError(f"Dispositivo {node_id} no encontrado")
        
        device = self.devices[node_id]
        
        # TODO: Unpair real del fabric Matter
        # await self.chip_controller.SendCommand(
        #     node_id, 0,
        #     OperationalCredentials.Commands.RemoveFabric(fabricIndex=1)
        # )
        
        del self.devices[node_id]
        
        # TODO: Eliminar de BD
        # await self._delete_from_db(node_id)
        
        logger.success(f"🗑️  Dispositivo eliminado: {device.name}")
    
    def list_devices(self) -> list[Device]:
        """Obtener lista de todos los dispositivos"""
        return list(self.devices.values())
    
    # ========== HELPERS PRIVADOS ==========
    
    def _get_next_node_id(self) -> int:
        """Obtener siguiente ID de nodo disponible"""
        if not self.devices:
            return 1
        return max(self.devices.keys()) + 1
    
    async def _load_saved_devices(self):
        """Cargar dispositivos guardados de sesiones anteriores"""
        # TODO: Cargar desde base de datos
        # Por ahora: crear un dispositivo de ejemplo
        db = get_database()
        devices = db.get_all_devices()
        if devices:
            for d in devices:
                state = json.loads(d.state) if d.state else {}
                device = Device(
                    node_id=d.node_id,
                    name=d.name,
                    device_type=d.device_type,
                    endpoint_id=d.endpoint_id,
                    is_online=d.is_online,
                    state=state
                )
                self.devices[d.node_id] = device
            logger.info(f"📦 {len(devices)} dispositivos cargados desde BD")
        else:
            example_device = Device(
                node_id=1,
                name="Luz de Ejemplo",
                device_type="light",
                is_online=True
            )
            self.devices[1] = example_device
            logger.info("📦 Dispositivo de ejemplo cargado")
            
    async def _save_device(self, device: Device):
        """Guardar dispositivo en base de datos"""
        db = get_database()
        db.save_device(
            node_id=device.node_id,
            name=device.name,
            device_type=device.device_type,
            endpoint_id=device.endpoint_id,
            is_online=device.is_online,
            state=device.state
        )
        logger.debug(f"💾 Dispositivo guardado en BD: {device.name}")