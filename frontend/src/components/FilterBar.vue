<script setup>
import { ref } from 'vue'

defineProps({
  filterLabel: { type: String, default: '' },
  hasFilter: { type: Boolean, default: false },
  filterFilename: { type: String, default: '' },
  filterFileHash: { type: String, default: '' },
  filterFileExt: { type: String, default: '' },
})

const emit = defineEmits(['update:filterFilename', 'update:filterFileHash', 'update:filterFileExt', 'clear'])

const expanded = ref(false)

function update(field, value) {
  emit(`update:${field}`, value)
}
</script>

<template>
  <section class="filter-bar panel">
    <div class="filter-bar-top">
      <div class="filter-bar-info">
        <h2>资料范围</h2>
        <p v-if="!hasFilter" class="filter-empty">当前未限定资料范围</p>
        <div v-else class="filter-active">
          <span class="filter-chip">当前过滤：{{ filterLabel }}</span>
        </div>
      </div>
      <div class="filter-bar-actions">
        <button
          class="btn btn-ghost btn-sm"
          type="button"
          @click="expanded = !expanded"
        >
          {{ expanded ? '收起高级筛选' : '展开高级筛选' }}
        </button>
        <button
          v-if="hasFilter"
          class="btn btn-secondary btn-sm"
          type="button"
          @click="emit('clear')"
        >
          清空过滤
        </button>
      </div>
    </div>

    <div v-show="expanded" class="filter-advanced">
      <label class="field">
        <span>文件名 filename</span>
        <input
          :value="filterFilename"
          class="input"
          placeholder="例如 华交888实验室_竞赛获奖记录.md"
          @input="update('filterFilename', $event.target.value)"
        />
      </label>
      <label class="field">
        <span>file_hash</span>
        <input
          :value="filterFileHash"
          class="input"
          placeholder="文档 hash"
          @input="update('filterFileHash', $event.target.value)"
        />
      </label>
      <label class="field">
        <span>文件类型 file_ext</span>
        <select
          :value="filterFileExt"
          class="input"
          @change="update('filterFileExt', $event.target.value)"
        >
          <option value="">全部类型</option>
          <option value=".txt">.txt</option>
          <option value=".md">.md</option>
          <option value=".pdf">.pdf</option>
          <option value=".docx">.docx</option>
          <option value=".csv">.csv</option>
          <option value=".xlsx">.xlsx</option>
          <option value=".xls">.xls</option>
        </select>
      </label>
    </div>
  </section>
</template>

<style scoped>
.filter-bar {
  padding: 16px 20px;
}

.filter-bar-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.filter-bar h2 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.filter-empty {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}

.filter-active {
  margin-top: 2px;
}

.filter-chip {
  display: inline-flex;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid #99f6e4;
  border-radius: 999px;
}

.filter-bar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.filter-advanced {
  display: grid;
  grid-template-columns: 1fr 1fr 160px;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f1f5f9;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .filter-advanced {
    grid-template-columns: 1fr;
  }
}
</style>
