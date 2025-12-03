import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronRight, Eye, TableProperties, Wand2, Send } from "lucide-react";
import ViewStep from "./steps/ViewStep";
import ColumnsStep from "./steps/ColumnsStep";
import DataStep from "./steps/DataStep";
import ReviewStep from "./steps/ReviewStep";

interface Step {
  id: number;
  title: string;
  icon: React.ReactNode;
  component: React.ReactNode;
}

const steps: Step[] = [
  {
    id: 0,
    title: "Visualização",
    icon: <Eye className="w-5 h-5" />,
    component: <ViewStep />,
  },
  {
    id: 1,
    title: "Tratamento de Estrutura",
    icon: <TableProperties className="w-5 h-5" />,
    component: <ColumnsStep />,
  },
  {
    id: 2,
    title: "Tratamento de Dados",
    icon: <Wand2 className="w-5 h-5" />,
    component: <DataStep />,
  },
  {
    id: 3,
    title: "Revisão e Envio",
    icon: <Send className="w-5 h-5" />,
    component: <ReviewStep />,
  },
];

export default function DevWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const [currentStep, setCurrentStep] = useState(0);

  const handleNextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Última etapa - enviar para validação
      console.log("Enviando para validação...");
      alert("Projeto enviado para validação!");
    }
  };

  const isLastStep = currentStep === steps.length - 1;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header com Breadcrumb */}
      <header className="bg-white border-b border-gray-200 shadow-soft">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <nav className="flex items-center gap-2 text-sm mb-2">
            <Link
              to="/validation"
              className="text-gray-500 hover:text-gray-700 transition-colors"
            >
              Dashboard
            </Link>
            <ChevronRight className="w-4 h-4 text-gray-400" />
            <span className="text-gray-900 font-medium">
              Projeto #{projectId}
            </span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900 tracking-wide">
            Workspace de Validação
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Ambiente de limpeza e validação de dados
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Card Principal */}
        <div className="bg-white rounded-card shadow-soft border border-gray-100">
          {/* Stepper - Navegação Horizontal */}
          <div className="border-b border-gray-200">
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
                        ? "border-sky-600 text-sky-600 bg-sky-50"
                        : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                    }
                  `}
                >
                  <span
                    className={
                      currentStep === index ? "text-sky-600" : "text-gray-400"
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
          <div className="min-h-[400px]">{steps[currentStep].component}</div>

          {/* Footer - Barra de Ação */}
          <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 rounded-b-card">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Etapa {currentStep + 1} de {steps.length}
              </div>
              <div className="flex items-center gap-3">
                {currentStep > 0 && (
                  <button
                    onClick={() => setCurrentStep(currentStep - 1)}
                    className="btn-secondary"
                  >
                    Voltar
                  </button>
                )}
                <button
                  onClick={handleNextStep}
                  className="bg-green-600 text-white px-6 py-2.5 rounded-button font-medium 
                           shadow-soft hover:bg-green-700 hover:shadow-soft-md 
                           transition-all duration-200 active:scale-95"
                >
                  {isLastStep
                    ? "Enviar para Validação"
                    : "Avançar para Próxima Etapa"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
