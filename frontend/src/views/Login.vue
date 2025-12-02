<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import api from "../services/api";

const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

const handleLogin = async () => {
  error.value = "";
  loading.value = true;

  try {
    const response = await api.login(username.value, password.value);

    console.log("Login response:", response.data);

    // Salvar token e dados do usuário
    localStorage.setItem("access_token", response.data.access_token);
    localStorage.setItem("username", username.value);

    // Decodificar token para pegar a role (simples parse do JWT)
    const tokenParts = response.data.access_token.split(".");
    const payload = JSON.parse(atob(tokenParts[1]));
    localStorage.setItem("user_role", payload.role);

    console.log("Token saved, redirecting to service-selector");

    // Redirecionar para seleção de serviço
    router.push("/service-selector");
  } catch (err) {
    console.error("Login error:", err);
    error.value =
      err.response?.data?.detail ||
      "Erro ao fazer login. Verifique suas credenciais.";
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100"
  >
    <div class="w-full max-w-md">
      <!-- Logo/Título -->
      <div class="text-center mb-8">
        <h1 class="text-4xl font-bold text-navy mb-2">Replicas-v2</h1>
        <p class="text-gray-600">Sistema de Gerenciamento de Réplicas</p>
      </div>

      <!-- Card de Login -->
      <div class="bg-white rounded-2xl shadow-xl p-8">
        <h2 class="text-2xl font-semibold text-gray-800 mb-6">Entrar</h2>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <!-- Campo Usuário -->
          <div>
            <label
              for="username"
              class="block text-sm font-medium text-gray-700 mb-2"
            >
              Usuário
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              required
              class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-navy focus:border-transparent transition-all outline-none"
              placeholder="Digite seu usuário"
            />
          </div>

          <!-- Campo Senha -->
          <div>
            <label
              for="password"
              class="block text-sm font-medium text-gray-700 mb-2"
            >
              Senha
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-navy focus:border-transparent transition-all outline-none"
              placeholder="Digite sua senha"
            />
          </div>

          <!-- Mensagem de Erro -->
          <div
            v-if="error"
            class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm"
          >
            {{ error }}
          </div>

          <!-- Botão de Login -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-navy text-white py-3 rounded-lg font-semibold hover:bg-navy-dark transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
          >
            <span v-if="!loading">Entrar</span>
            <span v-else class="flex items-center justify-center">
              <svg
                class="animate-spin h-5 w-5 mr-2"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Carregando...
            </span>
          </button>
        </form>
      </div>

      <!-- Footer -->
      <p class="text-center text-gray-500 text-sm mt-6">
        © 2025 Replicas-v2. Todos os direitos reservados.
      </p>
    </div>
  </div>
</template>
