<template>
  <div class="system-settings-container">
    <div class="form-card">
      <h1 class="title">⚙️ 系统设置</h1>
      <p class="subtitle">管理后端服务配置</p>
      
      <div class="form-body">
        <!-- Overdue Reservation Check Interval Setting -->
        <div class="form-group">
          <label for="overdue-interval">逾期预约检查频率 (秒)</label>
          <input 
            type="number" 
            id="overdue-interval" 
            v-model.number="settings.overdue_reservation_check_interval" 
            min="1" 
            placeholder="例如: 20 (秒)"
          />
          <p class="help-text">设置后端自动检查和取消逾期座位预约的频率。</p>
        </div>

        <button @click="handleSaveSettings" class="submit-btn" :disabled="isLoading">
          <span v-if="!isLoading">💾 保存设置</span>
          <span v-else>保存中...</span>
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
import { ref, reactive, onMounted } from 'vue';
import apiClient from '@/api'; // Assuming you have an apiClient setup

const OVERDUE_RESERVATION_CHECK_INTERVAL_KEY = "overdue_reservation_check_interval";

const settings = reactive({
  overdue_reservation_check_interval: 20, // Default value
});

const isLoading = ref(false);
const feedback = reactive({
  message: '',
  type: 'success', // 'success' or 'error'
});

const fetchSettings = async () => {
  isLoading.value = true;
  feedback.message = '';
  try {
    const response = await apiClient.get('/settings');
    const overdueSetting = response.data.find(
      (setting) => setting.key === OVERDUE_RESERVATION_CHECK_INTERVAL_KEY
    );
    if (overdueSetting && !isNaN(parseInt(overdueSetting.value))) {
      settings.overdue_reservation_check_interval = parseInt(overdueSetting.value);
    } else {
        // If not found or invalid, maybe create it with default value?
        // For now, we'll just rely on the default set in `settings` reactive object.
        // The backend will create it if it doesn't exist on first PUT.
    }
    showFeedback('设置已加载。', 'success');
  } catch (error) {
    console.error('Failed to fetch settings:', error);
    showFeedback('加载设置失败。请检查网络或联系管理员。', 'error');
  } finally {
    isLoading.value = false;
  }
};

const handleSaveSettings = async () => {
  isLoading.value = true;
  feedback.message = '';
  
  if (settings.overdue_reservation_check_interval < 1) {
    showFeedback('检查频率必须是正整数。', 'error');
    isLoading.value = false;
    return;
  }

  try {
    await apiClient.put(
      `/settings/${OVERDUE_RESERVATION_CHECK_INTERVAL_KEY}`,
      { value: String(settings.overdue_reservation_check_interval) }
    );
    showFeedback('设置已成功保存！', 'success');
  } catch (error) {
    console.error('Failed to save settings:', error);
    showFeedback('保存设置失败。请检查输入或联系管理员。', 'error');
  } finally {
    isLoading.value = false;
  }
};

const showFeedback = (message, type = 'success') => {
  feedback.message = message;
  feedback.type = type;
  setTimeout(() => {
    feedback.message = '';
  }, 5000);
};


onMounted(fetchSettings);

</script>
<style scoped>
.system-settings-container {
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

.help-text {
  font-size: 0.85rem;
  color: #888;
  margin-top: 0.5rem;
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