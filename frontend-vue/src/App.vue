<template>
  <main class="layout">
    <section class="chat">
      <h1>Legal QA Chat</h1>
      <form class="ask-form" @submit.prevent="submitQuestion">
        <input v-model="question" placeholder="Nhap cau hoi phap ly..." />
        <button :disabled="loading">{{ loading ? "Dang hoi..." : "Hoi" }}</button>
      </form>

      <div class="answer-box">
        <h2>Answer</h2>
        <p>{{ answer || "Chua co cau tra loi." }}</p>
      </div>
    </section>

    <CitationPanel :citations="citations" />
  </main>
</template>

<script setup>
import { ref } from "vue";
import CitationPanel from "./components/CitationPanel.vue";
import { queryLegalQA } from "./services/api";

const question = ref("Vượt đèn đỏ xe máy bị phạt bao nhiêu?");
const answer = ref("");
const citations = ref([]);
const loading = ref(false);

async function submitQuestion() {
  loading.value = true;
  try {
    const data = await queryLegalQA(question.value);
    answer.value = data.answer;
    citations.value = data.citations || [];
  } catch (error) {
    answer.value = `Loi: ${error.message}`;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 24px;
  max-width: 1200px;
  margin: 24px auto;
  font-family: Arial, sans-serif;
}
.chat {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ask-form {
  display: flex;
  gap: 8px;
}
input {
  flex: 1;
  height: 38px;
  padding: 0 10px;
}
button {
  height: 38px;
  padding: 0 14px;
}
.answer-box {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 12px;
}
</style>
