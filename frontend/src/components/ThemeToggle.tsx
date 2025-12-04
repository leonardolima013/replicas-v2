import { Moon, Sun } from "lucide-react";
import { useTheme } from "../hooks/useTheme";

/**
 * Componente de botão para alternar entre modo claro e escuro
 * Pode ser usado standalone com o hook useTheme
 */
export default function ThemeToggle() {
  const { isDarkMode, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 
                 transition-colors duration-200 flex items-center justify-center"
      title={isDarkMode ? "Mudar para modo claro" : "Mudar para modo escuro"}
      aria-label={
        isDarkMode ? "Mudar para modo claro" : "Mudar para modo escuro"
      }
    >
      {isDarkMode ? (
        <Sun className="w-5 h-5 text-yellow-400" />
      ) : (
        <Moon className="w-5 h-5 text-gray-700" />
      )}
    </button>
  );
}
