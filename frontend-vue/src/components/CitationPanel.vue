<template>
  <aside class="right-pane">
    <div class="heading-wrap">
      <span class="heading">Can cu phap ly</span>
      <div class="rule-line"></div>
    </div>

    <div class="list">
      <article v-for="(c, idx) in citations" :key="`${c.chunk_id}-${idx}`" :ref="(el) => setCitationRef(el, idx)"
        class="citation" :class="{ active: activeCitationIndex === idx }">
        <div class="source-tag">
          [Nguon {{ idx + 1 }}]
          <button class="source-link" @click="openMetadata(c)">
            {{ c.law_name || "Van ban phap luat" }}
          </button>
        </div>
        <h3 class="citation-title">
          {{ c.article || "Khong ro dieu" }}
          {{ c.clause ? `- ${c.clause}` : "" }}
        </h3>
        <p class="citation-content">{{ c.content }}</p>
      </article>

      <div v-if="!citations.length" class="empty">Chua co trich dan de hien thi.</div>
    </div>

    <!-- Metadata Drawer (Teleport to body) -->
    <DocumentMetadataDrawer
      :is-open="!!selectedCitation"
      :data="selectedCitation"
      @close="selectedCitation = null"
    />
  </aside>
</template>

<script setup>
import { ref, watch } from "vue";
import DocumentMetadataDrawer from "./DocumentMetadataDrawer.vue";

const props = defineProps({
  citations: {
    type: Array,
    default: () => [],
  },
  activeCitationIndex: {
    type: Number,
    default: null,
  },
});

const citationRefs = ref([]);
const selectedCitation = ref(null);

function setCitationRef(el, idx) {
  if (el) citationRefs.value[idx] = el;
}

function openMetadata(citation) {
  selectedCitation.value = citation;
}

watch(
  () => props.activeCitationIndex,
  (idx) => {
    if (idx === null || idx === undefined) return;
    const node = citationRefs.value[idx];
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }
);
</script>

<style scoped>
.right-pane {
  background: rgba(255, 255, 255, 0.32);
  padding: 40px;
  overflow-y: auto;
}

.heading-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
}

.heading {
  font-family: "Playfair Display", Georgia, serif;
  font-size: 32px;
  font-style: italic;
}

.rule-line {
  flex: 1;
  height: 1px;
  background: #e8e4df;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.citation {
  border-left: 2px solid rgba(184, 134, 11, 0.25);
  padding: 8px 0 8px 18px;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.citation:hover {
  border-left-color: #b8860b;
}

.citation.active {
  border-left-color: #b8860b;
  background: rgba(184, 134, 11, 0.09);
}

.source-tag {
  font-size: 10px;
  font-variant: small-caps;
  letter-spacing: 0.08em;
  color: #b8860b;
  margin-bottom: 6px;
}

.source-link {
  border: none;
  padding: 0;
  background: transparent;
  color: #b8860b;
  cursor: pointer;
  font-size: 11px;
  text-decoration: underline;
}

.citation-title {
  margin: 0 0 8px;
  font-family: "Playfair Display", Georgia, serif;
  font-size: 24px;
}

.citation-content {
  margin: 0;
  color: #6b6b6b;
  font-style: italic;
  line-height: 1.65;
}

.empty {
  color: #6b6b6b;
  font-family: "Playfair Display", Georgia, serif;
  font-style: italic;
}

/* Drawer moved to DocumentMetadataDrawer.vue component */

/* Removed - drawer styles now live in DocumentMetadataDrawer.vue */
</style>
