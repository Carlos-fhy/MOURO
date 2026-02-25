// 求解接口
import request from './request'

// 启动求解
export function startSolve(params) {
  return request.post('/solve/start', params)
}

// 获取求解结果
export function getResult(taskId) {
  return request.get(`/solve/result/${taskId}`)
}
