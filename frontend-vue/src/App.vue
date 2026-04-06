<template>
  <div class="page-shell">
    <header class="topbar">
      <h1 class="brand">
        Legal AI <span class="accent">Assistant</span>
      </h1>
      <div class="meta-label">Verified Law Source</div>
    </header>

    <main class="workspace">
      <section class="left-pane">
        <div class="ask-group">
          <label class="section-label">Dat cau hoi phap luat</label>
          <form class="ask-form" @submit.prevent="submitQuestion">
            <input
              v-model="question"
              class="question-input"
              placeholder="Vi du: Muc phat nong do con..."
            />
            <button class="send-btn" :disabled="loading">
              {{ loading ? "Dang gui..." : "Gui" }}
            </button>
          </form>
        </div>

        <div class="answer-box">
          <h2 class="answer-title">Cau tra loi tu van</h2>
          <p class="answer-text">{{ answer || "He thong dang san sang ho tro ban..." }}</p>
        </div>
      </section>

      <CitationPanel :citations="citations" />
    </main>
  </div>
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
.page-shell {
  min-height: 100vh;
  background: #fafaf8;
  color: #1a1a1a;
  font-family: "Source Sans 3", Georgia, serif;
  -webkit-font-smoothing: antialiased;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(6px);
  border-bottom: 1px solid #e8e4df;
  padding: 20px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  margin: 0;
  font-family: "Playfair Display", Georgia, serif;
  font-size: 30px;
  font-weight: 700;
  font-style: italic;
  letter-spacing: -0.02em;
}

.accent {
  color: #b8860b;
}

.meta-label {
  font-size: 10px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #6b6b6b;
}

.workspace {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: calc(100vh - 81px);
}

.left-pane {
  border-right: 1px solid #e8e4df;
  padding: 40px;
}

.ask-group {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-label {
  font-size: 11px;
  font-weight: 700;
  color: #b8860b;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-variant: small-caps;
}

.ask-form {
  display: flex;
  gap: 10px;
}

.question-input {
  flex: 1;
  padding: 14px 16px;
  border: 1px solid #e8e4df;
  background: #ffffff;
  border-radius: 3px;
  font-family: "Playfair Display", Georgia, serif;
  font-size: 19px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.question-input:focus {
  outline: none;
  border-color: #b8860b;
  box-shadow: 0 0 0 1px #b8860b;
}

.send-btn {
  background: #b8860b;
  border: 1px solid #b8860b;
  color: #ffffff;
  padding: 0 28px;
  border-radius: 3px;
  font-weight: 600;
  transition: background-color 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  background: #d4a84b;
}

.send-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.answer-box {
  margin-top: 34px;
  padding-top: 34px;
  border-top: 1px solid #e8e4df;
}

.answer-title {
  margin: 0 0 14px;
  font-family: "Playfair Display", Georgia, serif;
  font-size: 36px;
  font-style: italic;
}

.answer-text {
  margin: 0;
  font-size: 20px;
  line-height: 1.7;
  color: #333333;
}

@media (max-width: 1080px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .left-pane {
    border-right: none;
    border-bottom: 1px solid #e8e4df;
  }
}
</style>
