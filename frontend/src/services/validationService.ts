import api from "./api";

// ==================== INTERFACES ====================

// Interface para projeto
export interface Project {
  id: string;
  original_filename: string;
  created_at: string;
  status:
    | "DRAFT"
    | "PENDING_REVIEW"
    | "PROCESSING_REPORT"
    | "READY_TO_PUBLISH"
    | "PROCESSING_ERROR"
    | "DONE";
  owner_username?: string;
  total_rows?: number;
}

// Interface para progresso do processamento
export interface ProjectProgress {
  project_id: string;
  status: string;
  processing_status: string | null;
  processing_progress: number;
  processing_step: string | null;
  error_message: string | null;
}

// Interface para relatório do projeto
export interface ProjectReport {
  project_id: string;
  total_rows: number;
  columns_found: number;
  parts_new: number;
  parts_existing: number;
  brands_new: number;
  brands_existing: number;
  brands_to_create: string[];
  processing_time_seconds: number | null;
  created_at: string;
  updated_at: string;
}

// Interface para item do histórico de validações
export interface ValidationHistoryItem {
  project_id: string;
  original_filename: string;
  owner_id: number;
  owner_username: string;
  created_at: string;
  published_by_id: number | null;
  published_by_username: string | null;
  published_at: string | null;
  total_rows: number;
  parts_created: number | null;
  parts_updated: number | null;
  brands_created: number | null;
  processing_time_seconds: number | null;
  publish_time_seconds: number | null;
}

// Interface para resposta do histórico de validações
export interface ValidationHistoryResponse {
  items: ValidationHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
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

// Interface para estatísticas
export interface ColumnStatistics {
  column: string;
  min: number | null;
  max: number | null;
  avg: number | null;
  stddev: number | null;
  q25: number | null;
  q50: number | null;
  q75: number | null;
}

export interface StatisticsResponse {
  project_id: string;
  summary: ColumnStatistics[];
  violations: {
    count_weight_error: number;
    count_negative: number;
  };
  correlation: number | null;
}

// Interface para diagnóstico de duplicatas
export interface DuplicatesDiagnosisResponse {
  total_duplicates: number;
  preview: Record<string, any>[];
  columns_used: string[];
  page: number;
  page_size: number;
  total_pages: number;
}

// Interface para correção de marca
export interface BrandCorrection {
  original_brand: string;
  corrected_brand: string;
  occurrences: number;
}

// Interface para marca desconhecida
export interface UnknownBrand {
  brand: string;
  occurrences: number;
}

// Interface para análise de mapeamento de marcas
export interface BrandAnalysisResponse {
  total_rows: number;
  mapped_count: number;
  unknown_count: number;
  top_corrections: BrandCorrection[];
  unknown_brands: UnknownBrand[];
}

// Interface para aplicação de mapeamento de marcas
export interface BrandApplicationResponse {
  message: string;
  rows_affected: number;
}

// Interfaces para Similaridades
export interface SimilarityIssue {
  row_number: number;
  search_ref: string | null;
  brand: string | null;
  similarity_value: any;
  issues: string[];
}

export interface SimilaritiesDiagnosisResponse {
  column_exists: boolean;
  format_issues: number;
  search_ref_issues: number;
  brand_issues: number;
  invalid_refs: number;
  invalid_brands: number;
  empty_list_issues: number;
  total_issues: number;
  preview: SimilarityIssue[];
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SimilaritiesStatisticsResponse {
  total_rows: number;
  rows_with_similarities: number;
  percentage_with_similarities: number;
  total_similarities: number;
  avg_similarities_per_row: number;
  top_search_refs: Array<{ search_ref: string; count: number }>;
  top_brands: Array<{ brand: string; count: number }>;
  distribution: Array<{ similarity_count: number; row_count: number }>;
  invalid_search_refs: string[];
  invalid_brands: string[];
}

// Interfaces para Relatório de Qualidade
export interface StructuralQuality {
  required_columns_present: number;
  required_columns_total: number;
  extra_columns_mapped: number;
  missing_columns: number;
}

export interface DataQualityMetrics {
  completeness_pct: number;
  total_rows: number;
  uppercase_issues: number;
  null_string_issues: number;
  null_numeric_issues: number;
  brand_issues: number;
  ncm_issues: number;
  barcode_issues: number;
  weight_issues: number;
  dimension_issues: number;
  search_ref_issues: number;
  manufacturer_ref_issues: number;
}

export interface BrandQualityMetrics {
  total_rows: number;
  normalized_count: number;
  normalized_pct: number;
  unknown_count: number;
  unknown_pct: number;
  top_unknown_brands: UnknownBrand[];
}

export interface DuplicatesQuality {
  found: number;
  removed: number;
}

export interface StatisticsQuality {
  weight_correlation: number | null;
  physical_violations: number;
  negative_values: number;
}

export interface QualityReportResponse {
  project_id: string;
  overall_quality_score: number;
  structural: StructuralQuality;
  data_quality: DataQualityMetrics;
  brands: BrandQualityMetrics;
  duplicates: DuplicatesQuality;
  statistics: StatisticsQuality;
  warnings: string[];
  blockers: string[];
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
  projectName?: string,
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
      },
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail ||
          "Arquivo inválido. Envie um CSV válido.",
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao fazer upload do arquivo.",
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
  pageSize: number = 50,
): Promise<PreviewResponse> => {
  try {
    const response = await api.get<PreviewResponse>(
      `/validation/${projectId}/preview`,
      {
        params: { page, page_size: pageSize },
      },
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
      error.response?.data?.detail || "Erro ao buscar preview dos dados.",
    );
  }
};

/**
 * Busca diagnóstico de tratamentos de um projeto
 * @param projectId - ID do projeto
 */
export const getDiagnosis = async (
  projectId: string,
): Promise<TreatmentDiagnosisResponse> => {
  try {
    const response = await api.get<TreatmentDiagnosisResponse>(
      `/validation/${projectId}/treatments/diagnosis`,
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
      error.response?.data?.detail || "Erro ao buscar diagnóstico.",
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
      `/validation/${projectId}/treatments/fix-ncm`,
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
      `/validation/${projectId}/treatments/fix-barcode`,
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
      error.response?.data?.detail || "Erro ao corrigir códigos de barras.",
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
      `/validation/${projectId}/treatments/fix-negative-weights`,
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
  projectId: string,
): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-dimensions`,
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
      error.response?.data?.detail || "Erro ao corrigir dimensões.",
    );
  }
};

/**
 * Corrige problemas de códigos de referência (search_ref e manufacturer_ref)
 * @param projectId - ID do projeto
 */
export const fixCodes = async (projectId: string): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-codes`,
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
      error.response?.data?.detail || "Erro ao corrigir códigos de referência.",
    );
  }
};

