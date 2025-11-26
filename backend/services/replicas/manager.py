import docker
import socket
import time
from contextlib import closing

# Conecta ao Docker da máquina Host (graças ao volume que montámos)
client = docker.from_env()

def find_free_port():
    """Encontra uma porta aleatória livre no Host."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def create_replica_container(user_email: str):
    # Sanitiza o email para usar no nome do contentor (ex: joao@empresa -> replica_joao_empresa)
    safe_name = user_email.replace("@", "_").replace(".", "_")
    container_name = f"replica_{safe_name}"

    # 1. Verificar se já existe e remover (para evitar erro de nome duplicado)
    try:
        old_container = client.containers.get(container_name)
        if old_container.status == "running":
            old_container.stop()
        old_container.remove()
    except docker.errors.NotFound:
        pass # Se não existe, segue o baile

    # 2. Encontrar porta
    port = find_free_port()

    # 3. Criar o contentor
    # Nota: No futuro, mudaremos 'postgres:alpine' para 'sua-imagem-com-dump'
    container = client.containers.run(
        "postgres:alpine",
        name=container_name,
        environment=["POSTGRES_PASSWORD=replica_segura"],
        detach=True,
        ports={'5432/tcp': port} # Mapeia 5432 interna para a porta aleatória externa
    )

    # Pequena pausa para garantir que o contentor iniciou
    time.sleep(2)
    
    # Recarrega atributos para garantir que pegamos o status correto
    container.reload()

    return {
        "container_id": container.short_id,
        "name": container_name,
        "port": port,
        "status": container.status,
        "connection_string": f"ssh -L 5432:localhost:{port} utilizador@seu-servidor"
    }