import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { User, Lock, AlertCircle, Loader2 } from "lucide-react";
import * as authService from "../services/authService";

export default function Login() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      // Chamar serviço de autenticação
      const user = await authService.login(
        formData.username,
        formData.password
      );

      console.log("Login bem-sucedido:", user);

      // Redirecionar para o dashboard de serviços
      navigate("/services");
    } catch (err: any) {
      // Exibir mensagem de erro
      setError(err.message || "Erro ao fazer login. Tente novamente.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    // Limpar erro ao digitar
    if (error) setError(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="card max-w-md w-full p-8 space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-gray-900 tracking-wide">
            Bem-vindo
          </h1>
          <p className="text-gray-500 text-sm">Faça login para continuar</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Mensagem de Erro */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-button p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Username/Email Input */}
          <div className="space-y-2">
            <label
              htmlFor="username"
              className="block text-sm font-medium text-gray-700"
            >
              Usuário/Email
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="username"
                name="username"
                type="text"
                required
                value={formData.username}
                onChange={handleChange}
                className="input-base pl-10 w-full"
                placeholder="Digite seu usuário ou email"
              />
            </div>
          </div>

          {/* Password Input */}
          <div className="space-y-2">
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700"
            >
              Senha
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                className="input-base pl-10 w-full"
                placeholder="Digite sua senha"
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                Entrando...
              </span>
            ) : (
              "Entrar"
            )}
          </button>
        </form>

        {/* Footer opcional */}
        <div className="text-center">
          <a
            href="#"
            className="text-sm text-sky-500 hover:text-sky-600 transition-colors"
          >
            Esqueceu sua senha?
          </a>
        </div>
      </div>
    </div>
  );
}
