import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  Download,
} from "lucide-react";
import * as validationService from "../../services/validationService";

export default function AdminValidationReview() {
  const { projectId } = useParams<{ projectId: string }>();

  const [project, setProject] = useState<validationService.Project | null>(
    null
  );
  const [previewData, setPreviewData] =
    useState<validationService.PreviewResponse | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

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

  const handleApprove = async () => {
    if (!projectId) return;

    if (
      !confirm(
        "Tem certeza que deseja APROVAR este projeto? O status será alterado para PUBLICADO."
      )
    ) {
      return;
    }

    setActionLoading(true);
    try {
      // TODO: Implementar endpoint de aprovação no backend
      // Por enquanto, apenas exibir mensagem
      alert(
        "Funcionalidade de aprovação será implementada no backend. Status: PENDING → DONE"
      );
      // await validationService.approveProject(projectId);
      // navigate("/admin/validation");
    } catch (err: any) {
      alert(err.message || "Erro ao aprovar projeto");
    } finally {
      setActionLoading(false);
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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-soft">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <Link
              to="/admin/validation"
              className="btn-secondary flex items-center gap-2"
            >
              <ArrowLeft className="w-5 h-5" />
              Voltar
            </Link>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 tracking-wide">
                Revisão de Projeto
              </h1>
              {project && (
                <p className="text-sm text-gray-500 mt-1">
                  {project.original_filename} • Enviado por{" "}
                  {project.owner_username} em {formatDate(project.created_at)}
                </p>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Loading State */}
        {loading && (
          <div className="card text-center py-16">
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Carregando dados do projeto...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="card bg-red-50 border border-red-200">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-red-700 font-medium">
                  Erro ao carregar projeto
                </p>
                <p className="text-sm text-red-600 mt-1">{error}</p>
                <button
                  onClick={fetchProjectData}
                  className="btn-secondary mt-4 text-sm"
                >
                  Tentar Novamente
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Preview Content */}
        {!loading && !error && project && previewData && (
          <>
            {/* Info Card */}
            <div className="card mb-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <p className="text-sm text-gray-500 mb-1">Total de Linhas</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {previewData.total_rows.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">Total de Colunas</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {previewData.columns.length}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">Status</p>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
                    Aguardando Aprovação
                  </span>
                </div>
              </div>
            </div>

            {/* Data Preview */}
            <div className="card p-0 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <h2 className="text-lg font-semibold text-gray-900">
                  Visualização dos Dados (Somente Leitura)
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Mostrando {(currentPage - 1) * pageSize + 1} -{" "}
                  {Math.min(currentPage * pageSize, previewData.total_rows)} de{" "}
                  {previewData.total_rows.toLocaleString()} linhas
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-100">
                    <tr>
                      {previewData.columns.map((column) => (
                        <th
                          key={column}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider whitespace-nowrap"
                        >
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {previewData.rows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        {previewData.columns.map((column) => (
                          <td
                            key={column}
                            className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap"
                          >
                            {row[column] !== null &&
                            row[column] !== undefined ? (
                              String(row[column])
                            ) : (
                              <span className="text-gray-400 italic">null</span>
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
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Anterior
                  </button>
                  <span className="text-sm text-gray-600">
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
            <div className="card mt-6">
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
                    className="btn-secondary bg-red-50 text-red-700 border-red-200 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {actionLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <XCircle className="w-5 h-5" />
                    )}
                    Rejeitar
                  </button>

                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="btn-primary bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {actionLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <CheckCircle className="w-5 h-5" />
                    )}
                    Aprovar e Publicar no S3
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
