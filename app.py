import subprocess
import json
import os
import logging
from colorama import Fore, Style

# Configuración para registro de logs
logging.basicConfig(
    filename="docker_manager.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

CONFIG_FILE = "docker_services_config.json"

# Funciones para manejo de configuraciones
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(service_name, config):
    configs = load_config()
    configs[service_name] = config
    with open(CONFIG_FILE, "w") as f:
        json.dump(configs, f, indent=4)
    print(f"{Fore.YELLOW}Configuración de {service_name} guardada exitosamente.{Style.RESET_ALL}")

# Función para verificar si un puerto está en uso
def is_port_in_use(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", int(port))) == 0

# Función para verificar si un contenedor ya existe
def container_exists(name):
    result = subprocess.run(["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}"],
                            stdout=subprocess.PIPE, text=True)
    return name in result.stdout.splitlines()

# Lista de servicios disponibles
SERVICES = {
    "grafana": {
        "image": "grafana/grafana:latest",
        "port": "3000:3000",
        "name": "grafana"
    },
    "minio": {
        "image": "minio/minio:latest",
        "port": "9000:9000",
        "name": "minio",
        "env": ["MINIO_ROOT_USER=admin", "MINIO_ROOT_PASSWORD=password"],
        "command": "server /data"
    },
    "jenkins": {
        "image": "jenkins/jenkins:lts",
        "port": "8080:8080",
        "name": "jenkins"
    },
    "gitlab": {
        "image": "gitlab/gitlab-ce:latest",
        "port": "8081:80",
        "name": "gitlab",
        "env": ["GITLAB_OMNIBUS_CONFIG=external_url 'http://localhost:8081'"]
    }
}

# Función para crear contenedores
def create_container(service, custom=False):
    if service not in SERVICES:
        print(f"{Fore.RED}Servicio no soportado.{Style.RESET_ALL}")
        return

    config = SERVICES[service]

    # Verificar si ya existe el contenedor
    if container_exists(config["name"]):
        print(f"{Fore.RED}Ya existe un contenedor con el nombre {config['name']}. Detén o elimina el contenedor antes de continuar.{Style.RESET_ALL}")
        return

    # Personalización
    if custom:
        print(f"Configurando {service}...")
        config["port"] = input(f"Ingrese el puerto (predeterminado {config['port']}): ") or config["port"]
        config["name"] = input(f"Ingrese el nombre del contenedor (predeterminado {config['name']}): ") or config["name"]
        if "env" in config:
            for i, env_var in enumerate(config["env"]):
                key, value = env_var.split("=")
                new_value = input(f"{key} (predeterminado {value}): ") or value
                config["env"][i] = f"{key}={new_value}"
        save_config(service, config)

    # Verificar si el puerto está en uso
    host_port = config["port"].split(":")[0]
    if is_port_in_use(host_port):
        print(f"{Fore.RED}El puerto {host_port} ya está en uso. Selecciona otro puerto.{Style.RESET_ALL}")
        return

    command = [
        "docker", "run", "-d", "--name", config["name"],
        "-p", config["port"]
    ]

    if "env" in config:
        for env_var in config["env"]:
            command += ["-e", env_var]

    if "volume" in config:
        for volume in config["volume"]:
            command += ["-v", volume]

    command.append(config["image"])
    
    if "command" in config:
        command.append(config["command"])

    try:
        subprocess.run(command, check=True)
        print(f"{Fore.GREEN}Contenedor para {service} creado exitosamente.{Style.RESET_ALL}")
        logging.info(f"Creación exitosa del contenedor {service}.")
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error al crear el contenedor de {service}: {e}{Style.RESET_ALL}")
        logging.error(f"Error al crear el contenedor {service}: {e}")

# Función para listar contenedores activos
def list_containers():
    print("\nContenedores activos:")
    try:
        subprocess.run(["docker", "ps"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error al listar contenedores: {e}{Style.RESET_ALL}")

# Función para detener un contenedor
def stop_container():
    container_name = input("Ingresa el nombre del contenedor a detener: ")
    try:
        subprocess.run(["docker", "stop", container_name], check=True)
        print(f"{Fore.GREEN}Contenedor {container_name} detenido exitosamente.{Style.RESET_ALL}")
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error al detener el contenedor: {e}{Style.RESET_ALL}")

# Función para eliminar un contenedor
def remove_container():
    container_name = input("Ingresa el nombre del contenedor a eliminar: ")
    try:
        subprocess.run(["docker", "rm", container_name], check=True)
        print(f"{Fore.GREEN}Contenedor {container_name} eliminado exitosamente.{Style.RESET_ALL}")
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error al eliminar el contenedor: {e}{Style.RESET_ALL}")

# Función para seleccionar contenedores
def select_containers():
    print("\nOpciones de creación de contenedores:")
    print("1. Crear un contenedor")
    print("2. Crear todos los contenedores")
    print("3. Crear un rango de contenedores (por índice)")
    print("4. Crear una lista de contenedores separados por comas")
    choice = input("Selecciona una opción: ")

    if choice == "1":
        service = input(f"Ingrese el servicio a crear ({', '.join(SERVICES.keys())}): ").strip().lower()
        custom = input("¿Quieres personalizar la configuración? (s/n): ").lower() == "s"
        create_container(service, custom)
    elif choice == "2":
        for service in SERVICES:
            create_container(service)
    elif choice == "3":
        print(f"Índices disponibles: {', '.join(f'{i}-{service}' for i, service in enumerate(SERVICES.keys()))}")
        start = int(input("Ingrese el índice inicial: "))
        end = int(input("Ingrese el índice final: "))
        for i, service in enumerate(SERVICES.keys()):
            if start <= i <= end:
                create_container(service)
    elif choice == "4":
        services = input(f"Ingrese los servicios separados por coma ({', '.join(SERVICES.keys())}): ").strip().lower().split(",")
        for service in services:
            create_container(service.strip())
    else:
        print(f"{Fore.RED}Opción no válida.{Style.RESET_ALL}")

# Menú principal
def show_menu():
    print("\nMenú de Servicios Docker")
    print("1. Crear contenedores")
    print("2. Listar contenedores activos")
    print("3. Detener un contenedor")
    print("4. Eliminar un contenedor")
    print("5. Salir")
    choice = input("Selecciona una opción: ")
    return choice

# Programa principal
def main():
    while True:
        choice = show_menu()
        if choice == "1":
            select_containers()
        elif choice == "2":
            list_containers()
        elif choice == "3":
            stop_container()
        elif choice == "4":
            remove_container()
        elif choice == "5":
            print(f"{Fore.YELLOW}Saliendo del programa. ¡Adiós!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Opción no válida, intenta nuevamente.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
