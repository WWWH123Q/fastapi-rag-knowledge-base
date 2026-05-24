<script setup>
import { computed, onMounted, ref } from 'vue'
import { BASE_URL, getErrorMessage } from './api/request'
import {
  askHybrid,
  askLocal,
  askWeb,
  checkHealth,
  deleteDocument,
  listDocuments,
  searchDocuments,
  uploadDocument,
} from './api/rag'
import ChunkResultCard from './components/ChunkResultCard.vue'
import DocumentPanel from './components/DocumentPanel.vue'
import FilterBar from './components/FilterBar.vue'
import ModuleDetailModal from './components/ModuleDetailModal.vue'
import OverviewCards from './components/OverviewCards.vue'
import {
  OVERVIEW_MODULES,
  buildMetadataFilter,
  confidenceClass,
  confidenceLabel,
  extractRerankDebug,
  formatScore,
  matchDocsForModule,
  sourceLabel,
  sourceTagClass,
} from './types/rag'

const ACCEPT_EXT = '.txt,.md,.pdf,.docx,.csv,.xlsx,.xls'
const HERO_TAGS = ['Local RAG', 'Hybrid Search', 'BM25 + Vector', 'Rerank Diagnosis']

const healthStatus = ref('checking')
const healthMessage = ref('检测中')
const apiKey = ref(localStorage.getItem('rag_api_key') || '')
const settingsOpen = ref(false)

const uploadInput = ref(null)
const uploadLoading = ref(false)
const uploadError = ref('')
const uploadResult = ref(null)

const documents = ref([])
const documentsTotal = ref(0)
const documentsLoading = ref(false)
const documentsError = ref('')
const deleteLoadingHash = ref('')

const filterFilename = ref('')
const filterFileHash = ref('')
const filterFileExt = ref('')

const searchQuery = ref('')
const searchTopK = ref(5)
const searchAdvancedOpen = ref(false)
const searchLoading = ref(false)
const searchError = ref('')
const searchResults = ref(null)

const askModes = [
  { key: 'local', label: '本地 RAG', hint: '实验室私有资料' },
  { key: 'web', label: 'Web RAG', hint: '互联网公开信息' },
  { key: 'hybrid', label: 'Hybrid RAG', hint: '本地 + 联网融合' },
]
const askMode = ref('local')
const askQuery = ref('')
const askTopK = ref(5)
const askLocalTopK = ref(5)
const askWebTopK = ref(5)
const askProvider = ref('')
const askAdvancedOpen = ref(false)
const askLoading = ref(false)
const askError = ref('')
const askAnswer = ref('')
const askSources = ref([])
const askDebug = ref(null)
const debugExpanded = ref(false)
const lowConfidence = ref(false)

const moduleModalOpen = ref(false)
const activeModuleId = ref('')

const exampleQuestions = [
  '华为杯数学建模有哪些学生获奖？',
  '某个 SCI 期刊有没有投稿经验？',
  'GPU 服务器使用有什么规范？',
  '近几年实验室学生发表过哪些论文？',
  '如果服务器显存不够怎么办？',
]

const statusLabel = computed(() => {
  if (healthStatus.value === 'online') return '服务正常'
  if (healthStatus.value === 'offline') return '服务离线'
  return '检测中'
})

const apiKeyEnabled = computed(() => Boolean(apiKey.value.trim()))

const chunkTotal = computed(() =>
  documents.value.reduce((sum, doc) => sum + (Number(doc.chunk_count) || 0), 0),
)

const filterLabel = computed(() => {
  if (filterFilename.value) return filterFilename.value
  if (filterFileHash.value) return `hash ${filterFileHash.value.slice(0, 10)}…`
  if (filterFileExt.value) return `类型 ${filterFileExt.value}`
  return ''
})

const hasFilter = computed(() => Boolean(filterLabel.value))

const activeModule = computed(() =>
  OVERVIEW_MODULES.find((m) => m.id === activeModuleId.value) || null,
)

const moduleMatchedDocs = computed(() =>
  matchDocsForModule(documents.value, activeModuleId.value),
)

const currentSourceTitle = computed(() => {
  if (askMode.value === 'local') return '本地引用资料'
  if (askMode.value === 'web') return '网络参考来源'
  return '混合参考来源'
})

