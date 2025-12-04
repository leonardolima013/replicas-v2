import api from "./api";

// ==================== INTERFACES ====================

// Interface para projeto
export interface Project {
  id: string;
  original_filename: string;
  created_at: string;
  status: "DRAFT" | "PENDING" | "DONE";
  owner_username?: string;
  total_rows?: number;
}

// Interface para resposta de listagem de projetos
export interface ProjectsListResponse {
  projects: Project[];
  total: number;
}

// Interface para upload de arquivo
export interface UploadResponse {
  id: string;
  original_filename: string;
  status: string;
  created_at: string;
  owner_username?: string;
}

// Interface para preview de dados
export interface PreviewResponse {
  rows: Record<string, any>[];
  total_rows: number;
  page: number;
  page_size: number;
  columns: string[];
}

// Interface para diagnóstico de tratamentos
export interface TreatmentDiagnosisResponse {
  project_id?: string;
  // Diagnósticos básicos (retornam arrays de nomes de colunas)
  uppercase_issues?: string[];
  null_string_issues?: string[];
  null_numeric_issues?: string[];
  // Diagnósticos avançados (retornam contadores)
  brand_issues: number;
  ncm_issues: number;
  barcode_issues: number;
  weight_issues: number;
  dimension_issues: number;
  search_ref_issues: number;
  manufacturer_ref_issues: number;
}

// Interface para resposta de fix
export interface FixResponse {
  message: string;
  columns_affected: string[];
  rows_affected: number;
}

// Interface para análise de colunas
export interface ColumnsAnalysisResponse {
  missing: string[]; // Colunas obrigatórias que faltam
  extra: string[]; // Colunas não reconhecidas
  present: string[]; // Colunas presentes na tabela
  required: string[]; // Lista de colunas obrigatórias
  optional: string[]; // Lista de colunas opcionais
}

// Interface para renomear coluna
export interface RenameColumnRequest {
  old_name: string;
  new_name: string;
}

export interface RenameColumnResponse {
  message: string;
  old_name: string;
  new_name: string;
}

// ==================== FUNÇÕES DE API ====================

/**
 * Lista todos os projetos do usuário logado
 */
export const getProjects = async (): Promise<ProjectsListResponse> => {
  try {
    const response = await api.get<Project[]>("/validation/projects");
    return {
      projects: response.data,
      total: response.data.length,
    };
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao buscar projetos.");
  }
};

/**
 * Faz upload de um arquivo CSV
 * @param file - Arquivo CSV
 * @param projectName - Nome do projeto (opcional)
 */
export const uploadCSV = async (
  file: File,
  projectName?: string
): Promise<UploadResponse> => {
  try {
    const formData = new FormData();
    formData.append("file", file);
    if (projectName) {
      formData.append("project_name", projectName);
    }

    const response = await api.post<UploadResponse>(
      "/validation/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail || "Arquivo inválido. Envie um CSV válido."
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao fazer upload do arquivo."
    );
  }
};

/**
 * Busca preview dos dados de um projeto com paginação
 * @param projectId - ID do projeto
 * @param page - Número da página (começa em 1)
 * @param pageSize - Tamanho da página (padrão: 50)
 */
export const getPreview = async (
  projectId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<PreviewResponse> => {
  try {
    const response = await api.get<PreviewResponse>(
      `/validation/${projectId}/preview`,
      {
        params: { page, page_size: pageSize },
      }
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao buscar preview dos dados."
    );
  }
};

/**
 * Busca diagnóstico de tratamentos de um projeto
 * @param projectId - ID do projeto
 */
export const getDiagnosis = async (
  projectId: string
): Promise<TreatmentDiagnosisResponse> => {
  try {
    const response = await api.get<TreatmentDiagnosisResponse>(
      `/validation/${projectId}/treatments/diagnosis`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao buscar diagnóstico."
    );
  }
};

/**
 * Corrige problemas de NCM
 * @param projectId - ID do projeto
 */
export const fixNCM = async (projectId: string): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-ncm`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao corrigir NCM.");
  }
};

/**
 * Corrige problemas de código de barras
 * @param projectId - ID do projeto
 */
export const fixBarcodes = async (projectId: string): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-barcode`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao corrigir códigos de barras."
    );
  }
};

/**
 * Corrige problemas de pesos
 * @param projectId - ID do projeto
 */
export const fixWeights = async (projectId: string): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-negative-weights`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao corrigir pesos.");
  }
};

/**
 * Corrige problemas de dimensões
 * @param projectId - ID do projeto
 */
export const fixDimensions = async (
  projectId: string
): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-codes`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao corrigir dimensões."
    );
  }
};

/**
 * Corrige valores nulos em colunas de string
 * @param projectId - ID do projeto
 */
export const fixNullStrings = async (
  projectId: string
): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-nulls-string`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao corrigir nulos em strings."
    );
  }
};

/**
 * Converte valores para UPPERCASE
 * @param projectId - ID do projeto
 */
export const fixUppercase = async (projectId: string): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-uppercase`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao aplicar uppercase."
    );
  }
};

/**
 * Corrige valores nulos em colunas numéricas
 * @param projectId - ID do projeto
 */
export const fixNullNumerics = async (
  projectId: string
): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-nulls-numeric`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao corrigir nulos em numéricos."
    );
  }
};

/**
 * Analisa as colunas do projeto
 * @param projectId - ID do projeto
 */
export const getColumnsAnalysis = async (
  projectId: string
): Promise<ColumnsAnalysisResponse> => {
  try {
    const response = await api.get<ColumnsAnalysisResponse>(
      `/validation/${projectId}/columns/analysis`
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao analisar colunas."
    );
  }
};

/**
 * Renomeia uma coluna do projeto
 * @param projectId - ID do projeto
 * @param oldName - Nome atual da coluna
 * @param newName - Novo nome da coluna
 */
export const renameColumn = async (
  projectId: string,
  oldName: string,
  newName: string
): Promise<RenameColumnResponse> => {
  try {
    const response = await api.post<RenameColumnResponse>(
      `/validation/${projectId}/columns/rename`,
      { old_name: oldName, new_name: newName }
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto ou coluna não encontrada.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail || "Erro de validação ao renomear coluna."
      );
    }
    throw new Error(error.response?.data?.detail || "Erro ao renomear coluna.");
  }
};

/**
 * Envia o projeto para validação (DRAFT -> PENDING_REVIEW)
 * @param projectId - ID do projeto
 */
export const submitProject = async (projectId: string): Promise<Project> => {
  try {
    const response = await api.post<Project>(`/validation/${projectId}/submit`);
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão para enviar este projeto.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail || "Projeto não pode ser enviado."
      );
    }
    throw new Error(error.response?.data?.detail || "Erro ao enviar projeto.");
  }
};

/**
 * Cancela o envio do projeto (PENDING_REVIEW -> DRAFT)
 * @param projectId - ID do projeto
 */
export const cancelProject = async (projectId: string): Promise<Project> => {
  try {
    const response = await api.post<Project>(`/validation/${projectId}/cancel`);
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão para cancelar este projeto.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail || "Projeto não pode ser cancelado."
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao cancelar projeto."
    );
  }
};

/**
 * Deleta um projeto
 * @param projectId - ID do projeto
 */
export const deleteProject = async (projectId: string): Promise<void> => {
  try {
    await api.delete(`/validation/${projectId}`);
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão para deletar este projeto.");
    }
    throw new Error(error.response?.data?.detail || "Erro ao deletar projeto.");
  }
};
