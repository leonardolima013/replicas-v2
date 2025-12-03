import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FileCheck,
  ArrowRight,
  Loader2,
  AlertCircle,
  ArrowLeft,
  Download,
} from "lucide-react";
import * as validationService from "../../services/validationService";

export default function AdminValidationDashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<validationService.Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPendingProjects();
  }, []);

  const fetchPendingProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await validationService.getProjects();
      // Filtrar apenas projetos com status PENDING
      const pendingProjects = response.projects.filter(
        (p) => p.status === "PENDING"
      );
      setProjects(pendingProjects);
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
        }
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
      alert(err.message || "Erro ao baixar CSV");
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-soft">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <Link
              to="/services"
              className="btn-secondary flex items-center gap-2"
            >
              <ArrowLeft className="w-5 h-5" />
              Voltar
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-wide flex items-center gap-3">
                <FileCheck className="w-8 h-8 text-yellow-600" />
                Validação - Aprovação de Projetos
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Projetos aguardando revisão e aprovação
              </p>
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
            <p className="text-gray-600">Carregando projetos...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="card bg-red-50 border border-red-200">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-red-700 font-medium">
                  Erro ao carregar projetos
                </p>
                <p className="text-sm text-red-600 mt-1">{error}</p>
                <button
                  onClick={fetchPendingProjects}
                  className="btn-secondary mt-4 text-sm"
                >
                  Tentar Novamente
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && projects.length === 0 && (
          <div className="card text-center py-16">
            <div className="bg-gray-100 rounded-full p-8 w-32 h-32 mx-auto mb-6 flex items-center justify-center">
              <FileCheck className="w-16 h-16 text-gray-300" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">
              Nenhum projeto pendente
            </h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              Não há projetos aguardando aprovação no momento
            </p>
          </div>
        )}

        {/* Projects Table */}
        {!loading && !error && projects.length > 0 && (
          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Nome do Arquivo
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Proprietário
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Data de Envio
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Ações
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {projects.map((project) => (
                    <tr
                      key={project.id}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {project.original_filename}
                        </div>
                        {project.total_rows && (
                          <div className="text-xs text-gray-500">
                            {project.total_rows.toLocaleString()} linhas
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-600">
                          {project.owner_username || "N/A"}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-600">
                          {formatDate(project.created_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() =>
                              handleDownloadCSV(
                                project.id,
                                project.original_filename
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
      </main>
    </div>
  );
}
