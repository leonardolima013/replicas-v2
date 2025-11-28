<script setup>
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import api from "../services/api";

const router = useRouter();
const userRole = ref(localStorage.getItem("user_role") || "");
const username = ref(localStorage.getItem("username") || "");

// Estados para Admin
const newUser = ref({
  usuario: "",
  password: "",
  role: "dev",
});
const allReplicas = ref([]);
const users = ref([]);

// Estados para Dev
const myReplica = ref(null);
const dbPassword = ref("");
const hasReplica = ref(false);

// Estados gerais
const loading = ref(false);
const error = ref("");
const success = ref("");

const isAdmin = computed(() => userRole.value === "adm");
const isDev = computed(() => userRole.value === "dev");

// Logout
const handleLogout = () => {
  localStorage.clear();
  router.push("/login");
};

// ===== ADMIN FUNCTIONS =====
const createUser = async () => {
  error.value = "";
  success.value = "";
  loading.value = true;

  try {
    await api.createUser(newUser.value);
    success.value = `Usuário ${newUser.value.usuario} criado com sucesso!`;
    newUser.value = { usuario: "", password: "", role: "dev" };
    await loadUsers();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao criar usuário";
  } finally {
    loading.value = false;
  }
};

const loadAllReplicas = async () => {
  try {
    const response = await api.listAllReplicas();
    allReplicas.value = response.replicas;
  } catch (err) {
    console.error("Erro ao carregar réplicas:", err);
  }
};

const loadUsers = async () => {
  try {
    users.value = await api.getUsers();
  } catch (err) {
    console.error("Erro ao carregar usuários:", err);
  }
};

const deleteReplica = async (username) => {
  if (
    !confirm(`Tem certeza que deseja deletar a réplica do usuário ${username}?`)
  )
    return;

  try {
    await api.deleteReplica(username);
    success.value = `Réplica de ${username} deletada com sucesso!`;
    await loadAllReplicas();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao deletar réplica";
  }
};

const deleteAllReplicas = async () => {
  if (
    !confirm("ATENÇÃO: Isso irá deletar TODAS as réplicas. Deseja continuar?")
  )
    return;

  try {
    const response = await api.deleteAllReplicas();
    success.value = `${response.deleted_count} réplica(s) deletada(s) com sucesso!`;
    await loadAllReplicas();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao deletar réplicas";
  }
};

// ===== DEV FUNCTIONS =====
const checkMyReplica = async () => {
  try {
    myReplica.value = await api.getMyReplica();
    hasReplica.value = true;
  } catch (err) {
    if (err.response?.status === 404) {
      hasReplica.value = false;
      myReplica.value = null;
    }
  }
};

const createMyReplica = async () => {
  error.value = "";
  success.value = "";
  loading.value = true;

  try {
    const response = await api.createReplica(dbPassword.value);
    success.value = response.msg;
    dbPassword.value = "";
    await checkMyReplica();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao criar réplica";
  } finally {
    loading.value = false;
  }
};

const deleteMyReplica = async () => {
  if (!confirm("Tem certeza que deseja deletar sua réplica?")) return;

  error.value = "";
  success.value = "";
  loading.value = true;

  try {
    await api.deleteReplica(username.value);
    success.value = "Réplica deletada com sucesso!";
    await checkMyReplica();
  } catch (err) {
    error.value = err.response?.data?.detail || "Erro ao deletar réplica";
  } finally {
    loading.value = false;
  }
};

