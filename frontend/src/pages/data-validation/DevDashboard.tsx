import { Plus, ArrowRight, Loader2, AlertCircle, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import * as validationService from "../../services/validationService";
import { getCurrentUser } from "../../services/authService";

export default function DevDashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<validationService.Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const currentUser = getCurrentUser();

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await validationService.getProjects();
      setProjects(response.projects);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar projetos");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (projectId: string, fileName: string) => {
    if (
      !window.confirm(`Tem certeza que deseja excluir o projeto "${fileName}"?`)
    ) {
      return;
    }

    try {
      await validationService.deleteProject(projectId);
      // Remover projeto da lista localmente
      setProjects((prev) => prev.filter((p) => p.id !== projectId));
    } catch (err: any) {
      alert(err.message || "Erro ao excluir projeto");
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === "DRAFT") {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          Em Andamento
        </span>
      );
    }
    if (status === "PENDING") {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          Aguardando Aprovação
        </span>
      );
    }
    if (status === "DONE") {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
          Publicado
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
        {status}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  return (
    <div className="p-8">
      {/* Botão Novo Projeto */}
      <div className="mb-6 flex justify-end">
        <Link
          to="/validation/new"
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Novo Projeto
        </Link>
      </div>
      {/* Loading State */}
      {loading && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft p-8 border border-gray-200 dark:border-gray-800 text-center py-16">
          <Loader2 className="w-12 h-12 text-primary-500 dark:text-primary-400 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-300">
            Carregando projetos...
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft p-8 border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
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
                onClick={fetchProjects}
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
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft p-8 border border-gray-200 dark:border-gray-800 text-center py-16">
          <div className="bg-gray-100 dark:bg-gray-800 rounded-full p-8 w-32 h-32 mx-auto mb-6 flex items-center justify-center">
            <Plus className="w-16 h-16 text-gray-300 dark:text-gray-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
            Nenhum projeto encontrado
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
            Comece criando um novo projeto de validação de dados
          </p>
          <Link
            to="/validation/new"
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Novo Projeto
          </Link>
        </div>
      )}

      {/* Projects Table */}
      {!loading && !error && projects.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-200 dark:border-gray-800 p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Nome do Arquivo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Data de Upload
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
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
                      <div className="text-sm text-gray-600 dark:text-gray-300">
                        {formatDate(project.created_at)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(project.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => navigate(`/validation/${project.id}`)}
                          className="btn-secondary text-sm inline-flex items-center gap-2"
                        >
                          Continuar Trabalho
                          <ArrowRight className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() =>
                            handleDelete(project.id, project.original_filename)
                          }
                          className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-button transition-colors"
                          title="Excluir projeto"
                        >
                          <Trash2 className="w-4 h-4" />
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
    </div>
  );
}
