<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";

const router = useRouter();
const token = ref(localStorage.getItem("access_token") || "");
const username = ref(localStorage.getItem("username") || "");

// Estados
const projects = ref([]);
const selectedFile = ref(null);
const selectedProjectId = ref("");
const previewData = ref(null);
const columnsAnalysis = ref(null);
const currentPage = ref(1);
const loading = ref(false);
const error = ref("");
const success = ref("");

// Renomeação
const oldColumnName = ref("");
const newColumnName = ref("");

// Tratamentos (Fase 2)
const treatmentDiagnosis = ref(null);

// Duplicadas
const duplicatesAnalysis = ref(null);

// API Client
const api = axios.create({
  baseURL: window.location.origin,
  headers: {
    Authorization: `Bearer ${token.value}`,
  },
});

// Funções
const handleFileSelect = (event) => {
  selectedFile.value = event.target.files[0];
};

const uploadFile = async () => {
  if (!selectedFile.value) {
    error.value = "Selecione um arquivo CSV";
    return;
  }

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);

    const response = await api.post("/validation/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    success.value = "Upload realizado com sucesso!";
    selectedProjectId.value = response.data.id;
    await loadProjects();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao fazer upload";
  } finally {
    loading.value = false;
  }
};

const loadProjects = async () => {
  loading.value = true;
  try {
    const response = await api.get("/validation/projects");
    projects.value = response.data;
  } catch (err) {
    error.value = "Erro ao carregar projetos";
  } finally {
    loading.value = false;
  }
};

const loadPreview = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const response = await api.get(
      `/validation/${selectedProjectId.value}/preview`,
      {
        params: { page: currentPage.value, limit: 20 },
      }
    );
    previewData.value = response.data;
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao carregar preview";
  } finally {
    loading.value = false;
  }
};

const downloadCSV = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  try {
    const response = await api.get(
      `/validation/${selectedProjectId.value}/download`,
      {
        responseType: "blob",
      }
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "export.csv");
    document.body.appendChild(link);
    link.click();
    link.remove();

    success.value = "Download concluído!";
  } catch (err) {
    error.value = "Erro ao fazer download";
  }
};

const analyzeColumns = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const response = await api.get(
      `/validation/${selectedProjectId.value}/columns/analysis`
    );
    columnsAnalysis.value = response.data;
    success.value = "Análise de colunas concluída!";
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao analisar colunas";
  } finally {
    loading.value = false;
  }
};

const renameColumn = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (!oldColumnName.value || !newColumnName.value) {
    error.value = "Preencha ambos os nomes de coluna";
    return;
  }

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/columns/rename`,
      {
        old_name: oldColumnName.value,
        new_name: newColumnName.value,
      }
    );
    success.value = response.data.message;
    oldColumnName.value = "";
    newColumnName.value = "";

    await analyzeColumns();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao renomear coluna";
  } finally {
    loading.value = false;
  }
};

const goBack = () => {
  router.push("/service-selector");
};

const logout = () => {
  localStorage.clear();
  router.push("/login");
};

// --- FASE 2: TRATAMENTOS ---

const diagnoseTreatments = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const response = await api.get(
      `/validation/${selectedProjectId.value}/treatments/diagnosis`
    );
    treatmentDiagnosis.value = response.data;
    success.value = "Diagnóstico concluído!";
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao diagnosticar";
  } finally {
    loading.value = false;
  }
};

const fixNullStrings = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (!confirm("Substituir valores nulos/nan por string vazia?")) return;

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/treatments/fix-nulls-string`
    );
    success.value = `${response.data.message} - ${response.data.rows_affected} linhas afetadas`;
    await diagnoseTreatments();
    await loadPreview();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao corrigir nulos";
  } finally {
    loading.value = false;
  }
};

const fixUppercase = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (!confirm("Converter valores para UPPERCASE?")) return;

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/treatments/fix-uppercase`
    );
    success.value = `${response.data.message} - ${response.data.rows_affected} linhas afetadas`;
    await diagnoseTreatments();
    await loadPreview();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao aplicar uppercase";
  } finally {
    loading.value = false;
  }
};

const fixNullNumerics = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (!confirm("Substituir nulos em colunas numéricas por 0?")) return;

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/treatments/fix-nulls-numeric`
    );
    success.value = `${response.data.message} - ${response.data.rows_affected} linhas afetadas`;
    await diagnoseTreatments();
    await loadPreview();
  } catch (err) {
    error.value =
      err.response?.data?.detail || "Erro ao corrigir nulos numéricos";
  } finally {
    loading.value = false;
  }
};

