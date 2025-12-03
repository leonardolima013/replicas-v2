import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Loader2, AlertCircle } from "lucide-react";
import { getPreview } from "../../../services/validationService";

interface PreviewData {
  rows: Record<string, any>[];
  columns: string[];
  total_rows: number;
  page: number;
  page_size: number;
}

export default function ViewStep() {
  const { projectId } = useParams<{ projectId: string }>();
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50;

  useEffect(() => {
    fetchPreview(currentPage);
  }, [currentPage, projectId]);

  const fetchPreview = async (page: number) => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getPreview(projectId, page, pageSize);
      setPreview(data);
    } catch (err: any) {
      console.error("Erro ao carregar preview:", err);
      setError(err.message || "Erro ao carregar dados. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    const totalPages = preview
      ? Math.ceil(preview.total_rows / preview.page_size)
      : 0;
    if (preview && currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  // Loading State
  if (loading) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
        <p className="text-gray-600">Carregando dados...</p>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <div className="bg-red-50 border border-red-200 rounded-card p-6 max-w-md">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900 mb-1">
                Erro ao Carregar Dados
              </h3>
              <p className="text-sm text-red-700 mb-4">{error}</p>
              <button
                onClick={() => fetchPreview(currentPage)}
                className="btn-primary text-sm"
              >
                Tentar Novamente
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Empty State
  if (!preview || preview.rows.length === 0) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-gray-600">
          Nenhum dado disponível para visualização.
        </p>
      </div>
    );
  }

  const totalPages = Math.ceil(preview.total_rows / preview.page_size);

  return (
    <div className="p-6">
      {/* Header com Info */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">
            Visualização dos Dados
          </h2>
          <p className="text-sm text-gray-600">
            Total: {preview.total_rows.toLocaleString("pt-BR")} linhas |
            Mostrando {preview.rows.length} linhas (página {preview.page} de{" "}
            {totalPages})
          </p>
        </div>
      </div>

      {/* Tabela com Scroll Horizontal */}
      <div className="border border-gray-200 rounded-card overflow-hidden mb-6">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {preview.columns.map((column) => (
                  <th
                    key={column}
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider whitespace-nowrap"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {preview.rows.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className="hover:bg-gray-50 transition-colors"
                >
                  {preview.columns.map((column) => (
                    <td
                      key={`${rowIndex}-${column}`}
                      className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap"
                    >
                      {row[column] !== null && row[column] !== undefined ? (
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
      </div>

      {/* Paginação */}
      <div className="flex items-center justify-between">
        <button
          onClick={handlePreviousPage}
          disabled={currentPage === 1}
          className="btn-secondary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
          Anterior
        </button>

        <span className="text-sm text-gray-600">
          Página {currentPage} de {totalPages}
        </span>

        <button
          onClick={handleNextPage}
          disabled={currentPage === totalPages}
          className="btn-secondary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Próximo
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
