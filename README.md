# MatterCenter - J Bridge

Un servidor API REST autohospedado para controlar dispositivos Matter, construido sobre `python-matter-server`.

Este proyecto nace como una capa de control unificada, escrita en FastAPI, que se comunica con un `python-matter-server` oficial para gestionar el comisionamiento y el control de dispositivos Matter.

## Stack Tecnológico

* **API:** FastAPI
* **Motor Matter:** `python-matter-server` (imagen oficial de Home Assistant)
* **Base de Datos:** SQLite (para persistir nombres de dispositivos y estados)
* **Contenerización:** Docker & Docker Compose

## Despliegue (¡Leer con Atención!)

El despliegue de `python-matter-server` es complejo y requiere permisos elevados y una configuración específica del **servidor anfitrión (Host)**.

### 1. Prerrequisitos del Servidor Anfitrión (Host)

Asume un servidor Ubuntu/Debian. **El `docker-compose` fallará si no se cumplen estos pasos.**

#### a. Instalar Servicios de Red Esenciales

El servidor Matter necesita acceso de bajo nivel a Bluetooth y Wi-Fi.

```bash
# Instala el stack de Bluetooth de Linux
sudo apt install bluez -y

# Instala el gestor de redes (CRÍTICO para pasar credenciales Wi-Fi)
sudo apt install network-manager -y

# (Opcional) Herramientas de Docker
sudo apt install git docker-compose-plugin -y
```
#### b. Conectar el Host a Wi-Fi

#### c. Configurar Permisos D-Bus

matter-server (desde Docker) necesita permiso para hablar con NetworkManager y bluez (Bluetooth) en el host.

### 2. Instalación del proyecto

```bash
# 1. Clona el repositorio
git clone [https://github.com/tu-usuario/tu-proyecto.git](https://github.com/tu-usuario/tu-proyecto.git)
cd tu-proyecto

# 2. Construye y levanta los contenedores
docker compose up --build -d
```