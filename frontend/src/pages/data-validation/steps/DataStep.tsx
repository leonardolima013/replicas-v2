import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import {
  Barcode,
  Scale,
  Ruler,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Code,
  Type,
  Hash,
  FileText,
} from "lucide-react";
import {
  getDiagnosis,
  fixNCM,
  fixBarcodes,
  fixWeights,
  fixDimensions,
  fixNullStrings,
  fixUppercase,
  fixNullNumerics,
} from "../../../services/validationService";

// Interface baseada no schema TreatmentDiagnosisResponse do backend
interface DiagnosisData {
  project_id?: string;
  // Básicos (arrays de nomes de colunas)
  uppercase_issues?: string[];
  null_string_issues?: string[];
  null_numeric_issues?: string[];
  // Avançados (contadores)
  brand_issues: number;
  ncm_issues: number;
  barcode_issues: number;
  weight_issues: number;
  dimension_issues: number;
  search_ref_issues: number;
  manufacturer_ref_issues: number;
}

// Mock de dados - simula resposta da API /validation/{project_id}/treatments/diagnosis
const mockDiagnosis: DiagnosisData = {
  brand_issues: 12,
  ncm_issues: 45,
  barcode_issues: 8,
  weight_issues: 3,
  dimension_issues: 0,
  search_ref_issues: 22,
  manufacturer_ref_issues: 15,
};

interface TreatmentCard {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  issuesKey:
    | "uppercase_issues"
    | "null_string_issues"
    | "null_numeric_issues"
    | "brand_issues"
    | "ncm_issues"
    | "barcode_issues"
    | "weight_issues"
    | "dimension_issues"
    | "search_ref_issues"
    | "manufacturer_ref_issues";
  fixFunction: (projectId: string) => Promise<any>;
  isArrayIssue?: boolean; // Para diferenciar arrays de números
}

const treatmentGroups: TreatmentCard[] = [
  {
    id: "null_strings",
    title: "Valores Nulos em Strings",
    description: "Colunas de texto com valores nulos ou 'nan'",
    icon: <FileText className="w-6 h-6" />,
    issuesKey: "null_string_issues",
    fixFunction: fixNullStrings,
    isArrayIssue: true,
  },
  {
    id: "uppercase",
    title: "Conversão para MAIÚSCULAS",
    description: "Colunas de texto com valores que não estão em UPPERCASE",
    icon: <Type className="w-6 h-6" />,
    issuesKey: "uppercase_issues",
    fixFunction: fixUppercase,
    isArrayIssue: true,
  },
  {
    id: "null_numerics",
    title: "Valores Nulos em Números",
    description: "Colunas numéricas com valores nulos",
    icon: <Hash className="w-6 h-6" />,
    issuesKey: "null_numeric_issues",
    fixFunction: fixNullNumerics,
    isArrayIssue: true,
  },
  {
    id: "ncm",
    title: "Validação de NCM",
    description: "Códigos NCM que não possuem exatamente 8 dígitos",
    icon: <Code className="w-6 h-6" />,
    issuesKey: "ncm_issues",
    fixFunction: fixNCM,
  },
  {
    id: "barcode",
    title: "Códigos de Barras (EAN/UPC)",
    description:
      "Barcodes com formato inválido (esperado: 8, 12 ou 13 dígitos)",
    icon: <Barcode className="w-6 h-6" />,
    issuesKey: "barcode_issues",
    fixFunction: fixBarcodes,
  },
  {
    id: "weights",
    title: "Pesos (Bruto vs Líquido)",
    description: "Peso bruto menor que líquido ou valores negativos",
    icon: <Scale className="w-6 h-6" />,
    issuesKey: "weight_issues",
    fixFunction: fixWeights,
  },
  {
    id: "dimensions",
    title: "Dimensões",
    description: "Dimensões inválidas (valores <= 0 ou >= 1000 cm)",
    icon: <Ruler className="w-6 h-6" />,
    issuesKey: "dimension_issues",
    fixFunction: fixDimensions,
  },
];

interface DataStepProps {
  readOnly?: boolean;
}

