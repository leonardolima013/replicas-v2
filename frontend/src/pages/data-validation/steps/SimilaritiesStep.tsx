import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  CheckCircle,
  AlertTriangle,
  Info,
  Loader2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Wand2,
  XCircle,
  BarChart3,
} from "lucide-react";
import * as validationService from "../../../services/validationService";
import Modal from "../../../components/Modal";
import { useModal } from "../../../hooks/useModal";

interface SimilaritiesStepProps {
  readOnly?: boolean;
}

export default function SimilaritiesStep({
  readOnly = false,
}: SimilaritiesStepProps) {
  const { projectId } = useParams<{ projectId: string }>();
  const [diagnosis, setDiagnosis] =
    useState<validationService.SimilaritiesDiagnosisResponse | null>(null);
  const [statistics, setStatistics] =
    useState<validationService.SimilaritiesStatisticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [fixing, setFixing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [showStatistics, setShowStatistics] = useState(false);
  const { modalState, closeModal, showConfirm } = useModal();

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
      const data = await validationService.getSimilaritiesDiagnosis(
        projectId,
        currentPage,
        pageSize,
      );
      setDiagnosis(data);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar diagnóstico de similaridades");
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    if (!projectId) return;

    try {
      const data = await validationService.getSimilaritiesStatistics(projectId);
      setStatistics(data);
      setShowStatistics(true);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar estatísticas");
    }
  };

  const handleFixAll = async () => {
    if (!projectId || readOnly) return;

    showConfirm(
      `Tem certeza que deseja aplicar todas as correções?\n\n` +
        `Isso irá:\n` +
        `- Normalizar search_ref (remover espaços e caracteres especiais)\n` +
        `- Converter marcas para MAIÚSCULAS\n` +
        `- Aplicar mapeamento de marcas\n` +
        `- Validar referências existentes no projeto`,
      async () => {
        try {
          setFixing(true);
          setError(null);
          setSuccessMessage(null);

          const result = await validationService.fixAllSimilarities(projectId);

          setSuccessMessage(
            `✅ Correções aplicadas! ${result.rows_affected} linhas foram processadas.`,
          );

          // Recarregar diagnóstico após correção
          setTimeout(() => {
            setCurrentPage(1);
            loadDiagnosis();
            setSuccessMessage(null);
          }, 3000);
        } catch (err: any) {
          setError(err.message || "Erro ao aplicar correções");
        } finally {
          setFixing(false);
        }
      },
      "Aplicar Correções",
      "Aplicar",
      "Cancelar",
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">Analisando similaridades...</p>
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

  // Se coluna não existe
  if (diagnosis && !diagnosis.column_exists) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">
            Validação de Similaridades
          </h2>
          <p className="text-zinc-500 mt-1">
            Análise e validação da coluna similarity
          </p>
        </div>

        <div className="bg-amber-900/20 border border-amber-500 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <AlertTriangle className="w-12 h-12 text-amber-500 flex-shrink-0" />
            <div>
              <h3 className="text-xl font-bold text-amber-400">
                Coluna "similarity" não encontrada
              </h3>
              <p className="text-zinc-400 mt-2">
                Seu projeto não possui a coluna <strong>similarity</strong>.
                Esta coluna é opcional, mas quando presente, deve estar
                corretamente formatada.
              </p>
            </div>
          </div>
        </div>

        {/* Card de Explicação */}
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
          <div className="flex items-start gap-3">
            <Info className="w-6 h-6 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-zinc-100 mb-3">
                Como deve estar formatada a coluna similarity
              </h3>

              <div className="space-y-3 text-sm text-zinc-300">
                <p>
                  A coluna deve conter uma{" "}
                  <strong className="text-emerald-400">
                    lista de dicionários
                  </strong>{" "}
                  em formato JSON, onde cada dicionário representa uma
                  similaridade:
                </p>

                <div className="bg-zinc-950 border border-zinc-700 rounded-lg p-4 font-mono text-xs">
                  <code className="text-emerald-400">
                    [{"{"}
                    <span className="text-blue-400">"search_ref"</span>:
                    <span className="text-yellow-400">"ABC123"</span>,{" "}
                    <span className="text-blue-400">"brand"</span>:
                    <span className="text-yellow-400">"RENAULT"</span>
                    {"}"}]
                  </code>
                </div>

                <div className="space-y-2 mt-4">
                  <p className="font-semibold text-zinc-200">
                    Regras de formatação:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-zinc-400">
                    <li>
                      <strong className="text-zinc-300">search_ref</strong>: Não
                      pode conter espaços nem caracteres especiais (apenas
                      letras, números e underscore)
                    </li>
                    <li>
                      <strong className="text-zinc-300">brand</strong>: Deve
                      estar em MAIÚSCULAS
                    </li>
                    <li>
                      Quando não houver similaridades, usar{" "}
                      <strong className="text-zinc-300">lista vazia []</strong>{" "}
                      (não NULL)
                    </li>
                    <li>
                      Múltiplas similaridades:{" "}
                      <code className="text-xs bg-zinc-800 px-1 py-0.5 rounded">
                        [{"{"}...{"}"}, {"{"}...{"}"}, {"{"}...{"}"}]
                      </code>
                    </li>
                  </ul>
                </div>

                <div className="bg-emerald-900/20 border border-emerald-700 rounded-lg p-3 mt-4">
                  <p className="text-emerald-400 text-xs font-semibold mb-1">
                    ✅ Exemplo válido
                  </p>
                  <code className="text-xs font-mono text-emerald-300">
                    [{"{"}
                    <span className="text-blue-300">"search_ref"</span>:
                    <span className="text-yellow-300">"ABC123"</span>,{" "}
                    <span className="text-blue-300">"brand"</span>:
                    <span className="text-yellow-300">"FIAT"</span>
                    {"}"}, {"{"}
                    <span className="text-blue-300">"search_ref"</span>:
                    <span className="text-yellow-300">"DEF456"</span>,{" "}
                    <span className="text-blue-300">"brand"</span>:
                    <span className="text-yellow-300">"VOLKSWAGEN"</span>
                    {"}"}]
                  </code>
                </div>

                <div className="bg-rose-900/20 border border-rose-700 rounded-lg p-3 mt-2">
                  <p className="text-rose-400 text-xs font-semibold mb-1">
                    ❌ Exemplos inválidos
                  </p>
                  <div className="space-y-1 text-xs font-mono text-rose-300">
                    <div>
                      <code>
                        [{"{"}
                        <span className="text-blue-300">"search_ref"</span>:
                        <span className="text-yellow-300">"ABC 123"</span>
                        {"}"}]
                      </code>{" "}
                      <span className="text-zinc-500">
                        (espaço no search_ref)
                      </span>
                    </div>
                    <div>
                      <code>
                        [{"{"}
                        <span className="text-blue-300">"brand"</span>:
                        <span className="text-yellow-300">"Fiat"</span>
                        {"}"}]
                      </code>{" "}
                      <span className="text-zinc-500">
                        (marca em minúsculas)
                      </span>
                    </div>
                    <div>
                      <code>null</code>{" "}
                      <span className="text-zinc-500">(deve ser [])</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const hasIssues =
    diagnosis &&
    (diagnosis.format_issues > 0 ||
      diagnosis.search_ref_issues > 0 ||
      diagnosis.brand_issues > 0 ||
      diagnosis.empty_list_issues > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">
          Validação de Similaridades
        </h2>
        <p className="text-zinc-500 mt-1">
          Análise e validação da coluna similarity
        </p>
      </div>

      {/* Card de Explicação */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
        <div className="flex items-start gap-3">
          <Info className="w-6 h-6 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-zinc-100 mb-3">
              Como deve estar formatada a coluna similarity
            </h3>

            <div className="space-y-3 text-sm text-zinc-300">
              <p>
                A coluna deve conter uma{" "}
                <strong className="text-emerald-400">
                  lista de dicionários
                </strong>{" "}
                em formato JSON:
              </p>

              <div className="bg-zinc-950 border border-zinc-700 rounded-lg p-4 font-mono text-xs">
                <code className="text-emerald-400">
                  [{"{"}
                  <span className="text-blue-400">"search_ref"</span>:
                  <span className="text-yellow-400">"ABC123"</span>,{" "}
                  <span className="text-blue-400">"brand"</span>:
                  <span className="text-yellow-400">"RENAULT"</span>
                  {"}"}]
                </code>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                <div className="bg-zinc-800 border border-zinc-700 rounded p-3">
                  <p className="font-semibold text-zinc-200 text-xs mb-1">
                    ✅ search_ref
                  </p>
                  <p className="text-zinc-400 text-xs">
                    Apenas letras, números e underscore (sem espaços ou
                    caracteres especiais)
                  </p>
                </div>
                <div className="bg-zinc-800 border border-zinc-700 rounded p-3">
                  <p className="font-semibold text-zinc-200 text-xs mb-1">
                    ✅ brand
                  </p>
                  <p className="text-zinc-400 text-xs">
                    Deve estar em MAIÚSCULAS
                  </p>
                </div>
              </div>
            </div>
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

      {/* Card de Status */}
      {!hasIssues ? (
        <div className="bg-emerald-900/20 border border-emerald-500 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <CheckCircle className="w-12 h-12 text-emerald-500 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-xl font-bold text-emerald-400">
                Coluna Similarity Válida
              </h3>
              <p className="text-zinc-400 mt-2">
                A coluna está corretamente formatada! Todas as similaridades
                seguem o padrão esperado.
              </p>
              <button
                onClick={loadStatistics}
                className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg flex items-center gap-2 transition-colors"
              >
                <BarChart3 className="w-4 h-4" />
                Ver Estatísticas
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-rose-900/20 border border-rose-500 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <XCircle className="w-12 h-12 text-rose-500 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-xl font-bold text-rose-400">
                Problemas Detectados na Coluna Similarity
              </h3>
              <p className="text-zinc-400 mt-2">
                Foram encontrados problemas de formatação que precisam ser
                corrigidos.
              </p>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
                {diagnosis.format_issues > 0 && (
                  <div className="bg-zinc-800 border border-zinc-700 rounded p-3">
                    <p className="text-zinc-400 text-xs">Formato Inválido</p>
                    <p className="text-2xl font-bold text-rose-400">
                      {diagnosis.format_issues}
                    </p>
                  </div>
                )}
                {diagnosis.search_ref_issues > 0 && (
                  <div className="bg-zinc-800 border border-zinc-700 rounded p-3">
                    <p className="text-zinc-400 text-xs">Search Ref Inválido</p>
                    <p className="text-2xl font-bold text-rose-400">
                      {diagnosis.search_ref_issues}
                    </p>
                  </div>
                )}
                {diagnosis.brand_issues > 0 && (
                  <div className="bg-zinc-800 border border-zinc-700 rounded p-3">
                    <p className="text-zinc-400 text-xs">Marcas Minúsculas</p>
                    <p className="text-2xl font-bold text-rose-400">
                      {diagnosis.brand_issues}
                    </p>
                  </div>
                )}
                {diagnosis.invalid_refs > 0 && (
                  <div className="bg-zinc-800 border border-zinc-700 rounded p-3">
                    <p className="text-zinc-400 text-xs">Refs Não Existentes</p>
                    <p className="text-2xl font-bold text-amber-400">
                      {diagnosis.invalid_refs}
                    </p>
                  </div>
                )}
                {diagnosis.invalid_brands > 0 && (
                  <div className="bg-zinc-800 border border-zinc-700 rounded p-3">
                    <p className="text-zinc-400 text-xs">
                      Marcas Desconhecidas
                    </p>
                    <p className="text-2xl font-bold text-amber-400">
                      {diagnosis.invalid_brands}
                    </p>
                  </div>
                )}
                {diagnosis.empty_list_issues > 0 && (
                  <div className="bg-zinc-800 border border-zinc-700 rounded p-3">
                    <p className="text-zinc-400 text-xs">NULL ao invés de []</p>
                    <p className="text-2xl font-bold text-rose-400">
                      {diagnosis.empty_list_issues}
                    </p>
                  </div>
                )}
              </div>

              {!readOnly && (
                <button
                  onClick={handleFixAll}
                  disabled={fixing}
                  className="mt-4 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg flex items-center gap-2 transition-colors"
                >
                  {fixing ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Aplicando Correções...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-5 h-5" />
                      Aplicar Todas as Correções
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

      {/* Preview de Linhas Problemáticas */}
      {hasIssues && diagnosis.preview.length > 0 && (
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <h3 className="text-lg font-semibold text-zinc-100">
              Linhas com Problemas
            </h3>
            <p className="text-zinc-500 text-sm mt-1">
              Página {diagnosis.page} de {diagnosis.total_pages} (
              {diagnosis.total_issues} total)
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-800">
                <tr>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Linha
                  </th>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Search Ref
                  </th>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Brand
                  </th>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Similarity Atual
                  </th>
                  <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                    Problemas
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {diagnosis.preview.map((row, idx) => (
                  <tr key={idx} className="hover:bg-zinc-800/50">
                    <td className="py-3 px-4 text-zinc-300">
                      {row.row_number}
                    </td>
                    <td className="py-3 px-4 text-zinc-300">
                      {row.search_ref || "-"}
                    </td>
                    <td className="py-3 px-4 text-zinc-300">
                      {row.brand || "-"}
                    </td>
                    <td className="py-3 px-4">
                      <code className="text-xs bg-zinc-800 px-2 py-1 rounded text-zinc-400">
                        {row.similarity_value
                          ? JSON.stringify(row.similarity_value).substring(
                              0,
                              50,
                            ) + "..."
                          : "null"}
                      </code>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {row.issues.map((issue, i) => (
                          <span
                            key={i}
                            className="px-2 py-1 bg-rose-900/50 text-rose-300 text-xs rounded"
                          >
                            {issue}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {diagnosis.total_pages > 1 && (
            <div className="p-4 border-t border-zinc-800 flex items-center justify-between">
              <div className="text-sm text-zinc-400">
                Mostrando {(currentPage - 1) * pageSize + 1} a{" "}
                {Math.min(currentPage * pageSize, diagnosis.total_issues)} de{" "}
                {diagnosis.total_issues} linhas com problemas
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronsLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-zinc-400 px-4">
                  Página {currentPage} de {diagnosis.total_pages}
                </span>
                <button
                  onClick={() =>
                    setCurrentPage((p) =>
                      Math.min(diagnosis.total_pages, p + 1),
                    )
                  }
                  disabled={currentPage === diagnosis.total_pages}
                  className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setCurrentPage(diagnosis.total_pages)}
                  disabled={currentPage === diagnosis.total_pages}
                  className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronsRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Estatísticas */}
      {showStatistics && statistics && (
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
          <h3 className="text-xl font-semibold text-zinc-100 mb-4">
            📊 Estatísticas de Similaridades
          </h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-zinc-800 border border-zinc-700 rounded p-4">
              <p className="text-zinc-400 text-sm">Total de Linhas</p>
              <p className="text-3xl font-bold text-emerald-400">
                {statistics.total_rows}
              </p>
            </div>
            <div className="bg-zinc-800 border border-zinc-700 rounded p-4">
              <p className="text-zinc-400 text-sm">Com Similaridades</p>
              <p className="text-3xl font-bold text-blue-400">
                {statistics.rows_with_similarities}
              </p>
              <p className="text-xs text-zinc-500 mt-1">
                {statistics.percentage_with_similarities}%
              </p>
            </div>
            <div className="bg-zinc-800 border border-zinc-700 rounded p-4">
              <p className="text-zinc-400 text-sm">Total Similaridades</p>
              <p className="text-3xl font-bold text-purple-400">
                {statistics.total_similarities}
              </p>
            </div>
            <div className="bg-zinc-800 border border-zinc-700 rounded p-4">
              <p className="text-zinc-400 text-sm">Média por Linha</p>
              <p className="text-3xl font-bold text-amber-400">
                {statistics.avg_similarities_per_row}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top Search Refs */}
            <div>
              <h4 className="text-lg font-semibold text-zinc-200 mb-3">
                🔗 Top 10 Search Refs Mais Referenciados
              </h4>
              <div className="space-y-2">
                {statistics.top_search_refs.map((item, idx) => (
                  <div
                    key={idx}
                    className="bg-zinc-800 border border-zinc-700 rounded p-3 flex justify-between items-center"
                  >
                    <span className="text-zinc-300 font-mono text-sm">
                      {item.search_ref}
                    </span>
                    <span className="text-emerald-400 font-bold">
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Brands */}
            <div>
              <h4 className="text-lg font-semibold text-zinc-200 mb-3">
                🏭 Top 10 Marcas Mais Referenciadas
              </h4>
              <div className="space-y-2">
                {statistics.top_brands.map((item, idx) => (
                  <div
                    key={idx}
                    className="bg-zinc-800 border border-zinc-700 rounded p-3 flex justify-between items-center"
                  >
                    <span className="text-zinc-300 font-semibold text-sm">
                      {item.brand}
                    </span>
                    <span className="text-blue-400 font-bold">
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Distribuição */}
          <div className="mt-6">
            <h4 className="text-lg font-semibold text-zinc-200 mb-3">
              📈 Distribuição de Quantidade de Similaridades
            </h4>
            <div className="bg-zinc-800 border border-zinc-700 rounded p-4">
              <div className="space-y-2">
                {statistics.distribution.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-3">
                    <span className="text-zinc-400 text-sm w-32">
                      {item.similarity_count} similaridade
                      {item.similarity_count !== 1 ? "s" : ""}
                    </span>
                    <div className="flex-1 bg-zinc-900 rounded-full h-6 relative">
                      <div
                        className="bg-gradient-to-r from-emerald-500 to-blue-500 h-full rounded-full transition-all"
                        style={{
                          width: `${
                            (item.row_count / statistics.total_rows) * 100
                          }%`,
                        }}
                      />
                      <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
                        {item.row_count} linhas
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Refs/Brands Inexistentes */}
          {(statistics.invalid_search_refs.length > 0 ||
            statistics.invalid_brands.length > 0) && (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              {statistics.invalid_search_refs.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-amber-400 mb-3">
                    ⚠️ Search Refs Não Existentes no Projeto
                  </h4>
                  <div className="bg-amber-900/20 border border-amber-700 rounded p-4 max-h-60 overflow-y-auto">
                    <div className="space-y-1 text-sm">
                      {statistics.invalid_search_refs.map((ref, idx) => (
                        <div
                          key={idx}
                          className="text-amber-300 font-mono text-xs"
                        >
                          • {ref}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {statistics.invalid_brands.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-amber-400 mb-3">
                    ⚠️ Marcas Não Existentes no Mapeamento
                  </h4>
                  <div className="bg-amber-900/20 border border-amber-700 rounded p-4 max-h-60 overflow-y-auto">
                    <div className="space-y-1 text-sm">
                      {statistics.invalid_brands.map((brand, idx) => (
                        <div
                          key={idx}
                          className="text-amber-300 font-semibold text-xs"
                        >
                          • {brand}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
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
