import {
  Upload,
  ArrowLeft,
  FileCheck,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useState, type DragEvent, type ChangeEvent } from "react";
import { uploadCSV } from "../../services/validationService";

export default function NewProjectUpload() {
  const navigate = useNavigate();
  const [projectName, setProjectName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      const file = files[0];
      if (file.type === "text/csv" || file.name.endsWith(".csv")) {
        setSelectedFile(file);
        // Se não tiver nome do projeto, usar o nome do arquivo
        if (!projectName) {
          setProjectName(file.name.replace(".csv", ""));
        }
      } else {
        alert("Por favor, selecione um arquivo CSV");
      }
    }
  };

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      const file = files[0];
      if (file.type === "text/csv" || file.name.endsWith(".csv")) {
        setSelectedFile(file);
        if (!projectName) {
          setProjectName(file.name.replace(".csv", ""));
        }
      } else {
        alert("Por favor, selecione um arquivo CSV");
      }
    }
  };

  const handleStartTreatment = async () => {
    if (!projectName || !selectedFile) {
      alert("Por favor, preencha o nome do projeto e selecione um arquivo");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadCSV(selectedFile, projectName);
      console.log("Upload bem-sucedido:", response);
      // Redirecionar para o workspace com o ID real do projeto
      navigate(`/validation/${response.id}`);
    } catch (err: any) {
      console.error("Erro ao fazer upload:", err);
      setError(
        err.message || "Erro ao fazer upload do arquivo. Tente novamente."
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-soft">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <Link
              to="/validation"
              className="btn-secondary flex items-center gap-2"
            >
              <ArrowLeft className="w-5 h-5" />
              Voltar
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-wide">
                Novo Projeto
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Faça upload de um dataset para validação
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Mensagem de Erro */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-card p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-red-900 mb-1">
                Erro no Upload
              </h3>
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-600 hover:text-red-700 font-medium text-sm"
            >
              Fechar
            </button>
          </div>
        )}

        <div className="card space-y-6">
          {/* Nome do Projeto */}
          <div>
            <label
              htmlFor="projectName"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Nome do Projeto
            </label>
            <input
              id="projectName"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Ex: Catálogo de Produtos 2024"
              className="input-base w-full"
            />
          </div>

          {/* Dropzone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Arquivo CSV
            </label>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`
                relative border-2 border-dashed rounded-card p-12 text-center transition-all
                ${
                  isDragging
                    ? "border-primary-500 bg-primary-50"
                    : "border-gray-300 bg-white hover:border-gray-400"
                }
              `}
            >
              <input
                type="file"
                accept=".csv"
                onChange={handleFileInput}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />

              {!selectedFile ? (
                <>
                  <Upload
                    className={`w-12 h-12 mx-auto mb-4 ${
                      isDragging ? "text-primary-500" : "text-gray-400"
                    }`}
                  />
                  <p className="text-base font-medium text-gray-900 mb-1">
                    Arraste seu CSV aqui
                  </p>
                  <p className="text-sm text-gray-500">
                    ou clique para selecionar um arquivo
                  </p>
                </>
              ) : (
                <>
                  <FileCheck className="w-12 h-12 text-green-500 mx-auto mb-4" />
                  <p className="text-base font-medium text-gray-900 mb-1">
                    {selectedFile.name}
                  </p>
                  <p className="text-sm text-gray-500">
                    {(selectedFile.size / 1024).toFixed(2)} KB
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    className="mt-3 text-sm text-red-600 hover:text-red-700 font-medium"
                  >
                    Remover arquivo
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Botão de Ação */}
          <div className="flex justify-end gap-3 pt-4">
            <Link to="/validation" className="btn-secondary">
              Cancelar
            </Link>
            <button
              onClick={handleStartTreatment}
              disabled={!projectName || !selectedFile || isUploading}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Enviando arquivo...
                </>
              ) : (
                "Iniciar Tratamento"
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
