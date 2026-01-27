import { useState, useEffect } from "react";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Database,
  Tag,
  Loader2,
  Settings,
  Upload,
  Server,
  RefreshCw,
  Package,
  AlertCircle,
} from "lucide-react";
import * as validationService from "../../../services/validationService";
import Modal from "../../../components/Modal";
import { useModal } from "../../../hooks/useModal";

interface PublishConfigTabProps {
  projectId: string;
  onPublishSuccess?: () => void;
}

type FieldMode =
  | "ignore"
  | "force_override"
  | "concatenate"
  | "update_if_empty";

interface FieldConfig {
  field: string;
  mode: FieldMode;
  description: string;
}

const FIELD_DESCRIPTIONS: Record<string, string> = {
  name: "Nome da peça",
  ncm: "Código NCM (formato XXXX.XX.XX)",
  barcode: "Código de barras",
  gross_weight: "Peso bruto (kg)",
  net_weight: "Peso líquido (kg)",
  width: "Largura (cm)",
  depth: "Profundidade/Comprimento (cm)",
  height: "Altura (cm)",
  notes: "Especificações/Observações",
  application: "Aplicação da peça",
};

const MODE_LABELS: Record<FieldMode, string> = {
  ignore: "Ignorar",
  force_override: "Substituir",
  concatenate: "Concatenar",
  update_if_empty: "Preencher se vazio",
};

const MODE_DESCRIPTIONS: Record<FieldMode, string> = {
  ignore: "Não atualizar este campo em peças existentes",
  force_override: "Sempre substituir o valor atual pelo novo",
  concatenate: "Juntar novo valor ao existente (com quebra de linha)",
  update_if_empty: "Atualizar apenas se o campo estiver vazio/NULL",
};

// Tipos e configurações para modo de imagens
type ImageMode = "ignore" | "concatenate" | "add_if_empty";

const IMAGE_MODE_LABELS: Record<ImageMode, string> = {
  ignore: "Ignorar",
  concatenate: "Concatenar",
  add_if_empty: "Adicionar se vazio",
};

const IMAGE_MODE_DESCRIPTIONS: Record<ImageMode, string> = {
  ignore: "Nenhuma imagem é adicionada ao banco de dados",
  concatenate: "Peças novas e existentes recebem imagens",
  add_if_empty: "Apenas peças novas ou sem imagens recebem imagens",
};

