import request from '../utils/request'

export const getAgents = () => request.get('/agents')
export const getAgent = (id) => request.get(`/agents/${id}`)
export const updateAgent = (id, data) => request.put(`/agents/${id}`, data)

export const getSources = () => request.get('/sources')
export const createSource = (data) => request.post('/sources', data)
export const updateSource = (id, data) => request.put(`/sources/${id}`, data)
export const deleteSource = (id) => request.delete(`/sources/${id}`)
export const fetchSource = (id) => request.post(`/sources/${id}/fetch`)
export const getNewsArticles = (params) => request.get('/news/articles', { params })
export const getNewsBriefs = (params) => request.get('/news/briefs', { params })
export const syncNews = (params) => request.post('/news/sync', null, { params })
export const getMarketDataOverview = (params) => request.get('/market-data/overview', { params })
export const searchMarketStocks = (params) => request.get('/market-data/stocks/search', { params })
export const syncMarketData = (data) => request.post('/market-data/sync', data)
export const getMarketDataSyncStatus = (syncId) =>
  request.get('/market-data/sync/status', { params: syncId ? { sync_id: syncId } : {} })

export const getRecommendations = (params) => request.get('/recommend', { params })
export const getRecommendDates = () => request.get('/recommend/dates')

export const getReviews = (params) => request.get('/review', { params })

export const getMLExperimentOptions = () => request.get('/ml/options')
export const runMLExperiment = (data) => request.post('/ml/experiments/run', data)

export const getHotKnowledge = (params) => request.get('/knowledge/hot', { params })
export const getColdKnowledge = (agent) => request.get(`/knowledge/cold/${agent}`)
export const deleteHotKnowledge = (id) => request.delete(`/knowledge/hot/${id}`)

export const runBacktest = (params) => request.post('/backtest', null, { params })

export const getTrades = (params) => request.get('/trades', { params })
export const createTrade = (data) => request.post('/trades', data)

export const runWorkflow = (type, params) => request.post(`/workflow/${type}`, null, { params })
export const getWorkflowStatus = (id) => request.get('/workflow/status', { params: { workflow_id: id } })

export const getUsers = () => request.get('/users')
export const createUser = (data) => request.post('/users', data)
export const updateUser = (id, data) => request.put(`/users/${id}`, data)
export const deleteUser = (id) => request.delete(`/users/${id}`)
export const getAdminUsageLogs = (params) => request.get('/admin/logs', { params })