const askButtonLabel = computed(() => {
  if (askLoading.value) return '生成中…'
  if (askMode.value === 'hybrid') return '混合检索回答'
  return '生成回答'
})

const confidenceText = computed(() => confidenceLabel(askDebug.value))
const confidenceCss = computed(() => confidenceClass(askDebug.value))

function saveApiKey() {
  const value = apiKey.value.trim()
  if (value) localStorage.setItem('rag_api_key', value)
  else localStorage.removeItem('rag_api_key')
}

async function fetchHealth() {
  healthStatus.value = 'checking'
  healthMessage.value = '检测中'
  try {
    const { data } = await checkHealth()
    healthStatus.value = data?.status === 'ok' ? 'online' : 'offline'
    healthMessage.value = data?.status === 'ok' ? '后端已连接' : '响应异常'
  } catch {
    healthStatus.value = 'offline'
    healthMessage.value = '无法连接'
  }
}

function metadataFilterPayload() {
  return buildMetadataFilter({
    filename: filterFilename.value,
    file_hash: filterFileHash.value,
    file_ext: filterFileExt.value,
  })
}

function clearFilters() {
  filterFilename.value = ''
  filterFileHash.value = ''
  filterFileExt.value = ''
}

function setFilterFromDoc(doc) {
  filterFilename.value = doc.filename || ''
  filterFileHash.value = doc.file_hash || ''
  filterFileExt.value = doc.file_ext || ''
}

function openModule(moduleId) {
  activeModuleId.value = moduleId
  moduleModalOpen.value = true
}

function closeModule() {
  moduleModalOpen.value = false
}

function handleModuleFilter(doc) {
  if (doc) setFilterFromDoc(doc)
  closeModule()
}

function handleModuleQuestion(q) {
  searchQuery.value = q
  askQuery.value = q
  searchError.value = ''
  askError.value = ''
  closeModule()
}

function applyExample(question) {
  searchQuery.value = question
  askQuery.value = question
  searchError.value = ''
  askError.value = ''
}

async function handleUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return

  uploadLoading.value = true
  uploadError.value = ''
  uploadResult.value = null

  try {
    const { data } = await uploadDocument(file)
    uploadResult.value = data
    await loadDocuments()
  } catch (err) {
    uploadError.value = getErrorMessage(err, '上传失败')
  } finally {
    uploadLoading.value = false
    if (uploadInput.value) uploadInput.value.value = ''
  }
}

async function loadDocuments() {
  documentsLoading.value = true
  documentsError.value = ''
  try {
    const { data } = await listDocuments()
    documents.value = data?.documents ?? []
    documentsTotal.value = data?.total ?? documents.value.length
  } catch (err) {
    documentsError.value = getErrorMessage(err, '文档列表加载失败')
    documents.value = []
    documentsTotal.value = 0
  } finally {
    documentsLoading.value = false
  }
}

async function handleDelete(doc) {
  const name = doc.filename || doc.file_hash
  if (!window.confirm(`确定删除「${name}」吗？`)) return

  deleteLoadingHash.value = doc.file_hash
  documentsError.value = ''
  try {
    await deleteDocument(doc.file_hash)
    if (filterFileHash.value === doc.file_hash) clearFilters()
    await loadDocuments()
  } catch (err) {
    documentsError.value = getErrorMessage(err, '删除失败')
  } finally {
    deleteLoadingHash.value = ''
  }
}

async function handleSearch() {
  const query = searchQuery.value.trim()
  if (!query) {
    searchError.value = '请输入检索问题'
    return
  }

  searchLoading.value = true
  searchError.value = ''
  searchResults.value = null
  try {
    const { data } = await searchDocuments({
      query,
      top_k: Number(searchTopK.value) || 5,
      ...metadataFilterPayload(),
    })
    searchResults.value = data
  } catch (err) {
    searchError.value = getErrorMessage(err, '检索失败')
  } finally {
    searchLoading.value = false
  }
}

function providerPayload() {
  const p = askProvider.value.trim()
  return p ? { provider: p } : { provider: null }
}