// Carregar dados ao montar
onMounted(async () => {
  if (isAdmin.value) {
    await loadAllReplicas();
    await loadUsers();
  } else if (isDev.value) {
    await checkMyReplica();
  }
});
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navbar -->
    <nav class="bg-white shadow-md">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center">
            <h1 class="text-2xl font-bold text-navy">Replicas-v2</h1>
            <span
              class="ml-4 px-3 py-1 bg-navy text-white text-xs rounded-full uppercase"
            >
              {{ userRole }}
            </span>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-gray-700"
              >Olá, <strong>{{ username }}</strong></span
            >
            <button
              @click="handleLogout"
              class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all"
            >
              Sair
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Mensagens de Feedback -->
      <div
        v-if="error"
        class="mb-6 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-lg"
      >
        <p class="font-medium">{{ error }}</p>
      </div>
      <div
        v-if="success"
        class="mb-6 bg-green-50 border-l-4 border-green-500 text-green-700 p-4 rounded-lg"
      >
        <p class="font-medium">{{ success }}</p>
      </div>

      <!-- ===== ADMIN VIEW ===== -->
      <div v-if="isAdmin" class="space-y-8">
        <!-- Criar Usuário -->
        <div class="bg-white rounded-2xl shadow-lg p-6">
          <h2 class="text-2xl font-bold text-gray-800 mb-6">
            Criar Novo Usuário
          </h2>
          <form
            @submit.prevent="createUser"
            class="grid grid-cols-1 md:grid-cols-4 gap-4"
          >
            <input
              v-model="newUser.usuario"
              type="text"
              required
              placeholder="Usuário"
              class="px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-navy focus:border-transparent outline-none"
            />
            <input
              v-model="newUser.password"
              type="password"
              required
              placeholder="Senha"
              class="px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-navy focus:border-transparent outline-none"
            />
            <select
              v-model="newUser.role"
              class="px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-navy focus:border-transparent outline-none"
            >
              <option value="dev">Desenvolvedor</option>
              <option value="adm">Administrador</option>
            </select>
            <button
              type="submit"
              :disabled="loading"
              class="bg-navy text-white py-3 rounded-lg font-semibold hover:bg-navy-dark transition-all disabled:opacity-50"
            >
              Criar Usuário
            </button>
          </form>
        </div>

        <!-- Lista de Réplicas Ativas -->
        <div class="bg-white rounded-2xl shadow-lg p-6">
          <div class="flex justify-between items-center mb-6">
            <h2 class="text-2xl font-bold text-gray-800">Réplicas Ativas</h2>
            <div class="flex gap-2">
              <button
                @click="loadAllReplicas"
                class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all"
              >
                Atualizar
              </button>
              <button
                @click="deleteAllReplicas"
                class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all"
              >
                Deletar Todas
              </button>
            </div>
          </div>

          <div
            v-if="allReplicas.length === 0"
            class="text-center py-8 text-gray-500"
          >
            Nenhuma réplica ativa no momento
          </div>

          <div v-else class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Usuário
                  </th>
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Container
                  </th>
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Banco
                  </th>
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Porta
                  </th>
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Status
                  </th>
                  <th
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="replica in allReplicas" :key="replica.container_id">
                  <td class="px-6 py-4 whitespace-nowrap font-medium">
                    {{ replica.username }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {{ replica.container_id }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm">
                    {{ replica.database_name }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm">
                    {{ replica.port }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span
                      :class="{
                        'bg-green-100 text-green-800':
                          replica.status === 'running',
                        'bg-red-100 text-red-800': replica.status !== 'running',
                      }"
                      class="px-2 py-1 rounded-full text-xs font-semibold"
                    >
                      {{ replica.status }}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      @click="deleteReplica(replica.username)"
                      class="text-red-600 hover:text-red-800 font-medium"
                    >
                      Deletar
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- ===== DEV VIEW ===== -->
      <div v-if="isDev" class="space-y-8">
        <!-- Sem Réplica: Criar Nova -->
        <div
          v-if="!hasReplica"
          class="bg-white rounded-2xl shadow-lg p-8 max-w-2xl mx-auto"
        >
          <h2 class="text-2xl font-bold text-gray-800 mb-6">
            Criar Minha Réplica
          </h2>
          <p class="text-gray-600 mb-6">
            Você ainda não possui um banco de dados réplica. Crie um agora!
          </p>

          <form @submit.prevent="createMyReplica" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2"
                >Senha do Banco de Dados</label
              >
              <input
                v-model="dbPassword"
                type="password"
                required
                placeholder="Digite a senha para o banco"
                class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-navy focus:border-transparent outline-none"
              />
            </div>
            <button
              type="submit"
              :disabled="loading"
              class="w-full bg-navy text-white py-3 rounded-lg font-semibold hover:bg-navy-dark transition-all disabled:opacity-50"
            >
              <span v-if="!loading">Criar Réplica</span>
              <span v-else>Criando...</span>
            </button>
          </form>
        </div>

        <!-- Com Réplica: Detalhes e Conexão -->
        <div v-else class="space-y-6 max-w-4xl mx-auto">
          <!-- Card com Informações -->
          <div class="bg-white rounded-2xl shadow-lg p-8">
            <div class="flex justify-between items-start mb-6">
              <div>
                <h2 class="text-2xl font-bold text-gray-800">Minha Réplica</h2>
                <p class="text-gray-600">
                  Banco de dados ativo e pronto para uso
                </p>
              </div>
              <span
                class="px-4 py-2 bg-green-100 text-green-800 rounded-full text-sm font-semibold"
              >
                {{ myReplica.status }}
              </span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div class="bg-gray-50 p-4 rounded-lg">
                <p class="text-sm text-gray-600 mb-1">Host</p>
                <p class="font-mono font-semibold">localhost</p>
              </div>
              <div class="bg-gray-50 p-4 rounded-lg">
                <p class="text-sm text-gray-600 mb-1">Porta</p>
                <p class="font-mono font-semibold">{{ myReplica.port }}</p>
              </div>
              <div class="bg-gray-50 p-4 rounded-lg">
                <p class="text-sm text-gray-600 mb-1">Database</p>
                <p class="font-mono font-semibold">
                  {{ myReplica.database_name }}
                </p>
              </div>
              <div class="bg-gray-50 p-4 rounded-lg">
                <p class="text-sm text-gray-600 mb-1">Usuário</p>
                <p class="font-mono font-semibold">{{ myReplica.username }}</p>
              </div>
            </div>

            <button
              @click="deleteMyReplica"
              :disabled="loading"
              class="w-full bg-red-500 text-white py-3 rounded-lg font-semibold hover:bg-red-600 transition-all disabled:opacity-50"
            >
              Excluir Réplica
            </button>
          </div>

          <!-- Passo a Passo de Conexão -->
          <div class="bg-white rounded-2xl shadow-lg p-8">
            <h3 class="text-xl font-bold text-gray-800 mb-6">
              Como Conectar ao Banco de Dados
            </h3>

            <div class="space-y-4">
              <div class="flex gap-4">
                <div
                  class="flex-shrink-0 w-8 h-8 bg-navy text-white rounded-full flex items-center justify-center font-bold"
                >
                  1
                </div>
                <div>
                  <h4 class="font-semibold text-gray-800 mb-2">
                    Usando DBeaver ou pgAdmin
                  </h4>
                  <p class="text-gray-600 mb-2">
                    Configure a conexão com os seguintes dados:
                  </p>
                  <div class="bg-gray-50 p-3 rounded-lg font-mono text-sm">
                    <p>
                      Host:
                      <span class="text-navy font-semibold">localhost</span>
                    </p>
                    <p>
                      Porta:
                      <span class="text-navy font-semibold">{{
                        myReplica.port
                      }}</span>
                    </p>
                    <p>
                      Database:
                      <span class="text-navy font-semibold">{{
                        myReplica.database_name
                      }}</span>
                    </p>
                    <p>
                      Usuário:
                      <span class="text-navy font-semibold">{{
                        myReplica.username
                      }}</span>
                    </p>
                    <p>
                      Senha:
                      <span class="text-navy font-semibold"
                        >[a senha que você definiu]</span
                      >
                    </p>
                  </div>
                </div>
              </div>

              <div class="flex gap-4">
                <div
                  class="flex-shrink-0 w-8 h-8 bg-navy text-white rounded-full flex items-center justify-center font-bold"
                >
                  2
                </div>
                <div>
                  <h4 class="font-semibold text-gray-800 mb-2">
                    Usando psql (Terminal)
                  </h4>
                  <div
                    class="bg-gray-900 p-3 rounded-lg font-mono text-sm text-green-400"
                  >
                    psql -h localhost -p {{ myReplica.port }} -U
                    {{ myReplica.username }} -d {{ myReplica.database_name }}
                  </div>
                </div>
              </div>

              <div class="flex gap-4">
                <div
                  class="flex-shrink-0 w-8 h-8 bg-navy text-white rounded-full flex items-center justify-center font-bold"
                >
                  3
                </div>
                <div>
                  <h4 class="font-semibold text-gray-800 mb-2">
                    String de Conexão (Python/Node.js)
                  </h4>
                  <div
                    class="bg-gray-900 p-3 rounded-lg font-mono text-sm text-green-400 break-all"
                  >
                    postgresql://{{ myReplica.username }}:[senha]@localhost:{{
                      myReplica.port
                    }}/{{ myReplica.database_name }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
