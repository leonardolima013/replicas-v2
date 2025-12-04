import axios, { type AxiosError } from "axios";

// Configuração base do Axios
const api = axios.create({
  baseURL: "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor de Request - Adiciona token de autenticação
api.interceptors.request.use(
  (config) => {
    // Buscar token do localStorage
    const token = localStorage.getItem("access_token");

    // Se existir token, adicionar ao header Authorization
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor de Response - Trata erros de autenticação
api.interceptors.response.use(
  (response) => {
    // Se a resposta for bem-sucedida, apenas retorna
    return response;
  },
  (error: AxiosError) => {
    // Se receber 401 Unauthorized
    if (error.response?.status === 401) {
      // Limpar token do localStorage
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");

      // Redirecionar para login
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

export default api;
