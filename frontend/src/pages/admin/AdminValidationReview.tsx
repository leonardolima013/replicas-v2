import { useState, useEffect } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  Download,
  FileText,
  BarChart3,
  Upload,
} from "lucide-react";
import * as validationService from "../../services/validationService";
import QualityReportTab from "./components/QualityReportTab";
import PublishConfigTab from "./components/PublishConfigTab";

export default function AdminValidationReview() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<validationService.Project | null>(
    null
  );
  const [previewData, setPreviewData] =
    useState<validationService.PreviewResponse | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"preview" | "quality" | "publish">(
    "preview"
  );

  const pageSize = 50;

  useEffect(() => {
    if (projectId) {
      fetchProjectData();
    }
  }, [projectId, currentPage]);

  const fetchProjectData = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);

      // Buscar informações do projeto e preview
      const [projectsResponse, preview] = await Promise.all([
        validationService.getProjects(),
        validationService.getPreview(projectId, currentPage, pageSize),
      ]);

      const currentProject = projectsResponse.projects.find(
        (p) => p.id === projectId
      );

      if (!currentProject) {
        throw new Error("Projeto não encontrado");
      }

      if (currentProject.status !== "PENDING") {
        throw new Error("Este projeto não está pendente de aprovação");
      }

      setProject(currentProject);
      setPreviewData(preview);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar dados do projeto");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCSV = async () => {
    if (!projectId || !project) return;

    try {
      const response = await fetch(
        `http://localhost:8000/validation/${projectId}/download`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Erro ao baixar arquivo");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project.original_filename.replace(
        ".csv",
        ""
      )}_processed.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(err.message || "Erro ao baixar CSV");
    }
  };

  const handleReject = async () => {
    if (!projectId) return;

    if (
      !confirm(
        "Tem certeza que deseja REJEITAR este projeto? Esta ação não pode ser desfeita."
      )
    ) {
      return;
    }

    setActionLoading(true);
    try {
      // TODO: Implementar endpoint de rejeição no backend
      // Por enquanto, apenas exibir mensagem
      alert(
        "Funcionalidade de rejeição será implementada no backend. Projeto será deletado ou marcado como REJECTED."
      );
      // await validationService.rejectProject(projectId);
      // navigate("/admin/validation");
    } catch (err: any) {
      alert(err.message || "Erro ao rejeitar projeto");
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const totalPages = previewData
    ? Math.ceil(previewData.total_rows / pageSize)
    : 0;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-4 mb-4">
          <Link
            to="/admin/validation"
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-5 h-5" />
            Voltar
          </Link>
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white tracking-wide">
            Revisão de Projeto
          </h1>
          {project && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {project.original_filename} • Enviado por {project.owner_username}{" "}
              em {formatDate(project.created_at)}
            </p>
          )}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 text-center py-16">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">
            Carregando dados do projeto...
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 p-6">
          <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 dark:border-red-600 p-4 rounded-card">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-red-700 dark:text-red-300 font-medium">
                  Erro ao carregar projeto
                </p>
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                  {error}
                </p>
                <button
                  onClick={fetchProjectData}
                  className="btn-secondary mt-4 text-sm"
                >
                  Tentar Novamente
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preview Content */}
      {!loading && !error && project && previewData && (
        <>
          {/* Tabs Navigation */}
          <div className="bg-white dark:bg-gray-900 rounded-t-card shadow-soft border border-gray-100 dark:border-gray-800 border-b-0">
            <div className="flex border-b border-gray-200 dark:border-gray-800">
              <button
                onClick={() => setActiveTab("preview")}
                className={`
                  flex items-center gap-2 px-6 py-4 font-medium text-sm transition-all
                  border-b-2 ${
                    activeTab === "preview"
                      ? "border-sky-600 text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-900/20"
                      : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                  }
                `}
              >
                <FileText className="w-5 h-5" />
                Visualização dos Dados
              </button>
              <button
                onClick={() => setActiveTab("quality")}
                className={`
                  flex items-center gap-2 px-6 py-4 font-medium text-sm transition-all
                  border-b-2 ${
                    activeTab === "quality"
                      ? "border-sky-600 text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-900/20"
                      : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                  }
                `}
              >
                <BarChart3 className="w-5 h-5" />
                Relatório de Qualidade
              </button>
              <button
                onClick={() => setActiveTab("publish")}
                className={`
                  flex items-center gap-2 px-6 py-4 font-medium text-sm transition-all
                  border-b-2 ${
                    activeTab === "publish"
                      ? "border-green-600 text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20"
                      : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                  }
                `}
              >
                <Upload className="w-5 h-5" />
                Publicar na Hubbi
              </button>
            </div>
          </div>

          {/* Tab Content: Preview */}
          {activeTab === "preview" && (
            <>
              {/* Info Card */}
              <div className="bg-white dark:bg-gray-900 shadow-soft border border-gray-100 dark:border-gray-800 border-t-0 p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                      Total de Linhas
                    </p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {previewData.total_rows.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                      Total de Colunas
                    </p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {previewData.columns.length}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                      Status
                    </p>
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300">
                      Aguardando Aprovação
                    </span>
                  </div>
                </div>
              </div>

              {/* Data Preview */}
              <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Visualização dos Dados (Somente Leitura)
                  </h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Mostrando {(currentPage - 1) * pageSize + 1} -{" "}
                    {Math.min(currentPage * pageSize, previewData.total_rows)}{" "}
                    de {previewData.total_rows.toLocaleString()} linhas
                  </p>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
                    <thead className="bg-gray-100 dark:bg-gray-800">
                      <tr>
                        {previewData.columns.map((column) => (
                          <th
                            key={column}
                            className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider whitespace-nowrap"
                          >
                            {column}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                      {previewData.rows.map((row, idx) => (
                        <tr
                          key={idx}
                          className="hover:bg-gray-50 dark:hover:bg-gray-800"
                        >
                          {previewData.columns.map((column) => (
                            <td
                              key={column}
                              className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100 whitespace-nowrap"
                            >
                              {row[column] !== null &&
                              row[column] !== undefined ? (
                                String(row[column])
                              ) : (
                                <span className="text-gray-400 dark:text-gray-600 italic">
                                  null
                                </span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 flex items-center justify-between">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Anterior
                    </button>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Página {currentPage} de {totalPages}
                    </span>
                    <button
                      onClick={() =>
                        setCurrentPage((p) => Math.min(totalPages, p + 1))
                      }
                      disabled={currentPage === totalPages}
                      className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Próxima
                    </button>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="bg-white dark:bg-gray-900 rounded-b-card shadow-soft border border-gray-100 dark:border-gray-800 border-t p-6 mt-6">
                <div className="flex items-center justify-between gap-4">
                  <button
                    onClick={handleDownloadCSV}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Baixar CSV
                  </button>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleReject}
                      disabled={actionLoading}
                      className="btn-secondary bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {actionLoading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <XCircle className="w-5 h-5" />
                      )}
                      Rejeitar
                    </button>

                    <button
                      onClick={() => setActiveTab("publish")}
                      className="btn-primary bg-green-600 hover:bg-green-700 flex items-center gap-2"
                    >
                      <Upload className="w-5 h-5" />
                      Ir para Publicação
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Tab Content: Quality Report */}
          {activeTab === "quality" && projectId && (
            <>
              <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 border-t-0">
                <QualityReportTab projectId={projectId} />
              </div>

              {/* Action Buttons na aba de qualidade */}
              <div className="bg-white dark:bg-gray-900 rounded-b-card shadow-soft border border-gray-100 dark:border-gray-800 p-6 mt-6">
                <div className="flex items-center justify-between gap-4">
                  <button
                    onClick={handleDownloadCSV}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Baixar CSV
                  </button>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleReject}
                      disabled={actionLoading}
                      className="btn-secondary bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {actionLoading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <XCircle className="w-5 h-5" />
                      )}
                      Rejeitar
                    </button>

                    <button
                      onClick={() => setActiveTab("publish")}
                      className="btn-primary bg-green-600 hover:bg-green-700 flex items-center gap-2"
                    >
                      <Upload className="w-5 h-5" />
                      Ir para Publicação
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Tab Content: Publish */}
          {activeTab === "publish" && projectId && (
            <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 border-t-0">
              <PublishConfigTab
                projectId={projectId}
                onPublishSuccess={() => {
                  // Redirecionar para lista após sucesso
                  setTimeout(() => {
                    navigate("/admin/validation");
                  }, 3000);
                }}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
