import {
  Database,
  FileCheck,
  Users,
  ShieldCheck,
  Settings,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getCurrentUser } from "../services/authService";
import { useEffect, useState } from "react";

interface Service {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  path: string;
}

// Serviços exclusivos para DEV
const devServices: Service[] = [
  {
    id: "my-replica",
    title: "Minha Réplica",
    description: "Acesse e gerencie sua réplica pessoal de dados",
    icon: <Database className="w-16 h-16 text-blue-500" />,
    path: "/replicas",
  },
  {
    id: "data-validation",
    title: "Data Validation",
    description: "Validação e tratamento de dados importados",
    icon: <FileCheck className="w-16 h-16 text-green-500" />,
    path: "/validation",
  },
];

// Serviços exclusivos para ADM
const adminServices: Service[] = [
  {
    id: "user-management",
    title: "Gestão de Usuários",
    description: "Administração de usuários e permissões",
    icon: <Users className="w-16 h-16 text-purple-500" />,
    path: "/admin/users",
  },
  {
    id: "validation-approval",
    title: "Aprovação de Validações",
    description: "Revisar e aprovar projetos de validação de dados",
    icon: <ShieldCheck className="w-16 h-16 text-amber-500" />,
    path: "/admin/validation",
  },
  {
    id: "replicas-management",
    title: "Gestão de Réplicas",
    description: "Gerenciar réplicas de todos os desenvolvedores",
    icon: <Settings className="w-16 h-16 text-sky-500" />,
    path: "/admin/replicas",
  },
];

export default function ServiceSelector() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(() => getCurrentUser());
  const userRole: "dev" | "adm" = (currentUser?.role as "dev" | "adm") || "dev";

  // Atualizar usuário quando componente montar
  useEffect(() => {
    const user = getCurrentUser();
    setCurrentUser(user);
  }, []);

  // Selecionar serviços baseado no role do usuário
  const availableServices = userRole === "adm" ? adminServices : devServices;

  const handleServiceClick = (service: Service) => {
    console.log(`Navegando para: ${service.title} (${service.path})`);
    navigate(service.path);
  };

  return (
    <div className="p-8">
      {/* Grid de serviços */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {availableServices.map((service) => (
          <button
            key={service.id}
            onClick={() => handleServiceClick(service)}
            className="group bg-white dark:bg-gray-900 rounded-card shadow-soft p-8 border border-gray-100 dark:border-gray-800
                         hover:shadow-soft-md hover:-translate-y-1 hover:border-primary-500 dark:hover:border-primary-400
                         transition-all duration-200 focus:outline-none focus:ring-2 
                         focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-950"
          >
            {/* Ícone */}
            <div className="flex justify-center mb-4 group-hover:scale-110 transition-transform duration-200">
              {service.icon}
            </div>

            {/* Título */}
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 text-center">
              {service.title}
            </h3>

            {/* Descrição */}
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center leading-relaxed">
              {service.description}
            </p>

            {/* Indicador de hover */}
            <div className="mt-4 flex justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <span className="text-xs font-medium text-primary-500 dark:text-primary-400 uppercase tracking-wider">
                Acessar →
              </span>
            </div>
          </button>
        ))}
      </div>

      {/* Mensagem caso não haja serviços disponíveis */}
      {availableServices.length === 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft p-8 border border-gray-200 dark:border-gray-800 text-center py-12">
          <Users className="w-16 h-16 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Nenhum serviço disponível
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Entre em contato com o administrador para obter acesso.
          </p>
        </div>
      )}
    </div>
  );
}
