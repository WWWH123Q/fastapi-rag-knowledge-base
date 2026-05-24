/**
 * @typedef {Object} DocumentItem
 * @property {string} filename
 * @property {string} file_hash
 * @property {string} [file_ext]
 * @property {string} [uploaded_at]
 * @property {number} [chunk_count]
 */

/**
 * @typedef {Object} DocumentListResponse
 * @property {number} total
 * @property {DocumentItem[]} documents
 */

/**
 * @typedef {Object} UploadResponse
 * @property {string} message
 * @property {string} filename
 * @property {string} file_hash
 * @property {number} chunk_count
 * @property {number} [embedding_dimension]
 * @property {boolean} [duplicated]
 * @property {string} [file_ext]
 * @property {string} [uploaded_at]
 */

/**
 * @typedef {Object} ContextItem
 * @property {number} rank
 * @property {string} text
 * @property {string} [filename]
 * @property {string} [file_hash]
 * @property {string} [file_ext]
 * @property {string} [uploaded_at]
 * @property {string} [chunk_hash]
 * @property {number|null} [score]
 * @property {number|null} [vector_score]
 * @property {number|null} [bm25_score]
 * @property {number|null} [retrieval_rank]
 * @property {number|null} [rerank_score]
 * @property {string} [retrieval_source]
 * @property {string[]} [retrieval_sources]
 * @property {string} [source_type]
 * @property {string} [provider]
 * @property {string} [title]
 * @property {string} [url]
 */

/**
 * @typedef {Object} SearchResponse
 * @property {string} query
 * @property {number} top_k
 * @property {number} [embedding_dimension]
 * @property {ContextItem[]} [results]
 */

/**
 * @typedef {Object} RerankDebug
 * @property {number|null|undefined} best_rerank_score
 * @property {number|null|undefined} min_rerank_threshold
 * @property {number} [retrieved_count]
 * @property {number} [reranked_count]
 * @property {boolean} [rejected_by_low_confidence]
 */

/**
 * @typedef {Object} AskResponse
 * @property {string} query
 * @property {string} answer
 * @property {number} [top_k]
 * @property {ContextItem[]} [contexts]
 * @property {RerankDebug} [RerankDebug]
 */

/**
 * @typedef {Object} MetadataFilter
 * @property {string} [filename]
 * @property {string} [file_hash]
 * @property {string} [file_ext]
 * @property {string} [uploaded_after]
 * @property {string} [uploaded_before]
 */

/** @param {MetadataFilter} filter */
export function buildMetadataFilter(filter = {}) {
  const payload = {}
  if (filter.filename?.trim()) payload.filename = filter.filename.trim()
  if (filter.file_hash?.trim()) payload.file_hash = filter.file_hash.trim()
  if (filter.file_ext?.trim()) payload.file_ext = filter.file_ext.trim()
  if (filter.uploaded_after?.trim()) payload.uploaded_after = filter.uploaded_after.trim()
  if (filter.uploaded_before?.trim()) payload.uploaded_before = filter.uploaded_before.trim()
  return payload
}

/** @param {unknown} data */
export function extractRerankDebug(data) {
  if (!data || typeof data !== 'object') return null
  if (data.best_rerank_score === undefined && data.retrieved_count === undefined) {
    return null
  }
  return {
    best_rerank_score: data.best_rerank_score ?? null,
    min_rerank_threshold: data.min_rerank_threshold ?? null,
    retrieved_count: data.retrieved_count ?? 0,
    reranked_count: data.reranked_count ?? 0,
    rejected_by_low_confidence: Boolean(data.rejected_by_low_confidence),
  }
}

/** @param {number|null|undefined} score @param {number} [digits=3] */
export function formatScore(score, digits = 3) {
  if (score === null || score === undefined || score === '') return '--'
  const value = Number(score)
  return Number.isFinite(value) ? value.toFixed(digits) : String(score)
}

/** @param {string} [hash] @param {number} [len=12] */
export function shortHash(hash, len = 12) {
  if (!hash) return '--'
  return hash.length > len ? `${hash.slice(0, len)}...` : hash
}

/** @param {ContextItem} item */
export function sourceLabel(item) {
  if (item?.retrieval_source) return item.retrieval_source
  if (Array.isArray(item?.retrieval_sources) && item.retrieval_sources.length) {
    return item.retrieval_sources.join(' + ')
  }
  if (item?.source_type === 'web' || item?.url) return 'web'
  return item?.source_type || item?.provider || 'source'
}

/** @param {string} label */
export function sourceTagClass(label) {
  const key = String(label || '').toLowerCase()
  if (key.includes('web')) return 'tag-web'
  if (key.includes('bm25')) return 'tag-bm25'
  if (key.includes('hybrid')) return 'tag-hybrid'
  if (key.includes('vector')) return 'tag-vector'
  return 'tag-default'
}

