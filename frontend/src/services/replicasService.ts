import api from "./api";

// Interface para resposta de criação de réplica
export interface ReplicaCreateResponse {
  msg: string;
  details: ReplicaDetails;
  user: string;
}

// Interface para detalhes da réplica
export interface ReplicaDetails {
  container_id: string;
  name: string;
  database_name: string;
  port: number;
  status: string;
  connection_string: string;
}

// Interface para resposta de get my replica
export interface MyReplicaResponse {
  container_id: string;
  name: string;
  username: string;
  database_name: string;
  port: number;
  status: string;
  created: string;
  connection_string: string | null;
}

// Interface para réplica no painel admin
export interface AdminReplicaItem {
  container_id: string;
  name: string;
  username: string;
  database_name: string;
  port: number;
  status: string;
  created: string;
}

// Interface para resposta de listagem admin
export interface AdminReplicasListResponse {
  total: number;
  replicas: AdminReplicaItem[];
}

/**
 * Cria uma nova réplica para o usuário logado
 * @param dbPassword - Senha para o banco de dados PostgreSQL
 * @returns Detalhes da réplica criada
 */
export const createReplica = async (
  dbPassword: string
): Promise<ReplicaCreateResponse> => {
  try {
    const response = await api.post<ReplicaCreateResponse>("/replicas/create", {
      db_password: dbPassword,
    });
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 409) {
      throw new Error("Você já possui uma réplica ativa.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao criar réplica.");
  }
};

/**
 * Busca informações da réplica do usuário logado
 * @returns Detalhes da réplica ou null se não encontrada
 */
export const getMyReplica = async (): Promise<MyReplicaResponse | null> => {
  try {
    const response = await api.get<MyReplicaResponse>("/replicas/my-replica");
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 404) {
      return null; // Usuário não tem réplica
    }
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao buscar réplica.");
  }
};

/**
 * Lista todas as réplicas do sistema (para admin)
 * @returns Lista de todas as réplicas
 */
export const listAllReplicas = async (): Promise<AdminReplicasListResponse> => {
  try {
    const response = await api.get<AdminReplicasListResponse>("/replicas/list");
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao listar réplicas.");
  }
};

/**
 * Deleta a réplica de um usuário específico (para admin)
 * @param username - Nome do usuário
 * @returns Resultado da operação
 */
export const deleteUserReplica = async (username: string): Promise<any> => {
  try {
    const response = await api.delete(`/replicas/user/${username}`);
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Réplica não encontrada.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao deletar réplica.");
  }
};

/**
 * Deleta todas as réplicas do sistema (para admin)
 * @returns Resultado da operação
 */
export const deleteAllReplicas = async (): Promise<any> => {
  try {
    const response = await api.delete("/replicas/delete-all");
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao deletar todas as réplicas."
    );
  }
};
