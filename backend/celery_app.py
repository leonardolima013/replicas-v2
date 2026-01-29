"""
Configuração do Celery para processamento assíncrono de relatórios de validação.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from celery import Celery

# Carregar variáveis de ambiente do .env (se existir - não existe no Docker)
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Configuração do broker Redis
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

# Criar instância do Celery
celery_app = Celery(
    "replicas_v2",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.services.data_validation.tasks"]
)

# Configurações do Celery
celery_app.conf.update(
    # Serialização
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="America/Sao_Paulo",
    enable_utc=True,
    
    # Controle de concorrência - facilmente ajustável
    worker_concurrency=int(os.getenv("MAX_CONCURRENT_PROCESSING", "1")),
    
    # Não pré-buscar tasks (garante processamento sequencial)
    worker_prefetch_multiplier=1,
    
    # Resultado expira em 24 horas
    result_expires=86400,
    
    # Não perder task se worker morrer
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Retry automático em caso de falha de conexão
    broker_connection_retry_on_startup=True,
    
    # Rate limit (pode ser ajustado)
    task_default_rate_limit="10/m",
)

# Para permitir descoberta automática de tasks
celery_app.autodiscover_tasks(["backend.services.data_validation"])