async function handleAsk() {
  const query = askQuery.value.trim()
  if (!query) {
    askError.value = '请输入问题'
    return
  }

  askLoading.value = true
  askError.value = ''
  askAnswer.value = ''
  askSources.value = []
  askDebug.value = null
  debugExpanded.value = false
  lowConfidence.value = false

  try {
    let data
    if (askMode.value === 'local') {
      const res = await askLocal({
        query,
        top_k: Number(askTopK.value) || 5,
        ...metadataFilterPayload(),
      })
      data = res.data
      askSources.value = data.contexts ?? []
    } else if (askMode.value === 'web') {
      const res = await askWeb({
        query,
        top_k: Number(askTopK.value) || 5,
        ...providerPayload(),
      })
      data = res.data
      askSources.value = data.sources ?? []
    } else {
      const res = await askHybrid({
        query,
        local_top_k: Number(askLocalTopK.value) || 5,
        web_top_k: Number(askWebTopK.value) || 5,
        ...providerPayload(),
        ...metadataFilterPayload(),
      })
      data = res.data
      askSources.value = data.sources ?? []
    }

    askAnswer.value = data?.answer ?? ''
    askDebug.value = extractRerankDebug(data)
    lowConfidence.value = Boolean(data?.rejected_by_low_confidence)
  } catch (err) {
    askError.value = getErrorMessage(err, '问答失败')
  } finally {
    askLoading.value = false
  }
}

onMounted(() => {
  fetchHealth()
  loadDocuments()
})
</script>

