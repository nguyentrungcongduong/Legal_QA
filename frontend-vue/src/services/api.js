/**
 * services/api.js
 * Dung axios instance (tu plugins/api.js) voi JWT token tu dong
 */
import api from '@/plugins/api'

/**
 * Gui cau hoi phap ly voi lich su hoi thoai cho multi-turn memory.
 *
 * @param {string}   question    - Cau hoi hien tai cua user
 * @param {Array}    chatHistory - [{role: "user"|"assistant", content: string}]
 * @param {number}   topK        - So luong chunks can retrieve
 * @returns {Promise<{answer, citations, conflicts, rewritten_query}>}
 */
export async function queryLegalQA(question, chatHistory = [], topK = 5) {
  const response = await api.post('/api/ai/query', {
    question,
    top_k: topK,
    // Chi gui 6 messages gan nhat (3 turns) de tranh payload qua lon
    chat_history: chatHistory.slice(-6).map(m => ({
      role: m.role,
      content: typeof m.content === 'string' ? m.content.slice(0, 400) : ''
    }))
  })
  return response.data
}