// --- FASE 2.2: CORREÇÕES AVANÇADAS ---

const fixBarcode = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (!confirm("Aplicar correção de barcode (EAN-13 checksum)?")) return;

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/treatments/fix-barcode`
    );
    success.value = `${response.data.message} - ${response.data.rows_affected} linhas afetadas`;
    await diagnoseTreatments();
    await loadPreview();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao corrigir barcode";
  } finally {
    loading.value = false;
  }
};

const fixNCM = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (!confirm("Sanitizar NCM (remover pontos e caracteres não-numéricos)?"))
    return;

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/treatments/fix-ncm`
    );
    success.value = `${response.data.message} - ${response.data.rows_affected} linhas afetadas`;
    await diagnoseTreatments();
    await loadPreview();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao corrigir NCM";
  } finally {
    loading.value = false;
  }
};

const fixCodes = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (!confirm("Sanitizar códigos (UPPER + remover caracteres especiais)?"))
    return;

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/treatments/fix-codes`
    );
    success.value = `${response.data.message} - ${response.data.rows_affected} linhas afetadas`;
    await diagnoseTreatments();
    await loadPreview();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao corrigir códigos";
  } finally {
    loading.value = false;
  }
};

const fixNegativeWeights = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (!confirm("Converter pesos negativos em valores absolutos?")) return;

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/treatments/fix-negative-weights`
    );
    success.value = `${response.data.message} - ${response.data.rows_affected} linhas afetadas`;
    await diagnoseTreatments();
    await loadPreview();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao corrigir pesos";
  } finally {
    loading.value = false;
  }
};

// --- ANÁLISE DE DUPLICADAS ---

const analyzeDuplicates = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const response = await api.get(
      `/validation/${selectedProjectId.value}/duplicates/analysis`
    );
    duplicatesAnalysis.value = response.data;
    success.value = `Análise concluída! ${response.data.total_duplicates} duplicadas encontradas em ${response.data.duplicate_groups} grupos`;
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao analisar duplicadas";
  } finally {
    loading.value = false;
  }
};

const removeDuplicates = async () => {
  if (!selectedProjectId.value) {
    error.value = "Selecione um projeto";
    return;
  }

  if (
    !confirm(
      "Remover todas as duplicadas mantendo apenas a primeira ocorrência?"
    )
  )
    return;

  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await api.post(
      `/validation/${selectedProjectId.value}/duplicates/remove`
    );
    success.value = `${response.data.message} - ${response.data.rows_affected} linhas removidas`;
    duplicatesAnalysis.value = null;
    await analyzeDuplicates();
    await loadPreview();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao remover duplicadas";
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadProjects();
});
</script>

