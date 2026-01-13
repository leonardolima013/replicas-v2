import { useState, useEffect } from "react";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  FileCheck,
  Database,
  Tag,
  Copy,
  BarChart3,
  Loader2,
  TrendingUp,
} from "lucide-react";
import * as validationService from "../../../services/validationService";

interface QualityReportTabProps {
  projectId: string;
}

export default function QualityReportTab({ projectId }: QualityReportTabProps) {
  const [report, setReport] =
    useState<validationService.QualityReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReport();
  }, [projectId]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await validationService.getQualityReport(projectId);
      setReport(data);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar relatório de qualidade");
    } finally {
      setLoading(false);
    }
  };

  // Helper para determinar cor do score
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600 dark:text-green-400";
    if (score >= 60) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 80)
      return "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800";
    if (score >= 60)
      return "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800";
    return "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800";
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        <span className="ml-3 text-gray-600 dark:text-gray-400">
          Gerando relatório de qualidade...
        </span>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8">
        <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 dark:border-red-600 p-4 rounded-card">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-800 dark:text-red-300">
                Erro ao Carregar Relatório
              </h3>
              <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                {error || "Dados do relatório não disponíveis"}
              </p>
              <button
                onClick={fetchReport}
                className="btn-secondary mt-4 text-sm"
              >
                Tentar Novamente
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {/* Score Geral */}
      <div
        className={`rounded-card border-2 p-6 ${getScoreBgColor(
          report.overall_quality_score
        )}`}
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
              Score de Qualidade Geral
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Avaliação consolidada de todas as métricas
            </p>
          </div>
          <div className="text-center">
            <div
              className={`text-5xl font-bold ${getScoreColor(
                report.overall_quality_score
              )}`}
            >
              {report.overall_quality_score.toFixed(1)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              / 100
            </div>
          </div>
        </div>
      </div>

      {/* Warnings e Blockers */}
      {report.blockers.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-600 dark:border-red-700 p-4 rounded-card">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">
                ⚠️ Problemas Críticos
              </h3>
              <ul className="list-disc list-inside space-y-1">
                {report.blockers.map((blocker, idx) => (
                  <li
                    key={idx}
                    className="text-sm text-red-700 dark:text-red-400"
                  >
                    {blocker}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {report.warnings.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 dark:border-yellow-600 p-4 rounded-card">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
                Avisos de Atenção
              </h3>
              <ul className="list-disc list-inside space-y-1">
                {report.warnings.map((warning, idx) => (
                  <li
                    key={idx}
                    className="text-sm text-yellow-700 dark:text-yellow-400"
                  >
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Grid de Métricas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. Estrutura */}
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <FileCheck className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Estrutura
            </h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Colunas Obrigatórias
              </span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                {report.structural.required_columns_present} /{" "}
                {report.structural.required_columns_total}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Colunas Extras Mapeadas
              </span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                {report.structural.extra_columns_mapped}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Colunas Faltando
              </span>
              <span
                className={`text-sm font-semibold ${
                  report.structural.missing_columns === 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {report.structural.missing_columns}
              </span>
            </div>

            <div className="pt-3 border-t border-gray-200 dark:border-gray-800">
              {report.structural.missing_columns === 0 ? (
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">
                    Estrutura completa
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                  <XCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">
                    Estrutura incompleta
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 2. Qualidade dos Dados */}
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <Database className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Qualidade dos Dados
            </h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Completude
              </span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                {report.data_quality.completeness_pct.toFixed(1)}%
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Total de Linhas
              </span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                {report.data_quality.total_rows.toLocaleString()}
              </span>
            </div>

            <div className="pt-3 border-t border-gray-200 dark:border-gray-800">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                Issues detectados:
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">
                    Uppercase:
                  </span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {report.data_quality.uppercase_issues}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">NCM:</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {report.data_quality.ncm_issues}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">
                    Barcodes:
                  </span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {report.data_quality.barcode_issues}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">
                    Pesos:
                  </span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {report.data_quality.weight_issues}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 3. Marcas */}
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <Tag className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Mapeamento de Marcas
            </h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Marcas Normalizadas
              </span>
              <span className="text-sm font-semibold text-green-600 dark:text-green-400">
                {report.brands.normalized_pct.toFixed(1)}%
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Marcas Desconhecidas
              </span>
              <span
                className={`text-sm font-semibold ${
                  report.brands.unknown_pct > 10
                    ? "text-yellow-600 dark:text-yellow-400"
                    : "text-green-600 dark:text-green-400"
                }`}
              >
                {report.brands.unknown_pct.toFixed(1)}%
              </span>
            </div>

            {report.brands.top_unknown_brands.length > 0 && (
              <div className="pt-3 border-t border-gray-200 dark:border-gray-800">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  Top marcas desconhecidas:
                </p>
                <ul className="space-y-1">
                  {report.brands.top_unknown_brands.slice(0, 3).map((brand) => (
                    <li
                      key={brand.brand}
                      className="text-xs flex justify-between"
                    >
                      <span className="text-gray-600 dark:text-gray-400 truncate max-w-[150px]">
                        {brand.brand}
                      </span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {brand.occurrences}x
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* 4. Duplicatas */}
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
              <Copy className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Duplicatas
            </h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Encontradas
              </span>
              <span
                className={`text-sm font-semibold ${
                  report.duplicates.found === 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-orange-600 dark:text-orange-400"
                }`}
              >
                {report.duplicates.found}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Removidas
              </span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                {report.duplicates.removed}
              </span>
            </div>

            <div className="pt-3 border-t border-gray-200 dark:border-gray-800">
              {report.duplicates.found === 0 ? (
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">Sem duplicatas</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-sm font-medium">
                    Atenção necessária
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 5. Estatísticas */}
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 p-6 md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
              <BarChart3 className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Análise Estatística
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col">
              <span className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Correlação Peso Líquido × Bruto
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {report.statistics.weight_correlation !== null
                    ? report.statistics.weight_correlation.toFixed(2)
                    : "N/A"}
                </span>
                {report.statistics.weight_correlation !== null &&
                  report.statistics.weight_correlation >= 0.8 && (
                    <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
                      <TrendingUp className="w-4 h-4" />
                      <span className="text-xs font-medium">Forte</span>
                    </div>
                  )}
              </div>
            </div>

            <div className="flex flex-col">
              <span className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Violações Físicas
              </span>
              <span
                className={`text-2xl font-bold ${
                  report.statistics.physical_violations === 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {report.statistics.physical_violations}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Peso líquido &gt; bruto
              </span>
            </div>

            <div className="flex flex-col">
              <span className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Valores Negativos
              </span>
              <span
                className={`text-2xl font-bold ${
                  report.statistics.negative_values === 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {report.statistics.negative_values}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Valores negativos em numéricos
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