<template>
  <div class="app-shell">
    <header class="hero">
      <div class="hero-main">
        <p class="hero-lab">华交888实验室</p>
        <h1>华交888实验室内部知识库</h1>
        <p class="hero-sub">
          实验室成果、论文、竞赛、服务器与内部经验的统一检索平台
        </p>
        <div class="hero-tags">
          <span v-for="tag in HERO_TAGS" :key="tag" class="hero-tag">{{ tag }}</span>
        </div>
        <div class="hero-status">
          <span class="status-dot" :class="healthStatus" />
          <span>{{ statusLabel }} · {{ healthMessage }}</span>
        </div>
      </div>
      <aside class="settings-card">
        <button class="settings-toggle" type="button" @click="settingsOpen = !settingsOpen">
          ⚙ 系统设置
        </button>
        <div v-show="settingsOpen" class="settings-body">
          <label class="field">
            <span>API Key（X-API-Key）</span>
            <input
              v-model="apiKey"
              class="input input-compact"
              type="password"
              placeholder="未开启鉴权可留空"
              @change="saveApiKey"
            />
          </label>
          <p class="settings-hint">
            {{ apiKeyEnabled ? '已填写 · 请求自动携带 Header' : '未填写 API Key' }}
          </p>
          <p class="settings-url">{{ BASE_URL }}</p>
          <div class="settings-actions">
            <button class="btn btn-secondary btn-sm" type="button" @click="saveApiKey">保存</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="fetchHealth">检测连接</button>
          </div>
        </div>
      </aside>
    </header>

    <OverviewCards
      :documents="documents"
      :document-total="documentsTotal"
      :chunk-total="chunkTotal"
      :modules="OVERVIEW_MODULES"
      @open-module="openModule"
    />

    <ModuleDetailModal
      :open="moduleModalOpen"
      :module="activeModule"
      :matched-docs="moduleMatchedDocs"
      @close="closeModule"
      @apply-filter="handleModuleFilter"
      @apply-question="handleModuleQuestion"
    />

    <div class="workbench">
      <div class="workbench-main">
        <section class="panel panel-upload">
          <div class="panel-head">
            <div>
              <h2>上传实验室资料</h2>
              <p>论文、投稿经验、竞赛记录、GPU 说明、组会资料等</p>
            </div>
          </div>
          <input
            ref="uploadInput"
            class="hidden-input"
            type="file"
            :accept="ACCEPT_EXT"
            :disabled="uploadLoading"
            @change="handleUpload"
          />
          <button class="upload-box" type="button" :disabled="uploadLoading" @click="uploadInput?.click()">
            <span class="upload-icon">↑</span>
            <strong>{{ uploadLoading ? '正在入库…' : '点击选择文件上传' }}</strong>
            <span>txt · md · pdf · docx · csv · xlsx · xls</span>
          </button>
          <div v-if="uploadLoading" class="loading-bar"><span class="spinner" />正在解析与向量化…</div>
          <div v-if="uploadError" class="alert error">{{ uploadError }}</div>
          <div v-if="uploadResult" class="upload-success">
            <div><span>文件</span><strong>{{ uploadResult.filename || '--' }}</strong></div>
            <div><span>切片</span><strong>{{ uploadResult.chunk_count ?? '--' }}</strong></div>
            <div><span>维度</span><strong>{{ uploadResult.embedding_dimension ?? '--' }}</strong></div>
            <div class="wide"><span>状态</span><strong>{{ uploadResult.message || '完成' }}</strong></div>
          </div>
        </section>

        <FilterBar
          :filter-label="filterLabel"
          :has-filter="hasFilter"
          :filter-filename="filterFilename"
          :filter-file-hash="filterFileHash"
          :filter-file-ext="filterFileExt"
          @update:filter-filename="filterFilename = $event"
          @update:filter-file-hash="filterFileHash = $event"
          @update:filter-file-ext="filterFileExt = $event"
          @clear="clearFilters"
        />

        <section class="panel panel-search">
          <div class="panel-head">
            <div>
              <h2>本地知识库检索</h2>
              <p>从已上传的实验室私有资料中语义检索，不调用大模型</p>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="searchAdvancedOpen = !searchAdvancedOpen">
              {{ searchAdvancedOpen ? '收起参数' : '检索参数' }}
            </button>
          </div>
          <div class="search-box">
            <input
              v-model="searchQuery"
              class="input input-lg"
              placeholder="例如：华为杯数学建模有哪些学生获奖？"
              @keyup.enter="handleSearch"
            />
            <button class="btn btn-primary btn-lg" type="button" :disabled="searchLoading" @click="handleSearch">
              {{ searchLoading ? '检索中…' : '检索资料' }}
            </button>
          </div>
          <div v-show="searchAdvancedOpen" class="advanced-row">
            <label class="field inline">
              <span>返回条数 top_k</span>
              <input v-model.number="searchTopK" class="input number" type="number" min="1" max="20" />
            </label>
          </div>
          <div class="examples">
            <button v-for="q in exampleQuestions" :key="'s-' + q" type="button" @click="applyExample(q)">
              {{ q }}
            </button>
          </div>
          <div v-if="searchLoading" class="loading-bar"><span class="spinner" />检索中…</div>
          <div v-if="searchError" class="alert error">{{ searchError }}</div>
          <div v-if="searchResults" class="result-meta">
            <span>命中 {{ searchResults.results?.length ?? 0 }} 条</span>
            <span v-if="searchResults.embedding_dimension">维度 {{ searchResults.embedding_dimension }}</span>
          </div>
          <div v-if="searchResults?.results?.length" class="source-list">
            <ChunkResultCard
              v-for="item in searchResults.results"
              :key="`${item.rank}-${item.chunk_hash || item.text?.slice(0, 24)}`"
              :item="item"
            />
          </div>
          <div v-else-if="searchResults && !searchLoading" class="empty compact">未检索到相关内容</div>
        </section>

        <section class="panel panel-ask">
          <div class="panel-head">
            <div>
              <h2>智能问答</h2>
              <p>结合实验室内部资料与联网信息，生成可读回答</p>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="askAdvancedOpen = !askAdvancedOpen">
              {{ askAdvancedOpen ? '收起参数' : '问答参数' }}
            </button>
          </div>

          <div class="mode-tabs">
            <button
              v-for="mode in askModes"
              :key="mode.key"
              class="mode-tab"
              :class="{ active: askMode === mode.key }"
              type="button"
              @click="askMode = mode.key"
            >
              <strong>{{ mode.label }}</strong>
              <span>{{ mode.hint }}</span>
            </button>
          </div>

          <textarea
            v-model="askQuery"
            class="input textarea-lg"
            placeholder="例如：某个 SCI 期刊有没有投稿经验？审稿周期怎么样？"
            rows="4"
          />

          <div v-show="askAdvancedOpen" class="advanced-row">
            <template v-if="askMode !== 'hybrid'">
              <label class="field inline">
                <span>top_k</span>
                <input v-model.number="askTopK" class="input number" type="number" min="1" max="20" />
              </label>
            </template>
            <template v-else>
              <label class="field inline">
                <span>local_top_k</span>
                <input v-model.number="askLocalTopK" class="input number" type="number" min="1" max="20" />
              </label>
              <label class="field inline">
                <span>web_top_k</span>
                <input v-model.number="askWebTopK" class="input number" type="number" min="1" max="10" />
              </label>
            </template>
            <label v-if="askMode !== 'local'" class="field inline">
              <span>provider</span>
              <select v-model="askProvider" class="input select-sm">
                <option value="">默认</option>
                <option value="tavily">tavily</option>
                <option value="duckduckgo">duckduckgo</option>
              </select>
            </label>
          </div>

          <div class="ask-submit-row">
            <button class="btn btn-primary btn-lg" type="button" :disabled="askLoading" @click="handleAsk">
              {{ askButtonLabel }}
            </button>
          </div>

          <div class="examples">
            <button v-for="q in exampleQuestions" :key="'a-' + q" type="button" @click="applyExample(q)">
              {{ q }}
            </button>
          </div>

          <div v-if="askLoading" class="loading-bar"><span class="spinner" />正在生成回答…</div>
          <div v-if="askError" class="alert error">{{ askError }}</div>
          <div v-if="lowConfidence" class="alert warning">
            当前资料置信度较低，答案可能不完整
          </div>

          <div v-if="askAnswer" class="answer-card">
            <h3>回答</h3>
            <p>{{ askAnswer }}</p>
          </div>

          <div v-if="askDebug" class="confidence-bar">
            <div class="confidence-summary" :class="confidenceCss">
              <span>置信度：{{ confidenceText }}</span>
              <span>召回 {{ askDebug.retrieved_count ?? 0 }} 条</span>
              <span>rerank 最高 {{ formatScore(askDebug.best_rerank_score) }}</span>
              <button class="btn-link" type="button" @click="debugExpanded = !debugExpanded">
                {{ debugExpanded ? '收起详情' : '查看详情' }}
              </button>
            </div>
            <div v-show="debugExpanded" class="debug-detail">
              <div><span>best_rerank_score</span><strong>{{ formatScore(askDebug.best_rerank_score) }}</strong></div>
              <div><span>min_rerank_threshold</span><strong>{{ formatScore(askDebug.min_rerank_threshold) }}</strong></div>
              <div><span>reranked_count</span><strong>{{ askDebug.reranked_count ?? 0 }}</strong></div>
              <div><span>低置信拒答</span><strong>{{ askDebug.rejected_by_low_confidence ? '是' : '否' }}</strong></div>
            </div>
          </div>

          <details v-if="askSources.length" class="sources" open>
            <summary>{{ currentSourceTitle }} · {{ askSources.length }} 条</summary>
            <div class="source-list">
              <article
                v-for="item in askSources"
                :key="`${item.rank}-${item.chunk_hash || item.url || item.text?.slice(0, 16)}`"
                class="source-card"
              >
                <div class="source-head">
                  <strong>#{{ item.rank }}</strong>
                  <span>{{ item.filename || item.title || 'unknown' }}</span>
                  <span class="tag" :class="sourceTagClass(sourceLabel(item))">{{ sourceLabel(item) }}</span>
                  <span v-if="item.rerank_score != null">rerank {{ formatScore(item.rerank_score) }}</span>
                </div>
                <a v-if="item.url" :href="item.url" target="_blank" rel="noreferrer">{{ item.url }}</a>
                <p>{{ item.text }}</p>
              </article>
            </div>
          </details>
        </section>
      </div>

      <aside class="workbench-side">
        <DocumentPanel
          :documents="documents"
          :documents-total="documentsTotal"
          :loading="documentsLoading"
          :error="documentsError"
          :delete-loading-hash="deleteLoadingHash"
          :active-file-hash="filterFileHash"
          @refresh="loadDocuments"
          @filter="setFilterFromDoc"
          @delete="handleDelete"
        />
      </aside>
    </div>
  </div>
</template>
