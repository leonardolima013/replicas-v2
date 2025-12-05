import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  CheckCircle,
  AlertTriangle,
  Trash2,
  Info,
  Loader2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import * as validationService from "../../../services/validationService";

interface DuplicatesDiagnosisProps {
  readOnly?: boolean;
}

export default function DuplicatesStep({ readOnly = false }: DuplicatesDiagnosisProps) {
  const { projectId } = useParams<{ projectId: string }>();
  const [diagnosis, setDiagnosis] = useState<validationService.DuplicatesDiagnosisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);

  useEffect(() => {
    if (projectId) {
      loadDiagnosis();
    }
  }, [projectId, currentPage]);

  const loadDiagnosis = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await validationService.getDuplicatesDiagnosis(projectId, currentPage, pageSize);
      setDiagnosis(data);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar diagnóstico de duplicatas");
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveDuplicates = async () => {
    if (!projectId || readOnly) return;

    const confirmed = window.confirm(
      `Tem certeza que deseja remover ${diagnosis?.total_duplicates} registos duplicados?\n\nApenas a primeira ocorrência de cada combinação (search_ref + brand) será mantida.`
    );

    if (!confirmed) return;

    try {
      setRemoving(true);
      setError(null);
      setSuccessMessage(null);

      const result = await validationService.removeDuplicates(projectId);
      
      setSuccessMessage(
        `✅ Limpeza concluída! ${result.rows_affected} registos duplicados foram removidos.`
      );

      // Recarregar diagnóstico após remoção
      setTimeout(() => {
        setCurrentPage(1); // Voltar para a primeira página
        loadDiagnosis();
        setSuccessMessage(null);
      }, 3000);
    } catch (err: any) {
      setError(err.message || "Erro ao remover duplicatas");
    } finally {
      setRemoving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">Analisando duplicatas...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-900/20 border border-rose-500 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-rose-500" />
          <p className="text-rose-500 font-medium">{error}</p>
        </div>
        <button
          onClick={loadDiagnosis}
          className="mt-4 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Tentar Novamente
        </button>
      </div>
    );
  }

  const hasDuplicates = diagnosis && diagnosis.total_duplicates > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">
          Análise de Duplicatas
        </h2>
        <p className="text-zinc-500 mt-1">
          Identificação e remoção de registos duplicados baseado em search_ref + brand
        </p>
      </div>

      {/* Alerta de Padronização */}
      <div className="bg-blue-900/20 border border-blue-500 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-blue-400 font-medium text-sm">
              💡 Dica: Padronize antes de remover duplicatas
            </p>
            <p className="text-zinc-400 text-sm mt-1">
              Recomendamos executar a <strong>Padronização de Texto (Uppercase/Trim)</strong> na aba 
              "Tratamento de Dados" antes de remover duplicatas. Isso garante que variações de escrita 
              como "FILTRO DE OLEO" e "Filtro de oleo" sejam detectadas como duplicatas.
            </p>
          </div>
        </div>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="bg-emerald-900/20 border border-emerald-500 rounded-lg p-4 animate-pulse">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-500" />
            <p className="text-emerald-500 font-medium">{successMessage}</p>
          </div>
        </div>
      )}

      {/* Card de Resumo (Hero) */}
      {!hasDuplicates ? (
        <div className="bg-emerald-900/20 border border-emerald-500 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <CheckCircle className="w-12 h-12 text-emerald-500 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-xl font-bold text-emerald-400">
                Nenhuma Duplicata Encontrada
              </h3>
              <p className="text-zinc-400 mt-2">
                A base está limpa! Não foram encontrados registos com a mesma combinação 
                de search_ref e brand.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-amber-900/20 border border-amber-500 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <AlertTriangle className="w-12 h-12 text-amber-500 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-xl font-bold text-amber-400">
                {diagnosis.total_duplicates} Registos Duplicados Encontrados
              </h3>
              <p className="text-zinc-400 mt-2">
                Estes itens compartilham o mesmo <strong>search_ref</strong> e <strong>brand</strong>. 
                Ao limpar, manteremos apenas a primeira linha encontrada no arquivo 
                e removeremos as {diagnosis.total_duplicates} ocorrências duplicadas.
              </p>
              <p className="text-zinc-500 text-sm mt-2">
                Colunas usadas: {diagnosis.columns_used.join(", ")}
              </p>

              {!readOnly && (
                <button
                  onClick={handleRemoveDuplicates}
                  disabled={removing}
                  className="mt-4 px-6 py-3 bg-rose-600 hover:bg-rose-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg flex items-center gap-2 transition-colors"
                >
                  {removing ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Removendo...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-5 h-5" />
                      Remover Duplicatas
                    </>
                  )}
                </button>
              )}

              {readOnly && (
                <div className="mt-4 bg-zinc-800 border border-zinc-700 rounded-lg p-3">
                  <p className="text-zinc-400 text-sm flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    Projeto bloqueado para edição
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tabela de Evidências */}
      {hasDuplicates && diagnosis.preview.length > 0 && (
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <h3 className="text-lg font-semibold text-zinc-100">
              Registos Duplicados
            </h3>
            <p className="text-zinc-500 text-sm mt-1">
              Página {diagnosis.page} de {diagnosis.total_pages} ({diagnosis.total_duplicates} total)
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-800">
                <tr>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Search Ref
                  </th>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Brand
                  </th>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Name
                  </th>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    NCM
                  </th>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Barcode
                  </th>
                </tr>
              </thead>
              <tbody>
                {diagnosis.preview.map((row, index) => (
                  <tr
                    key={index}
                    className="border-b border-zinc-800 hover:bg-zinc-800/50 transition-colors"
                  >
                    <td className="py-3 px-4 text-zinc-100 font-mono text-xs">
                      {row.search_ref || "-"}
                    </td>
                    <td className="py-3 px-4 text-zinc-300">
                      {row.brand || "-"}
                    </td>
                    <td className="py-3 px-4 text-zinc-300 max-w-xs truncate">
                      {row.name || "-"}
                    </td>
                    <td className="py-3 px-4 text-zinc-400 font-mono text-xs">
                      {row.ncm || "-"}
                    </td>
                    <td className="py-3 px-4 text-zinc-400 font-mono text-xs">
                      {row.barcode || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Controles de Paginação */}
          {diagnosis.total_pages > 1 && (
            <div className="p-4 bg-zinc-800/50 border-t border-zinc-800">
              <div className="flex items-center justify-between">
                <p className="text-zinc-500 text-sm">
                  Exibindo {((diagnosis.page - 1) * diagnosis.page_size) + 1} - {Math.min(diagnosis.page * diagnosis.page_size, diagnosis.total_duplicates)} de {diagnosis.total_duplicates} registos
                </p>
                
                <div className="flex items-center gap-2">
                  {/* Primeira Página */}
                  <button
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                    className="p-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:cursor-not-allowed disabled:text-zinc-600 text-zinc-300 rounded-lg transition-colors"
                    title="Primeira página"
                  >
                    <ChevronsLeft className="w-4 h-4" />
                  </button>

                  {/* Página Anterior */}
                  <button
                    onClick={() => setCurrentPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="p-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:cursor-not-allowed disabled:text-zinc-600 text-zinc-300 rounded-lg transition-colors"
                    title="Página anterior"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>

                  {/* Números de Página */}
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, diagnosis.total_pages) }, (_, i) => {
                      let pageNum;
                      if (diagnosis.total_pages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= diagnosis.total_pages - 2) {
                        pageNum = diagnosis.total_pages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }

                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                            currentPage === pageNum
                              ? "bg-emerald-600 text-white"
                              : "bg-zinc-700 hover:bg-zinc-600 text-zinc-300"
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  {/* Próxima Página */}
                  <button
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={currentPage === diagnosis.total_pages}
                    className="p-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:cursor-not-allowed disabled:text-zinc-600 text-zinc-300 rounded-lg transition-colors"
                    title="Próxima página"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>

                  {/* Última Página */}
                  <button
                    onClick={() => setCurrentPage(diagnosis.total_pages)}
                    disabled={currentPage === diagnosis.total_pages}
                    className="p-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:cursor-not-allowed disabled:text-zinc-600 text-zinc-300 rounded-lg transition-colors"
                    title="Última página"
                  >
                    <ChevronsRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Estatísticas Adicionais */}
      {diagnosis && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <p className="text-zinc-500 text-sm">Total de Duplicatas</p>
            <p className="text-2xl font-bold text-zinc-100 mt-1">
              {diagnosis.total_duplicates}
            </p>
          </div>
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <p className="text-zinc-500 text-sm">Colunas Analisadas</p>
            <p className="text-2xl font-bold text-zinc-100 mt-1">
              {diagnosis.columns_used.length}
            </p>
          </div>
          <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <p className="text-zinc-500 text-sm">Preview Disponível</p>
            <p className="text-2xl font-bold text-zinc-100 mt-1">
              {diagnosis.preview.length}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