<template>
  <div class="min-h-screen bg-gray-100 p-8">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="flex justify-between items-center">
        <div class="flex items-center gap-4">
          <button
            @click="goBack"
            class="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            ← Voltar
          </button>
          <h1 class="text-2xl font-bold">Data Validation - Teste de API</h1>
        </div>
        <div class="flex items-center gap-4">
          <span class="text-gray-700">{{ username }}</span>
          <button
            @click="logout"
            class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Sair
          </button>
        </div>
      </div>
    </div>

    <!-- Alerts -->
    <div
      v-if="error"
      class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4"
    >
      {{ error }}
    </div>
    <div
      v-if="success"
      class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4"
    >
      {{ success }}
    </div>

    <div class="grid grid-cols-2 gap-6">
      <!-- Coluna Esquerda -->
      <div class="space-y-6">
        <!-- Upload -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">1. Upload CSV</h2>
          <input
            type="file"
            accept=".csv"
            @change="handleFileSelect"
            class="mb-4 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <button
            @click="uploadFile"
            :disabled="loading"
            class="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {{ loading ? "Carregando..." : "Upload" }}
          </button>
        </div>

        <!-- Lista de Projetos -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">2. Projetos</h2>
          <div class="space-y-2 max-h-96 overflow-y-auto">
            <div
              v-for="project in projects"
              :key="project.id"
              @click="selectedProjectId = project.id"
              :class="[
                'p-3 border rounded cursor-pointer hover:bg-gray-50',
                selectedProjectId === project.id
                  ? 'bg-blue-100 border-blue-500'
                  : 'border-gray-200',
              ]"
            >
              <div class="font-semibold">{{ project.original_filename }}</div>
              <div class="text-sm text-gray-600">
                ID: {{ project.id.substring(0, 8) }}...
              </div>
              <div class="text-sm text-gray-600">
                Criado por: {{ project.owner_username }}
              </div>
              <div class="text-sm text-gray-600">
                Status: {{ project.status }}
              </div>
              <div class="text-sm text-gray-500">
                {{ new Date(project.created_at).toLocaleString() }}
              </div>
            </div>
          </div>
        </div>

        <!-- Ações -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">3. Ações</h2>
          <div class="space-y-2">
            <button
              @click="analyzeColumns"
              :disabled="!selectedProjectId || loading"
              class="w-full px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
            >
              Analisar Colunas
            </button>
            <button
              @click="diagnoseTreatments"
              :disabled="!selectedProjectId || loading"
              class="w-full px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50"
            >
              Diagnosticar Tratamentos
            </button>
            <button
              @click="analyzeDuplicates"
              :disabled="!selectedProjectId || loading"
              class="w-full px-4 py-2 bg-rose-600 text-white rounded hover:bg-rose-700 disabled:opacity-50"
            >
              Analisar Duplicadas
            </button>
            <button
              @click="loadPreview"
              :disabled="!selectedProjectId || loading"
              class="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              Visualizar Preview
            </button>
            <button
              @click="downloadCSV"
              :disabled="!selectedProjectId"
              class="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
            >
              Download CSV
            </button>
          </div>
        </div>

        <!-- Renomear Coluna -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">4. Renomear Coluna</h2>
          <div class="space-y-3">
            <input
              v-model="oldColumnName"
              type="text"
              placeholder="Nome atual da coluna"
              class="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              v-model="newColumnName"
              type="text"
              placeholder="Novo nome da coluna"
              class="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              @click="renameColumn"
              :disabled="!selectedProjectId || loading"
              class="w-full px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              Renomear
            </button>
          </div>
        </div>

        <!-- Tratamentos Automatizados -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">5. Tratamentos (Fase 2)</h2>
          <div class="space-y-2">
            <button
              @click="fixNullStrings"
              :disabled="
                !selectedProjectId ||
                loading ||
                !treatmentDiagnosis?.null_string_issues?.length
              "
              class="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              Corrigir Nulos em Strings
              <span
                v-if="treatmentDiagnosis?.null_string_issues?.length"
                class="ml-2 px-2 py-1 bg-red-500 rounded-full text-xs"
              >
                {{ treatmentDiagnosis.null_string_issues.length }}
              </span>
            </button>
            <button
              @click="fixUppercase"
              :disabled="
                !selectedProjectId ||
                loading ||
                !treatmentDiagnosis?.uppercase_issues?.length
              "
              class="w-full px-4 py-2 bg-teal-600 text-white rounded hover:bg-teal-700 disabled:opacity-50"
            >
              Converter para UPPERCASE
              <span
                v-if="treatmentDiagnosis?.uppercase_issues?.length"
                class="ml-2 px-2 py-1 bg-red-500 rounded-full text-xs"
              >
                {{ treatmentDiagnosis.uppercase_issues.length }}
              </span>
            </button>
            <button
              @click="fixNullNumerics"
              :disabled="
                !selectedProjectId ||
                loading ||
                !treatmentDiagnosis?.null_numeric_issues?.length
              "
              class="w-full px-4 py-2 bg-cyan-600 text-white rounded hover:bg-cyan-700 disabled:opacity-50"
            >
              Corrigir Nulos Numéricos
              <span
                v-if="treatmentDiagnosis?.null_numeric_issues?.length"
                class="ml-2 px-2 py-1 bg-red-500 rounded-full text-xs"
              >
                {{ treatmentDiagnosis.null_numeric_issues.length }}
              </span>
            </button>
          </div>
        </div>

        <!-- Correções Avançadas (Fase 2.2) -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">6. Correções Avançadas</h2>
          <div class="space-y-2">
            <button
              @click="fixBarcode"
              :disabled="
                !selectedProjectId ||
                loading ||
                !treatmentDiagnosis?.barcode_issues
              "
              class="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
            >
              Corrigir Barcode (EAN-13)
              <span
                v-if="treatmentDiagnosis?.barcode_issues > 0"
                class="ml-2 px-2 py-1 bg-red-500 rounded-full text-xs"
              >
                {{ treatmentDiagnosis.barcode_issues }}
              </span>
            </button>
            <button
              @click="fixNCM"
              :disabled="
                !selectedProjectId || loading || !treatmentDiagnosis?.ncm_issues
              "
              class="w-full px-4 py-2 bg-pink-600 text-white rounded hover:bg-pink-700 disabled:opacity-50"
            >
              Sanitizar NCM
              <span
                v-if="treatmentDiagnosis?.ncm_issues > 0"
                class="ml-2 px-2 py-1 bg-red-500 rounded-full text-xs"
              >
                {{ treatmentDiagnosis.ncm_issues }}
              </span>
            </button>
            <button
              @click="fixCodes"
              :disabled="
                !selectedProjectId ||
                loading ||
                (!treatmentDiagnosis?.search_ref_issues &&
                  !treatmentDiagnosis?.manufacturer_ref_issues)
              "
              class="w-full px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
            >
              Sanitizar Códigos
              <span
                v-if="
                  (treatmentDiagnosis?.search_ref_issues || 0) +
                    (treatmentDiagnosis?.manufacturer_ref_issues || 0) >
                  0
                "
                class="ml-2 px-2 py-1 bg-red-500 rounded-full text-xs"
              >
                {{
                  (treatmentDiagnosis?.search_ref_issues || 0) +
                  (treatmentDiagnosis?.manufacturer_ref_issues || 0)
                }}
              </span>
            </button>
            <button
              @click="fixNegativeWeights"
              :disabled="
                !selectedProjectId ||
                loading ||
                !treatmentDiagnosis?.weight_issues
              "
              class="w-full px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50"
            >
              Corrigir Pesos Negativos
              <span
                v-if="treatmentDiagnosis?.weight_issues > 0"
                class="ml-2 px-2 py-1 bg-red-500 rounded-full text-xs"
              >
                {{ treatmentDiagnosis.weight_issues }}
              </span>
            </button>
          </div>
        </div>

        <!-- Remoção de Duplicadas -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">7. Duplicadas</h2>
          <div class="space-y-2">
            <button
              @click="removeDuplicates"
              :disabled="
                !selectedProjectId ||
                loading ||
                !duplicatesAnalysis?.total_duplicates
              "
              class="w-full px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              Remover Duplicadas
              <span
                v-if="duplicatesAnalysis?.total_duplicates > 0"
                class="ml-2 px-2 py-1 bg-yellow-500 rounded-full text-xs"
              >
                {{ duplicatesAnalysis.total_duplicates }}
              </span>
            </button>
          </div>
        </div>
      </div>

      <!-- Coluna Direita -->
      <div class="space-y-6">
        <!-- Análise de Duplicadas -->
        <div v-if="duplicatesAnalysis" class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">Análise de Duplicadas</h2>

          <div class="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div class="grid grid-cols-2 gap-4 text-center">
              <div>
                <div class="text-3xl font-bold text-blue-600">
                  {{ duplicatesAnalysis.total_duplicates }}
                </div>
                <div class="text-sm text-gray-600">Linhas Duplicadas</div>
              </div>
              <div>
                <div class="text-3xl font-bold text-blue-600">
                  {{ duplicatesAnalysis.duplicate_groups }}
                </div>
                <div class="text-sm text-gray-600">Grupos de Duplicadas</div>
              </div>
            </div>
          </div>

          <div
            v-if="duplicatesAnalysis.duplicates.length > 0"
            class="space-y-4 max-h-96 overflow-y-auto"
          >
            <div
              v-for="(group, idx) in duplicatesAnalysis.duplicates"
              :key="idx"
              class="border border-gray-200 rounded-lg p-4 bg-gray-50"
            >
              <div class="flex justify-between items-center mb-3">
                <div>
                  <div class="font-semibold text-gray-800">
                    <span class="text-blue-600">{{ group.search_ref }}</span> +
                    <span class="text-green-600">{{ group.brand }}</span>
                  </div>
                  <div class="text-xs text-gray-500">
                    {{ group.count }} ocorrências
                  </div>
                </div>
                <div
                  class="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-semibold"
                >
                  {{ group.count - 1 }} duplicadas
                </div>
              </div>

              <div class="space-y-2">
                <div
                  v-for="(row, rowIdx) in group.rows"
                  :key="rowIdx"
                  :class="[
                    'p-2 rounded text-xs',
                    rowIdx === 0
                      ? 'bg-green-100 border border-green-300'
                      : 'bg-red-100 border border-red-300',
                  ]"
                >
                  <div class="font-semibold mb-1">
                    {{ rowIdx === 0 ? "✓ Será mantida" : "✗ Será removida" }}
                  </div>
                  <div class="grid grid-cols-2 gap-1 text-gray-700">
                    <div
                      v-for="(value, key) in row"
                      :key="key"
                      class="truncate"
                    >
                      <span class="font-semibold">{{ key }}:</span>
                      {{ value || "(vazio)" }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="text-center py-8 text-gray-500">
            ✓ Nenhuma duplicada encontrada!
          </div>
        </div>

        <!-- Diagnóstico de Tratamentos -->
        <div v-if="treatmentDiagnosis" class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">Diagnóstico de Tratamentos</h2>

          <div class="space-y-4">
            <!-- Uppercase Issues -->
            <div class="border-l-4 border-blue-500 bg-blue-50 p-4">
              <h3 class="font-bold text-blue-800 mb-2">
                🔤 Uppercase Issues ({{
                  treatmentDiagnosis.uppercase_issues.length
                }})
              </h3>
              <div
                v-if="treatmentDiagnosis.uppercase_issues.length > 0"
                class="flex flex-wrap gap-2"
              >
                <span
                  v-for="col in treatmentDiagnosis.uppercase_issues"
                  :key="col"
                  class="px-2 py-1 bg-blue-200 text-blue-800 text-xs rounded"
                >
                  {{ col }}
                </span>
              </div>
              <p v-else class="text-sm text-blue-700">✓ Sem problemas</p>
            </div>

            <!-- Null String Issues -->
            <div class="border-l-4 border-orange-500 bg-orange-50 p-4">
              <h3 class="font-bold text-orange-800 mb-2">
                📝 Nulos em Strings ({{
                  treatmentDiagnosis.null_string_issues.length
                }})
              </h3>
              <div
                v-if="treatmentDiagnosis.null_string_issues.length > 0"
                class="flex flex-wrap gap-2"
              >
                <span
                  v-for="col in treatmentDiagnosis.null_string_issues"
                  :key="col"
                  class="px-2 py-1 bg-orange-200 text-orange-800 text-xs rounded"
                >
                  {{ col }}
                </span>
              </div>
              <p v-else class="text-sm text-orange-700">✓ Sem problemas</p>
            </div>

            <!-- Null Numeric Issues -->
            <div class="border-l-4 border-cyan-500 bg-cyan-50 p-4">
              <h3 class="font-bold text-cyan-800 mb-2">
                🔢 Nulos em Numéricos ({{
                  treatmentDiagnosis.null_numeric_issues.length
                }})
              </h3>
              <div
                v-if="treatmentDiagnosis.null_numeric_issues.length > 0"
                class="flex flex-wrap gap-2"
              >
                <span
                  v-for="col in treatmentDiagnosis.null_numeric_issues"
                  :key="col"
                  class="px-2 py-1 bg-cyan-200 text-cyan-800 text-xs rounded"
                >
                  {{ col }}
                </span>
              </div>
              <p v-else class="text-sm text-cyan-700">✓ Sem problemas</p>
            </div>

            <!-- Diagnósticos Avançados (Fase 2.1) -->
            <div class="border-t-2 border-gray-200 pt-4 mt-4">
              <h3 class="font-bold text-gray-800 mb-3">
                🔍 Diagnósticos Avançados
              </h3>

              <div class="grid grid-cols-2 gap-3">
                <!-- Brand Issues -->
                <div
                  :class="[
                    'p-3 rounded-lg border-l-4',
                    treatmentDiagnosis.brand_issues > 0
                      ? 'border-red-500 bg-red-50'
                      : 'border-green-500 bg-green-50',
                  ]"
                >
                  <div
                    class="font-semibold text-sm"
                    :class="
                      treatmentDiagnosis.brand_issues > 0
                        ? 'text-red-800'
                        : 'text-green-800'
                    "
                  >
                    Brand
                  </div>
                  <div
                    class="text-2xl font-bold"
                    :class="
                      treatmentDiagnosis.brand_issues > 0
                        ? 'text-red-600'
                        : 'text-green-600'
                    "
                  >
                    {{ treatmentDiagnosis.brand_issues }}
                  </div>
                  <div class="text-xs text-gray-600">linhas com problemas</div>
                </div>

                <!-- NCM Issues -->
                <div
                  :class="[
                    'p-3 rounded-lg border-l-4',
                    treatmentDiagnosis.ncm_issues > 0
                      ? 'border-red-500 bg-red-50'
                      : 'border-green-500 bg-green-50',
                  ]"
                >
                  <div
                    class="font-semibold text-sm"
                    :class="
                      treatmentDiagnosis.ncm_issues > 0
                        ? 'text-red-800'
                        : 'text-green-800'
                    "
                  >
                    NCM
                  </div>
                  <div
                    class="text-2xl font-bold"
                    :class="
                      treatmentDiagnosis.ncm_issues > 0
                        ? 'text-red-600'
                        : 'text-green-600'
                    "
                  >
                    {{ treatmentDiagnosis.ncm_issues }}
                  </div>
                  <div class="text-xs text-gray-600">linhas com problemas</div>
                </div>

                <!-- Barcode Issues -->
                <div
                  :class="[
                    'p-3 rounded-lg border-l-4',
                    treatmentDiagnosis.barcode_issues > 0
                      ? 'border-red-500 bg-red-50'
                      : 'border-green-500 bg-green-50',
                  ]"
                >
                  <div
                    class="font-semibold text-sm"
                    :class="
                      treatmentDiagnosis.barcode_issues > 0
                        ? 'text-red-800'
                        : 'text-green-800'
                    "
                  >
                    Barcode
                  </div>
                  <div
                    class="text-2xl font-bold"
                    :class="
                      treatmentDiagnosis.barcode_issues > 0
                        ? 'text-red-600'
                        : 'text-green-600'
                    "
                  >
                    {{ treatmentDiagnosis.barcode_issues }}
                  </div>
                  <div class="text-xs text-gray-600">linhas com problemas</div>
                </div>

                <!-- Weight Issues -->
                <div
                  :class="[
                    'p-3 rounded-lg border-l-4',
                    treatmentDiagnosis.weight_issues > 0
                      ? 'border-red-500 bg-red-50'
                      : 'border-green-500 bg-green-50',
                  ]"
                >
                  <div
                    class="font-semibold text-sm"
                    :class="
                      treatmentDiagnosis.weight_issues > 0
                        ? 'text-red-800'
                        : 'text-green-800'
                    "
                  >
                    Pesos
                  </div>
                  <div
                    class="text-2xl font-bold"
                    :class="
                      treatmentDiagnosis.weight_issues > 0
                        ? 'text-red-600'
                        : 'text-green-600'
                    "
                  >
                    {{ treatmentDiagnosis.weight_issues }}
                  </div>
                  <div class="text-xs text-gray-600">linhas com problemas</div>
                </div>

                <!-- Dimension Issues -->
                <div
                  :class="[
                    'p-3 rounded-lg border-l-4',
                    treatmentDiagnosis.dimension_issues > 0
                      ? 'border-red-500 bg-red-50'
                      : 'border-green-500 bg-green-50',
                  ]"
                >
                  <div
                    class="font-semibold text-sm"
                    :class="
                      treatmentDiagnosis.dimension_issues > 0
                        ? 'text-red-800'
                        : 'text-green-800'
                    "
                  >
                    Dimensões
                  </div>
                  <div
                    class="text-2xl font-bold"
                    :class="
                      treatmentDiagnosis.dimension_issues > 0
                        ? 'text-red-600'
                        : 'text-green-600'
                    "
                  >
                    {{ treatmentDiagnosis.dimension_issues }}
                  </div>
                  <div class="text-xs text-gray-600">linhas com problemas</div>
                </div>

                <!-- Search Ref Issues -->
                <div
                  :class="[
                    'p-3 rounded-lg border-l-4',
                    treatmentDiagnosis.search_ref_issues > 0
                      ? 'border-red-500 bg-red-50'
                      : 'border-green-500 bg-green-50',
                  ]"
                >
                  <div
                    class="font-semibold text-sm"
                    :class="
                      treatmentDiagnosis.search_ref_issues > 0
                        ? 'text-red-800'
                        : 'text-green-800'
                    "
                  >
                    Search Ref
                  </div>
                  <div
                    class="text-2xl font-bold"
                    :class="
                      treatmentDiagnosis.search_ref_issues > 0
                        ? 'text-red-600'
                        : 'text-green-600'
                    "
                  >
                    {{ treatmentDiagnosis.search_ref_issues }}
                  </div>
                  <div class="text-xs text-gray-600">linhas com problemas</div>
                </div>

                <!-- Manufacturer Ref Issues -->
                <div
                  :class="[
                    'p-3 rounded-lg border-l-4',
                    treatmentDiagnosis.manufacturer_ref_issues > 0
                      ? 'border-red-500 bg-red-50'
                      : 'border-green-500 bg-green-50',
                  ]"
                >
                  <div
                    class="font-semibold text-sm"
                    :class="
                      treatmentDiagnosis.manufacturer_ref_issues > 0
                        ? 'text-red-800'
                        : 'text-green-800'
                    "
                  >
                    Manuf. Ref
                  </div>
                  <div
                    class="text-2xl font-bold"
                    :class="
                      treatmentDiagnosis.manufacturer_ref_issues > 0
                        ? 'text-red-600'
                        : 'text-green-600'
                    "
                  >
                    {{ treatmentDiagnosis.manufacturer_ref_issues }}
                  </div>
                  <div class="text-xs text-gray-600">linhas com problemas</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Análise de Colunas -->
        <div v-if="columnsAnalysis" class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">Análise de Colunas</h2>

          <div class="space-y-4">
            <!-- Colunas Faltantes -->
            <div
              v-if="
                columnsAnalysis.missing && columnsAnalysis.missing.length > 0
              "
              class="border-l-4 border-red-500 bg-red-50 p-4"
            >
              <h3 class="font-bold text-red-800 mb-2">
                ❌ Faltantes ({{ columnsAnalysis.missing.length }})
              </h3>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="col in columnsAnalysis.missing"
                  :key="col"
                  class="px-2 py-1 bg-red-200 text-red-800 text-xs rounded"
                >
                  {{ col }}
                </span>
              </div>
            </div>

            <!-- Colunas Extras -->
            <div
              v-if="columnsAnalysis.extra && columnsAnalysis.extra.length > 0"
              class="border-l-4 border-yellow-500 bg-yellow-50 p-4"
            >
              <h3 class="font-bold text-yellow-800 mb-2">
                ⚠️ Não Reconhecidas ({{ columnsAnalysis.extra.length }})
              </h3>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="col in columnsAnalysis.extra"
                  :key="col"
                  class="px-2 py-1 bg-yellow-200 text-yellow-800 text-xs rounded"
                >
                  {{ col }}
                </span>
              </div>
            </div>

            <!-- Colunas Presentes -->
            <div class="border-l-4 border-green-500 bg-green-50 p-4">
              <h3 class="font-bold text-green-800 mb-2">
                ✅ Presentes ({{ columnsAnalysis.present.length }})
              </h3>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="col in columnsAnalysis.present"
                  :key="col"
                  class="px-2 py-1 bg-green-200 text-green-800 text-xs rounded"
                >
                  {{ col }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Preview dos Dados -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-bold mb-4">Preview dos Dados</h2>

          <div v-if="previewData">
            <div class="mb-4 text-sm text-gray-600">
              <p>Total de linhas: {{ previewData.total_rows }}</p>
              <p>
                Página: {{ previewData.page }} ({{ previewData.page_size }}
                linhas por página)
              </p>
            </div>

            <!-- Paginação -->
            <div class="flex gap-2 mb-4">
              <button
                @click="
                  currentPage--;
                  loadPreview();
                "
                :disabled="currentPage === 1"
                class="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                @click="
                  currentPage++;
                  loadPreview();
                "
                :disabled="
                  currentPage * previewData.page_size >= previewData.total_rows
                "
                class="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50"
              >
                Próximo
              </button>
            </div>

            <!-- Tabela -->
            <div class="overflow-x-auto max-h-96">
              <table class="min-w-full text-xs border">
                <thead class="bg-gray-100">
                  <tr>
                    <th
                      v-for="col in previewData.columns"
                      :key="col"
                      class="px-2 py-2 text-left border"
                    >
                      {{ col }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(row, idx) in previewData.rows"
                    :key="idx"
                    class="border-t"
                  >
                    <td
                      v-for="col in previewData.columns"
                      :key="col"
                      class="px-2 py-2 border"
                    >
                      {{ row[col] }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-else class="text-gray-500 text-center py-8">
            Selecione um projeto e clique em "Visualizar Preview"
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
