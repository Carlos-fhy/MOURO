// SSE 通信封装
// 不自动重连，算法运行是一次性任务

export function createSseConnection(url, { onMessage, onDone, onError }) {
  const token = localStorage.getItem('token')
  const fullUrl = `${url}${url.includes('?') ? '&' : '?'}token=${token}`
  const eventSource = new EventSource(fullUrl)
  let reconnectErrors = 0

  eventSource.onopen = () => {
    reconnectErrors = 0
  }

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'heartbeat') {
        return
      }
      if (data.type === 'done') {
        onDone(data)
        eventSource.close()
      } else if (data.type === 'error') {
        onError(data.message || '算法运行异常')
        eventSource.close()
      } else {
        onMessage(data)
      }
    } catch (e) {
      onError('消息解析失败')
      eventSource.close()
    }
  }

  eventSource.onerror = () => {
    // EventSource 自带自动重连，不要立刻 close。
    reconnectErrors += 1
    if (reconnectErrors >= 5) {
      onError('SSE 连接异常（多次重连失败）')
      eventSource.close()
    }
  }

  return eventSource
}
