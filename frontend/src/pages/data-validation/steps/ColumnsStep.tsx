import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  AlertCircle,
  Save,
} from "lucide-react";
import {
  getColumnsAnalysis,
  renameColumn,
  type ColumnsAnalysisResponse,
} from "../../../services/validationService";

interface ColumnMapping {
  currentName: string;
  newName: string;
  type: "required" | "optional" | "extra";
}

export default function ColumnsStep() {
  const { projectId } = useParams<{ projectId: string }>();
  const [analysis, setAnalysis] = useState<ColumnsAnalysisResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [columnMappings, setColumnMappings] = useState<Record<string, string>>(
    {}
  );
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalysis();
  }, [projectId]);

  const fetchAnalysis = async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getColumnsAnalysis(projectId);
      setAnalysis(data);
    } catch (err: any) {
      console.error("Erro ao carregar análise de colunas:", err);
      setError(err.message || "Erro ao carregar análise de colunas.");
    } finally {
      setLoading(false);
    }
  };

  const handleMappingChange = (currentName: string, newName: string) => {
    setColumnMappings((prev) => ({
      ...prev,
      [currentName]: newName,
    }));
  };

  const handleApplyChanges = async () => {
    if (!projectId || !analysis) return;

    // Filtrar apenas as colunas que têm mapeamento definido
    const mappingsToApply = Object.entries(columnMappings).filter(
      ([_, newName]) => newName && newName !== ""
    );

    if (mappingsToApply.length === 0) {
      alert("Nenhuma alteração selecionada para aplicar.");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Aplicar cada renomeação sequencialmente
      for (const [oldName, newName] of mappingsToApply) {
        await renameColumn(projectId, oldName, newName);
      }

      setSuccessMessage(
        `${mappingsToApply.length} coluna(s) renomeada(s) com sucesso!`
      );

      // Recarregar análise
      setColumnMappings({});
      await fetchAnalysis();
    } catch (err: any) {
      console.error("Erro ao aplicar alterações:", err);
      setError(err.message || "Erro ao aplicar alterações.");
    } finally {
      setSaving(false);
    }
  };

  // Loading State
  if (loading) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
        <p className="text-gray-600">Analisando colunas...</p>
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
                Erro ao Carregar Análise
              </h3>
              <p className="text-sm text-red-700 mb-4">{error}</p>
              <button onClick={fetchAnalysis} className="btn-primary text-sm">
                Tentar Novamente
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Empty State
  if (!analysis) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-gray-600">Nenhuma análise disponível.</p>
      </div>
    );
  }

  // Combinar todas as colunas presentes com seu tipo
  const allColumns: ColumnMapping[] = [
    // Colunas que estão presentes e são reconhecidas (obrigatórias ou opcionais)
    ...analysis.present.map((col) => {
      const isRequired = analysis.required.includes(col);
      const isOptional = analysis.optional.includes(col);

      if (isRequired) {
        return { currentName: col, newName: col, type: "required" as const };
      } else if (isOptional) {
        return { currentName: col, newName: col, type: "optional" as const };
      } else {
        return { currentName: col, newName: col, type: "extra" as const };
      }
    }),
    // Colunas extras (não reconhecidas) - devem aparecer na tabela para mapeamento
    ...analysis.extra.map((col) => ({
      currentName: col,
      newName: col,
      type: "extra" as const,
    })),
  ];

  // Colunas obrigatórias que faltam (disponíveis para mapeamento)
  const availableTargets = [
    ...analysis.missing,
    ...analysis.optional.filter((opt) => !analysis.present.includes(opt)),
  ];

  const getColumnBadge = (type: "required" | "optional" | "extra") => {
    if (type === "required") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
          <CheckCircle2 className="w-3 h-3" />
          Obrigatória
        </span>
      );
    }
    if (type === "optional") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
          <AlertTriangle className="w-3 h-3" />
          Opcional
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
        <XCircle className="w-3 h-3" />
        Não Listada
      </span>
    );
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Tratamento de Estrutura
        </h2>
        <p className="text-gray-600">
          Análise e mapeamento de colunas do projeto
        </p>
      </div>

      {/* Informações sobre Colunas Esperadas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Colunas Obrigatórias */}
        <div className="card bg-green-50 border-2 border-green-200">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            <h3 className="text-lg font-semibold text-green-900">
              Colunas Obrigatórias
            </h3>
          </div>
          <p className="text-sm text-green-700 mb-3">
            Estas colunas devem estar presentes no seu arquivo:
          </p>
          <div className="flex flex-wrap gap-2">
            {analysis?.required.map((col) => (
              <span
                key={col}
                className="px-3 py-1.5 bg-green-100 text-green-800 rounded-full text-sm font-medium"
              >
                {col}
              </span>
            ))}
          </div>
        </div>

        {/* Colunas Opcionais */}
        <div className="card bg-yellow-50 border-2 border-yellow-200">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <h3 className="text-lg font-semibold text-yellow-900">
              Colunas Opcionais
            </h3>
          </div>
          <p className="text-sm text-yellow-700 mb-3">
            Estas colunas são reconhecidas, mas não obrigatórias:
          </p>
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
            {analysis?.optional.map((col) => (
              <span
                key={col}
                className="px-3 py-1.5 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Resumo de Colunas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="card bg-green-50 border border-green-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle2 className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-green-700 font-medium">
                Colunas Obrigatórias
              </p>
              <p className="text-2xl font-bold text-green-900">
                {
                  analysis.required.filter((r) => analysis.present.includes(r))
                    .length
                }{" "}
                / {analysis.required.length}
              </p>
            </div>
          </div>
        </div>

        <div className="card bg-yellow-50 border border-yellow-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-yellow-700 font-medium">
                Colunas Opcionais
              </p>
              <p className="text-2xl font-bold text-yellow-900">
                {
                  analysis.optional.filter((o) => analysis.present.includes(o))
                    .length
                }{" "}
                / {analysis.optional.length}
              </p>
            </div>
          </div>
        </div>

        <div className="card bg-red-50 border border-red-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <XCircle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-red-700 font-medium">
                Colunas Não Listadas
              </p>
              <p className="text-2xl font-bold text-red-900">
                {analysis.extra.length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Mensagem de Sucesso */}
      {successMessage && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-card p-4 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-green-700 font-medium">
              {successMessage}
            </p>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="text-green-600 hover:text-green-700 font-medium text-sm"
          >
            Fechar
          </button>
        </div>
      )}

      {/* Tabela de Colunas */}
      <div className="card p-0 overflow-hidden mb-6">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Coluna Atual
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Mapear Para
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {allColumns.map((column) => (
                <tr key={column.currentName} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900">
                      {column.currentName}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getColumnBadge(column.type)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {column.type === "extra" ? (
                      <select
                        value={columnMappings[column.currentName] || ""}
                        onChange={(e) =>
                          handleMappingChange(
                            column.currentName,
                            e.target.value
                          )
                        }
                        className="input-base text-sm w-64"
                      >
                        <option value="">Selecione uma coluna...</option>
                        {availableTargets.map((target) => (
                          <option key={target} value={target}>
                            {target}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-sm text-gray-500 italic">
                        Coluna reconhecida
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Botão de Aplicar Alterações */}
      <div className="flex justify-end">
        <button
          onClick={handleApplyChanges}
          disabled={
            saving ||
            Object.keys(columnMappings).filter((k) => columnMappings[k])
              .length === 0
          }
          className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Aplicando Alterações...
            </>
          ) : (
            <>
              <Save className="w-5 h-5" />
              Aplicar Alterações
            </>
          )}
        </button>
      </div>
    </div>
  );
}
