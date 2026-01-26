import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  Upload,
  Image as ImageIcon,
  Loader2,
  CheckCircle2,
  AlertCircle,
  XCircle,
  RefreshCw,
  Link2,
  Eye,
  FolderOpen,
  Server,
  TestTube,
} from "lucide-react";
import {
  uploadImagesBatch,
  getImagesProcessingStatus,
  getImagesProcessingResult,
  linkImagesToProject,
  getImagesPreview,
  prepareImagesForUpload,
} from "../../../services/validationService";
import type {
  ImageProcessingStatusResponse,
  ImageProcessingResultResponse,
  ImageLinkResponse,
  ImagePreviewResponse,
} from "../../../services/validationService";
import Modal from "../../../components/Modal";
import { useModal } from "../../../hooks/useModal";

interface MediaIngestionStepProps {
  readOnly?: boolean;
}

type Environment = "test" | "production";

export default function MediaIngestionStep({
  readOnly = false,
}: MediaIngestionStepProps) {
  const { projectId } = useParams<{ projectId: string }>();

  // Estados de ambiente
  const [environment, setEnvironment] = useState<Environment>("test");

  // Estados de upload
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Estados de processamento
  const [processingStatus, setProcessingStatus] =
    useState<ImageProcessingStatusResponse | null>(null);
  const [processingResult, setProcessingResult] =
    useState<ImageProcessingResultResponse | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  // Estados de vinculação
  const [linkResult, setLinkResult] = useState<ImageLinkResponse | null>(null);
  const [isLinking, setIsLinking] = useState(false);

  // Estados de preview
  const [preview, setPreview] = useState<ImagePreviewResponse | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  // Estados gerais
  const [error, setError] = useState<string | null>(null);
  const { modalState, closeModal, showSuccess, showError, showConfirm } =
    useModal();

  // Buscar status inicial ao carregar
  useEffect(() => {
    if (projectId) {
      fetchProcessingStatus();
    }
  }, [projectId]);

  // Polling do status quando processando
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    if (
      isPolling &&
      processingStatus &&
      (processingStatus.status === "pending" ||
        processingStatus.status === "running")
    ) {
      interval = setInterval(() => {
        fetchProcessingStatus();
      }, 2000); // Poll a cada 2 segundos
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPolling, processingStatus?.status]);

  // Buscar status do processamento
  const fetchProcessingStatus = async () => {
    if (!projectId) return;

    try {
      const status = await getImagesProcessingStatus(projectId);
      setProcessingStatus(status);

      // Se completou, buscar resultado
      if (status.status === "completed") {
        setIsPolling(false);
        fetchProcessingResult();
      } else if (status.status === "error") {
        setIsPolling(false);
      }
    } catch (err: any) {
      console.error("Erro ao buscar status:", err);
    }
  };

  // Buscar resultado do processamento
  const fetchProcessingResult = async () => {
    if (!projectId) return;

    try {
      const result = await getImagesProcessingResult(projectId);
      setProcessingResult(result);
    } catch (err: any) {
      // Pode não ter resultado ainda
      console.log("Resultado ainda não disponível");
    }
  };

  // Handler de drag & drop
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files).filter((file) =>
      file.type.startsWith("image/"),
    );

    if (files.length > 0) {
      setSelectedFiles((prev) => [...prev, ...files]);
    }
  }, []);

  // Handler de seleção de arquivo
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      const imageFiles = Array.from(files).filter((file) =>
        file.type.startsWith("image/"),
      );
      setSelectedFiles((prev) => [...prev, ...imageFiles]);
    }
    // Reset input para permitir selecionar mesmos arquivos novamente
    e.target.value = "";
  };

  // Remover arquivo selecionado
  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Limpar todos os arquivos
  const clearFiles = () => {
    setSelectedFiles([]);
  };

  // Iniciar upload e processamento
  const handleUpload = async () => {
    if (!projectId || selectedFiles.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      // Preparar imagens para upload (converter para base64)
      const imageItems = await prepareImagesForUpload(selectedFiles);

      // Enviar para processamento
      const response = await uploadImagesBatch(
        projectId,
        imageItems,
        environment,
      );

      showSuccess(
        `✅ ${response.message} Ambiente: ${
          environment === "test" ? "Teste" : "Produção"
        }`,
      );

      // Iniciar polling
      setIsPolling(true);
      setSelectedFiles([]);

      // Buscar status imediatamente
      setTimeout(fetchProcessingStatus, 500);
    } catch (err: any) {
      setError(err.message);
      showError(`❌ ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Vincular imagens ao projeto
  const handleLink = async () => {
    if (!projectId) return;

    setIsLinking(true);
    setError(null);

    try {
      const result = await linkImagesToProject(projectId);
      setLinkResult(result);

      if (result.not_found_skus.length > 0) {
        showConfirm(
          `⚠️ ${result.message}\n\nSKUs não encontrados no CSV:\n${result.not_found_skus
            .slice(0, 10)
            .join(", ")}${
            result.not_found_skus.length > 10
              ? `\n... e mais ${result.not_found_skus.length - 10}`
              : ""
          }`,
          () => {},
          "Entendido",
        );
      } else {
        showSuccess(`✅ ${result.message}`);
      }
    } catch (err: any) {
      setError(err.message);
      showError(`❌ ${err.message}`);
    } finally {
      setIsLinking(false);
    }
  };

  // Buscar preview de imagens vinculadas
  const fetchPreview = async () => {
    if (!projectId) return;

    try {
      const previewData = await getImagesPreview(projectId);
      setPreview(previewData);
      setShowPreview(true);
    } catch (err: any) {
      showError(`❌ ${err.message}`);
    }
  };

  // Renderizar status do processamento
  const renderProcessingStatus = () => {
    if (!processingStatus || processingStatus.status === "not_started") {
      return null;
    }

    const statusConfig = {
      pending: {
        icon: <Loader2 className="w-5 h-5 animate-spin text-yellow-500" />,
        label: "Aguardando",
        bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
        borderColor: "border-yellow-200 dark:border-yellow-800",
      },
      running: {
        icon: <Loader2 className="w-5 h-5 animate-spin text-blue-500" />,
        label: "Processando",
        bgColor: "bg-blue-50 dark:bg-blue-900/20",
        borderColor: "border-blue-200 dark:border-blue-800",
      },
      completed: {
        icon: <CheckCircle2 className="w-5 h-5 text-green-500" />,
        label: "Concluído",
        bgColor: "bg-green-50 dark:bg-green-900/20",
        borderColor: "border-green-200 dark:border-green-800",
      },
      error: {
        icon: <XCircle className="w-5 h-5 text-red-500" />,
        label: "Erro",
        bgColor: "bg-red-50 dark:bg-red-900/20",
        borderColor: "border-red-200 dark:border-red-800",
      },
    };

    const config =
      statusConfig[processingStatus.status as keyof typeof statusConfig] ||
      statusConfig.pending;

    return (
      <div
        className={`p-4 rounded-lg border ${config.bgColor} ${config.borderColor}`}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {config.icon}
            <span className="font-medium">{config.label}</span>
          </div>
          <button
            onClick={fetchProcessingStatus}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            title="Atualizar status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Barra de progresso */}
        {(processingStatus.status === "running" ||
          processingStatus.status === "pending") && (
          <div className="mb-3">
            <div className="flex justify-between text-sm mb-1">
              <span>{processingStatus.current_step || "Iniciando..."}</span>
              <span>{processingStatus.progress.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${processingStatus.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Métricas */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400">Total:</span>
            <span className="ml-2 font-medium">
              {processingStatus.total_images}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">
              Processadas:
            </span>
            <span className="ml-2 font-medium text-green-600">
              {processingStatus.processed_images}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Erros:</span>
            <span className="ml-2 font-medium text-red-600">
              {processingStatus.failed_images}
            </span>
          </div>
        </div>

        {/* Tempo de processamento */}
        {processingStatus.processing_time_seconds && (
          <div className="mt-2 text-sm text-gray-500">
            Tempo: {processingStatus.processing_time_seconds.toFixed(2)}s
          </div>
        )}

        {/* Erro */}
        {processingStatus.error_message && (
          <div className="mt-3 p-2 bg-red-100 dark:bg-red-900/30 rounded text-sm text-red-700 dark:text-red-300">
            {processingStatus.error_message}
          </div>
        )}
      </div>
    );
  };

  // Renderizar resultado do processamento
  const renderProcessingResult = () => {
    if (!processingResult || processingStatus?.status !== "completed") {
      return null;
    }

    return (
      <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
        <h4 className="font-medium text-green-700 dark:text-green-300 mb-3">
          Resultado do Processamento
        </h4>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {processingResult.skus_count}
            </div>
            <div className="text-sm text-gray-500">SKUs</div>
          </div>
          <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-green-600">
              {processingResult.processed_images}
            </div>
            <div className="text-sm text-gray-500">Processadas</div>
          </div>
          <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-red-600">
              {processingResult.failed_images}
            </div>
            <div className="text-sm text-gray-500">Erros</div>
          </div>
          <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-gray-600">
              {processingResult.processing_time_seconds?.toFixed(1)}s
            </div>
            <div className="text-sm text-gray-500">Tempo</div>
          </div>
        </div>

        {/* Erros de processamento */}
        {processingResult.errors.length > 0 && (
          <div className="mb-4">
            <h5 className="text-sm font-medium text-red-600 mb-2">
              Erros ({processingResult.errors.length}):
            </h5>
            <div className="max-h-32 overflow-y-auto bg-red-50 dark:bg-red-900/30 rounded p-2">
              {processingResult.errors.slice(0, 10).map((err, idx) => (
                <div
                  key={idx}
                  className="text-sm text-red-700 dark:text-red-300"
                >
                  <span className="font-medium">{err.filename}:</span>{" "}
                  {err.error}
                </div>
              ))}
              {processingResult.errors.length > 10 && (
                <div className="text-sm text-red-500 mt-1">
                  ... e mais {processingResult.errors.length - 10} erros
                </div>
              )}
            </div>
          </div>
        )}

        {/* Botão de vincular */}
        {!readOnly && (
          <button
            onClick={handleLink}
            disabled={isLinking}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg flex items-center justify-center gap-2"
          >
            {isLinking ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Vinculando...
              </>
            ) : (
              <>
                <Link2 className="w-4 h-4" />
                Vincular ao Projeto
              </>
            )}
          </button>
        )}
      </div>
    );
  };

  // Renderizar resultado da vinculação
  const renderLinkResult = () => {
    if (!linkResult) return null;

    return (
      <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <h4 className="font-medium text-blue-700 dark:text-blue-300 mb-3">
          Resultado da Vinculação
        </h4>

        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {linkResult.total_skus}
            </div>
            <div className="text-sm text-gray-500">Total SKUs</div>
          </div>
          <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-green-600">
              {linkResult.linked_skus}
            </div>
            <div className="text-sm text-gray-500">Vinculados</div>
          </div>
          <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
            <div className="text-2xl font-bold text-yellow-600">
              {linkResult.not_found_skus.length}
            </div>
            <div className="text-sm text-gray-500">Não Encontrados</div>
          </div>
        </div>

        {linkResult.not_found_skus.length > 0 && (
          <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded text-sm">
            <span className="font-medium text-yellow-700 dark:text-yellow-300">
              SKUs não encontrados no CSV:
            </span>
            <div className="text-yellow-600 dark:text-yellow-400 mt-1">
              {linkResult.not_found_skus.slice(0, 10).join(", ")}
              {linkResult.not_found_skus.length > 10 &&
                ` ... e mais ${linkResult.not_found_skus.length - 10}`}
            </div>
          </div>
        )}

        <button
          onClick={fetchPreview}
          className="mt-3 w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg flex items-center justify-center gap-2"
        >
          <Eye className="w-4 h-4" />
          Ver Preview das Imagens Vinculadas
        </button>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-500 to-pink-500 text-white p-6 rounded-lg">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <ImageIcon className="w-7 h-7" />
          Ingestão de Imagens
        </h2>
        <p className="mt-2 opacity-90">
          Faça upload das imagens das peças. As imagens serão redimensionadas em
          4 variantes (alta, média, baixa e marca d'água) e vinculadas ao CSV
          pelo código da peça (search_ref).
        </p>
        <p className="mt-1 text-sm opacity-75">
          Formato esperado dos arquivos:{" "}
          <code className="bg-white/20 px-1 rounded">
            {"{search_ref}-{índice}.jpg"}
          </code>{" "}
          (ex: ABC123-0.jpg, ABC123-1.jpg)
        </p>
      </div>

      {/* Seletor de Ambiente */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
          <Server className="w-5 h-5" />
          Ambiente de Destino
        </h3>
        <div className="flex gap-4">
          <label
            className={`flex-1 p-4 border-2 rounded-lg cursor-pointer transition-all ${
              environment === "test"
                ? "border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20"
                : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
            }`}
          >
            <input
              type="radio"
              name="environment"
              value="test"
              checked={environment === "test"}
              onChange={(e) => setEnvironment(e.target.value as Environment)}
              disabled={readOnly || isUploading}
              className="sr-only"
            />
            <div className="flex items-center gap-3">
              <TestTube
                className={`w-6 h-6 ${
                  environment === "test" ? "text-yellow-600" : "text-gray-400"
                }`}
              />
              <div>
                <div className="font-medium">Ambiente de Teste</div>
                <div className="text-sm text-gray-500">
                  Pasta S3: <code>test-lambda/</code>
                </div>
              </div>
            </div>
          </label>

          <label
            className={`flex-1 p-4 border-2 rounded-lg cursor-pointer transition-all ${
              environment === "production"
                ? "border-green-500 bg-green-50 dark:bg-green-900/20"
                : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
            }`}
          >
            <input
              type="radio"
              name="environment"
              value="production"
              checked={environment === "production"}
              onChange={(e) => setEnvironment(e.target.value as Environment)}
              disabled={readOnly || isUploading}
              className="sr-only"
            />
            <div className="flex items-center gap-3">
              <Server
                className={`w-6 h-6 ${
                  environment === "production"
                    ? "text-green-600"
                    : "text-gray-400"
                }`}
              />
              <div>
                <div className="font-medium">Ambiente de Produção</div>
                <div className="text-sm text-gray-500">
                  Pasta S3: <code>media/</code>
                </div>
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Área de Upload */}
      {!readOnly && (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload de Imagens
          </h3>

          {/* Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
              isDragging
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                : "border-gray-300 dark:border-gray-600 hover:border-gray-400"
            }`}
          >
            <FolderOpen className="w-12 h-12 mx-auto text-gray-400 mb-3" />
            <p className="text-gray-600 dark:text-gray-300 mb-2">
              Arraste e solte imagens aqui ou
            </p>
            <label className="inline-block">
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
                // @ts-ignore - webkitdirectory é uma prop válida mas não reconhecida pelo TS
                webkitdirectory=""
                directory=""
              />
              <span className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg cursor-pointer">
                Selecionar Pasta
              </span>
            </label>
            <label className="inline-block ml-2">
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
              />
              <span className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg cursor-pointer">
                Selecionar Arquivos
              </span>
            </label>
          </div>

          {/* Lista de arquivos selecionados */}
          {selectedFiles.length > 0 && (
            <div className="mt-4">
              <div className="flex justify-between items-center mb-2">
                <span className="font-medium">
                  {selectedFiles.length} arquivo(s) selecionado(s)
                </span>
                <button
                  onClick={clearFiles}
                  className="text-sm text-red-600 hover:text-red-700"
                >
                  Limpar todos
                </button>
              </div>

              <div className="max-h-48 overflow-y-auto bg-gray-50 dark:bg-gray-900 rounded p-2">
                {selectedFiles.slice(0, 20).map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between py-1 px-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                  >
                    <span className="text-sm truncate">{file.name}</span>
                    <button
                      onClick={() => removeFile(idx)}
                      className="text-red-500 hover:text-red-600 ml-2"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {selectedFiles.length > 20 && (
                  <div className="text-sm text-gray-500 text-center py-2">
                    ... e mais {selectedFiles.length - 20} arquivos
                  </div>
                )}
              </div>

              {/* Botão de upload */}
              <button
                onClick={handleUpload}
                disabled={isUploading || selectedFiles.length === 0}
                className="mt-4 w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-lg flex items-center justify-center gap-2 font-medium"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Enviando...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Processar {selectedFiles.length} Imagens (
                    {environment === "test" ? "Teste" : "Produção"})
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Status do Processamento */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
          <Loader2 className="w-5 h-5" />
          Status do Processamento
        </h3>

        {renderProcessingStatus()}
        {renderProcessingResult()}
        {renderLinkResult()}

        {(!processingStatus || processingStatus.status === "not_started") && (
          <div className="text-center py-8 text-gray-500">
            <ImageIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Nenhum processamento de imagens iniciado</p>
            <p className="text-sm mt-1">Selecione imagens acima para começar</p>
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {showPreview && preview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b dark:border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-medium">
                Preview de Imagens Vinculadas
              </h3>
              <button
                onClick={() => setShowPreview(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded">
                  <span className="text-green-700 dark:text-green-300 font-medium">
                    Com imagens: {preview.total_with_images}
                  </span>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-gray-700 dark:text-gray-300 font-medium">
                    Sem imagens: {preview.total_without_images}
                  </span>
                </div>
              </div>

              {preview.rows.length > 0 ? (
                <div className="space-y-3">
                  {preview.rows.map((row, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-gray-50 dark:bg-gray-700 rounded"
                    >
                      <div className="font-medium mb-2">
                        {row.search_ref} - {row.brand}
                      </div>
                      <div className="grid grid-cols-4 gap-2 text-xs">
                        {[
                          "file_high",
                          "file_medium",
                          "file_low",
                          "file_water_mark",
                        ].map((col) => (
                          <div key={col}>
                            <span className="text-gray-500">{col}:</span>
                            <div className="truncate text-blue-600">
                              {row[col] || "-"}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-8">
                  Nenhum registro com imagens encontrado
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal */}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        type={modalState.type}
        message={modalState.message}
        onConfirm={modalState.onConfirm}
        confirmText={modalState.confirmText}
      />

      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 p-4 rounded-lg shadow-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 hover:text-red-900"
          >
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
