<script setup>
defineProps({
  open: { type: Boolean, default: false },
  module: { type: Object, default: null },
  matchedDocs: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'apply-filter', 'apply-question'])
</script>

<template>
  <Teleport to="body">
    <div v-if="open && module" class="modal-backdrop" @click.self="emit('close')">
      <div class="modal-card" role="dialog" aria-modal="true">
        <button class="modal-close" type="button" aria-label="关闭" @click="emit('close')">×</button>
        <span class="modal-icon">{{ module.icon }}</span>
        <h3 class="modal-title">{{ module.detailTitle || module.title }}</h3>
        <p class="modal-desc">{{ module.description }}</p>

        <div v-if="matchedDocs.length" class="modal-docs">
          <span class="modal-label">匹配资料（{{ matchedDocs.length }}）</span>
          <ul>
            <li v-for="doc in matchedDocs.slice(0, 5)" :key="doc.file_hash">
              {{ doc.filename }}
            </li>
            <li v-if="matchedDocs.length > 5">… 另有 {{ matchedDocs.length - 5 }} 份</li>
          </ul>
        </div>
        <p v-else class="modal-empty">暂无匹配文档，可先上传相关实验室资料。</p>

        <div class="modal-questions">
          <span class="modal-label">推荐提问</span>
          <button
            v-for="q in module.questions"
            :key="q"
            type="button"
            class="question-chip"
            @click="emit('apply-question', q)"
          >
            {{ q }}
          </button>
        </div>

        <div class="modal-actions">
          <button
            v-if="matchedDocs.length"
            class="btn btn-primary"
            type="button"
            @click="emit('apply-filter', matchedDocs[0])"
          >
            作为过滤条件检索
          </button>
          <button class="btn btn-secondary" type="button" @click="emit('close')">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(4px);
}

.modal-card {
  position: relative;
  width: min(480px, 100%);
  max-height: 85vh;
  overflow-y: auto;
  padding: 28px 24px 24px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
}

.modal-close {
  position: absolute;
  top: 12px;
  right: 14px;
  width: 32px;
  height: 32px;
  border: none;
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 20px;
  line-height: 1;
  color: #64748b;
  cursor: pointer;
}

.modal-close:hover {
  background: #e2e8f0;
}

.modal-icon {
  font-size: 28px;
}

.modal-title {
  margin: 10px 0 8px;
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.modal-desc {
  margin: 0 0 16px;
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
}

.modal-label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.modal-docs ul {
  margin: 0 0 16px;
  padding-left: 18px;
  color: #475569;
  font-size: 13px;
}

.modal-empty {
  margin: 0 0 16px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 10px;
  color: #64748b;
  font-size: 13px;
}

.modal-questions {
  margin-bottom: 20px;
}

.question-chip {
  display: block;
  width: 100%;
  margin-bottom: 8px;
  padding: 10px 12px;
  text-align: left;
  font: inherit;
  font-size: 13px;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.question-chip:hover {
  background: #dbeafe;
}

.modal-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
