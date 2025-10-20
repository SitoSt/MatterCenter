"""
MatterController - Gestión de dispositivos Matter
Implementación como cliente para un `python-matter-server` a través de WebSockets.
"""

import asyncio
import json
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import websockets
from websockets.protocol import State
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException
from loguru import logger
import os

from storage.database import get_database


# La clase Device sigue siendo útil para estructurar los datos en nuestra aplicación
@dataclass
class Device:
    """Representación de un dispositivo Matter en MatterCenter."""

    node_id: int
    name: str
    device_type: str  # Ej: "dimmable_light"
    is_online: bool = True
    endpoint_id: int = 1
    state: Dict = field(default_factory=dict)

    # Podríamos añadir más campos que nos dé el matter-server, como:
    # unique_id: str = ""
    # available: bool = False


class MatterController:
    """
    Controlador que se conecta a `python-matter-server` para gestionar dispositivos.

    Responsabilidades:
    - Mantener una conexión WebSocket persistente con el servidor.
    - Sincronizar el estado de los dispositivos.
    - Traducir los comandos de la API a comandos del servidor Matter.
    - Gestionar el comisionamiento y eliminación de dispositivos a través del servidor.
    """

    def __init__(self):
        # El caché local de dispositivos. El servidor es la fuente de verdad.
        self.devices: Dict[int, Device] = {}

        # Configuración del servidor
        server_host = os.getenv("MATTER_SERVER_HOST", "localhost")
        server_port = os.getenv("MATTER_SERVER_PORT", "5580")
        self.server_url = f"ws://{server_host}:{server_port}/ws"

        self.connection: Optional[WebSocketClientProtocol] = None
        self.is_initialized = False
        self._message_id_counter = 1
        # self.reconnect_task = None
        # # CAMBIO CLAVE: "Buzones" para las respuestas a comandos
        # self._pending_commands: Dict[str, asyncio.Future] = {}

    def _get_next_message_id(self) -> str:
        """Genera un ID de mensaje incremental."""
        current_id = str(self._message_id_counter)
        self._message_id_counter += 1
        return current_id

    async def initialize(self):
        """
        Inicializa el controlador estableciendo la conexión WebSocket
        y comenzando a escuchar eventos del servidor Matter.
        """
        if self.is_initialized:
            return

        logger.info(f"🔧 Conectando a python-matter-server en {self.server_url}...")

        try:
            # 1. Conectar con un timeout generoso.
            self.connection = await websockets.connect(self.server_url, open_timeout=15)
            logger.success("🔌 Conexión WebSocket establecida.")

            # # 2. Iniciar el listener de eventos. Es crucial que se inicie ANTES
            # # de enviar cualquier comando para no perder respuestas.
            # asyncio.create_task(self._listen_for_events())

            # 3. Suscribirse a los eventos y ESPERAR la confirmación.
            logger.info("Subscribiendo a eventos del servidor...")
            await self._send_and_wait_for_response("start_listening")
            logger.success("✅ Subscripción a eventos confirmada.")

            # 4. Cargar los dispositivos iniciales.
            await self._load_initial_devices()

            self.is_initialized = True
            logger.success("✅ Conectado y sincronizado con python-matter-server")

        except (
            ConnectionRefusedError,
            OSError,
            WebSocketException,
            asyncio.TimeoutError,
        ) as e:
            logger.error("❌ Todos los intentos de conexión han fallado.")
            logger.error("Asegúrate de que el servidor esté en ejecución y accesible.")

    async def shutdown(self):
        """Cierra la conexión con el servidor Matter y guarda el estado."""
        if self.connection and self.connection.state == State.OPEN:
            await self.connection.close()
            logger.info("🔌 Conexión con Matter Server cerrada.")

        self.is_initialized = False

    async def _send_and_wait_for_response(self, command: str, **kwargs) -> Dict:
        """
        Método único y robusto para la comunicación.
        Envía un comando y entra en un bucle de escucha hasta encontrar la respuesta.
        """
        if not self.connection or self.connection.state != State.OPEN:
            raise ConnectionError("No hay conexión con el Matter Server.")

        message_id = self._get_next_message_id()
        payload = {"message_id": message_id, "command": command, "args": kwargs}

        logger.debug(f"--> Enviando comando: {payload}")
        await self.connection.send(json.dumps(payload))

        start_time = time.time()
        while time.time() - start_time < 20:  # Timeout de 20 segundos
            try:
                raw_response = await asyncio.wait_for(
                    self.connection.recv(), timeout=1.0
                )
                response = json.loads(raw_response)
                logger.debug(f"<-- Mensaje recibido: {response}")

                if response.get("message_id") == message_id:
                    if response.get("error_code"):
                        error_details = response.get("details", str(response))
                        raise RuntimeError(f"Error del servidor: {error_details}")
                    return response
                else:
                    # Ignorar eventos o respuestas para otros comandos
                    logger.debug(
                        "Mensaje recibido pero no es la respuesta esperada. Ignorando."
                    )
                    continue

            except asyncio.TimeoutError:
                # No hubo mensajes en 1 segundo, el bucle de 20s continúa.
                continue

        raise TimeoutError(
            f"No se recibió respuesta para el comando '{command}' (id: {message_id}) en 20 segundos."
        )

    def _update_device_from_server_data(self, data: Dict):
        node_id = data["node_id"]

        device_type = "unknown"
        if 257 in data["device_info"]["device_type_configs"]:
            device_type = "light"
        if 259 in data["device_info"]["device_type_configs"]:
            device_type = "dimmable_light"

        state = {}
        for endpoint in data["attributes"].values():
            if "6.1" in endpoint:
                state["on"] = endpoint["6.1"]
            if "8.0" in endpoint:
                state["brightness"] = round(endpoint["8.0"] / 2.54)

        if node_id in self.devices:
            device = self.devices[node_id]
            device.is_online = data["available"]
            device.state = state
        else:
            device = Device(
                node_id=node_id.to,
                name=data["node_info"].get("name", f"Dispositivo {node_id}"),
                device_type=device_type,
                is_online=data["available"],
                state=state,
            )
            self.devices[node_id] = device
            logger.info(
                f"✨ Dispositivo nuevo detectado: {device.name} (Node {node_id})"
            )

    async def _load_initial_devices(self):
        """Pide al servidor la lista completa de nodos al iniciar."""
        logger.info("📦 Solicitando lista de dispositivos al servidor...")
        response = await self._send_and_wait_for_response("get_nodes")
        for data in response["result"]:
            self._update_device_from_server_data(data)
        logger.success(
            f"✅ {len(self.devices)} dispositivos cargados desde el servidor."
        )

    # ========== MÉTODOS PÚBLICOS USADOS POR LA API ==========

    async def commission_device(self, setup_code: str):
        logger.info("🔗 Solicitando comisionamiento al servidor...")
        response = await self._send_and_wait_for_response(
            "commission_with_code", code=setup_code
        )
        # Después de comisionar, volvemos a cargar la lista para obtener el nuevo dispositivo
        await self._load_initial_devices()
        logger.success(f"Dispositivo comisionado con éxito: {response.get('result')}")
        return response.get("result", {})

    def list_devices(self) -> List[Device]:
        """Devuelve la lista de dispositivos desde el caché local."""
        return list(self.devices.values())

    async def send_command(self, node_id: int, command: str, **params):
        """
        Envía un comando a un dispositivo, traduciéndolo al formato del servidor.
        """
        if node_id not in self.devices:
            raise ValueError(f"Dispositivo {node_id} no encontrado")

        device = self.devices[node_id]
        logger.info(f"📤 Comando '{command}' → {device.name} (Node {node_id})")

        # Traducción de comandos de la API a comandos del servidor
        server_command = ""
        command_params = {}

        if command == "on":
            server_command = "on_off.on"
        elif command == "off":
            server_command = "on_off.off"
        elif command == "toggle":
            server_command = "on_off.toggle"
        elif command == "level":
            brightness_percent = params.get("level", 100)
            if not 0 <= brightness_percent <= 100:
                raise ValueError("El brillo debe estar entre 0 y 100")
            # Convertir porcentaje a valor Matter (0-254)
            level = int(brightness_percent * 2.54)
            server_command = "level_control.move_to_level"
            command_params = {"level": level, "transition_time": 1}  # 0.1s transition
        else:
            raise ValueError(f"Comando no reconocido: {command}")

        # Enviar comando al servidor
        result = await self._send_and_wait_for_response(
            "device_command",
            node_id=node_id,
            name=server_command,
            params=command_params,
        )
        logger.debug(f"Respuesta del servidor al comando: {result}")
        return result.get("result", {})

    async def remove_device(self, node_id: int):
        if node_id not in self.devices:
            raise ValueError(f"Dispositivo {node_id} no encontrado")

        logger.warning(
            f"🗑️ Solicitando eliminación del dispositivo {node_id} al servidor..."
        )
        await self._send_and_wait_for_response("remove_node", node_id=node_id)
        # Refrescar la lista de dispositivos después de eliminar
        await self._load_initial_devices()