/** @param {string} name @param {number} [max=36] */
export function truncateFilename(name, max = 36) {
  if (!name) return 'unknown'
  if (name.length <= max) return name
  const ext = name.includes('.') ? name.slice(name.lastIndexOf('.')) : ''
  const base = name.slice(0, max - ext.length - 1)
  return `${base}…${ext}`
}

/** @type {Array<{id:string,title:string,icon:string,detailTitle?:string,description:string,questions:string[],match:(doc:DocumentItem)=>boolean}>} */
export const OVERVIEW_MODULES = [
  {
    id: 'overview',
    title: '实验室资料总览',
    icon: '📚',
    description:
      '汇总当前知识库中的全部实验室内部资料，可按文档类型浏览与检索。',
    questions: [
      '知识库里目前有哪些类型的资料？',
      '近几年实验室有哪些代表性成果？',
    ],
    match: () => true,
  },
  {
    id: 'sci',
    title: 'SCI 投稿经验',
    icon: '📰',
    detailTitle: 'SCI 投稿经验检索提示',
    description:
      '可检索期刊投稿经历、审稿周期、录用难度、学生评价等信息。',
    questions: [
      '哪些期刊适合降水预测方向？',
      '某个 SCI 期刊有没有投稿经验？',
      '哪些期刊审稿周期较短？',
    ],
    match: (doc) => /SCI/i.test(doc.filename || '') || doc.file_ext === '.xlsx',
  },
  {
    id: 'competition',
    title: '竞赛获奖记录',
    icon: '🏆',
    detailTitle: '竞赛获奖记录检索提示',
    description:
      '可检索华为杯、数学建模、研究生竞赛、互联网+、挑战杯等奖项记录。',
    questions: [
      '华为杯数学建模有哪些学生获奖？',
      '研究生数学建模历年获奖情况如何？',
      '实验室有哪些竞赛获奖记录？',
    ],
    match: (doc) => /竞赛|获奖/.test(doc.filename || ''),
  },
  {
    id: 'gpu',
    title: 'GPU 服务器',
    icon: '🖥️',
    detailTitle: 'GPU 服务器使用提醒',
    description:
      '可检索服务器排队记录、GPU 使用说明、账号规范与注意事项。',
    questions: [
      'GPU 服务器怎么申请使用？',
      '当前有哪些服务器资源？',
      '使用 GPU 时有哪些注意事项？',
    ],
    match: (doc) => /GPU|服务器/i.test(doc.filename || ''),
  },
  {
    id: 'papers',
    title: '学生论文成果',
    icon: '📝',
    description:
      '可检索学生论文、作者、研究方向、年份与期刊信息。',
    questions: [
      '近几年实验室学生发表过哪些论文？',
      '有哪些降水预测相关的论文成果？',
      '某方向有哪些代表性论文？',
    ],
    match: (doc) => /论文|成果/.test(doc.filename || ''),
  },
  {
    id: 'faq',
    title: '内部规范 FAQ',
    icon: '📋',
    description:
      '可查询资料上传规范、脱敏规则、知识库使用说明等内部 FAQ。',
    questions: [
      '知识库资料上传有什么规范？',
      '哪些内容需要脱敏处理？',
      '如何使用实验室内部知识库？',
    ],
    match: (doc) => /FAQ|规范/i.test(doc.filename || ''),
  },
]

/** @param {DocumentItem[]} docs @param {string} moduleId */
export function matchDocsForModule(docs, moduleId) {
  const mod = OVERVIEW_MODULES.find((m) => m.id === moduleId)
  if (!mod) return []
  if (moduleId === 'overview') return docs
  return docs.filter((doc) => mod.match(doc))
}

/** @param {DocumentItem[]} docs */
export function summarizeExtTypes(docs) {
  const counts = {}
  for (const doc of docs) {
    const ext = doc.file_ext || 'unknown'
    counts[ext] = (counts[ext] || 0) + 1
  }
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([ext, n]) => `${ext}×${n}`)
    .join(' · ') || '暂无'
}

/** @param {RerankDebug|null} debug */
export function confidenceLabel(debug) {
  if (!debug) return '暂无'
  if (debug.rejected_by_low_confidence) return '偏低'
  const score = debug.best_rerank_score
  if (score === null || score === undefined) return '暂无'
  const threshold = Number(debug.min_rerank_threshold ?? 0.55)
  if (score >= threshold + 0.12) return '较高'
  if (score >= threshold) return '中等'
  return '偏低'
}

/** @param {RerankDebug|null} debug */
export function confidenceClass(debug) {
  const label = confidenceLabel(debug)
  if (label === '较高') return 'conf-high'
  if (label === '中等') return 'conf-mid'
  if (label === '偏低') return 'conf-low'
  return 'conf-none'
}
