<template>
  <div class="route-map" ref="mapContainer"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  depot: { type: Object, default: null },
  customers: { type: Array, default: () => [] },
  routes: { type: Array, default: () => [] },
  mode: { type: String, default: 'preview' },
  // solomon 用平面坐标，seoul 用经纬度
  coordMode: { type: String, default: 'solomon' },
  // 调度明细，用于弹窗显示到达时间等
  schedule: { type: Array, default: () => [] },
  // 路线绘制动画开关
  animated: { type: Boolean, default: true }
})

// 动画状态
let animationTimers = []
let isAnimating = ref(false)

// 路线颜色方案
const ROUTE_COLORS = [
  '#409EFF', '#67C23A', '#E6A23C', '#F56C6C',
  '#909399', '#B37FEB', '#36CFC9', '#FF85C0'
]

// 应急等级颜色和半径
const EMERGENCY_STYLE = {
  medical: { color: '#F56C6C', radius: 8 },
  fresh: { color: '#E6A23C', radius: 6 },
  normal: { color: '#409EFF', radius: 5 }
}

const mapContainer = ref(null)
let map = null
let layerGroup = null

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  stopAnimation()
  if (map) {
    map.remove()
    map = null
  }
})

// 清除所有动画定时器
function stopAnimation() {
  animationTimers.forEach(t => clearTimeout(t))
  animationTimers = []
  isAnimating.value = false
}

// 监听数据变化重新渲染
watch(
  () => [props.depot, props.customers, props.routes, props.mode],
  () => { nextTick(() => renderMap()) },
  { deep: true }
)

function initMap() {
  if (!mapContainer.value) return

  const crs = props.coordMode === 'solomon' ? L.CRS.Simple : L.CRS.EPSG3857

  map = L.map(mapContainer.value, {
    crs,
    zoomControl: true,
    attributionControl: false
  })

  // Solomon 模式不需要底图瓦片；首尔模式加载 OSM
  if (props.coordMode !== 'solomon') {
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map)
  }

  layerGroup = L.layerGroup().addTo(map)
  renderMap()
}

function renderMap() {
  if (!map || !layerGroup) return
  stopAnimation()
  layerGroup.clearLayers()

  const bounds = []

  // 绘制配送中心
  if (props.depot) {
    const pos = toLatLng(props.depot)
    bounds.push(pos)
    // 黑色方形图标
    const depotIcon = L.divIcon({
      className: 'depot-icon',
      html: '<div style="width:14px;height:14px;background:#000;border:2px solid #fff;"></div>',
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    })
    L.marker(pos, { icon: depotIcon })
      .bindPopup('配送中心')
      .addTo(layerGroup)
  }

  // 绘制客户点
  if (props.customers.length) {
    props.customers.forEach(c => {
      const pos = toLatLng(c)
      bounds.push(pos)
      const level = c.emergency_level || 'normal'
      const style = EMERGENCY_STYLE[level] || EMERGENCY_STYLE.normal

      const marker = L.circleMarker(pos, {
        radius: style.radius,
        fillColor: style.color,
        color: '#fff',
        weight: 1,
        fillOpacity: 0.8
      }).addTo(layerGroup)

      // 弹窗内容
      const popupContent = buildPopup(c)
      marker.bindPopup(popupContent)
    })
  }

  // 路线模式：绘制路线（支持动画）
  if (props.mode === 'route' && props.routes.length) {
    // 预处理所有路线的坐标
    const allRoutePoints = props.routes.map((route, idx) => ({
      color: ROUTE_COLORS[idx % ROUTE_COLORS.length],
      points: route.map(nodeId => {
        if (nodeId === 0 && props.depot) return toLatLng(props.depot)
        const c = props.customers.find(cu => cu.id === nodeId)
        return c ? toLatLng(c) : null
      }).filter(Boolean)
    }))

    if (props.animated) {
      animateRoutes(allRoutePoints)
    } else {
      // 无动画：直接绘制
      allRoutePoints.forEach(({ color, points }) => {
        if (points.length > 1) {
          L.polyline(points, { color, weight: 3, opacity: 0.7 }).addTo(layerGroup)
        }
      })
    }
  }

  // 自动适配视野
  if (bounds.length) {
    map.fitBounds(L.latLngBounds(bounds).pad(0.1))
  }
}

// 所有路线同时从配送中心出发，并行逐段绘制
function animateRoutes(allRoutePoints) {
  stopAnimation()
  isAnimating.value = true

  const segmentDelay = 80
  // 找出最长路线的段数，用于判断动画结束
  const maxSegments = Math.max(...allRoutePoints.map(r => r.points.length))
  let finishedCount = 0

  allRoutePoints.forEach(({ color, points }) => {
    if (points.length < 2) { finishedCount++; return }

    const polyline = L.polyline([points[0]], {
      color, weight: 3, opacity: 0.8
    }).addTo(layerGroup)

    for (let i = 1; i < points.length; i++) {
      const t = setTimeout(() => {
        polyline.addLatLng(points[i])
        // 该路线最后一段画完
        if (i === points.length - 1) {
          finishedCount++
          if (finishedCount >= allRoutePoints.length) {
            isAnimating.value = false
          }
        }
      }, i * segmentDelay)
      animationTimers.push(t)
    }
  })
}

// 重播动画
function replay() {
  renderMap()
}

// 暴露给父组件
defineExpose({ replay, isAnimating })

function toLatLng(node) {
  // Solomon 平面坐标：y 作为 lat，x 作为 lng
  // 首尔经纬度：y_coord 是纬度，x_coord 是经度
  return L.latLng(node.y_coord, node.x_coord)
}

function buildPopup(customer) {
  const level = customer.emergency_level || 'normal'
  const levelMap = { medical: '医疗急件', fresh: '生鲜', normal: '普通' }

  let html = `<b>客户 #${customer.id}</b><br/>`
  html += `应急等级：${levelMap[level]}<br/>`
  html += `时间窗：[${customer.early_time}, ${customer.late_time}]<br/>`

  // 如果有调度信息，显示到达时间
  if (props.schedule.length) {
    const info = props.schedule.find(s => s.customer_id === customer.id)
    if (info) {
      const statusMap = { on_time: '准时', early: '早到', late: '迟到' }
      html += `到达时间：${info.arrival_time.toFixed(1)}<br/>`
      html += `状态：${statusMap[info.status] || info.status}`
    }
  }
  return html
}
</script>

<style scoped>
.route-map {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: #f5f5f5;
}
</style>
