import { useState, useEffect } from "react";
import { RefreshCw, Trash2, AlertTriangle, Database, X } from "lucide-react";
import * as replicasService from "../../services/replicasService";

interface ConfirmDeleteAllModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  totalReplicas: number;
}

function ConfirmDeleteAllModal({
  isOpen,
  onClose,
  onConfirm,
  totalReplicas,
}: ConfirmDeleteAllModalProps) {
  const [confirmText, setConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const handleConfirm = async () => {
    setIsDeleting(true);
    try {
      await onConfirm();
      setConfirmText("");
      onClose();
    } finally {
      setIsDeleting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft-lg max-w-md w-full mx-4 p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                Ação Destrutiva
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Esta ação é irreversível
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="mb-6">
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
            Você está prestes a deletar{" "}
            <span className="font-bold text-red-600 dark:text-red-400">
              {totalReplicas} container(s)
            </span>{" "}
            de banco de dados. Todos os dados serão perdidos permanentemente.
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
            Para confirmar, digite{" "}
            <span className="font-mono font-bold text-red-600 dark:text-red-400">
              DELETAR
            </span>{" "}
            no campo abaixo:
          </p>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Digite DELETAR para confirmar"
            className="input-base w-full"
            disabled={isDeleting}
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="btn-secondary"
            disabled={isDeleting}
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={confirmText !== "DELETAR" || isDeleting}
            className="bg-red-600 text-white px-4 py-2 rounded-button font-medium 
                     shadow-soft hover:bg-red-700 hover:shadow-soft-md 
                     transition-all duration-200 disabled:opacity-50 
                     disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isDeleting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Deletando...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                Confirmar Exclusão
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminReplicasDashboard() {
  const [replicas, setReplicas] = useState<replicasService.AdminReplicaItem[]>(
    []
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);

  const fetchReplicas = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await replicasService.listAllReplicas();
      setReplicas(response.replicas);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar réplicas");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReplicas();
  }, []);

  const handleDeleteSingle = async (username: string, containerId: string) => {
    const confirmed = window.confirm(
      `Tem certeza que deseja derrubar o banco de ${username}?\n\nContainer: ${containerId}`
    );

    if (!confirmed) return;

    setDeletingIds((prev) => new Set(prev).add(containerId));

    try {
      await replicasService.deleteUserReplica(username);
      setReplicas((prev) => prev.filter((r) => r.container_id !== containerId));
      alert(`✅ Réplica de ${username} deletada com sucesso`);
    } catch (err: any) {
      alert(`❌ ${err.message}`);
    } finally {
      setDeletingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(containerId);
        return newSet;
      });
    }
  };

  const handleDeleteAll = async () => {
    try {
      await replicasService.deleteAllReplicas();
      setReplicas([]);
      alert(`✅ Todas as réplicas foram deletadas com sucesso`);
    } catch (err: any) {
      alert(`❌ ${err.message}`);
    }
  };

  // Loading State
  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <RefreshCw className="w-8 h-8 text-primary-500 dark:text-primary-400 animate-spin" />
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="p-8">
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft p-8 border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-1">
                Erro ao Carregar Réplicas
              </h3>
              <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            </div>
          </div>
          <button onClick={fetchReplicas} className="btn-primary mt-4">
            Tentar Novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header com Botões */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {/* Badge Total */}
          <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-button">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <div className="text-left">
                <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                  Containers Ativos
                </p>
                <p className="text-lg font-bold text-blue-700 dark:text-blue-300">
                  {replicas.length}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Botão de Pânico */}
        <button
          onClick={() => setShowDeleteAllModal(true)}
          disabled={replicas.length === 0}
          className="bg-red-600 text-white px-4 py-2.5 rounded-button font-medium 
                     shadow-soft hover:bg-red-700 hover:shadow-soft-md 
                     transition-all duration-200 disabled:opacity-50 
                     disabled:cursor-not-allowed flex items-center gap-2"
        >
          <AlertTriangle className="w-5 h-5" />
          Excluir TODOS os Bancos
        </button>
      </div>

      {/* Barra de Ações */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Tabela de Monitoramento
        </h2>
        <button
          onClick={fetchReplicas}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Atualizar Lista
        </button>
      </div>

      {/* Tabela */}
      {replicas.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft p-8 border border-gray-200 dark:border-gray-800 text-center py-12">
          <Database className="w-16 h-16 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Nenhuma Réplica Ativa
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Não há containers de banco de dados em execução no momento.
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-card shadow-soft border border-gray-100 dark:border-gray-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Dono
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    ID do Container
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Nome do Banco
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Porta
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Criado
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                {replicas.map((replica, index) => (
                  <tr
                    key={replica.container_id}
                    className={
                      index % 2 === 0
                        ? "bg-white dark:bg-gray-900"
                        : "bg-gray-50 dark:bg-gray-800"
                    }
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-8 w-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                          <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                            {replica.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="ml-3">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {replica.username}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-xs font-mono text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                        {replica.container_id.substring(0, 12)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      {replica.database_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-mono text-gray-700 dark:text-gray-300">
                        {replica.port}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          replica.status === "running"
                            ? "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300"
                        }`}
                      >
                        {replica.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(replica.created).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() =>
                          handleDeleteSingle(
                            replica.username,
                            replica.container_id
                          )
                        }
                        disabled={deletingIds.has(replica.container_id)}
                        className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 disabled:opacity-50 
                                   disabled:cursor-not-allowed inline-flex items-center gap-1"
                        title={`Derrubar banco de ${replica.username}`}
                      >
                        {deletingIds.has(replica.container_id) ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                        Derrubar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal de Confirmação de Exclusão Total */}
      <ConfirmDeleteAllModal
        isOpen={showDeleteAllModal}
        onClose={() => setShowDeleteAllModal(false)}
        onConfirm={handleDeleteAll}
        totalReplicas={replicas.length}
      />
    </div>
  );
}
