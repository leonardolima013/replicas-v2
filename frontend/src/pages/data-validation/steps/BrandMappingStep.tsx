import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  CheckCircle,
  AlertTriangle,
  Loader2,
  RefreshCw,
  ArrowRight,
  Package,
  CheckCheck,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import * as validationService from "../../../services/validationService";

interface BrandMappingStepProps {
  readOnly?: boolean;
}

export default function BrandMappingStep({
  readOnly = false,
}: BrandMappingStepProps) {
  const { projectId } = useParams<{ projectId: string }>();
  const [analysis, setAnalysis] =
    useState<validationService.BrandAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (projectId) {
      loadAnalysis();
    }
  }, [projectId]);

  const loadAnalysis = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await validationService.analyzeBrands(projectId);
      setAnalysis(data);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar análise de marcas");
    } finally {
      setLoading(false);
    }
  };

  const handleApplyNormalization = async () => {
    if (!projectId || readOnly) return;

    if (!analysis || analysis.mapped_count === 0) {
      alert("Não há marcas para normalizar.");
      return;
    }

    const confirmed = window.confirm(
      `Tem certeza que deseja normalizar ${analysis.mapped_count} marcas?\n\nEsta ação irá padronizar os nomes de marcas de acordo com o mapeamento oficial.`
    );

    if (!confirmed) return;

    try {
      setApplying(true);
      setError(null);
      setSuccessMessage(null);

      const result = await validationService.applyBrandNormalization(projectId);

      setSuccessMessage(
        `✅ Normalização concluída! ${result.rows_affected} marcas foram padronizadas.`
      );

      // Recarregar análise após aplicação
      setTimeout(() => {
        loadAnalysis();
        setSuccessMessage(null);
      }, 3000);
    } catch (err: any) {
      setError(err.message || "Erro ao aplicar normalização de marcas");
    } finally {
      setApplying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">Analisando mapeamento de marcas...</p>
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
          onClick={loadAnalysis}
          className="mt-4 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Tentar Novamente
        </button>
      </div>
    );
  }

  if (!analysis) return null;

  const mappedPercentage =
    analysis.total_rows > 0
      ? ((analysis.mapped_count / analysis.total_rows) * 100).toFixed(1)
      : "0.0";
  const unknownPercentage =
    analysis.total_rows > 0
      ? ((analysis.unknown_count / analysis.total_rows) * 100).toFixed(1)
      : "0.0";

  const hasMappings = analysis.mapped_count > 0;
  const hasUnknown = analysis.unknown_count > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">
          Mapeamento de Marcas
        </h2>
        <p className="text-zinc-500 mt-1">
          Normalização automática de nomes de marcas usando mapeamento oficial
        </p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="bg-emerald-900/20 border border-emerald-500 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-500" />
            <p className="text-emerald-500 font-medium">{successMessage}</p>
          </div>
        </div>
      )}

      {/* Cards de Resumo */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total de Produtos */}
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <Package className="w-5 h-5 text-blue-400" />
            <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wide">
              Total de Produtos
            </h3>
          </div>
          <p className="text-3xl font-bold text-zinc-100">
            {analysis.total_rows.toLocaleString()}
          </p>
        </div>

        {/* Marcas Reconhecidas */}
        <div className="bg-emerald-900/20 border border-emerald-500/50 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <CheckCheck className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-medium text-emerald-400 uppercase tracking-wide">
              Marcas Reconhecidas
            </h3>
          </div>
          <p className="text-3xl font-bold text-emerald-400">
            {analysis.mapped_count.toLocaleString()}
          </p>
          <p className="text-sm text-emerald-500 mt-1">
            {mappedPercentage}% do total • Serão padronizadas
          </p>
        </div>

        {/* Marcas Desconhecidas */}
        <div
          className={`${
            hasUnknown
              ? "bg-orange-900/20 border-orange-500/50"
              : "bg-zinc-800/50 border-zinc-700"
          } border rounded-lg p-6`}
        >
          <div className="flex items-center gap-3 mb-2">
            <AlertCircle
              className={`w-5 h-5 ${
                hasUnknown ? "text-orange-400" : "text-zinc-500"
              }`}
            />
            <h3
              className={`text-sm font-medium uppercase tracking-wide ${
                hasUnknown ? "text-orange-400" : "text-zinc-400"
              }`}
            >
              Peças de Marcas Desconhecidas
            </h3>
          </div>
          <p
            className={`text-3xl font-bold ${
              hasUnknown ? "text-orange-400" : "text-zinc-500"
            }`}
          >
            {analysis.unknown_count.toLocaleString()}
          </p>
          <p
            className={`text-sm mt-1 ${
              hasUnknown ? "text-orange-500" : "text-zinc-600"
            }`}
          >
            {unknownPercentage}% do total{" "}
            {hasUnknown && "• Não estão no mapeamento"}
          </p>
        </div>
      </div>

      {/* Visualização de Impacto */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Correções */}
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden">
          <div className="bg-zinc-900/50 px-6 py-4 border-b border-zinc-700">
            <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              Top Correções
            </h3>
            <p className="text-sm text-zinc-500 mt-1">
              Principais marcas que serão padronizadas
            </p>
          </div>
          <div className="p-6">
            {analysis.top_corrections.length > 0 ? (
              <div className="space-y-4">
                {analysis.top_corrections.map((correction, index) => (
                  <div
                    key={index}
                    className="bg-zinc-900/50 border border-zinc-700 rounded-lg p-4 hover:border-emerald-500/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3 flex-1">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-zinc-400 font-mono text-sm">
                              {correction.original_brand}
                            </span>
                            <ArrowRight className="w-4 h-4 text-emerald-400" />
                            <span className="text-emerald-400 font-mono text-sm font-semibold">
                              {correction.corrected_brand}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Package className="w-4 h-4 text-zinc-500" />
                        <span className="text-sm text-zinc-500">
                          {correction.occurrences.toLocaleString()}{" "}
                          {correction.occurrences === 1 ? "item" : "itens"}
                        </span>
                      </div>
                      {/* Progress bar */}
                      <div className="flex-1 max-w-xs ml-4">
                        <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-500 rounded-full"
                            style={{
                              width: `${Math.min(
                                (correction.occurrences /
                                  analysis.top_corrections[0].occurrences) *
                                  100,
                                100
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                <p className="text-zinc-400">
                  Não há marcas para padronizar ou todas já foram normalizadas!
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Estatísticas e Informações */}
        <div className="space-y-4">
          {/* Tabela de marcas desconhecidas */}
          {hasUnknown && analysis.unknown_brands.length > 0 && (
            <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden">
              <div className="bg-zinc-900/50 px-6 py-4 border-b border-zinc-700">
                <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-orange-400" />
                  Marcas Desconhecidas
                </h3>
                <p className="text-sm text-zinc-500 mt-1">
                  Top {analysis.unknown_brands.length} marcas que não constam no
                  mapeamento oficial
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-zinc-900/30 border-b border-zinc-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                        Marca
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-zinc-400 uppercase tracking-wider">
                        Ocorrências
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-700">
                    {analysis.unknown_brands.map((brand, index) => (
                      <tr
                        key={index}
                        className="hover:bg-zinc-700/30 transition-colors"
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm font-mono text-orange-400">
                            {brand.brand}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          <span className="text-sm text-zinc-400">
                            {brand.occurrences.toLocaleString()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Info sobre marcas desconhecidas */}
          {hasUnknown && (
            <div className="bg-orange-900/20 border border-orange-500/50 rounded-lg p-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-orange-400 font-semibold mb-2">
                    Marcas Desconhecidas Detectadas
                  </h4>
                  <p className="text-sm text-zinc-400 leading-relaxed">
                    Foram encontradas {analysis.unknown_count.toLocaleString()}{" "}
                    peças de marcas que não constam no mapeamento oficial. Estas
                    marcas permanecerão com seus nomes originais.
                  </p>
                  <p className="text-sm text-orange-500 mt-3 font-medium">
                    💡 Considere atualizar o arquivo de mapeamento ou verificar
                    se há erros de digitação nos dados.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Info sobre o processo */}
          <div className="bg-blue-900/20 border border-blue-500/50 rounded-lg p-6">
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-blue-400 font-semibold mb-2">
                  Como Funciona a Normalização
                </h4>
                <ul className="text-sm text-zinc-400 space-y-2 leading-relaxed">
                  <li className="flex items-start gap-2">
                    <span className="text-blue-400 mt-1">•</span>
                    <span>
                      O sistema usa um mapeamento oficial de marcas para
                      padronizar nomes inconsistentes
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-400 mt-1">•</span>
                    <span>
                      Exemplos: "3M DO BRASIL" → "3M", "BOSCH BRASIL" → "BOSCH"
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-400 mt-1">•</span>
                    <span>
                      A normalização é aplicada em massa e não pode ser desfeita
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-400 mt-1">•</span>
                    <span>
                      Marcas não mapeadas permanecerão com seus nomes originais
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Progresso visual */}
          {hasMappings && (
            <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-6">
              <h4 className="text-zinc-300 font-semibold mb-4">
                Distribuição de Marcas
              </h4>
              <div className="space-y-3">
                {/* Barra de progresso - Reconhecidas */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-emerald-400">
                      Reconhecidas
                    </span>
                    <span className="text-sm text-emerald-400 font-mono">
                      {mappedPercentage}%
                    </span>
                  </div>
                  <div className="h-3 bg-zinc-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                      style={{ width: `${mappedPercentage}%` }}
                    />
                  </div>
                </div>

                {/* Barra de progresso - Desconhecidas */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-orange-400">
                      Desconhecidas
                    </span>
                    <span className="text-sm text-orange-400 font-mono">
                      {unknownPercentage}%
                    </span>
                  </div>
                  <div className="h-3 bg-zinc-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-orange-500 rounded-full transition-all duration-500"
                      style={{ width: `${unknownPercentage}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Ação Principal */}
      <div className="border-t border-zinc-700 pt-6">
        {hasMappings ? (
          <button
            onClick={handleApplyNormalization}
            disabled={applying || readOnly}
            className={`w-full py-4 px-6 rounded-lg font-semibold text-lg flex items-center justify-center gap-3 transition-all ${
              applying || readOnly
                ? "bg-zinc-700 text-zinc-500 cursor-not-allowed"
                : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg hover:shadow-emerald-500/20"
            }`}
          >
            {applying ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Aplicando Normalização...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Normalizar Marcas Automaticamente
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        ) : (
          <div className="text-center py-8">
            <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-zinc-100 mb-2">
              Marcas Já Padronizadas
            </h3>
            <p className="text-zinc-400">
              Não há marcas pendentes para normalização neste projeto.
            </p>
          </div>
        )}

        {readOnly && hasMappings && (
          <p className="text-center text-sm text-zinc-500 mt-3">
            Projeto em modo somente leitura. Não é possível aplicar
            normalização.
          </p>
        )}
      </div>
    </div>
  );
}