/**
 * Corrige valores nulos em colunas de string
 * @param projectId - ID do projeto
 */
export const fixNullStrings = async (
  projectId: string,
): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-nulls-string`,
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
      error.response?.data?.detail || "Erro ao corrigir nulos em strings.",
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
      `/validation/${projectId}/treatments/fix-uppercase`,
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
      error.response?.data?.detail || "Erro ao aplicar uppercase.",
    );
  }
};

/**
 * Corrige valores nulos em colunas numéricas
 * @param projectId - ID do projeto
 */
export const fixNullNumerics = async (
  projectId: string,
): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/treatments/fix-nulls-numeric`,
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
      error.response?.data?.detail || "Erro ao corrigir nulos em numéricos.",
    );
  }
};

/**
 * Analisa as colunas do projeto
 * @param projectId - ID do projeto
 */
export const getColumnsAnalysis = async (
  projectId: string,
): Promise<ColumnsAnalysisResponse> => {
  try {
    const response = await api.get<ColumnsAnalysisResponse>(
      `/validation/${projectId}/columns/analysis`,
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
      error.response?.data?.detail || "Erro ao analisar colunas.",
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
  newName: string,
): Promise<RenameColumnResponse> => {
  try {
    const response = await api.post<RenameColumnResponse>(
      `/validation/${projectId}/columns/rename`,
      { old_name: oldName, new_name: newName },
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
        error.response?.data?.detail || "Erro de validação ao renomear coluna.",
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
        error.response?.data?.detail || "Projeto não pode ser enviado.",
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
        error.response?.data?.detail || "Projeto não pode ser cancelado.",
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao cancelar projeto.",
    );
  }
};

/**
 * Busca estatísticas matemáticas de um projeto
 * @param projectId - ID do projeto
 */
export const getStatistics = async (
  projectId: string,
): Promise<StatisticsResponse> => {
  try {
    const response = await api.get<StatisticsResponse>(
      `/validation/${projectId}/statistics`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão para acessar este projeto.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao buscar estatísticas.",
    );
  }
};

/**
 * Busca diagnóstico de duplicatas de um projeto
 * @param projectId - ID do projeto
 * @param page - Página atual (padrão: 1)
 * @param pageSize - Tamanho da página (padrão: 50)
 */
export const getDuplicatesDiagnosis = async (
  projectId: string,
  page: number = 1,
  pageSize: number = 50,
): Promise<DuplicatesDiagnosisResponse> => {
  try {
    const response = await api.get<DuplicatesDiagnosisResponse>(
      `/validation/${projectId}/duplicates/diagnosis`,
      { params: { page, page_size: pageSize } },
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão para acessar este projeto.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao diagnosticar duplicatas.",
    );
  }
};

/**
 * Remove duplicatas de um projeto
 * @param projectId - ID do projeto
 */
export const removeDuplicates = async (
  projectId: string,
): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/duplicates/remove`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão para alterar este projeto.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao remover duplicatas.",
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

/**
 * Analisa o impacto do mapeamento de marcas
 * @param projectId - ID do projeto
 */
export const analyzeBrands = async (
  projectId: string,
): Promise<BrandAnalysisResponse> => {
  try {
    const response = await api.get<BrandAnalysisResponse>(
      `/validation/${projectId}/brands/analysis`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão de acesso a este projeto.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao analisar mapeamento de marcas.",
    );
  }
};

/**
 * Aplica a normalização de marcas usando o mapeamento
 * @param projectId - ID do projeto
 */
export const applyBrandNormalization = async (
  projectId: string,
): Promise<BrandApplicationResponse> => {
  try {
    const response = await api.post<BrandApplicationResponse>(
      `/validation/${projectId}/brands/apply`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão para alterar este projeto.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail ||
          "Projeto não pode ser alterado. Apenas projetos em DRAFT podem ser editados.",
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao aplicar normalização de marcas.",
    );
  }
};

/**
 * Obtém relatório consolidado de qualidade do projeto
 * @param projectId - ID do projeto
 */
export const getQualityReport = async (
  projectId: string,
): Promise<QualityReportResponse> => {
  try {
    const response = await api.get<QualityReportResponse>(
      `/validation/${projectId}/quality-report`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão de acesso a este projeto.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao gerar relatório de qualidade.",
    );
  }
};

// ==================== PUBLICAÇÃO PARA PRODUÇÃO ====================

// Interface para brand a ser criada
export interface BrandToCreate {
  brand_name: string;
  occurrences: number;
}

// Interface para preview de similaridades
export interface SimilarityPreview {
  total_rows_with_similarity: number;
  unique_similarity_groups: number;
}

// Interface para preview de publicação
export interface PublishPreviewResponse {
  project_id: string;
  total_rows: number;
  parts_new: number;
  parts_existing: number;
  brands_existing: number;
  brands_to_create: number;
  brands_to_create_list: BrandToCreate[];
  available_fields: string[];
  similarity: SimilarityPreview | null;
  production_db_status: string;
  warnings: string[];
  blockers: string[];
  can_publish: boolean;
}

// Interface para configuração de publicação
export interface PublishConfiguration {
  force_override: string[];
  concatenate: string[];
  update_if_empty: string[];
}

// Interface para request de publicação
export interface PublishRequest {
  configuration: PublishConfiguration;
  author_id?: number;
  current_owner_id?: number;
}

// Interface para resultado da publicação
export interface PublishResult {
  success: boolean;
  project_id: string;
  total_rows_processed: number;
  invalid_records_skipped: number;
  manufacturers_created: number;
  brands_created: number;
  parts_inserted: number;
  parts_updated: number;
  parts_skipped: number;
  fields_updated: number;
  activities_created: number;
  similarity_groups_created: number;
  similarity_groups_merged: number;
  similarity_parts_updated: number;
  execution_time_seconds: number;
  message: string;
  warnings: string[];
  errors: string[];
}

// Interface para resposta de publicação
export interface PublishResponse {
  result: PublishResult;
  project_status: string;
  duckdb_deleted: boolean;
}

// Interface para status do banco de produção
export interface ProductionDBStatus {
  status: string;
  host: string;
  database: string;
  postgres_version?: string;
  existing_tables: string[];
  missing_tables: string[];
  ready: boolean;
  error?: string;
}

// Interface para campos disponíveis
export interface AvailableFieldsResponse {
  system_fields: string[];
  available_fields: string[];
  field_descriptions: Record<string, string>;
}

/**
 * Obtém preview da publicação
 * @param projectId - ID do projeto
 */
export const getPublishPreview = async (
  projectId: string,
): Promise<PublishPreviewResponse> => {
  try {
    const response = await api.get<PublishPreviewResponse>(
      `/validation/${projectId}/publish/preview`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error("Apenas administradores podem publicar dados.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail ||
          "Projeto deve estar em status PENDING_REVIEW para publicação.",
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao gerar preview de publicação.",
    );
  }
};

/**
 * Obtém status do banco de produção
 */
export const getProductionDBStatus = async (): Promise<ProductionDBStatus> => {
  try {
    const response = await api.get<ProductionDBStatus>(
      `/validation/publish/db-status`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error(
        "Apenas administradores podem verificar status do banco.",
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao verificar status do banco.",
    );
  }
};

/**
 * Obtém campos disponíveis para configuração
 */
export const getAvailableFields =
  async (): Promise<AvailableFieldsResponse> => {
    try {
      const response = await api.get<AvailableFieldsResponse>(
        `/validation/publish/available-fields`,
      );
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 401) {
        throw new Error("Não autenticado. Faça login novamente.");
      }
      if (error.response?.status === 403) {
        throw new Error("Apenas administradores podem acessar configuração.");
      }
      throw new Error(
        error.response?.data?.detail || "Erro ao buscar campos disponíveis.",
      );
    }
  };

/**
 * Executa publicação dos dados para produção
 * @param projectId - ID do projeto
 * @param request - Configuração de publicação
 */
export const executePublish = async (
  projectId: string,
  request: PublishRequest,
): Promise<PublishResponse> => {
  try {
    const response = await api.post<PublishResponse>(
      `/validation/${projectId}/publish`,
      request,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error("Apenas administradores podem publicar dados.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail ||
          "Projeto deve estar em status READY_TO_PUBLISH para publicação.",
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao executar publicação.",
    );
  }
};

// ==================== FUNÇÕES DE PROGRESSO E HISTÓRICO ====================

/**
 * Busca o progresso do processamento de um projeto
 * @param projectId - ID do projeto
 */
export const getProjectProgress = async (
  projectId: string,
): Promise<ProjectProgress> => {
  try {
    const response = await api.get<ProjectProgress>(
      `/validation/${projectId}/progress`,
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
      error.response?.data?.detail || "Erro ao buscar progresso do projeto.",
    );
  }
};

/**
 * Reprocessa um projeto que falhou
 * @param projectId - ID do projeto
 */
export const retryProjectProcessing = async (
  projectId: string,
): Promise<{ message: string }> => {
  try {
    const response = await api.post<{ message: string }>(
      `/validation/${projectId}/retry`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail ||
          "Projeto deve estar em status de erro para reprocessar.",
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao reprocessar projeto.",
    );
  }
};

/**
 * Recalcula o relatório de um projeto (apenas admin)
 * @param projectId - ID do projeto
 */
export const recalculateProjectReport = async (
  projectId: string,
): Promise<{ message: string }> => {
  try {
    const response = await api.post<{ message: string }>(
      `/validation/${projectId}/recalculate`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error("Apenas administradores podem recalcular relatórios.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail ||
          "Projeto deve estar em status READY_TO_PUBLISH para recalcular.",
      );
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao recalcular relatório.",
    );
  }
};

/**
 * Busca o relatório de um projeto
 * @param projectId - ID do projeto
 */
export const getProjectReport = async (
  projectId: string,
): Promise<ProjectReport> => {
  try {
    const response = await api.get<ProjectReport>(
      `/validation/${projectId}/report`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto ou relatório não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao buscar relatório do projeto.",
    );
  }
};

/**
 * Busca o histórico de validações publicadas (apenas admin)
 * @param page - Número da página (começa em 1)
 * @param pageSize - Tamanho da página (padrão: 20)
 */
export const getValidationHistory = async (
  page: number = 1,
  pageSize: number = 20,
): Promise<ValidationHistoryResponse> => {
  try {
    const response = await api.get<ValidationHistoryResponse>(
      `/validation/history`,
      {
        params: { page, page_size: pageSize },
      },
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error("Apenas administradores podem acessar o histórico.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao buscar histórico de validações.",
    );
  }
};

/**
 * Busca diagnóstico de similaridades de um projeto
 * @param projectId - ID do projeto
 * @param page - Número da página (começa em 1)
 * @param pageSize - Tamanho da página (padrão: 20)
 */
export const getSimilaritiesDiagnosis = async (
  projectId: string,
  page: number = 1,
  pageSize: number = 20,
): Promise<SimilaritiesDiagnosisResponse> => {
  try {
    const response = await api.get<SimilaritiesDiagnosisResponse>(
      `/validation/${projectId}/similarities/diagnosis`,
      {
        params: { page, page_size: pageSize },
      },
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
      error.response?.data?.detail ||
        "Erro ao buscar diagnóstico de similaridades.",
    );
  }
};

/**
 * Aplica todas as correções na coluna similarity
 * @param projectId - ID do projeto
 */
export const fixAllSimilarities = async (
  projectId: string,
): Promise<FixResponse> => {
  try {
    const response = await api.post<FixResponse>(
      `/validation/${projectId}/similarities/fix-all`,
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
      error.response?.data?.detail || "Erro ao corrigir similaridades.",
    );
  }
};

/**
 * Busca estatísticas de similaridades de um projeto
 * @param projectId - ID do projeto
 */
export const getSimilaritiesStatistics = async (
  projectId: string,
): Promise<SimilaritiesStatisticsResponse> => {
  try {
    const response = await api.get<SimilaritiesStatisticsResponse>(
      `/validation/${projectId}/similarities/statistics`,
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
      error.response?.data?.detail ||
        "Erro ao buscar estatísticas de similaridades.",
    );
  }
};

// ==============================================================================
// FUNÇÕES PARA PROCESSAMENTO DE IMAGENS (lambda_function)
// ==============================================================================

// Interface para item de imagem no upload
export interface ImageUploadItem {
  filename: string;
  content: string; // base64
}

// Interface para request de upload de imagens
export interface ImageUploadRequest {
  environment: "test" | "production";
  images: ImageUploadItem[];
}

// Interface para response do upload de imagens
export interface ImageUploadResponse {
  task_id: string;
  project_id: string;
  total_images: number;
  status: string;
  message: string;
}

// Interface para status do processamento
export interface ImageProcessingStatusResponse {
  project_id: string;
  task_id: string | null;
  environment: string;
  status: "not_started" | "pending" | "running" | "completed" | "error";
  progress: number;
  current_step: string | null;
  total_images: number;
  processed_images: number;
  failed_images: number;
  processing_time_seconds: number | null;
  error_message: string | null;
}

// Interface para erro de processamento
export interface ImageProcessingError {
  filename: string;
  error: string;
}

// Interface para URLs de um SKU
export interface ImageUrlSet {
  high: string[];
  medium: string[];
  low: string[];
  watermark: string[];
}

// Interface para resultado do processamento
export interface ImageProcessingResultResponse {
  project_id: string;
  status: string;
  total_images: number;
  processed_images: number;
  failed_images: number;
  skus_count: number;
  results: Record<string, ImageUrlSet>;
  errors: ImageProcessingError[];
  processing_time_seconds: number | null;
}

// Interface para response da vinculação
export interface ImageLinkResponse {
  project_id: string;
  total_skus: number;
  linked_skus: number;
  not_found_skus: string[];
  message: string;
}

// Interface para preview de imagens
export interface ImagePreviewResponse {
  total_with_images: number;
  total_without_images: number;
  rows: Record<string, any>[];
  page: number;
  page_size: number;
  message?: string;
}

/**
 * Faz upload de batch de imagens para processamento
 * @param projectId - ID do projeto
 * @param images - Lista de imagens (filename + content base64)
 * @param environment - Ambiente: 'test' ou 'production'
 */
export const uploadImagesBatch = async (
  projectId: string,
  images: ImageUploadItem[],
  environment: "test" | "production" = "test",
): Promise<ImageUploadResponse> => {
  try {
    const response = await api.post<ImageUploadResponse>(
      `/validation/${projectId}/images/upload`,
      {
        environment,
        images,
      },
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 403) {
      throw new Error("Sem permissão para este projeto.");
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao fazer upload das imagens.",
    );
  }
};

/**
 * Busca o status do processamento de imagens
 * @param projectId - ID do projeto
 */
export const getImagesProcessingStatus = async (
  projectId: string,
): Promise<ImageProcessingStatusResponse> => {
  try {
    const response = await api.get<ImageProcessingStatusResponse>(
      `/validation/${projectId}/images/status`,
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
      error.response?.data?.detail ||
        "Erro ao buscar status do processamento de imagens.",
    );
  }
};

/**
 * Busca o resultado completo do processamento de imagens
 * @param projectId - ID do projeto
 */
export const getImagesProcessingResult = async (
  projectId: string,
): Promise<ImageProcessingResultResponse> => {
  try {
    const response = await api.get<ImageProcessingResultResponse>(
      `/validation/${projectId}/images/result`,
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail || "Processamento ainda não concluído.",
      );
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto ou processamento não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail ||
        "Erro ao buscar resultado do processamento.",
    );
  }
};

/**
 * Vincula imagens processadas aos registros do DuckDB
 * @param projectId - ID do projeto
 * @param imageUrls - Opcional: URLs de imagens (se não fornecido, usa última task)
 */
export const linkImagesToProject = async (
  projectId: string,
  imageUrls?: Record<string, ImageUrlSet>,
): Promise<ImageLinkResponse> => {
  try {
    const response = await api.post<ImageLinkResponse>(
      `/validation/${projectId}/images/link`,
      imageUrls ? { image_urls: imageUrls } : {},
    );
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error("Não autenticado. Faça login novamente.");
    }
    if (error.response?.status === 400) {
      throw new Error(
        error.response?.data?.detail ||
          "Processe as imagens primeiro ou forneça URLs.",
      );
    }
    if (error.response?.status === 404) {
      throw new Error("Projeto não encontrado.");
    }
    throw new Error(
      error.response?.data?.detail || "Erro ao vincular imagens ao projeto.",
    );
  }
};

/**
 * Busca preview dos registros com imagens vinculadas
 * @param projectId - ID do projeto
 * @param page - Página atual
 * @param pageSize - Tamanho da página
 */
export const getImagesPreview = async (
  projectId: string,
  page: number = 1,
  pageSize: number = 50,
): Promise<ImagePreviewResponse> => {
  try {
    const response = await api.get<ImagePreviewResponse>(
      `/validation/${projectId}/images/preview`,
      {
        params: { page, page_size: pageSize },
      },
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
      error.response?.data?.detail || "Erro ao buscar preview de imagens.",
    );
  }
};

/**
 * Converte um arquivo File para base64
 * @param file - Arquivo a ser convertido
 */
export const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      const result = reader.result as string;
      // Remove o prefixo "data:image/...;base64,"
      const base64 = result.split(",")[1];
      resolve(base64);
    };
    reader.onerror = (error) => reject(error);
  });
};

/**
 * Prepara lista de arquivos para upload
 * @param files - FileList ou array de Files
 */
export const prepareImagesForUpload = async (
  files: FileList | File[],
): Promise<ImageUploadItem[]> => {
  const imageItems: ImageUploadItem[] = [];

  for (const file of Array.from(files)) {
    // Filtrar apenas imagens
    if (!file.type.startsWith("image/")) {
      continue;
    }

    const content = await fileToBase64(file);
    imageItems.push({
      filename: file.name,
      content,
    });
  }

  return imageItems;
};
