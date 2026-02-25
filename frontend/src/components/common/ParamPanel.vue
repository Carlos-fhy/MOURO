<template>
  <el-collapse v-model="activeNames">
    <el-collapse-item title="高级算法参数" name="params">
      <!-- ACO 参数 -->
      <template v-if="algorithm === 'improved_aco' || algorithm === 'standard_aco'">
        <el-form label-width="140px" size="small">
          <el-form-item label="蚂蚁数量">
            <el-input-number v-model="local.ant_count" :min="10" :max="200" />
            <span class="param-hint">留空则等于客户数</span>
          </el-form-item>
          <el-form-item label="最大迭代次数">
            <el-input-number v-model="local.max_iterations" :min="50" :max="500" />
          </el-form-item>
          <el-form-item label="早停耐心值">
            <el-input-number v-model="local.patience" :min="10" :max="100" />
          </el-form-item>
          <el-form-item label="α (成本信息素)">
            <el-input-number v-model="local.alpha" :min="0.1" :max="5" :step="0.1" />
          </el-form-item>
          <el-form-item label="β (成本启发式)">
            <el-input-number v-model="local.beta" :min="0.1" :max="5" :step="0.1" />
          </el-form-item>
          <el-form-item v-if="algorithm === 'improved_aco'" label="γ (时间信息素)">
            <el-input-number v-model="local.gamma" :min="0.1" :max="5" :step="0.1" />
          </el-form-item>
          <el-form-item v-if="algorithm === 'improved_aco'" label="δ (时间启发式)">
            <el-input-number v-model="local.delta" :min="0.1" :max="5" :step="0.1" />
          </el-form-item>
          <el-form-item label="ρ_cost (挥发系数)">
            <el-input-number v-model="local.rho_cost" :min="0.01" :max="0.5" :step="0.01" />
          </el-form-item>
          <el-form-item v-if="algorithm === 'improved_aco'" label="ρ_time (挥发系数)">
            <el-input-number v-model="local.rho_time" :min="0.01" :max="0.5" :step="0.01" />
          </el-form-item>
        </el-form>
      </template>

      <!-- GA 参数 -->
      <template v-if="algorithm === 'genetic'">
        <el-form label-width="140px" size="small">
          <el-form-item label="种群大小">
            <el-input-number v-model="local.population_size" :min="20" :max="300" />
          </el-form-item>
          <el-form-item label="最大迭代次数">
            <el-input-number v-model="local.max_iterations" :min="50" :max="500" />
          </el-form-item>
          <el-form-item label="早停耐心值">
            <el-input-number v-model="local.patience" :min="10" :max="100" />
          </el-form-item>
          <el-form-item label="交叉概率">
            <el-input-number v-model="local.crossover_rate" :min="0.5" :max="1" :step="0.05" />
          </el-form-item>
          <el-form-item label="变异概率">
            <el-input-number v-model="local.mutation_rate" :min="0.01" :max="0.3" :step="0.01" />
          </el-form-item>
        </el-form>
      </template>

      <!-- SA 参数 -->
      <template v-if="algorithm === 'simulated_annealing'">
        <el-form label-width="140px" size="small">
          <el-form-item label="初始温度">
            <el-input-number v-model="local.initial_temperature" :min="100" :max="5000" />
          </el-form-item>
          <el-form-item label="降温系数">
            <el-input-number v-model="local.cooling_rate" :min="0.9" :max="0.999" :step="0.001" />
          </el-form-item>
          <el-form-item label="终止温度">
            <el-input-number v-model="local.min_temperature" :min="0.0001" :max="1" :step="0.001" />
          </el-form-item>
          <el-form-item label="最大迭代次数">
            <el-input-number v-model="local.max_iterations" :min="50" :max="500" />
          </el-form-item>
          <el-form-item label="早停耐心值">
            <el-input-number v-model="local.patience" :min="10" :max="100" />
          </el-form-item>
        </el-form>
      </template>
    </el-collapse-item>
  </el-collapse>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  algorithm: { type: String, required: true },
  modelValue: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['update:modelValue'])

const activeNames = ref([])

// 各算法默认参数
const DEFAULTS = {
  improved_aco: {
    ant_count: null, max_iterations: 200, patience: 50,
    alpha: 1.0, beta: 2.0, gamma: 1.0, delta: 2.0,
    rho_cost: 0.1, rho_time: 0.1
  },
  standard_aco: {
    ant_count: null, max_iterations: 200, patience: 50,
    alpha: 1.0, beta: 2.0, rho_cost: 0.1
  },
  genetic: {
    population_size: 100, max_iterations: 200, patience: 50,
    crossover_rate: 0.8, mutation_rate: 0.1
  },
  simulated_annealing: {
    initial_temperature: 1000, cooling_rate: 0.995,
    min_temperature: 0.001, max_iterations: 200, patience: 50
  }
}

const local = ref({ ...DEFAULTS[props.algorithm], ...props.modelValue })

// 算法切换时重置参数
watch(() => props.algorithm, (algo) => {
  local.value = { ...(DEFAULTS[algo] || {}) }
  emit('update:modelValue', { ...local.value })
})

// 参数变化时同步到父组件
watch(local, (val) => {
  emit('update:modelValue', { ...val })
}, { deep: true })
</script>

<style scoped>
.param-hint {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
