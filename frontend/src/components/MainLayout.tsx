import { useState, useEffect } from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import {
  ChevronLeft,
  Menu,
  Database,
  FileCheck,
  Users,
  ShieldCheck,
  Settings,
  LogOut,
  User,
} from "lucide-react";
import { getCurrentUser, logout } from "../services/authService";

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: React.ReactNode;
}

// Links de navegação para DEV
const devNavItems: NavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    path: "/services",
    icon: <Database className="w-5 h-5" />,
  },
  {
    id: "replicas",
    label: "Minha Réplica",
    path: "/replicas",
    icon: <Database className="w-5 h-5" />,
  },
  {
    id: "validation",
    label: "Data Validation",
    path: "/validation",
    icon: <FileCheck className="w-5 h-5" />,
  },
];

// Links de navegação para ADM
const adminNavItems: NavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    path: "/services",
    icon: <Database className="w-5 h-5" />,
  },
  {
    id: "users",
    label: "Gestão de Usuários",
    path: "/admin/users",
    icon: <Users className="w-5 h-5" />,
  },
  {
    id: "validation-approval",
    label: "Aprovação de Validações",
    path: "/admin/validation",
    icon: <ShieldCheck className="w-5 h-5" />,
  },
  {
    id: "replicas-management",
    label: "Gestão de Réplicas",
    path: "/admin/replicas",
    icon: <Settings className="w-5 h-5" />,
  },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [currentUser, setCurrentUser] = useState(() => getCurrentUser());

  useEffect(() => {
    const user = getCurrentUser();
    setCurrentUser(user);
  }, []);

  const userRole: "dev" | "adm" = (currentUser?.role as "dev" | "adm") || "dev";
  const navItems = userRole === "adm" ? adminNavItems : devNavItems;

  const handleLogout = () => {
    const confirmed = window.confirm("Tem certeza que deseja sair?");
    if (confirmed) {
      logout();
      navigate("/login");
    }
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // Verificar se o link está ativo
  const isActiveLink = (path: string) => {
    return (
      location.pathname === path || location.pathname.startsWith(path + "/")
    );
  };

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950">
      {/* Sidebar */}
      <aside
        className={`
          ${isSidebarOpen ? "w-56" : "w-16"}
          bg-zinc-900 border-r border-zinc-800
          transition-all duration-300 ease-in-out
          flex flex-col
        `}
      >
        {/* Logo + Toggle */}
        <div className="h-14 flex items-center justify-between px-3 border-b border-zinc-800">
          {isSidebarOpen ? (
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-sky-400" />
              <span className="font-semibold text-base text-white">
                Réplicas
              </span>
            </div>
          ) : (
            <Database className="w-5 h-5 text-sky-400 mx-auto" />
          )}

          <button
            onClick={toggleSidebar}
            className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 transition-colors"
            title={isSidebarOpen ? "Recolher sidebar" : "Expandir sidebar"}
          >
            {isSidebarOpen ? (
              <ChevronLeft className="w-4 h-4" />
            ) : (
              <Menu className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navegação */}
        <nav className="flex-1 overflow-y-auto py-3 px-2">
          <ul className="space-y-0.5">
            {navItems.map((item) => {
              const isActive = isActiveLink(item.path);
              return (
                <li key={item.id}>
                  <Link
                    to={item.path}
                    className={`
                      flex items-center gap-2.5 px-2.5 py-2 rounded-lg
                      transition-all duration-200
                      ${
                        isActive
                          ? "bg-sky-500/10 text-sky-400 font-medium border-r-2 border-sky-500"
                          : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
                      }
                      ${!isSidebarOpen && "justify-center"}
                    `}
                    title={!isSidebarOpen ? item.label : undefined}
                  >
                    <span
                      className={isActive ? "text-sky-400" : "text-zinc-500"}
                    >
                      {item.icon}
                    </span>
                    {isSidebarOpen && (
                      <span className="text-sm">{item.label}</span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Rodapé - User Info + Logout */}
        <div className="border-t border-zinc-800 p-3">
          {isSidebarOpen ? (
            <div className="space-y-2">
              {/* User Info */}
              <div className="flex items-center gap-2 px-1.5">
                <div className="w-8 h-8 rounded-full bg-sky-500/20 flex items-center justify-center">
                  <User className="w-4 h-4 text-sky-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-white truncate">
                    {currentUser?.usuario || "Usuário"}
                  </p>
                  <p className="text-[10px] text-zinc-400 uppercase">
                    {userRole === "adm" ? "Admin" : "Dev"}
                  </p>
                </div>
              </div>

              {/* Logout Button */}
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg
                         text-red-400 hover:bg-red-500/10
                         transition-colors text-xs font-medium"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sair
              </button>
            </div>
          ) : (
            <button
              onClick={handleLogout}
              className="w-full p-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
              title="Sair"
            >
              <LogOut className="w-4 h-4 mx-auto" />
            </button>
          )}
        </div>
      </aside>

      {/* Área de Conteúdo */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-14 bg-zinc-900/50 backdrop-blur-md border-b border-zinc-800 flex items-center justify-between px-6">
          <div>
            <h1 className="text-lg font-semibold text-white">Réplicas v2</h1>
            <p className="text-xs text-zinc-400">Sistema de Gestão de Dados</p>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
