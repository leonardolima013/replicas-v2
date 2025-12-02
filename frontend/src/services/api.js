import axios from "axios";

const api = axios.create({
  baseURL: window.location.origin,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor para adicionar o token de autenticação
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
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default {
  // Autenticação
  login(username, password) {
    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);
    return api.post("/auth/login", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  logout() {
    localStorage.removeItem("access_token");
  },

  // Projetos
  getProjects() {
    return api.get("/data-validation/projects");
  },

  getValidationProject(projectId) {
    return api.get(`/data-validation/projects/${projectId}`);
  },

  getProjectPreview(projectId) {
    return api.get(`/data-validation/projects/${projectId}/preview`);
  },

  createProject(projectData) {
    return api.post("/data-validation/projects", projectData);
  },

  deleteProject(projectId) {
    return api.delete(`/data-validation/projects/${projectId}`);
  },

  // Upload de CSV
  uploadCSV(projectId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`/data-validation/projects/${projectId}/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  // Visualização de dados
  getProjectData(projectId, page = 1, pageSize = 50) {
    return api.get(`/data-validation/projects/${projectId}/data`, {
      params: { page, page_size: pageSize },
    });
  },

  // Schema do sistema
  getSystemSchema() {
    return api.get("/data-validation/system-schema");
  },

  // Mapeamento de colunas
  getCsvColumns(projectId) {
    return api.get(`/data-validation/projects/${projectId}/csv-columns`);
  },

  saveColumnMapping(projectId, columnMapping) {
    return api.post(`/data-validation/projects/${projectId}/column-mapping`, {
      column_mapping: columnMapping,
    });
  },

  getColumnMapping(projectId) {
    return api.get(`/data-validation/projects/${projectId}/column-mapping`);
  },

  // ETAPA 2: TRATAMENTOS AUTOMATIZADOS

  // Verificar strings nulas
  checkNullStrings(projectId) {
    return api.get(`/data-validation/projects/${projectId}/check-null-strings`);
  },

  // Substituir strings nulas
  replaceNullStrings(projectId) {
    return api.post(
      `/data-validation/projects/${projectId}/replace-null-strings`
    );
  },

  // Verificar lowercase
  checkLowercase(projectId) {
    return api.get(`/data-validation/projects/${projectId}/check-lowercase`);
  },

  // Converter para uppercase
  convertToUppercase(projectId, columns) {
    return api.post(
      `/data-validation/projects/${projectId}/convert-uppercase`,
      {
        columns,
      }
    );
  },

  // Verificar numéricos nulos
  checkNullNumerics(projectId) {
    return api.get(
      `/data-validation/projects/${projectId}/check-null-numerics`
    );
  },

  // Substituir numéricos nulos
  replaceNullNumerics(projectId) {
    return api.post(
      `/data-validation/projects/${projectId}/replace-null-numerics`
    );
  },
};
