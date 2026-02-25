// 数据管理接口
import request from './request'

// 获取 Solomon 算例列表
export function getSolomonList() {
  return request.get('/data/solomon/list')
}

// 获取首尔数据集列表
export function getSeoulList() {
  return request.get('/data/seoul/list')
}

// 加载数据集
export function loadDataset(params) {
  return request.post('/data/load', params)
}

// 获取已加载的客户列表
export function getCustomers() {
  return request.get('/data/customers')
}

// 获取配送中心信息
export function getDepot() {
  return request.get('/data/depot')
}
