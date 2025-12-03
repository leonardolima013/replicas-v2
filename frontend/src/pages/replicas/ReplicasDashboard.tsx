import { useState, useEffect } from "react";
import {
  Database,
  Copy,
  CheckCircle,
  Loader2,
  AlertCircle,
  Server,
  Trash2,
} from "lucide-react";
import * as replicasService from "../../services/replicasService";
import { getCurrentUser } from "../../services/authService";

export default function ReplicasDashboard() {
  const [replica, setReplica] =
    useState<replicasService.MyReplicaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dbPassword, setDbPassword] = useState("");
  const [copied, setCopied] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const currentUser = getCurrentUser();

  // Buscar réplica ao carregar componente
  useEffect(() => {
    fetchReplica();
  }, []);

  const fetchReplica = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await replicasService.getMyReplica();
      setReplica(data);
    } catch (err: any) {
      console.error("Erro ao buscar réplica:", err);
      setError(null); // Não mostrar erro se não encontrar réplica
    } finally {
      setLoading(false);
    }
  };

  const handleCreateReplica = async () => {
    if (!dbPassword) {
      setError("Por favor, defina uma senha para o banco de dados.");
      return;
    }

    try {
      setCreating(true);
      setError(null);
      const response = await replicasService.createReplica(dbPassword);
      setReplica(response.details);
      setDbPassword(""); // Limpar senha
    } catch (err: any) {
      setError(err.message || "Erro ao criar réplica. Tente novamente.");
    } finally {
      setCreating(false);
    }
  };

  const copyToClipboard = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSSHCommand = () => {
    if (!replica) return "";
    return `ssh -L 5432:localhost:${replica.port} user@localhost`;
  };

  const handleDeleteReplica = async () => {
    if (!currentUser?.usuario) return;

    const confirmDelete = window.confirm(
      `Tem certeza que deseja deletar sua réplica?\n\nContainer: ${replica?.name}\nDatabase: ${replica?.database_name}\n\nEsta ação não pode ser desfeita!`
    );

    if (!confirmDelete) return;

    try {
      setDeleting(true);
      setError(null);
      await replicasService.deleteUserReplica(currentUser.usuario);
      setReplica(null); // Limpar estado
      setDbPassword(""); // Limpar senha
    } catch (err: any) {
      setError(err.message || "Erro ao deletar réplica. Tente novamente.");
    } finally {
      setDeleting(false);
    }
  };

  // Estado de Loading inicial
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Carregando informações...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-soft">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-wide">
                Minha Réplica PostgreSQL
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Banco de dados isolado para desenvolvimento
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">
                Usuário:{" "}
                <span className="font-semibold text-gray-900">
                  {currentUser?.usuario}
                </span>
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Estado: Sem Réplica */}
        {!replica && !creating && (
          <div className="max-w-3xl mx-auto">
            <div className="card text-center py-16">
              {/* Ícone */}
              <div className="flex justify-center mb-6">
                <div className="bg-gray-100 rounded-full p-8">
                  <Database className="w-24 h-24 text-gray-300" />
                </div>
              </div>

              {/* Título */}
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Você ainda não possui uma réplica
              </h2>
              <p className="text-gray-600 mb-8 max-w-md mx-auto leading-relaxed">
                Crie seu banco de dados PostgreSQL isolado para desenvolvimento.
                Você terá acesso exclusivo e poderá usar para testes locais.
              </p>

              {/* Mensagem de erro */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-button p-4 mb-6 max-w-md mx-auto flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700 text-left">{error}</p>
                </div>
              )}

              {/* Input de senha */}
              <div className="max-w-md mx-auto mb-6">
                <label
                  htmlFor="dbPassword"
                  className="block text-sm font-medium text-gray-700 mb-2 text-left"
                >
                  Defina uma senha para o banco de dados
                </label>
                <input
                  id="dbPassword"
                  type="password"
                  value={dbPassword}
                  onChange={(e) => setDbPassword(e.target.value)}
                  className="input-base w-full"
                  placeholder="Digite uma senha"
                  onKeyDown={(e) => e.key === "Enter" && handleCreateReplica()}
                />
                <p className="text-xs text-gray-500 mt-2 text-left">
                  Esta será a senha para acessar o banco de dados PostgreSQL
                </p>
              </div>

              {/* Botão Criar */}
              <button
                onClick={handleCreateReplica}
                className="btn-primary px-8 py-3 text-lg"
                disabled={!dbPassword}
              >
                <Database className="w-5 h-5 inline mr-2" />
                Iniciar Minha Réplica
              </button>
            </div>
          </div>
        )}

        {/* Estado: Criando (Loading) */}
        {creating && (
          <div className="max-w-3xl mx-auto">
            <div className="card text-center py-16">
              <Loader2 className="w-16 h-16 text-primary-500 animate-spin mx-auto mb-6" />
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Provisionando banco isolado...
              </h2>
              <p className="text-gray-600 max-w-md mx-auto leading-relaxed">
                Estamos criando seu container PostgreSQL. Isso pode levar alguns
                segundos.
              </p>
              <div className="mt-8 flex justify-center gap-2">
                <div
                  className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"
                  style={{ animationDelay: "0ms" }}
                ></div>
                <div
                  className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                ></div>
                <div
                  className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"
                  style={{ animationDelay: "300ms" }}
                ></div>
              </div>
            </div>
          </div>
        )}

        {/* Estado: Réplica Rodando */}
        {replica && !creating && (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Card de Status */}
            <div className="bg-green-50 border-2 border-green-200 rounded-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
                <div>
                  <h2 className="text-xl font-bold text-green-900">
                    Réplica Ativa
                  </h2>
                  <p className="text-sm text-green-700">
                    Container:{" "}
                    <span className="font-mono font-semibold">
                      {replica.name}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            {/* Card de Detalhes de Conexão */}
            <div className="card">
              <div className="flex items-center gap-3 mb-6">
                <Server className="w-6 h-6 text-primary-500" />
                <h3 className="text-xl font-bold text-gray-900">
                  Detalhes de Conexão
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Host */}
                <div className="bg-gray-50 rounded-button p-4">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wider block mb-2">
                    Host
                  </label>
                  <div className="flex items-center justify-between">
                    <code className="text-sm font-mono text-gray-900">
                      localhost
                    </code>
                    <button
                      onClick={() => copyToClipboard("localhost", "host")}
                      className="text-gray-400 hover:text-primary-500 transition-colors"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Porta */}
                <div className="bg-primary-50 border-2 border-primary-200 rounded-button p-4">
                  <label className="text-xs font-medium text-primary-700 uppercase tracking-wider block mb-2">
                    Porta (Importante!)
                  </label>
                  <div className="flex items-center justify-between">
                    <code className="text-lg font-mono font-bold text-primary-600">
                      {replica.port}
                    </code>
                    <button
                      onClick={() =>
                        copyToClipboard(replica.port.toString(), "port")
                      }
                      className="text-primary-400 hover:text-primary-600 transition-colors"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Database */}
                <div className="bg-gray-50 rounded-button p-4">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wider block mb-2">
                    Database
                  </label>
                  <div className="flex items-center justify-between">
                    <code className="text-sm font-mono text-gray-900">
                      {replica.database_name}
                    </code>
                    <button
                      onClick={() =>
                        copyToClipboard(replica.database_name, "database")
                      }
                      className="text-gray-400 hover:text-primary-500 transition-colors"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Username */}
                <div className="bg-gray-50 rounded-button p-4">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wider block mb-2">
                    Usuário
                  </label>
                  <div className="flex items-center justify-between">
                    <code className="text-sm font-mono text-gray-900">
                      {replica.username}
                    </code>
                    <button
                      onClick={() =>
                        copyToClipboard(replica.username, "username")
                      }
                      className="text-gray-400 hover:text-primary-500 transition-colors"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* SSH Tunnel Command */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium text-gray-700">
                    Comando SSH Tunnel
                  </label>
                  {copied && (
                    <span className="text-xs text-green-600 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Copiado!
                    </span>
                  )}
                </div>
                <div className="bg-gray-900 rounded-button p-4 flex items-center justify-between">
                  <code className="text-sm font-mono text-green-400 flex-1">
                    {getSSHCommand()}
                  </code>
                  <button
                    onClick={() => copyToClipboard(getSSHCommand(), "ssh")}
                    className="ml-4 btn-secondary py-2 px-4 text-xs"
                  >
                    <Copy className="w-4 h-4 inline mr-1" />
                    Copiar
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Use este comando para criar um túnel SSH e conectar ao banco
                  localmente na porta 5432
                </p>
              </div>

              {/* Botão de Deletar */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <button
                  onClick={handleDeleteReplica}
                  disabled={deleting}
                  className="btn-secondary text-red-600 border-red-300 hover:bg-red-50 hover:border-red-400 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {deleting ? (
                    <>
                      <Loader2 className="w-4 h-4 inline mr-2 animate-spin" />
                      Deletando réplica...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4 inline mr-2" />
                      Deletar Réplica
                    </>
                  )}
                </button>
                <p className="text-xs text-gray-500 mt-2 text-center">
                  Atenção: Esta ação irá remover permanentemente o container e
                  todos os dados
                </p>
              </div>
            </div>

            {/* Informações Adicionais */}
            <div className="card bg-sky-50 border border-sky-200">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-sky-600" />
                Como Conectar
              </h4>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex gap-2">
                  <span className="text-sky-600 font-bold">1.</span>
                  <span>Use o comando SSH acima para criar o túnel</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-sky-600 font-bold">2.</span>
                  <span>
                    Conecte seu cliente PostgreSQL em{" "}
                    <code className="bg-sky-100 px-1 rounded">
                      localhost:5432
                    </code>
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-sky-600 font-bold">3.</span>
                  <span>
                    Use database{" "}
                    <code className="bg-sky-100 px-1 rounded">
                      {replica.database_name}
                    </code>{" "}
                    com usuário{" "}
                    <code className="bg-sky-100 px-1 rounded">
                      {replica.username}
                    </code>
                  </span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
