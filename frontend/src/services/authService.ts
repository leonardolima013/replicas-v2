import api from "./api";

// Interface para a resposta de login do backend
interface LoginResponse {
  access_token: string;
  token_type: string;
  usuario: string;
  role: string;
}

// Interface para os dados do usuário armazenados
export interface User {
  usuario: string;
  role: string;
}

/**
 * Função de login que autentica o usuário no backend
 * @param username - Email ou nome de usuário
 * @param password - Senha do usuário
 * @returns Dados do usuário autenticado
 */
export const login = async (
  username: string,
  password: string
): Promise<User> => {
  try {
    // Chamada à API de login (POST /auth/login)
    // O backend espera form-data (application/x-www-form-urlencoded)
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await api.post<LoginResponse>("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    const { access_token, usuario, role } = response.data;

    // Salvar token no localStorage
    localStorage.setItem("access_token", access_token);

    // Salvar dados do usuário no localStorage
    const user: User = { usuario, role };
    localStorage.setItem("user", JSON.stringify(user));

    return user;
  } catch (error: any) {
    // Tratar erros de autenticação
    if (error.response?.status === 401) {
      throw new Error("Credenciais inválidas. Verifique seu usuário e senha.");
    }

    if (error.response?.status === 422) {
      throw new Error("Dados de login inválidos. Preencha todos os campos.");
    }

    throw new Error("Erro ao fazer login. Tente novamente mais tarde.");
  }
};

/**
 * Função de logout que remove os dados de autenticação
 */
export const logout = (): void => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
  window.location.href = "/login";
};

/**
 * Retorna o usuário atualmente autenticado
 * @returns Dados do usuário ou null se não estiver autenticado
 */
export const getCurrentUser = (): User | null => {
  const userStr = localStorage.getItem("user");
  if (!userStr) return null;

  try {
    return JSON.parse(userStr) as User;
  } catch {
    return null;
  }
};

/**
 * Verifica se o usuário está autenticado
 * @returns true se houver um token válido
 */
export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem("access_token");
};
