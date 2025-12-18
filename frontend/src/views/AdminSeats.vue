<template>
  <div class="admin-seats-container">
    <div class="form-card">
      <h1 class="title">🪑 座位批量管理</h1>
      <p class="subtitle">高效添加、管理图书馆座位</p>
      
      <div class="form-body">
        <div class="input-row">
          <!-- Floor Selection -->
          <div class="form-group">
            <label for="floor">楼层</label>
            <select id="floor" v-model.number="params.floor">
              <option v-for="n in 7" :key="n" :value="n">第 {{ n }} 层</option>
            </select>
          </div>
          <!-- Seat Prefix -->
          <div class="form-group">
            <label for="prefix">座位号前缀</label>
            <input type="text" id="prefix" v-model="params.prefix" placeholder="如 F / A 区">
          </div>
        </div>

        <div class="input-row">
          <!-- Quantity -->
          <div class="form-group">
            <label for="quantity">创建数量</label>
            <input type="number" id="quantity" v-model.number="params.quantity" min="1" max="100">
          </div>
          <!-- Start Number -->
          <div class="form-group">
            <label for="startNum">起始编号</label>
            <input type="number" id="startNum" v-model.number="params.startNum" min="1">
          </div>
        </div>

        <div class="preview" v-if="params.quantity > 0">
          <p>将创建 <strong>{{ params.quantity }}</strong> 个座位，编号从 <strong>{{ generatedSeatCode(params.startNum) }}</strong> 到 <strong>{{ generatedSeatCode(params.startNum + params.quantity - 1) }}</strong></p>
        </div>

        <button @click="handleBulkAdd" class="submit-btn" :disabled="isLoading">
          <span v-if="!isLoading">🚀 立即创建</span>
          <span v-else>处理中...</span>
        </button>

        <transition name="fade">
          <div v-if="feedback.message" :class="['feedback-message', feedback.type]">
            {{ feedback.message }}
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue';
import apiClient from '@/api';

const params = reactive({
  floor: 1,
  prefix: 'F',
  quantity: 10,
  startNum: 1,
});

const isLoading = ref(false);
const feedback = reactive({
  message: '',
  type: 'success', // 'success' or 'error'
});

const fetchFloorStats = async () => {
  try {
    const response = await apiClient.get('/seats/stats', { params: { floor: params.floor } });
    params.startNum = response.data.max_seat_num + 1;
  } catch (error) {
    console.error(`Failed to fetch stats for floor ${params.floor}:`, error);
    // Don't block the user, but don't suggest a start number either.
    params.startNum = 1;
  }
};

// Fetch stats when the component mounts and whenever the floor changes
onMounted(fetchFloorStats);
watch(() => params.floor, fetchFloorStats);

const generatedSeatCode = (num) => {
  return `${params.prefix}${params.floor}-${String(num).padStart(3, '0')}`;
};

const showFeedback = (message, type = 'success') => {
  feedback.message = message;
  feedback.type = type;
  setTimeout(() => {
    feedback.message = '';
  }, 5000);
};

const handleBulkAdd = async () => {
  if (params.quantity <= 0 || params.startNum <= 0) {
    showFeedback('数量和起始编号必须大于0', 'error');
    return;
  }
  
  isLoading.value = true;
  feedback.message = '';

  const requests = [];
  for (let i = 0; i < params.quantity; i++) {
    const seatNumber = params.startNum + i;
    const seatCode = generatedSeatCode(seatNumber);
    requests.push(apiClient.post('/seats/', {
      floor: params.floor,
      code: seatCode,
    }));
  }

  try {
    const results = await Promise.allSettled(requests);
    
    const successfulCreations = results.filter(r => r.status === 'fulfilled').length;
    const failedCreations = results.length - successfulCreations;

    let message = `成功创建 ${successfulCreations} 个座位。`;
    if (failedCreations > 0) {
      const firstError = results.find(r => r.status === 'rejected');
      const errorDetail = firstError.reason.response?.data?.detail || '未知错误';
      message += `\n失败 ${failedCreations} 个（首个错误: ${errorDetail}）。请检查起始编号是否重复。`;
      showFeedback(message, 'error');
    } else {
      showFeedback(message, 'success');
    }

  } catch (error) {
    // This part will likely not be reached due to Promise.allSettled
    showFeedback('发生意外错误，请稍后重试。', 'error');
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.admin-seats-container {
  padding: 2rem;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 80vh;
  background-color: #f4f7f6;
}

.form-card {
  width: 100%;
  max-width: 650px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  padding: 2.5rem;
}

.title {
  font-size: 2rem;
  font-weight: 700;
  color: #333;
  text-align: center;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1rem;
  color: #666;
  text-align: center;
  margin-bottom: 2.5rem;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.input-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #555;
  font-size: 0.9rem;
}

input[type="text"],
input[type="number"],
select {
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid #dcdcdc;
  border-radius: 8px;
  box-sizing: border-box;
  font-size: 1rem;
  transition: border-color 0.3s, box-shadow 0.3s;
}

input:focus,
select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.preview {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #495057;
  text-align: center;
}

.submit-btn {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1rem;
  font-weight: 600;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(0, 123, 255, 0.2);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 123, 255, 0.3);
}

.submit-btn:disabled {
  background: #cccccc;
  cursor: not-allowed;
  box-shadow: none;
}

.feedback-message {
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
  font-weight: 500;
  white-space: pre-wrap; /* To show newlines in the message */
}

.feedback-message.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.feedback-message.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.5s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
