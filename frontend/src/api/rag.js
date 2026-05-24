/** 实验室 RAG 知识库 API 封装（路径与请求体字段与后端 schema 对齐） */
import request from './request'

export function checkHealth() {
  return request.get('/health')
}

/** @param {File} file */
export function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/rag/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listDocuments() {
  return request.get('/rag/documents')
}

/** @param {string} fileHash */
export function deleteDocument(fileHash) {
  return request.delete(`/rag/documents/${fileHash}`)
}

/** @param {Record<string, unknown>} data SearchRequest */
export function searchDocuments(data) {
  return request.post('/rag/search', data)
}

/** @param {Record<string, unknown>} data AskRequest */
export function askLocal(data) {
  return request.post('/rag/ask', data)
}

/** @param {Record<string, unknown>} data WebSearchRequest */
export function askWeb(data) {
  return request.post('/rag/ask-web', data)
}

/** @param {Record<string, unknown>} data HybridAskRequest */
export function askHybrid(data) {
  return request.post('/rag/ask-hybrid', data)
}
