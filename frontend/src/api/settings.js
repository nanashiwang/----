import request from '../utils/request'

export const getSettings = (category) => request.get(`/settings/${category}`)
export const updateSettings = (category, data) => request.put(`/settings/${category}`, data)
export const testLLM = (data) => request.post('/settings/test-llm', data, { timeout: 65000 })
export const testTushare = (data) => request.post('/settings/test-tushare', data)
