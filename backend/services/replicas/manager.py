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

def create_replica_container(username: str, db_password: str):
    # Nome do banco sempre será {usuario}_db
    db_name = f"{username}_db"
    container_name = f"replica_{username}"

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
        environment=[
            f"POSTGRES_USER={username}",
            f"POSTGRES_PASSWORD={db_password}",
            f"POSTGRES_DB={db_name}"
        ],
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
        "database_name": db_name,
        "port": port,
        "status": container.status,
        "connection_string": f"ssh -L 5432:localhost:{port} utilizador@seu-servidor"
    }

def list_all_replicas():
    """Lista todas as réplicas (containers que começam com 'replica_')."""
    containers = client.containers.list(all=True, filters={"name": "replica_"})
    
    replicas = []
    for container in containers:
        # Extrai o username do nome do container (remove o prefixo 'replica_')
        username = container.name.replace("replica_", "")
        
        # Pega a porta mapeada
        port = None
        if container.ports and '5432/tcp' in container.ports:
            port_bindings = container.ports['5432/tcp']
            if port_bindings:
                port = int(port_bindings[0]['HostPort'])
        
        replicas.append({
            "container_id": container.short_id,
            "name": container.name,
            "username": username,
            "database_name": f"{username}_db",
            "port": port,
            "status": container.status,
            "created": container.attrs['Created']
        })
    
    return replicas

def get_user_replica(username: str):
    """Retorna informações sobre a réplica de um usuário específico."""
    container_name = f"replica_{username}"
    
    try:
        container = client.containers.get(container_name)
        
        # Pega a porta mapeada
        port = None
        if container.ports and '5432/tcp' in container.ports:
            port_bindings = container.ports['5432/tcp']
            if port_bindings:
                port = int(port_bindings[0]['HostPort'])
        
        return {
            "container_id": container.short_id,
            "name": container.name,
            "username": username,
            "database_name": f"{username}_db",
            "port": port,
            "status": container.status,
            "created": container.attrs['Created'],
            "connection_string": f"ssh -L 5432:localhost:{port} utilizador@seu-servidor" if port else None
        }
    except docker.errors.NotFound:
        return None

def delete_user_replica(username: str):
    """Deleta a réplica de um usuário específico."""
    container_name = f"replica_{username}"
    
    try:
        container = client.containers.get(container_name)
        
        # Para o container se estiver rodando
        if container.status == "running":
            container.stop()
        
        # Remove o container
        container.remove()
        
        return {
            "msg": f"Réplica do usuário '{username}' deletada com sucesso",
            "container_name": container_name,
            "username": username
        }
    except docker.errors.NotFound:
        return None

def delete_all_replicas():
    """Deleta todas as réplicas (containers que começam com 'replica_')."""
    containers = client.containers.list(all=True, filters={"name": "replica_"})
    
    deleted_replicas = []
    
    for container in containers:
        username = container.name.replace("replica_", "")
        
        try:
            # Para o container se estiver rodando
            if container.status == "running":
                container.stop()
            
            # Remove o container
            container.remove()
            
            deleted_replicas.append({
                "container_name": container.name,
                "username": username,
                "status": "deleted"
            })
        except Exception as e:
            deleted_replicas.append({
                "container_name": container.name,
                "username": username,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "msg": f"{len(deleted_replicas)} réplica(s) processada(s)",
        "deleted_count": len([r for r in deleted_replicas if r["status"] == "deleted"]),
        "replicas": deleted_replicas
    }