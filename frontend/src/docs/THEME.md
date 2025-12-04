# Sistema de Tema (Dark Mode)

Este diretório contém a implementação do sistema de tema claro/escuro da aplicação.

## 📁 Estrutura

```
src/
├── hooks/
│   └── useTheme.ts          # Hook standalone para gerenciar tema
├── contexts/
│   └── ThemeContext.tsx     # Context + Provider para uso global
└── components/
    ├── ThemeToggle.tsx      # Botão toggle (usa hook)
    └── ThemeToggleContext.tsx # Botão toggle (usa context)
```

## 🎯 Duas Formas de Uso

### Opção 1: Hook Standalone (useTheme)

**Quando usar**: Componentes isolados que não precisam compartilhar estado de tema.

```tsx
import { useTheme } from "./hooks/useTheme";

function MyComponent() {
  const { isDarkMode, theme, toggleTheme, setTheme } = useTheme();

  return (
    <div>
      <p>Tema atual: {theme}</p>
      <button onClick={toggleTheme}>
        {isDarkMode ? "🌙 Escuro" : "☀️ Claro"}
      </button>
      <button onClick={() => setTheme("dark")}>Forçar Escuro</button>
    </div>
  );
}
```

### Opção 2: Context Global (ThemeContext) ⭐ RECOMENDADO

**Quando usar**: Para compartilhar o estado do tema em toda a aplicação.

**1. Envolver a aplicação com o Provider:**

```tsx
// App.tsx ou main.tsx
import { ThemeProvider } from "./contexts/ThemeContext";

function App() {
  return (
    <ThemeProvider>
      <YourApp />
    </ThemeProvider>
  );
}
```

**2. Usar em qualquer componente:**

```tsx
import { useThemeContext } from "./contexts/ThemeContext";

function Header() {
  const { isDarkMode, toggleTheme } = useThemeContext();

  return (
    <header>
      <button onClick={toggleTheme}>{isDarkMode ? "🌙" : "☀️"}</button>
    </header>
  );
}
```

## 🔧 API Completa

### Retorno do Hook/Context

```typescript
{
  isDarkMode: boolean;      // true se tema é escuro
  theme: 'light' | 'dark';  // tema atual
  toggleTheme: () => void;  // alterna entre claro/escuro
  setTheme: (theme: 'light' | 'dark') => void; // define tema específico
}
```

## ✨ Funcionalidades

### ✅ Persistência no localStorage

- Chave: `'theme'`
- Valores: `'light'` | `'dark'`
- Mantém preferência entre sessões

### ✅ Detecção do Sistema Operativo

- Detecta preferência automática se não houver tema salvo
- Usa: `window.matchMedia('(prefers-color-scheme: dark)')`

### ✅ Atualização Automática do DOM

- Adiciona/remove classe `dark` na tag `<html>`
- Permite usar classes Tailwind `dark:` em toda aplicação

### ✅ Listener de Mudanças do SO

- Reage a mudanças na preferência do sistema
- Só atualiza se usuário não tiver escolha manual

## 🎨 Usar com Tailwind CSS

O sistema adiciona a classe `dark` no elemento root, permitindo usar:

```tsx
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  Conteúdo que muda com o tema
</div>
```

**Configurar Tailwind:**

```js
// tailwind.config.js
export default {
  darkMode: "class", // ⚠️ IMPORTANTE: usar 'class' não 'media'
  // ... resto da config
};
```

## 📦 Componentes Prontos

### ThemeToggle (Hook)

```tsx
import ThemeToggle from "./components/ThemeToggle";

<ThemeToggle />;
```

### ThemeToggleContext (Context)

```tsx
import ThemeToggleContext from "./components/ThemeToggleContext";

// Deve estar dentro do ThemeProvider
<ThemeToggleContext />;
```

## 🚀 Exemplo Completo de Integração

```tsx
// main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ThemeProvider } from "./contexts/ThemeContext";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
```

```tsx
// Header.tsx
import { useThemeContext } from "./contexts/ThemeContext";
import { Moon, Sun } from "lucide-react";

export function Header() {
  const { isDarkMode, toggleTheme } = useThemeContext();

  return (
    <header className="bg-white dark:bg-gray-800 shadow">
      <div className="flex justify-between items-center p-4">
        <h1 className="text-gray-900 dark:text-white">Minha App</h1>

        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 
                     hover:bg-gray-300 dark:hover:bg-gray-600"
        >
          {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>
    </header>
  );
}
```

## 🔍 Debugging

Para verificar se está funcionando:

1. Abrir DevTools Console
2. Executar: `localStorage.getItem('theme')`
3. Inspecionar `<html>` - deve ter classe `dark` quando ativo
4. Mudar preferência do SO e verificar se atualiza

## 🎯 Melhores Práticas

✅ **Use ThemeContext** para apps completas  
✅ **Use useTheme** para componentes isolados/demos  
✅ **Sempre configure** `darkMode: 'class'` no Tailwind  
✅ **Teste** com preferência do SO e manual  
❌ **Não misture** hook e context no mesmo componente
