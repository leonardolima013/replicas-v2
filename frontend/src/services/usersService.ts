import api from "./api";

// ==================== INTERFACES ====================

export interface User {
  id: number;
  usuario: string;
  role: "adm" | "dev";
}

export interface UserCreate {
  usuario: string;
  password: string;
  role: "adm" | "dev";
}

export interface DeleteUserResponse {
  msg: string;
  replica_deleted: boolean;
}

// ==================== FUNÇÕES DE API ====================

/**
 * Lista todos os usuários (apenas admin)
 */
export const getUsers = async (): Promise<User[]> => {
  try {
    const response = await api.get<User[]>("/users");
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error("Apenas administradores podem listar usuários.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao buscar usuários.");
  }
};

/**
 * Cria um novo usuário (apenas admin)
 */
export const createUser = async (user: UserCreate): Promise<User> => {
  try {
    const response = await api.post<User>("/users/", user);
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error("Apenas administradores podem criar usuários.");
    }
    if (error.response?.status === 400) {
      throw new Error(error.response?.data?.detail || "Usuário já cadastrado.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao criar usuário.");
  }
};

/**
 * Deleta um usuário (apenas admin)
 */
export const deleteUser = async (
  username: string
): Promise<DeleteUserResponse> => {
  try {
    const response = await api.delete<DeleteUserResponse>(`/users/${username}`);
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error("Apenas administradores podem deletar usuários.");
    }
    if (error.response?.status === 404) {
      throw new Error("Usuário não encontrado.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail ||
          "Você não pode deletar seu próprio usuário."
      );
    }
    throw new Error(error.response?.data?.detail || "Erro ao deletar usuário.");
  }
};
