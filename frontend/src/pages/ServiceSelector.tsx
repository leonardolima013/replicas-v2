import { Database, FileCheck, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";

// Mock de role do usuário - mude para 'dev' ou 'adm' para testar
const userRole: "dev" | "adm" = "adm";

interface Service {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  path: string;
  allowedRoles: ("dev" | "adm")[];
}

const services: Service[] = [
  {
    id: "replicas",
    title: "Réplicas",
    description: "Gestão de peças e componentes do sistema",
    icon: <Database className="w-16 h-16 text-primary-500" />,
    path: "/replicas",
    allowedRoles: ["dev", "adm"],
  },
  {
    id: "data-validation",
    title: "Data Validation",
    description: "Validação e tratamento de dados importados",
    icon: <FileCheck className="w-16 h-16 text-primary-500" />,
    path: "/validation",
    allowedRoles: ["dev", "adm"],
  },
  {
    id: "user-management",
    title: "Gestão de Usuários",
    description: "Administração de usuários e permissões",
    icon: <Users className="w-16 h-16 text-primary-500" />,
    path: "/users",
    allowedRoles: ["adm"],
  },
];

export default function ServiceSelector() {
  const navigate = useNavigate();

  // Filtrar serviços baseado no role do usuário
  const availableServices = services.filter((service) =>
    service.allowedRoles.includes(userRole)
  );

  const handleServiceClick = (service: Service) => {
    console.log(`Navegando para: ${service.title} (${service.path})`);
    navigate(service.path);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-soft">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-wide">
                Dashboard
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Selecione o serviço que deseja acessar
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">
                Perfil:{" "}
                <span className="font-semibold text-primary-600 uppercase">
                  {userRole}
                </span>
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Grid de serviços */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {availableServices.map((service) => (
            <button
              key={service.id}
              onClick={() => handleServiceClick(service)}
              className="group bg-white rounded-card shadow-soft p-8 border border-gray-100 
                         hover:shadow-soft-md hover:-translate-y-1 hover:border-primary-500 
                         transition-all duration-200 focus:outline-none focus:ring-2 
                         focus:ring-primary-500 focus:ring-offset-2"
            >
              {/* Ícone */}
              <div className="flex justify-center mb-4 group-hover:scale-110 transition-transform duration-200">
                {service.icon}
              </div>

              {/* Título */}
              <h3 className="text-xl font-bold text-gray-900 mb-2 text-center">
                {service.title}
              </h3>

              {/* Descrição */}
              <p className="text-sm text-gray-500 text-center leading-relaxed">
                {service.description}
              </p>

              {/* Indicador de hover */}
              <div className="mt-4 flex justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <span className="text-xs font-medium text-primary-500 uppercase tracking-wider">
                  Acessar →
                </span>
              </div>
            </button>
          ))}
        </div>

        {/* Mensagem caso não haja serviços disponíveis */}
        {availableServices.length === 0 && (
          <div className="card text-center py-12">
            <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Nenhum serviço disponível
            </h3>
            <p className="text-sm text-gray-500">
              Entre em contato com o administrador para obter acesso.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
