<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const username = ref(localStorage.getItem("username") || "");

const goToDataValidation = () => {
  router.push("/data-validation-test");
};

const goToDashboard = () => {
  router.push("/dashboard");
};

const logout = () => {
  localStorage.clear();
  router.push("/login");
};
</script>

<template>
  <div class="min-h-screen bg-gray-100 flex items-center justify-center">
    <div class="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
      <h1 class="text-2xl font-bold mb-6 text-center">Selecione o Serviço</h1>

      <div class="space-y-4">
        <button
          @click="goToDataValidation"
          class="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all"
        >
          Data Validation (Teste)
        </button>

        <button
          @click="goToDashboard"
          class="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-all"
        >
          Dashboard
        </button>

        <button
          @click="logout"
          class="w-full px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all"
        >
          Sair
        </button>
      </div>
    </div>
  </div>
</template>