export default function DataStep({ readOnly = false }: DataStepProps) {
  const { projectId } = useParams<{ projectId: string }>();
  const [diagnosis, setDiagnosis] = useState<DiagnosisData | null>(null);
  const [loadingDiagnosis, setLoadingDiagnosis] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>(
    {}
  );
  const [successMessages, setSuccessMessages] = useState<
    Record<string, string>
  >({});

  useEffect(() => {
    fetchDiagnosis();
  }, [projectId]);

  const fetchDiagnosis = async () => {
    if (!projectId) return;

    setLoadingDiagnosis(true);
    setError(null);

    try {
      const data = await getDiagnosis(projectId);
      setDiagnosis(data);
    } catch (err: any) {
      console.error("Erro ao carregar diagnóstico:", err);
      setError(err.message || "Erro ao carregar diagnóstico. Tente novamente.");
    } finally {
      setLoadingDiagnosis(false);
    }
  };

  const handleFixIssues = async (card: TreatmentCard) => {
    if (!projectId) return;

    // Ativar loading para este card
    setLoadingStates((prev) => ({ ...prev, [card.id]: true }));
    setSuccessMessages((prev) => {
      const updated = { ...prev };
      delete updated[card.id];
      return updated;
    });

    try {
      const response = await card.fixFunction(projectId);
      console.log(`Correção aplicada para ${card.id}:`, response);

      // Mostrar mensagem de sucesso
      setSuccessMessages((prev) => ({
        ...prev,
        [card.id]: `${
          response.rows_affected
        } linhas corrigidas! Colunas afetadas: ${response.columns_affected.join(
          ", "
        )}`,
      }));

      // Recarregar diagnóstico para atualizar contadores
      await fetchDiagnosis();
    } catch (err: any) {
      console.error(`Erro ao corrigir ${card.id}:`, err);
      alert(`Erro ao aplicar correções: ${err.message}`);
    } finally {
      // Desativar loading
      setLoadingStates((prev) => ({ ...prev, [card.id]: false }));
    }
  };

  // Loading State
  if (loadingDiagnosis) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <Loader2 className="w-12 h-12 text-primary-500 dark:text-primary-400 animate-spin mb-4" />
        <p className="text-gray-600 dark:text-gray-400">
          Carregando diagnóstico...
        </p>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-card p-6 max-w-md">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900 dark:text-red-300 mb-1">
                Erro ao Carregar Diagnóstico
              </h3>
              <p className="text-sm text-red-700 dark:text-red-400 mb-4">
                {error}
              </p>
              <button onClick={fetchDiagnosis} className="btn-primary text-sm">
                Tentar Novamente
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Empty State
  if (!diagnosis) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-gray-600 dark:text-gray-400">
          Nenhum diagnóstico disponível.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Tratamento de Dados
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Diagnóstico de qualidade dos dados e correções automatizadas
        </p>
      </div>

      {/* Grid de Cards de Tratamento */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {treatmentGroups.map((group) => {
          const rawValue = diagnosis[group.issuesKey];
          const issuesCount = group.isArrayIssue
            ? (rawValue as string[]).length
            : (rawValue as number);
          const isLoading = loadingStates[group.id];
          const hasIssues = issuesCount > 0;

          return (
            <div
              key={group.id}
              className={`
                rounded-card border-2 p-6 transition-all duration-200
                ${
                  hasIssues
                    ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                    : "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                }
              `}
            >
              {/* Cabeçalho do Card */}
              <div className="flex items-start gap-3 mb-4">
                <div
                  className={`
                  p-2 rounded-lg
                  ${
                    hasIssues
                      ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"
                      : "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400"
                  }
                `}
                >
                  {group.icon}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                    {group.title}
                  </h3>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {group.description}
                  </p>
                </div>
              </div>

              {/* Status */}
              <div className="mb-4">
                {hasIssues ? (
                  <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
                    <AlertCircle className="w-5 h-5" />
                    <div className="text-sm">
                      {group.isArrayIssue ? (
                        <>
                          <div className="font-medium mb-1">
                            {issuesCount}{" "}
                            {issuesCount === 1
                              ? "coluna com problemas"
                              : "colunas com problemas"}
                          </div>
                          <div className="text-xs text-red-600 dark:text-red-400">
                            {(rawValue as string[]).join(", ")}
                          </div>
                        </>
                      ) : (
                        <span className="font-medium">
                          {issuesCount}{" "}
                          {issuesCount === 1
                            ? "inconsistência encontrada"
                            : "inconsistências encontradas"}
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-medium text-sm">Tudo certo</span>
                  </div>
                )}
              </div>

              {/* Mensagem de Sucesso */}
              {successMessages[group.id] && (
                <div className="mb-4 text-sm text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-900/30 rounded px-3 py-2">
                  {successMessages[group.id]}
                </div>
              )}

              {/* Botão de Ação (apenas se houver erros e não estiver em readOnly) */}
              {hasIssues && !readOnly && (
                <button
                  onClick={() => handleFixIssues(group)}
                  disabled={isLoading}
                  className="
                    w-full bg-white border border-gray-300 rounded-button 
                    px-4 py-2.5 font-medium text-sm text-gray-700
                    shadow-soft hover:bg-gray-50 hover:shadow-soft-md
                    transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
                    flex items-center justify-center gap-2
                  "
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Corrigindo...
                    </>
                  ) : (
                    "Corrigir Automaticamente"
                  )}
                </button>
              )}

              {/* Mensagem de modo somente leitura */}
              {hasIssues && readOnly && (
                <div className="text-center text-xs text-gray-500 py-2 italic">
                  Modo somente leitura
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Resumo Total */}
      <div className="mt-8 card bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 mb-1">
              Resumo do Diagnóstico
            </h3>
            <p className="text-sm text-gray-600">
              Total de inconsistências encontradas em todos os grupos
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-gray-900">
              {diagnosis.brand_issues +
                diagnosis.ncm_issues +
                diagnosis.barcode_issues +
                diagnosis.weight_issues +
                diagnosis.dimension_issues +
                diagnosis.search_ref_issues +
                diagnosis.manufacturer_ref_issues}
            </div>
            <div className="text-sm text-gray-500">problemas detectados</div>
          </div>
        </div>
      </div>
    </div>
  );
}
