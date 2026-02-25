// 认证接口
import request from './request'

// 登录
export function login(username, password) {
  return request.post('/auth/login', { username, password })
}
