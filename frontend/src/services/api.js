import axios from "axios";

const api = axios.create({
  baseURL: window.location.origin,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor para adicionar token em todas as requisições
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para tratar erros de autenticação
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_role");
      localStorage.removeItem("username");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default {
  // Auth
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await api.post("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return response.data;
  },

  // Users
  async createUser(userData) {
    const response = await api.post("/users/", userData);
    return response.data;
  },

  async getUsers() {
    const response = await api.get("/users/");
    return response.data;
  },

  // Replicas
  async createReplica(password) {
    const response = await api.post("/replicas/create", {
      db_password: password,
    });
    return response.data;
  },

  async getMyReplica() {
    const response = await api.get("/replicas/my-replica");
    return response.data;
  },

  async listAllReplicas() {
    const response = await api.get("/replicas/list");
    return response.data;
  },

  async deleteReplica(username) {
    const response = await api.delete(`/replicas/user/${username}`);
    return response.data;
  },

  async deleteAllReplicas() {
    const response = await api.delete("/replicas/delete-all");
    return response.data;
  },
};
