<template>
  <section class="citations">
    <h2>Citations</h2>
    <div v-if="!citations.length" class="empty">Chua co citation.</div>
    <article v-for="(c, idx) in citations" :key="`${c.chunk_id}-${idx}`" class="citation">
      <h3>{{ c.law_name }} - {{ c.article }} {{ c.clause ? `(${c.clause})` : "" }}</h3>
      <p>{{ c.content }}</p>
    </article>
  </section>
</template>

<script setup>
defineProps({
  citations: {
    type: Array,
    default: () => [],
  },
});
</script>

<style scoped>
.citations {
  border-left: 1px solid #ddd;
  padding-left: 16px;
}
.citation {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid #eee;
  border-radius: 8px;
}
.empty {
  color: #888;
}
</style>
