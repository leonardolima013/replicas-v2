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
import Modal from "../../../components/Modal";
import { useModal } from "../../../hooks/useModal";

interface ColumnMapping {
  currentName: string;
  newName: string;
  type: "required" | "optional" | "extra";
}

interface ColumnsStepProps {
  readOnly?: boolean;
}

export default function ColumnsStep({ readOnly = false }: ColumnsStepProps) {
  const { projectId } = useParams<{ projectId: string }>();
  const [analysis, setAnalysis] = useState<ColumnsAnalysisResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [columnMappings, setColumnMappings] = useState<Record<string, string>>(
    {},
  );
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const { modalState, closeModal, showWarning } = useModal();

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
      ([_, newName]) => newName && newName !== "",
    );

    if (mappingsToApply.length === 0) {
      showWarning("Nenhuma alteração selecionada para aplicar.");
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
        `${mappingsToApply.length} coluna(s) renomeada(s) com sucesso!`,
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
        <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mb-4" />
        <p className="text-zinc-400">Analisando colunas...</p>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <div className="bg-rose-900/20 border border-rose-500 rounded-lg p-6 max-w-md">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-rose-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-rose-400 mb-1">
                Erro ao Carregar Análise
              </h3>
              <p className="text-sm text-rose-300 mb-4">{error}</p>
              <button
                onClick={fetchAnalysis}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg transition-colors text-sm"
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
  if (!analysis) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-zinc-400">Nenhuma análise disponível.</p>
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
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3" />
          Obrigatória
        </span>
      );
    }
    if (type === "optional") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
          <AlertTriangle className="w-3 h-3" />
          Opcional
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30">
        <XCircle className="w-3 h-3" />
        Não Listada
      </span>
    );
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-zinc-100 mb-2">
          Tratamento de Estrutura
        </h2>
        <p className="text-zinc-500">
          Análise e mapeamento de colunas do projeto
        </p>
      </div>

      {/* Informações sobre Colunas Esperadas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Colunas Obrigatórias */}
        <div className="bg-emerald-900/20 border-2 border-emerald-500/50 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <h3 className="text-lg font-semibold text-emerald-400">
              Colunas Obrigatórias
            </h3>
          </div>
          <p className="text-sm text-emerald-500 mb-3">
            Estas colunas devem estar presentes no seu arquivo:
          </p>
          <div className="flex flex-wrap gap-2">
            {analysis?.required.map((col) => (
              <span
                key={col}
                className="px-3 py-1.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-sm font-medium"
              >
                {col}
              </span>
            ))}
          </div>
        </div>

        {/* Colunas Opcionais */}
        <div className="bg-yellow-900/20 border-2 border-yellow-500/50 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
            <h3 className="text-lg font-semibold text-yellow-400">
              Colunas Opcionais
            </h3>
          </div>
          <p className="text-sm text-yellow-500 mb-3">
            Estas colunas são reconhecidas, mas não obrigatórias:
          </p>
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
            {analysis?.optional.map((col) => (
              <span
                key={col}
                className="px-3 py-1.5 bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 rounded-full text-sm font-medium"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Resumo de Colunas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-emerald-900/20 border border-emerald-500/50 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/20 rounded-lg">
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-emerald-500 font-medium">
                Colunas Obrigatórias
              </p>
              <p className="text-2xl font-bold text-emerald-400">
                {
                  analysis.required.filter((r) => analysis.present.includes(r))
                    .length
                }{" "}
                / {analysis.required.length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-yellow-400" />
            </div>
            <div>
              <p className="text-sm text-yellow-500 font-medium">
                Colunas Opcionais
              </p>
              <p className="text-2xl font-bold text-yellow-400">
                {
                  analysis.optional.filter((o) => analysis.present.includes(o))
                    .length
                }{" "}
                / {analysis.optional.length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-rose-900/20 border border-rose-500/50 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-rose-500/20 rounded-lg">
              <XCircle className="w-6 h-6 text-rose-400" />
            </div>
            <div>
              <p className="text-sm text-rose-500 font-medium">
                Colunas Não Listadas
              </p>
              <p className="text-2xl font-bold text-rose-400">
                {analysis.extra.length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Mensagem de Sucesso */}
      {successMessage && (
        <div className="mb-6 bg-emerald-900/20 border border-emerald-500 rounded-lg p-4 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-emerald-500 font-medium">
              {successMessage}
            </p>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-400 hover:text-emerald-300 font-medium text-sm"
          >
            Fechar
          </button>
        </div>
      )}

      {/* Tabela de Colunas */}
      <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden mb-6">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-zinc-700">
            <thead className="bg-zinc-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Coluna Atual
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Mapear Para
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-700">
              {allColumns.map((column) => (
                <tr
                  key={column.currentName}
                  className="hover:bg-zinc-700/30 transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-zinc-100">
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
                            e.target.value,
                          )
                        }
                        disabled={readOnly}
                        className="bg-zinc-700 border border-zinc-600 text-zinc-100 rounded-lg px-3 py-2 text-sm w-64 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 disabled:bg-zinc-800 disabled:cursor-not-allowed"
                      >
                        <option value="">Selecione uma coluna...</option>
                        {availableTargets.map((target) => (
                          <option key={target} value={target}>
                            {target}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-sm text-zinc-500 italic">
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
      {!readOnly && (
        <div className="flex justify-end">
          <button
            onClick={handleApplyChanges}
            disabled={
              saving ||
              Object.keys(columnMappings).filter((k) => columnMappings[k])
                .length === 0
            }
            className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold flex items-center gap-2 transition-colors"
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
      )}

      {readOnly && (
        <div className="text-center text-sm text-zinc-500 py-4">
          <AlertCircle className="w-5 h-5 inline mr-2" />
          Modo somente leitura - Para editar, cancele o envio do projeto
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
