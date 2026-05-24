<script setup>
import { computed } from 'vue'
import { matchDocsForModule, summarizeExtTypes } from '../types/rag'

const props = defineProps({
  documents: { type: Array, default: () => [] },
  documentTotal: { type: Number, default: 0 },
  chunkTotal: { type: Number, default: 0 },
  modules: { type: Array, required: true },
})

const emit = defineEmits(['open-module'])

const extSummary = computed(() => summarizeExtTypes(props.documents))

function moduleCount(moduleId) {
  if (moduleId === 'overview') return props.documentTotal
  return matchDocsForModule(props.documents, moduleId).length
}

function moduleSubtitle(mod) {
  if (mod.id === 'overview') {
    return `${props.documentTotal} 份资料 · ${props.chunkTotal} chunks · ${extSummary.value}`
  }
  const count = moduleCount(mod.id)
  return count > 0 ? `已收录 ${count} 份相关文档` : '暂无匹配文档，可上传后检索'
}
</script>

<template>
  <section class="overview-section" aria-label="实验室概况">
    <div class="section-intro">
      <h2>实验室知识模块</h2>
      <p>点击模块查看检索建议，或一键设置资料过滤范围</p>
    </div>
    <div class="overview-grid">
      <button
        v-for="mod in modules"
        :key="mod.id"
        type="button"
        class="overview-card card-hover"
        @click="emit('open-module', mod.id)"
      >
        <span class="overview-arrow">查看 →</span>
        <span class="overview-icon">{{ mod.icon }}</span>
        <h3 class="overview-title">{{ mod.title }}</h3>
        <p class="overview-sub">{{ moduleSubtitle(mod) }}</p>
      </button>
    </div>
  </section>
</template>

<style scoped>
.overview-section {
  margin-bottom: 20px;
}

.section-intro {
  margin-bottom: 14px;
}

.section-intro h2 {
  margin: 0 0 4px;
  font-size: 17px;
  font-weight: 700;
  color: #1f2937;
}

.section-intro p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.overview-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  padding: 18px 18px 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.card-hover {
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.card-hover:hover {
  transform: translateY(-4px) scale(1.015);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.1);
  border-color: #bfdbfe;
}

.overview-arrow {
  position: absolute;
  top: 14px;
  right: 14px;
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  transition: color 0.15s;
}

.overview-card:hover .overview-arrow {
  color: #2563eb;
}

.overview-icon {
  font-size: 26px;
  margin-bottom: 10px;
}

.overview-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.overview-sub {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

@media (max-width: 960px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 560px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
