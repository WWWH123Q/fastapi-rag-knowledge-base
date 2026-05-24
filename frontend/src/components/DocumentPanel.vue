<script setup>
import { shortHash, truncateFilename } from '../types/rag'

defineProps({
  documents: { type: Array, default: () => [] },
  documentsTotal: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  deleteLoadingHash: { type: String, default: '' },
  activeFileHash: { type: String, default: '' },
})

const emit = defineEmits(['refresh', 'filter', 'delete'])
</script>

<template>
  <section class="panel doc-panel">
    <div class="panel-head doc-panel-head">
      <div>
        <h2>知识库文档</h2>
        <p>华交888实验室内部资料 · 共 {{ documentsTotal }} 份</p>
      </div>
      <button class="btn btn-ghost btn-sm" type="button" :disabled="loading" @click="emit('refresh')">
        刷新
      </button>
    </div>

    <div v-if="error" class="alert error doc-panel-alert">{{ error }}</div>

    <div class="doc-panel-body">
      <div v-if="loading" class="loading compact">加载中…</div>
      <div v-else-if="!documents.length" class="empty compact">
        <p>暂无内部资料</p>
        <span>上传论文、竞赛记录或 GPU 说明等文档</span>
      </div>
      <div v-else class="doc-scroll">
        <article
          v-for="doc in documents"
          :key="doc.file_hash"
          class="doc-item card-hover-subtle"
          :class="{ 'doc-item-active': activeFileHash && activeFileHash === doc.file_hash }"
        >
          <span
            v-if="activeFileHash && activeFileHash === doc.file_hash"
            class="doc-active-badge"
          >
            当前过滤
          </span>
          <div class="doc-item-main">
            <h3 class="doc-name" :title="doc.filename">{{ truncateFilename(doc.filename, 32) }}</h3>
            <div class="doc-meta">
              <span class="tag tag-ext">{{ doc.file_ext || '?' }}</span>
              <span class="tag tag-chunk">{{ doc.chunk_count ?? 0 }}</span>
            </div>
            <div class="doc-foot">
              <code class="hash-tag" :title="doc.file_hash">{{ shortHash(doc.file_hash, 10) }}</code>
              <span class="doc-time">{{ doc.uploaded_at || '--' }}</span>
            </div>
          </div>
          <div class="doc-actions">
            <button class="btn btn-ghost btn-xs" type="button" @click="emit('filter', doc)">
              过滤
            </button>
            <button
              class="btn btn-danger-soft btn-xs"
              type="button"
              :disabled="deleteLoadingHash === doc.file_hash"
              @click="emit('delete', doc)"
            >
              {{ deleteLoadingHash === doc.file_hash ? '…' : '删除' }}
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
