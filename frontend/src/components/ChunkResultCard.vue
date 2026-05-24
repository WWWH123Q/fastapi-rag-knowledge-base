<script setup>
import { computed, ref } from 'vue'
import { formatScore, sourceLabel, sourceTagClass, truncateFilename } from '../types/rag'

const props = defineProps({
  item: { type: Object, required: true },
  defaultLines: { type: Number, default: 4 },
})

const expanded = ref(false)

const source = computed(() => sourceLabel(props.item))
const tagClass = computed(() => sourceTagClass(source.value))
const isLong = computed(() => (props.item.text || '').length > 220)
</script>

<template>
  <article class="chunk-card">
    <div class="chunk-head">
      <span class="rank-pill">#{{ item.rank ?? '--' }}</span>
      <span class="tag tag-file" :title="item.filename">{{ truncateFilename(item.filename, 28) }}</span>
      <span v-if="item.file_ext" class="tag tag-ext">{{ item.file_ext }}</span>
      <span class="tag" :class="tagClass">{{ source }}</span>
      <span v-if="item.score != null" class="tag tag-score">score {{ formatScore(item.score) }}</span>
      <span v-if="item.rerank_score != null" class="tag tag-rerank">
        rerank {{ formatScore(item.rerank_score) }}
      </span>
    </div>
    <p class="chunk-text" :class="{ collapsed: !expanded && isLong }">{{ item.text || '（无正文）' }}</p>
    <button
      v-if="isLong"
      class="btn-link"
      type="button"
      @click="expanded = !expanded"
    >
      {{ expanded ? '收起' : '展开全文' }}
    </button>
  </article>
</template>

<style scoped>
.chunk-card {
  padding: 12px 14px;
  background: var(--panel-muted);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.chunk-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.rank-pill {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
  background: var(--soft);
  border-radius: 999px;
}

.chunk-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.55;
  font-size: 13px;
}

.chunk-text.collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.btn-link {
  margin-top: 8px;
  padding: 0;
  border: none;
  background: none;
  color: var(--primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-link:hover {
  text-decoration: underline;
}
</style>