export default function PublishConfigTab({
  projectId,
  onPublishSuccess,
}: PublishConfigTabProps) {
  const [preview, setPreview] =
    useState<validationService.PublishPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [publishResult, setPublishResult] =
    useState<validationService.PublishResult | null>(null);
  const { modalState, closeModal, showConfirm } = useModal();

  // Configuração de campos
  const [fieldConfigs, setFieldConfigs] = useState<FieldConfig[]>([]);

  // Configuração de imagens
  const [imageMode, setImageMode] = useState<ImageMode>("concatenate");

  useEffect(() => {
    fetchPreview();
  }, [projectId]);

  const fetchPreview = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await validationService.getPublishPreview(projectId);
      setPreview(data);

      // Inicializar configuração de campos com valores padrão
      const initialConfigs: FieldConfig[] = data.available_fields.map(
        (field) => ({
          field,
          mode: "update_if_empty" as FieldMode, // Padrão seguro
          description: FIELD_DESCRIPTIONS[field] || field,
        }),
      );
      setFieldConfigs(initialConfigs);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar preview de publicação");
    } finally {
      setLoading(false);
    }
  };

  const handleFieldModeChange = (field: string, mode: FieldMode) => {
    setFieldConfigs((prev) =>
      prev.map((config) =>
        config.field === field ? { ...config, mode } : config,
      ),
    );
  };

  const handlePublish = async () => {
    if (!preview?.can_publish) return;

    showConfirm(
      `Tem certeza que deseja publicar os dados para o banco de produção?\n\n` +
        `Esta ação irá:\n` +
        `• Inserir ${preview.parts_new.toLocaleString()} novas peças\n` +
        `• Atualizar até ${preview.parts_existing.toLocaleString()} peças existentes\n` +
        `• Criar ${preview.brands_to_create} novas marcas\n\n` +
        `Esta ação NÃO pode ser desfeita!`,
      async () => {
        setPublishing(true);
        setPublishResult(null);

        try {
          // Montar configuração
          const configuration: validationService.PublishConfiguration = {
            force_override: fieldConfigs
              .filter((c) => c.mode === "force_override")
              .map((c) => c.field),
            concatenate: fieldConfigs
              .filter((c) => c.mode === "concatenate")
              .map((c) => c.field),
            update_if_empty: fieldConfigs
              .filter((c) => c.mode === "update_if_empty")
              .map((c) => c.field),
            image_mode: imageMode,
          };

          const request: validationService.PublishRequest = {
            configuration,
          };

          const response = await validationService.executePublish(
            projectId,
            request,
          );
          setPublishResult(response.result);

          if (response.result.success && onPublishSuccess) {
            onPublishSuccess();
          }
        } catch (err: any) {
          setError(err.message || "Erro ao executar publicação");
        } finally {
          setPublishing(false);
        }
      },
      "Publicar Dados",
      "Publicar",
      "Cancelar",
    );
  };

  // Loading state
  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        <span className="ml-3 text-gray-600 dark:text-gray-400">
          Analisando dados para publicação...
        </span>
      </div>
    );
  }

  // Error state
  if (error && !preview) {
    return (
      <div className="p-8">
        <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 dark:border-red-600 p-4 rounded-card">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-800 dark:text-red-300">
                Erro ao Carregar Preview
              </h3>
              <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                {error}
              </p>
              <button
                onClick={fetchPreview}
                className="btn-secondary mt-4 text-sm flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Tentar Novamente
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Success state (após publicação)
  if (publishResult?.success) {
    return (
      <div className="p-8">
        <div className="bg-green-50 dark:bg-green-900/20 border-2 border-green-200 dark:border-green-800 rounded-card p-6">
          <div className="flex items-start gap-4">
            <CheckCircle className="w-10 h-10 text-green-600 dark:text-green-400 flex-shrink-0" />
            <div className="flex-1">
              <h2 className="text-xl font-bold text-green-800 dark:text-green-300 mb-2">
                Publicação Concluída com Sucesso!
              </h2>
              <p className="text-green-700 dark:text-green-400 mb-4">
                {publishResult.message}
              </p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-200 dark:border-green-800">
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {publishResult.parts_inserted.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Peças Inseridas
                  </p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-200 dark:border-green-800">
                  <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {publishResult.parts_updated.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Peças Atualizadas
                  </p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-200 dark:border-green-800">
                  <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {publishResult.brands_created.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Marcas Criadas
                  </p>
                </div>
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-200 dark:border-green-800">
                  <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                    {publishResult.execution_time_seconds.toFixed(1)}s
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Tempo de Execução
                  </p>
                </div>
              </div>

              {/* Assets de Imagens */}
              {(publishResult.assets_created > 0 ||
                publishResult.part_images_created > 0 ||
                publishResult.skipped_existing_images > 0) && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-indigo-200 dark:border-indigo-800">
                    <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                      {publishResult.assets_created.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      Assets Criados
                    </p>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-indigo-200 dark:border-indigo-800">
                    <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                      {publishResult.part_images_created.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      Vínculos de Imagem
                    </p>
                  </div>
                  {publishResult.skipped_existing_images > 0 && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
                      <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                        {publishResult.skipped_existing_images.toLocaleString()}
                      </p>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        Peças c/ Imagens (ignoradas)
                      </p>
                    </div>
                  )}
                  {publishResult.skipped_incomplete_images?.length > 0 && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-yellow-200 dark:border-yellow-800">
                      <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                        {publishResult.skipped_incomplete_images.length}
                      </p>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        Imagens Incompletas
                      </p>
                    </div>
                  )}
                </div>
              )}

              {publishResult.warnings.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-4">
                  <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-1">
                    Avisos:
                  </p>
                  <ul className="list-disc list-inside text-sm text-yellow-700 dark:text-yellow-400">
                    {publishResult.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!preview) return null;

  return (
    <div className="p-8 space-y-6">
      {/* Status do Banco de Produção */}
      <div
        className={`rounded-card border-2 p-4 ${
          preview.production_db_status === "connected"
            ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
            : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
        }`}
      >
        <div className="flex items-center gap-3">
          <Server
            className={`w-6 h-6 ${
              preview.production_db_status === "connected"
                ? "text-green-600 dark:text-green-400"
                : "text-red-600 dark:text-red-400"
            }`}
          />
          <div className="flex-1">
            <h3
              className={`font-medium ${
                preview.production_db_status === "connected"
                  ? "text-green-800 dark:text-green-300"
                  : "text-red-800 dark:text-red-300"
              }`}
            >
              Banco de Produção:{" "}
              {preview.production_db_status === "connected"
                ? "Conectado"
                : "Desconectado"}
            </h3>
          </div>
          {preview.production_db_status === "connected" && (
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          )}
        </div>
      </div>

      {/* Blockers */}
      {preview.blockers.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-600 dark:border-red-700 p-4 rounded-card">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">
                ⛔ Problemas que Impedem a Publicação
              </h3>
              <ul className="list-disc list-inside space-y-1">
                {preview.blockers.map((blocker, idx) => (
                  <li
                    key={idx}
                    className="text-sm text-red-700 dark:text-red-400"
                  >
                    {blocker}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Warnings */}
      {preview.warnings.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-500 dark:border-yellow-600 p-4 rounded-card">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
                ⚠️ Avisos
              </h3>
              <ul className="list-disc list-inside space-y-1">
                {preview.warnings.map((warning, idx) => (
                  <li
                    key={idx}
                    className="text-sm text-yellow-700 dark:text-yellow-400"
                  >
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Resumo da Publicação */}
      <div className="bg-white dark:bg-gray-800 rounded-card border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-primary-500" />
          Resumo da Publicação
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {preview.total_rows.toLocaleString()}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Total de Linhas
            </p>
          </div>

          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 border border-green-200 dark:border-green-800">
            <p className="text-3xl font-bold text-green-600 dark:text-green-400">
              {preview.parts_new.toLocaleString()}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Peças Novas
            </p>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
            <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {preview.parts_existing.toLocaleString()}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Peças Existentes
            </p>
          </div>

          <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
            <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              {preview.brands_to_create}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Marcas a Criar
            </p>
          </div>
        </div>

        {/* Marcas a serem criadas */}
        {preview.brands_to_create_list.length > 0 && (
          <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
            <h3 className="text-sm font-medium text-purple-800 dark:text-purple-300 mb-2 flex items-center gap-2">
              <Tag className="w-4 h-4" />
              Marcas que serão criadas automaticamente:
            </h3>
            <div className="flex flex-wrap gap-2">
              {preview.brands_to_create_list.slice(0, 10).map((brand, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-800 text-purple-800 dark:text-purple-200"
                >
                  {brand.brand_name}{" "}
                  <span className="ml-1 text-purple-500 dark:text-purple-400">
                    ({brand.occurrences})
                  </span>
                </span>
              ))}
              {preview.brands_to_create_list.length > 10 && (
                <span className="text-xs text-purple-600 dark:text-purple-400">
                  +{preview.brands_to_create_list.length - 10} outras
                </span>
              )}
            </div>
          </div>
        )}

        {/* Similaridades */}
        {preview.similarity &&
          preview.similarity.total_rows_with_similarity > 0 && (
            <div className="mt-4 p-4 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg border border-cyan-200 dark:border-cyan-800">
              <h3 className="text-sm font-medium text-cyan-800 dark:text-cyan-300 flex items-center gap-2">
                <Package className="w-4 h-4" />
                Similaridades:{" "}
                {preview.similarity.total_rows_with_similarity.toLocaleString()}{" "}
                linhas com informação de similaridade
              </h3>
            </div>
          )}
      </div>

      {/* Configuração de Campos */}
      <div className="bg-white dark:bg-gray-800 rounded-card border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
          <Settings className="w-5 h-5 text-primary-500" />
          Configuração de Atualização de Campos
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Configure como cada campo deve ser tratado ao encontrar peças que já
          existem no banco de produção.
        </p>

        <div className="space-y-3">
          {fieldConfigs.map((config) => (
            <div
              key={config.field}
              className="flex flex-col md:flex-row md:items-center gap-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              <div className="flex-1 min-w-[200px]">
                <p className="font-medium text-gray-900 dark:text-white">
                  {config.field}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {config.description}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    "ignore",
                    "update_if_empty",
                    "force_override",
                    "concatenate",
                  ] as FieldMode[]
                ).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => handleFieldModeChange(config.field, mode)}
                    title={MODE_DESCRIPTIONS[mode]}
                    className={`
                      px-3 py-1.5 text-xs font-medium rounded-lg transition-all
                      ${
                        config.mode === mode
                          ? mode === "ignore"
                            ? "bg-gray-600 text-white"
                            : mode === "force_override"
                              ? "bg-red-600 text-white"
                              : mode === "concatenate"
                                ? "bg-yellow-600 text-white"
                                : "bg-green-600 text-white"
                          : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                      }
                    `}
                  >
                    {MODE_LABELS[mode]}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Legenda */}
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-xs font-medium text-blue-800 dark:text-blue-300 mb-2">
            Legenda dos modos:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-blue-700 dark:text-blue-400">
            <div>
              <strong>Ignorar:</strong> {MODE_DESCRIPTIONS.ignore}
            </div>
            <div>
              <strong>Preencher se vazio:</strong>{" "}
              {MODE_DESCRIPTIONS.update_if_empty}
            </div>
            <div>
              <strong>Substituir:</strong> {MODE_DESCRIPTIONS.force_override}
            </div>
            <div>
              <strong>Concatenar:</strong> {MODE_DESCRIPTIONS.concatenate}
            </div>
          </div>
        </div>
      </div>

      {/* Configuração de Imagens */}
      <div className="bg-white dark:bg-gray-800 rounded-card border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
          <Upload className="w-5 h-5 text-indigo-500" />
          Configuração de Imagens
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Configure como as imagens devem ser tratadas ao publicar peças.
        </p>

        <div className="flex flex-col md:flex-row md:items-center gap-3 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex-1 min-w-[200px]">
            <p className="font-medium text-gray-900 dark:text-white">
              Modo de Imagens
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Defina como as imagens serão vinculadas às peças
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(["ignore", "add_if_empty", "concatenate"] as ImageMode[]).map(
              (mode) => (
                <button
                  key={mode}
                  onClick={() => setImageMode(mode)}
                  title={IMAGE_MODE_DESCRIPTIONS[mode]}
                  className={`
                  px-3 py-1.5 text-xs font-medium rounded-lg transition-all
                  ${
                    imageMode === mode
                      ? mode === "ignore"
                        ? "bg-gray-600 text-white"
                        : mode === "add_if_empty"
                          ? "bg-green-600 text-white"
                          : "bg-indigo-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                  }
                `}
                >
                  {IMAGE_MODE_LABELS[mode]}
                </button>
              ),
            )}
          </div>
        </div>

        {/* Legenda de Imagens */}
        <div className="mt-4 p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
          <p className="text-xs font-medium text-indigo-800 dark:text-indigo-300 mb-2">
            Legenda dos modos de imagem:
          </p>
          <div className="grid grid-cols-1 gap-2 text-xs text-indigo-700 dark:text-indigo-400">
            <div>
              <strong>Ignorar:</strong> {IMAGE_MODE_DESCRIPTIONS.ignore}
            </div>
            <div>
              <strong>Adicionar se vazio:</strong>{" "}
              {IMAGE_MODE_DESCRIPTIONS.add_if_empty}
            </div>
            <div>
              <strong>Concatenar:</strong> {IMAGE_MODE_DESCRIPTIONS.concatenate}
            </div>
          </div>
        </div>
      </div>

      {/* Botão de Publicar */}
      <div className="bg-white dark:bg-gray-800 rounded-card border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                Atenção: Esta ação não pode ser desfeita!
              </p>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Os dados serão inseridos/atualizados diretamente no banco de
                produção.
              </p>
            </div>
          </div>

          <button
            onClick={handlePublish}
            disabled={!preview.can_publish || publishing}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-white
              transition-all disabled:opacity-50 disabled:cursor-not-allowed
              ${
                preview.can_publish && !publishing
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-gray-400"
              }
            `}
          >
            {publishing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Publicando...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                Confirmar e Publicar na Hubbi
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Modal */}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        onConfirm={modalState.onConfirm}
        title={modalState.title}
        message={modalState.message}
        type={modalState.type}
        confirmText={modalState.confirmText}
        cancelText={modalState.cancelText}
      />
    </div>
  );
}
