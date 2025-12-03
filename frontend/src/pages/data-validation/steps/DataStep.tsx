import { useState } from "react";
import {
  Tag,
  Barcode,
  Scale,
  Ruler,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Code,
} from "lucide-react";

// Interface baseada no schema TreatmentDiagnosisResponse do backend
interface DiagnosisData {
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
  issuesKey: keyof DiagnosisData;
  fixEndpoint: string; // Endpoint da API que será chamado
}

const treatmentGroups: TreatmentCard[] = [
  {
    id: "brands",
    title: "Validação de Marcas",
    description: "Marcas com comprimento inválido ou caracteres especiais",
    icon: <Tag className="w-6 h-6" />,
    issuesKey: "brand_issues",
    fixEndpoint: "/treatments/fix-codes",
  },
  {
    id: "ncm",
    title: "Validação de NCM",
    description: "Códigos NCM que não possuem exatamente 8 dígitos",
    icon: <Code className="w-6 h-6" />,
    issuesKey: "ncm_issues",
    fixEndpoint: "/treatments/fix-ncm",
  },
  {
    id: "barcode",
    title: "Códigos de Barras (EAN/UPC)",
    description:
      "Barcodes com formato inválido (esperado: 8, 12 ou 13 dígitos)",
    icon: <Barcode className="w-6 h-6" />,
    issuesKey: "barcode_issues",
    fixEndpoint: "/treatments/fix-barcode",
  },
  {
    id: "weights",
    title: "Pesos (Bruto vs Líquido)",
    description: "Peso bruto menor que líquido ou valores negativos",
    icon: <Scale className="w-6 h-6" />,
    issuesKey: "weight_issues",
    fixEndpoint: "/treatments/fix-negative-weights",
  },
  {
    id: "dimensions",
    title: "Dimensões",
    description: "Dimensões inválidas (valores <= 0 ou >= 1000 cm)",
    icon: <Ruler className="w-6 h-6" />,
    issuesKey: "dimension_issues",
    fixEndpoint: "/treatments/fix-codes",
  },
  {
    id: "search_ref",
    title: "Código de Referência (Search Ref)",
    description: "Referências com caracteres não alfanuméricos",
    icon: <Code className="w-6 h-6" />,
    issuesKey: "search_ref_issues",
    fixEndpoint: "/treatments/fix-codes",
  },
  {
    id: "manufacturer_ref",
    title: "Código do Fabricante",
    description: "Códigos do fabricante com formato inválido",
    icon: <Code className="w-6 h-6" />,
    issuesKey: "manufacturer_ref_issues",
    fixEndpoint: "/treatments/fix-codes",
  },
];

export default function DataStep() {
  const [diagnosis, setDiagnosis] = useState<DiagnosisData>(mockDiagnosis);
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>(
    {}
  );

  const handleFixIssues = async (
    cardId: string,
    issuesKey: keyof DiagnosisData
  ) => {
    // Ativar loading para este card
    setLoadingStates((prev) => ({ ...prev, [cardId]: true }));

    // Simular chamada à API (2 segundos)
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Zerar os erros deste grupo (simular sucesso da correção)
    setDiagnosis((prev) => ({
      ...prev,
      [issuesKey]: 0,
    }));

    // Desativar loading
    setLoadingStates((prev) => ({ ...prev, [cardId]: false }));

    console.log(`Correção aplicada para ${cardId}`);
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Tratamento de Dados
        </h2>
        <p className="text-gray-600">
          Diagnóstico de qualidade dos dados e correções automatizadas
        </p>
      </div>

      {/* Grid de Cards de Tratamento */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {treatmentGroups.map((group) => {
          const issuesCount = diagnosis[group.issuesKey];
          const isLoading = loadingStates[group.id];
          const hasIssues = issuesCount > 0;

          return (
            <div
              key={group.id}
              className={`
                rounded-card border-2 p-6 transition-all duration-200
                ${
                  hasIssues
                    ? "bg-red-50 border-red-200"
                    : "bg-green-50 border-green-200"
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
                      ? "bg-red-100 text-red-600"
                      : "bg-green-100 text-green-600"
                  }
                `}
                >
                  {group.icon}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {group.title}
                  </h3>
                  <p className="text-xs text-gray-600">{group.description}</p>
                </div>
              </div>

              {/* Status */}
              <div className="mb-4">
                {hasIssues ? (
                  <div className="flex items-center gap-2 text-red-700">
                    <AlertCircle className="w-5 h-5" />
                    <span className="font-medium text-sm">
                      {issuesCount}{" "}
                      {issuesCount === 1
                        ? "inconsistência encontrada"
                        : "inconsistências encontradas"}
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-green-700">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-medium text-sm">Tudo certo</span>
                  </div>
                )}
              </div>

              {/* Botão de Ação (apenas se houver erros) */}
              {hasIssues && (
                <button
                  onClick={() => handleFixIssues(group.id, group.issuesKey)}
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
              {Object.values(diagnosis).reduce((acc, val) => acc + val, 0)}
            </div>
            <div className="text-sm text-gray-500">problemas detectados</div>
          </div>
        </div>
      </div>
    </div>
  );
}
