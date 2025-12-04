import { useState, useEffect } from "react";

type Theme = "light" | "dark";

interface UseThemeReturn {
  isDarkMode: boolean;
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

/**
 * Hook personalizado para gerir o tema da aplicação (claro/escuro)
 *
 * Funcionalidades:
 * - Persiste a preferência no localStorage
 * - Detecta preferência do sistema operativo se não houver preferência guardada
 * - Adiciona/remove a classe 'dark' na tag <html>
 *
 * @returns {UseThemeReturn} Objeto com estado e funções de controle do tema
 */
export function useTheme(): UseThemeReturn {
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

  return {
    isDarkMode: theme === "dark",
    theme,
    toggleTheme,
    setTheme,
  };
}
