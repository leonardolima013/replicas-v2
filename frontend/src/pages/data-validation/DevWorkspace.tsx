import { useState, useEffect } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import {
  ChevronRight,
  Eye,
  TableProperties,
  Wand2,
  Send,
  AlertCircle,
  Loader2,
  XCircle,
} from "lucide-react";
import ViewStep from "./steps/ViewStep";
import ColumnsStep from "./steps/ColumnsStep";
import DataStep from "./steps/DataStep";
import ReviewStep from "./steps/ReviewStep";
import * as validationService from "../../services/validationService";

interface Step {
  id: number;
  title: string;
  icon: React.ReactNode;
  getComponent: (readOnly: boolean) => React.ReactNode;
}

const steps: Step[] = [
  {
    id: 0,
    title: "Visualização",
    icon: <Eye className="w-5 h-5" />,
    getComponent: (readOnly) => <ViewStep />,
  },
  {
    id: 1,
    title: "Tratamento de Estrutura",
    icon: <TableProperties className="w-5 h-5" />,
    getComponent: (readOnly) => <ColumnsStep readOnly={readOnly} />,
  },
  {
    id: 2,
    title: "Tratamento de Dados",
    icon: <Wand2 className="w-5 h-5" />,
    getComponent: (readOnly) => <DataStep readOnly={readOnly} />,
  },
  {
    id: 3,
    title: "Revisão e Envio",
    icon: <Send className="w-5 h-5" />,
    getComponent: (readOnly) => <ReviewStep />,
  },
];

export default function DevWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [projectStatus, setProjectStatus] = useState<
    "DRAFT" | "PENDING" | "DONE"
  >("DRAFT");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Buscar informações do projeto ao carregar
  useEffect(() => {
    const fetchProject = async () => {
      if (!projectId) return;

      setIsLoading(true);
      setError(null);

      try {
        const response = await validationService.getProjects();
        const project = response.projects.find((p) => p.id === projectId);

        if (project) {
          setProjectStatus(project.status);
        }
      } catch (err: any) {
        setError(err.message || "Erro ao carregar projeto");
      } finally {
        setIsLoading(false);
      }
    };

    fetchProject();
  }, [projectId]);

  // Handler para enviar para validação
  const handleSubmit = async () => {
    if (!projectId) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const updatedProject = await validationService.submitProject(projectId);
      setProjectStatus(updatedProject.status);
      alert("✅ Projeto enviado para a fila de análise!");
    } catch (err: any) {
      setError(err.message || "Erro ao enviar projeto");
      alert(`❌ ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handler para cancelar envio
  const handleCancel = async () => {
    if (!projectId) return;

    const confirmCancel = window.confirm(
      "Tem certeza que deseja cancelar o envio?\n\n" +
        "Isso vai retirar o projeto da fila de prioridade do administrador e permitir que você edite novamente."
    );

    if (!confirmCancel) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const updatedProject = await validationService.cancelProject(projectId);
      setProjectStatus(updatedProject.status);
      alert("✅ Envio cancelado. Você pode editar o projeto novamente.");
    } catch (err: any) {
      setError(err.message || "Erro ao cancelar envio");
      alert(`❌ ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Última etapa - enviar para validação
      handleSubmit();
    }
  };

  const isLastStep = currentStep === steps.length - 1;
  const isDraft = projectStatus === "DRAFT";
  const isPending = projectStatus === "PENDING";
  const isDone = projectStatus === "DONE";

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm mb-6">
        <Link
          to="/validation"
          className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
        >
          Dashboard
        </Link>
        <ChevronRight className="w-4 h-4 text-gray-400 dark:text-gray-600" />
        <span className="text-gray-900 dark:text-white font-medium">
          Projeto #{projectId}
        </span>
      </nav>

      {/* Banner de Status - PENDING_REVIEW */}
      {isPending && (
        <div className="mb-6 bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 dark:border-yellow-600 p-4 rounded-card">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-yellow-800 dark:text-yellow-300">
                Projeto em Análise
              </h3>
              <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                Este projeto está na fila de análise do time de dados. Para
                realizar alterações, cancele o envio usando o botão abaixo.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Banner de Status - DONE */}
      {isDone && (
        <div className="mb-6 bg-green-50 dark:bg-green-900/20 border-l-4 border-green-400 dark:border-green-600 p-4 rounded-card">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-green-800 dark:text-green-300">
                Projeto Publicado
              </h3>
              <p className="text-sm text-green-700 dark:text-green-400 mt-1">
                Este projeto foi aprovado e publicado. Não é possível realizar
                alterações.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Card Principal */}
      <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800">
        {/* Stepper - Navegação Horizontal */}
        <div className="border-b border-gray-200 dark:border-gray-800">
          <div className="flex">
            {steps.map((step, index) => (
              <button
                key={step.id}
                onClick={() => setCurrentStep(index)}
                className={`
                    flex-1 flex items-center justify-center gap-3 px-6 py-4 
                    border-b-2 transition-all duration-200
                    ${
                      currentStep === index
                        ? "border-sky-600 text-sky-600 bg-sky-50 dark:bg-sky-900/20"
                        : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                    }
                  `}
              >
                <span
                  className={
                    currentStep === index
                      ? "text-sky-600"
                      : "text-gray-400 dark:text-gray-600"
                  }
                >
                  {step.icon}
                </span>
                <span className="font-medium text-sm hidden sm:inline">
                  {step.title}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Conteúdo Dinâmico da Etapa Atual */}
        <div className="min-h-[400px]">
          {steps[currentStep].getComponent(!isDraft)}
        </div>

        {/* Footer - Barra de Ação */}
        <div className="border-t border-gray-200 dark:border-gray-800 px-6 py-4 bg-gray-50 dark:bg-gray-800 rounded-b-card">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Etapa {currentStep + 1} de {steps.length}
              {isPending && (
                <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300">
                  Em Análise
                </span>
              )}
              {isDone && (
                <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
                  Publicado
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              {currentStep > 0 && isDraft && (
                <button
                  onClick={() => setCurrentStep(currentStep - 1)}
                  className="btn-secondary"
                  disabled={isSubmitting}
                >
                  Voltar
                </button>
              )}

              {/* Botão de Cancelar Envio (PENDING -> DRAFT) */}
              {isPending && (
                <button
                  onClick={handleCancel}
                  disabled={isSubmitting}
                  className="bg-yellow-600 text-white px-6 py-2.5 rounded-button font-medium 
                             shadow-soft hover:bg-yellow-700 hover:shadow-soft-md 
                             transition-all duration-200 active:scale-95 disabled:opacity-50
                             disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Cancelando...
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4" />
                      Cancelar Envio e Voltar a Editar
                    </>
                  )}
                </button>
              )}

              {/* Botão de Avançar/Enviar (somente DRAFT) */}
              {isDraft && (
                <button
                  onClick={handleNextStep}
                  disabled={isSubmitting}
                  className="bg-green-600 text-white px-6 py-2.5 rounded-button font-medium 
                             shadow-soft hover:bg-green-700 hover:shadow-soft-md 
                             transition-all duration-200 active:scale-95 disabled:opacity-50
                             disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      {isLastStep
                        ? "Enviar para Validação"
                        : "Avançar para Próxima Etapa"}
                    </>
                  )}
                </button>
              )}

              {/* Mensagem para projetos publicados */}
              {isDone && (
                <div className="text-sm text-green-700 dark:text-green-300 font-medium">
                  ✓ Projeto Finalizado
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
