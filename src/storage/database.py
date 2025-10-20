"""
Database - Persistencia de dispositivos con SQLite
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

Base = declarative_base()


class DeviceDB(Base):
    """
    Modelo de dispositivo en base de datos.
    Representa un dispositivo Matter guardado.
    """

    __tablename__ = "devices"

    node_id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)  # "light", "switch", etc
    endpoint_id = Column(Integer, default=1)
    is_online = Column(Boolean, default=True)
    state = Column(Text, nullable=True)  # JSON string del estado
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DeviceDB(node_id={self.node_id}, name='{self.name}')>"


class Database:
    """
    Gestor de base de datos SQLite.
    Maneja conexiones y operaciones CRUD de dispositivos.
    """

    def __init__(self, db_path: str = "data/mattercenter.db"):
        """
        Inicializar base de datos.

        Args:
            db_path: Ruta al archivo SQLite
        """
        # Asegurar que existe el directorio
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Crear engine
        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,  # True para ver queries SQL en logs
            connect_args={"check_same_thread": False},  # Para uso async
        )

        # Crear SessionMaker
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Crear tablas si no existen
        Base.metadata.create_all(self.engine)

        logger.info(f"💾 Base de datos inicializada: {db_path}")

    def get_session(self) -> Session:
        """Crear una nueva sesión de base de datos"""
        return self.SessionLocal()

    # ========== CRUD Operations ==========

    def save_device(
        self,
        node_id: int,
        name: str,
        device_type: str,
        endpoint_id: int,
        is_online: bool,
        state: dict,
    ) -> DeviceDB:
        """
        Guardar o actualizar un dispositivo.

        Args:
            node_id: ID del nodo
            name: Nombre del dispositivo
            device_type: Tipo de dispositivo
            endpoint_id: ID del endpoint
            is_online: Estado online
            state: Estado actual del dispositivo (dict)

        Returns:
            DeviceDB: Dispositivo guardado
        """
        session = self.get_session()

        try:
            # Buscar si ya existe
            device = session.query(DeviceDB).filter_by(node_id=node_id).first()

            if device:
                # Actualizar existente
                device.name = name
                device.device_type = device_type
                device.endpoint_id = endpoint_id
                device.is_online = is_online
                device.state = json.dumps(state)
                device.updated_at = datetime.utcnow()
                logger.debug(f"Actualizando dispositivo {node_id}")
            else:
                # Crear nuevo
                device = DeviceDB(
                    node_id=node_id,
                    name=name,
                    device_type=device_type,
                    endpoint_id=endpoint_id,
                    is_online=is_online,
                    state=json.dumps(state),
                )
                session.add(device)
                logger.debug(f"Creando dispositivo {node_id}")

            session.commit()
            session.refresh(device)

            return device

        except Exception as e:
            session.rollback()
            logger.error(f"Error guardando dispositivo: {e}")
            raise
        finally:
            session.close()

    def get_device(self, node_id: int) -> Optional[DeviceDB]:
        """
        Obtener un dispositivo por su node_id.

        Args:
            node_id: ID del nodo

        Returns:
            DeviceDB o None si no existe
        """
        session = self.get_session()
        try:
            return session.query(DeviceDB).filter_by(node_id=node_id).first()
        finally:
            session.close()

    def get_all_devices(self) -> List[DeviceDB]:
        """
        Obtener todos los dispositivos.

        Returns:
            Lista de dispositivos
        """
        session = self.get_session()
        try:
            return session.query(DeviceDB).all()
        finally:
            session.close()

    def delete_device(self, node_id: int) -> bool:
        """
        Eliminar un dispositivo.

        Args:
            node_id: ID del nodo

        Returns:
            True si se eliminó, False si no existía
        """
        session = self.get_session()
        try:
            device = session.query(DeviceDB).filter_by(node_id=node_id).first()

            if device:
                session.delete(device)
                session.commit()
                logger.info(f"Dispositivo {node_id} eliminado de DB")
                return True

            return False

        except Exception as e:
            session.rollback()
            logger.error(f"Error eliminando dispositivo: {e}")
            raise
        finally:
            session.close()

    def update_device_state(self, node_id: int, state: dict):
        """
        Actualizar solo el estado de un dispositivo.

        Args:
            node_id: ID del nodo
            state: Nuevo estado
        """
        session = self.get_session()
        try:
            device = session.query(DeviceDB).filter_by(node_id=node_id).first()

            if device:
                device.state = json.dumps(state)
                device.updated_at = datetime.utcnow()
                session.commit()
            else:
                logger.warning(f"Dispositivo {node_id} no encontrado en DB")

        except Exception as e:
            session.rollback()
            logger.error(f"Error actualizando estado: {e}")
            raise
        finally:
            session.close()

    def close(self):
        """Cerrar conexiones de base de datos"""
        self.engine.dispose()
        logger.info("Base de datos cerrada")


# ========== Instancia global ==========
# Se inicializará desde main.py
_database: Optional[Database] = None


def init_database(db_path: str = "data/mattercenter.db") -> Database:
    """
    Inicializar la base de datos global.

    Args:
        db_path: Ruta al archivo SQLite

    Returns:
        Instancia de Database
    """
    global _database
    _database = Database(db_path)
    return _database


def get_database() -> Database:
    """
    Obtener instancia de la base de datos.

    Returns:
        Database

    Raises:
        RuntimeError: Si la base de datos no está inicializada
    """
    if _database is None:
        raise RuntimeError("Database no inicializada. Llama a init_database() primero")
    return _database
