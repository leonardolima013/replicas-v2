import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";

type Theme = "light" | "dark";

interface ThemeContextType {
  isDarkMode: boolean;
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
}

/**
 * Provider do contexto de tema
 * Envolva sua aplicação com este componente para ter acesso ao tema globalmente
 */
export function ThemeProvider({ children }: ThemeProviderProps) {
  // Função para obter o tema inicial
  const getInitialTheme = (): Theme => {
    // 1. Verificar localStorage
    const savedTheme = localStorage.getItem("theme") as Theme | null;
    if (savedTheme === "light" || savedTheme === "dark") {
      return savedTheme;
    }

    // 2. Verificar preferência do sistema operativo
    if (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    ) {
      return "dark";
    }

    // 3. Valor padrão
    return "light";
  };

  const [theme, setThemeState] = useState<Theme>(getInitialTheme);

  // Aplicar tema ao DOM e localStorage
  useEffect(() => {
    const root = document.documentElement;

    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }

    // Guardar no localStorage
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Ouvir mudanças na preferência do sistema operativo
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = (e: MediaQueryListEvent) => {
      // Só atualizar se não houver preferência manual guardada
      const savedTheme = localStorage.getItem("theme");
      if (!savedTheme) {
        setThemeState(e.matches ? "dark" : "light");
      }
    };

    // Adicionar listener (compatível com browsers antigos)
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handleChange);
    } else {
      // Fallback para browsers antigos
      mediaQuery.addListener(handleChange);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener("change", handleChange);
      } else {
        mediaQuery.removeListener(handleChange);
      }
    };
  }, []);

  // Função para alternar entre claro e escuro
  const toggleTheme = () => {
    setThemeState((prevTheme) => (prevTheme === "light" ? "dark" : "light"));
  };

  // Função para definir tema específico
  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  const value: ThemeContextType = {
    isDarkMode: theme === "dark",
    theme,
    toggleTheme,
    setTheme,
  };

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

/**
 * Hook para consumir o contexto de tema
 * Deve ser usado dentro de um componente que está dentro do ThemeProvider
 *
 * @throws {Error} Se usado fora do ThemeProvider
 * @returns {ThemeContextType} Objeto com estado e funções de controle do tema
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { isDarkMode, toggleTheme } = useTheme();
 *
 *   return (
 *     <button onClick={toggleTheme}>
 *       {isDarkMode ? '🌙 Modo Escuro' : '☀️ Modo Claro'}
 *     </button>
 *   );
 * }
 * ```
 */
export function useThemeContext(): ThemeContextType {
  const context = useContext(ThemeContext);

  if (context === undefined) {
    throw new Error(
      "useThemeContext deve ser usado dentro de um ThemeProvider"
    );
  }

  return context;
}
