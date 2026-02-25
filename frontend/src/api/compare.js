// 算法对比接口
import request from './request'

// 启动对比
export function startCompare(params) {
  return request.post('/compare/start', params)
}

// 获取对比结果
export function getCompareResult(taskId) {
  return request.get(`/compare/result/${taskId}`)
}
