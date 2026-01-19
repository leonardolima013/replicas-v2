import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FileCheck,
  ArrowRight,
  Loader2,
  AlertCircle,
  ArrowLeft,
  Download,
  Clock,
  CheckCircle,
  XCircle,
} from "lucide-react";
import * as validationService from "../../services/validationService";
import Modal from "../../components/Modal";
import { useModal } from "../../hooks/useModal";

export default function AdminValidationDashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<validationService.Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { modalState, closeModal, showError } = useModal();

  useEffect(() => {
    fetchPendingProjects();
  }, []);

  const fetchPendingProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await validationService.getProjects();
      // Filtrar projetos com status que requerem ação do admin
      const actionableProjects = response.projects.filter(
        (p) =>
          p.status === "PENDING_REVIEW" ||
          p.status === "PROCESSING_REPORT" ||
          p.status === "READY_TO_PUBLISH" ||
          p.status === "PROCESSING_ERROR",
      );
      setProjects(actionableProjects);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar projetos");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCSV = async (projectId: string, filename: string) => {
    try {
      // Fazer download do CSV
      const response = await fetch(
        `http://localhost:8000/validation/${projectId}/download`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        },
      );

      if (!response.ok) {
        throw new Error("Erro ao baixar arquivo");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${filename.replace(".csv", "")}_processed.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      showError(err.message || "Erro ao baixar CSV");
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

  const getStatusBadge = (status: string) => {
    const statusMap: Record<
      string,
      { label: string; className: string; icon: React.ReactNode }
    > = {
      PENDING_REVIEW: {
        label: "Aguardando",
        className:
          "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300",
        icon: <Clock className="w-3 h-3" />,
      },
      PROCESSING_REPORT: {
        label: "Processando",
        className:
          "bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300",
        icon: <Loader2 className="w-3 h-3 animate-spin" />,
      },
      READY_TO_PUBLISH: {
        label: "Pronto",
        className:
          "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300",
        icon: <CheckCircle className="w-3 h-3" />,
      },
      PROCESSING_ERROR: {
        label: "Erro",
        className:
          "bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300",
        icon: <XCircle className="w-3 h-3" />,
      },
    };

    const statusInfo = statusMap[status] || {
      label: status,
      className:
        "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300",
      icon: null,
    };

    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${statusInfo.className}`}
      >
        {statusInfo.icon}
        {statusInfo.label}
      </span>
    );
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-4 mb-4">
          <Link
            to="/services"
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-5 h-5" />
            Voltar
          </Link>
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white tracking-wide flex items-center gap-3">
            <FileCheck className="w-8 h-8 text-yellow-600 dark:text-yellow-500" />
            Validação - Aprovação de Projetos
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Projetos aguardando revisão e aprovação
          </p>
        </div>
      </div>
      {/* Loading State */}
      {loading && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 text-center py-16">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">
            Carregando projetos...
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
                  Erro ao carregar projetos
                </p>
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                  {error}
                </p>
                <button
                  onClick={fetchPendingProjects}
                  className="btn-secondary mt-4 text-sm"
                >
                  Tentar Novamente
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && projects.length === 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 text-center py-16">
          <div className="bg-gray-100 dark:bg-gray-800 rounded-full p-8 w-32 h-32 mx-auto mb-6 flex items-center justify-center">
            <FileCheck className="w-16 h-16 text-gray-300 dark:text-gray-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
            Nenhum projeto pendente
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
            Não há projetos aguardando aprovação no momento
          </p>
        </div>
      )}

      {/* Projects Table */}
      {!loading && !error && projects.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Nome do Arquivo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Proprietário
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Data de Envio
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                {projects.map((project) => (
                  <tr
                    key={project.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {project.original_filename}
                      </div>
                      {project.total_rows && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {project.total_rows.toLocaleString()} linhas
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(project.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-600 dark:text-gray-300">
                        {project.owner_username || "N/A"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-600 dark:text-gray-300">
                        {formatDate(project.created_at)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() =>
                            handleDownloadCSV(
                              project.id,
                              project.original_filename,
                            )
                          }
                          className="btn-secondary text-sm inline-flex items-center gap-2"
                        >
                          <Download className="w-4 h-4" />
                          Baixar CSV
                        </button>
                        <button
                          onClick={() =>
                            navigate(`/admin/validation/${project.id}`)
                          }
                          className="btn-primary text-sm inline-flex items-center gap-2"
                        >
                          Revisar
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal */}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        onConfirm={modalState.onConfirm}
        title={modalState.title}
        message={modalState.message}
        type={modalState.type}
        confirmText={modalState.confirmText}
        cancelText={modalState.cancelText}
      />
    </div>
  );
}
