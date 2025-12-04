import docker
import socket
import time
from contextlib import closing

# Conecta ao Docker da máquina Host (graças ao volume que montámos)
client = docker.from_env()

# Credenciais ORIGINAIS que estão gravadas na imagem 'replicas/base:v1'
# Não mude isso, senão o container não sobe ou não conseguimos logar para criar o novo user.
BASE_IMAGE_USER = "pgroot"
BASE_IMAGE_PASSWORD = "pg@root"
BASE_IMAGE_DB = "pgroot"  # Banco onde o dump foi restaurado

def find_free_port():
    """Encontra uma porta aleatória livre no Host."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def wait_for_postgres(container, delay=2):
    """
    Aguarda o PostgreSQL ficar pronto para aceitar comandos.
    Continua tentando indefinidamente até conseguir conexão.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            # Tenta rodar 'SELECT 1' usando o usuário ROOT da imagem
            exit_code, output = container.exec_run(
                f"psql -U {BASE_IMAGE_USER} -d {BASE_IMAGE_DB} -c 'SELECT 1'",
                environment={"PGPASSWORD": BASE_IMAGE_PASSWORD}
            )
            if exit_code == 0:
                print(f"PostgreSQL pronto após {attempt} tentativa(s)")
                return True
        except Exception as e:
            print(f"Tentativa {attempt} falhou: {e}")
        time.sleep(delay)

def create_replica_container(username: str, db_password: str):
    """
    Cria um container de réplica a partir da imagem base com dump.
    
    1. Sobe o container com as credenciais originais da imagem
    2. Aguarda o PostgreSQL ficar pronto
    3. Cria um novo usuário com as credenciais fornecidas pelo dev
    4. Concede permissões SUPERUSER para acesso total aos dados
    """
    image_name = "replicas/base:v1"
    container_name = f"replica_{username}"

    # 1. Verificar se já existe e remover (para evitar erro de nome duplicado)
    try:
        old_container = client.containers.get(container_name)
        print(f"Removendo container antigo: {container_name}")
        if old_container.status == "running":
            old_container.stop(timeout=10)
        old_container.remove()
    except docker.errors.NotFound:
        pass  # Se não existe, segue o baile

    # 2. Encontrar porta livre
    port = find_free_port()

    # 3. Criar o container
    # Nota: A imagem já tem o usuário e senha configurados (pgroot/pg@root)
    # Não passamos POSTGRES_USER/PASSWORD pois a imagem já está configurada
    print(f"Criando container {container_name} na porta {port}")
    container = client.containers.run(
        image_name,
        name=container_name,
        detach=True,
        ports={'5432/tcp': port},
        environment=["PGDATA=/var/lib/postgresql/data_fixed"]
    )

    try:
        # 4. Aguardar o PostgreSQL ficar pronto
        print(f"Aguardando PostgreSQL iniciar no container {container_name}...")
        wait_for_postgres(container)

        # 5. Criar o usuário personalizado do dev
        print(f"Criando usuário '{username}' no banco de dados...")
        
        # Primeiro, verifica se o usuário já existe
        check_user_cmd = f"""
        psql -U {BASE_IMAGE_USER} -d {BASE_IMAGE_DB} -tAc "SELECT 1 FROM pg_roles WHERE rolname='{username}'"
        """
        exit_code, output = container.exec_run(
            ['/bin/sh', '-c', check_user_cmd],
            environment={"PGPASSWORD": BASE_IMAGE_PASSWORD}
        )
        
        user_exists = output.decode().strip() == '1'
        
        if user_exists:
            # Se já existe, apenas atualiza a senha
            print(f"Usuário '{username}' já existe, atualizando senha...")
            alter_user_cmd = f"""
            psql -U {BASE_IMAGE_USER} -d {BASE_IMAGE_DB} -c "
            ALTER USER {username} WITH PASSWORD '{db_password}';
            ALTER USER {username} WITH SUPERUSER;
            "
            """
            exit_code, output = container.exec_run(
                ['/bin/sh', '-c', alter_user_cmd],
                environment={"PGPASSWORD": BASE_IMAGE_PASSWORD}
            )
        else:
            # Cria o usuário novo
            print(f"Criando novo usuário '{username}'...")
            create_user_cmd = f"""
            psql -U {BASE_IMAGE_USER} -d {BASE_IMAGE_DB} -c "
            CREATE USER {username} WITH PASSWORD '{db_password}';
            ALTER USER {username} WITH SUPERUSER;
            "
            """
            exit_code, output = container.exec_run(
                ['/bin/sh', '-c', create_user_cmd],
                environment={"PGPASSWORD": BASE_IMAGE_PASSWORD}
            )
        
        if exit_code != 0:
            error_msg = output.decode()
            print(f"Erro ao configurar usuário: {error_msg}")
            raise Exception(f"Falha ao criar/atualizar usuário: {error_msg}")
        
        print(f"Usuário '{username}' configurado com sucesso!")

    except Exception as e:
        # Se algo falhar, limpa o container
        print(f"Erro durante a criação da réplica: {e}")
        try:
            container.stop(timeout=5)
            container.remove()
        except:
            pass
        raise

    # 6. Recarrega atributos para garantir status correto
    container.reload()

    return {
        "container_id": container.short_id,
        "name": container_name,
        "database_name": BASE_IMAGE_DB,  # O banco real onde estão os dados do dump
        "username": username,  # Usuário criado para o dev
        "port": port,
        "status": container.status,
        "connection_string": f"ssh -L 5432:localhost:{port} user@host"
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
            "database_name": BASE_IMAGE_DB,  # Banco real da imagem base
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
            "database_name": BASE_IMAGE_DB,  # Banco real da imagem base
            "port": port,
            "status": container.status,
            "created": container.attrs['Created'],
            "connection_string": f"ssh -L 5432:localhost:{port} user@host" if port else None
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