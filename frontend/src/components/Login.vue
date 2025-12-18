<template>
  <div class="login-wrapper">
    <div class="login-box">
      <div class="header">
        <div class="logo">📚</div>
        <div class="title">
          <h2>图书馆管理系统</h2>
          <p>Library Management System</p>
        </div>
      </div>

      <div class="form-content">
        <div class="tabs">
          <span :class="{ active: isLogin }" @click="switchMode(true)">用户登录</span>
          <span :class="{ active: !isLogin }" @click="switchMode(false)">新用户注册</span>
        </div>

        <div class="role-slider-container" v-if="!isLogin">
          <div class="role-slider">
            <div 
              class="slider-bg" 
              :style="{ left: registerRole === 'student' ? '4px' : '50%' }"
            ></div>
            <div 
              class="role-option" 
              :class="{ active: registerRole === 'student' }"
              @click="registerRole = 'student'"
            >
              🎓 学生注册
            </div>
            <div 
              class="role-option" 
              :class="{ active: registerRole === 'admin' }"
              @click="registerRole = 'admin'"
            >
              🛡️ 管理员注册
            </div>
          </div>
        </div>

        <div class="input-group">
          <label>用户名</label>
          <input 
            type="text" 
            v-model="formData.username" 
            placeholder="请输入用户名"
            @keyup.enter="handleSubmit"
          >
          <p class="error" v-if="errors.username">{{ errors.username }}</p>
        </div>

        <div class="input-group">
          <label>密码</label>
          <input 
            type="password" 
            v-model="formData.password" 
            placeholder="请输入密码"
            @keyup.enter="handleSubmit"
          >
          <p class="error" v-if="errors.password">{{ errors.password }}</p>
        </div>

        <transition name="slide-fade">
          <div class="input-group admin-token-group" v-if="!isLogin && registerRole === 'admin'">
            <label class="admin-label">🔐 管理员注册密钥 (Token)</label>
            <input 
              type="password" 
              v-model="formData.adminToken" 
              placeholder="请输入系统管理员提供的密钥"
              class="admin-input"
            >
            <p class="hint">密钥由系统维护人员提供，错误将无法注册</p>
          </div>
        </transition>

        <div class="input-group" v-if="!isLogin">
          <label>确认密码</label>
          <input 
            type="password" 
            v-model="formData.confirmPassword" 
            placeholder="请再次输入密码"
          >
          <p class="error" v-if="errors.confirmPassword">{{ errors.confirmPassword }}</p>
        </div>

        <div class="input-group" v-if="!isLogin">
          <label>电子邮箱 <span style="color:red">*</span></label>
          <input 
            type="email" 
            v-model="formData.email" 
            placeholder="example@email.com"
          >
          <p class="error" v-if="errors.email">{{ errors.email }}</p>
        </div>

        <div class="db-slider-container" v-if="isLogin">
          <label>选择登录数据库</label>
          <div class="role-slider">
            <div 
              class="slider-bg"
              :style="{ left: dbSliderPosition, width: 'calc(33.33% - 4px)' }"
            ></div>
            <div 
              class="role-option" 
              :class="{ active: formData.dbKey === 'MySQL' }"
              @click="formData.dbKey = 'MySQL'"
            >
              MySQL
            </div>
            <div 
              class="role-option" 
              :class="{ active: formData.dbKey === 'PostgreSQL' }"
              @click="formData.dbKey = 'PostgreSQL'"
            >
              PostgreSQL
            </div>
            <div 
              class="role-option" 
              :class="{ active: formData.dbKey === 'SQLServer' }"
              @click="formData.dbKey = 'SQLServer'"
            >
              SQLServer
            </div>
          </div>
        </div>

        <button class="submit-btn" @click="handleSubmit" :disabled="isLoading">
          {{ btnText }}
        </button>
      </div>
    </div>
    
    <div class="footer-copyright">
      © 2025 Library System | CSU Project
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api'

export default {
  name: 'UserLogin',
  setup() {
    const router = useRouter()
    const isLogin = ref(true)
    const isLoading = ref(false)
    const registerRole = ref('student') // 'student' or 'admin'
    
    const formData = reactive({
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      adminToken: '',
      dbKey: 'MySQL'
    })
    
    const errors = reactive({
      username: '',
      password: '',
      confirmPassword: '',
      email: '' // 新增邮箱错误状态
    })

    const btnText = computed(() => {
      if (isLoading.value) return '处理中...';
      if (isLogin.value) return '立即登录';
      return registerRole.value === 'admin' ? '注册管理员账号' : '注册学生账号';
    })

    const dbSliderPosition = computed(() => {
      if (formData.dbKey === 'MySQL') return '4px';
      if (formData.dbKey === 'PostgreSQL') return '33.33%';
      return '66.66%';
    });

    const validate = () => {
      let isValid = true;
      // 重置错误信息
      errors.username = '';
      errors.password = '';
      errors.confirmPassword = '';
      errors.email = '';

      if (!formData.username || formData.username.length < 3) {
        errors.username = '用户名至少3位';
        isValid = false;
      }
      if (!formData.password || formData.password.length < 4) {
        errors.password = '密码至少4位';
        isValid = false;
      }
      
      // 注册时的额外校验
      if (!isLogin.value) {
        if (formData.password !== formData.confirmPassword) {
          errors.confirmPassword = '两次密码不一致';
          isValid = false;
        }
        
        // 邮箱必填校验
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!formData.email) {
          errors.email = '电子邮箱不能为空';
          isValid = false;
        } else if (!emailRegex.test(formData.email)) {
          errors.email = '请输入有效的邮箱格式';
          isValid = false;
        }

        // 管理员 Token 校验
        if (registerRole.value === 'admin' && !formData.adminToken) {
          alert('请填写管理员注册密钥');
          return false;
        }
      }
      return isValid;
    }

    const switchMode = (loginMode) => {
      isLogin.value = loginMode;
      errors.username = '';
      errors.password = '';
      errors.confirmPassword = '';
      errors.email = '';
    }

    const handleSubmit = async () => {
      if (!validate()) return;
      isLoading.value = true;

      try {
        if (isLogin.value) {
          // --- 登录逻辑 ---
          const res = await apiClient.post(`/user/login`, {
            username: formData.username,
            password: formData.password,
            db_key: formData.dbKey
          });
          const { access_token } = res.data;
          
          sessionStorage.setItem('token', access_token);
          
          // The request interceptor will automatically add the new token
          const userRes = await apiClient.get(`/users/me`);
          sessionStorage.setItem('user', JSON.stringify(userRes.data));
          
          router.push('/dashboard');
        } else {
          // --- 注册逻辑 ---
          const payload = {
            username: formData.username,
            password: formData.password,
            email: formData.email, // 必填
            role: registerRole.value,
            admin_token: registerRole.value === 'admin' ? formData.adminToken : null
          };

          await apiClient.post(`/user/register`, payload);
          
          alert(`🎉 ${registerRole.value === 'admin' ? '管理员' : '学生'}账号注册成功！请登录。`);
          isLogin.value = true;
          registerRole.value = 'student';
          formData.adminToken = '';
          formData.email = ''; // 清空邮箱
        }
      } catch (error) {
        const msg = error.response?.data?.detail || '请求失败，请检查网络或输入信息';
        // 如果是 Pydantic 校验错误，通常在 detail 中
        if (Array.isArray(error.response?.data?.detail)) {
             alert('❌ 注册失败: 请检查输入格式');
        } else {
             alert('❌ ' + msg);
        }
      } finally {
        isLoading.value = false;
      }
    }

    return { 
      isLogin, 
      isLoading, 
      registerRole,
      formData, 
      errors, 
      btnText,
      dbSliderPosition,
      switchMode,
      handleSubmit 
    }
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-size: cover;
}

.login-box {
  width: 400px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.header {
  background: #fff;
  padding: 30px 20px 20px;
  text-align: center;
  border-bottom: 1px solid #f0f0f0;
}

.logo { font-size: 48px; margin-bottom: 10px; }
.title h2 { margin: 0; color: #333; font-size: 24px; }
.title p { margin: 5px 0 0; color: #666; font-size: 14px; letter-spacing: 1px; }

.form-content { padding: 30px; }

/* 顶部 Tab */
.tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
  border-bottom: 2px solid #f0f0f0;
}
.tabs span {
  padding: 10px 20px;
  cursor: pointer;
  color: #999;
  font-weight: 600;
  position: relative;
  transition: color 0.3s;
}
.tabs span.active { color: #764ba2; }
.tabs span.active::after {
  content: ''; position: absolute; bottom: -2px; left: 0; width: 100%; height: 2px; background: #764ba2;
}

/* 角色切换滑块 */
.role-slider-container, .db-slider-container {
  margin-bottom: 20px;
}
.db-slider-container label {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
  font-weight: 500;
}
.role-slider {
  background: #f3f4f6;
  border-radius: 20px;
  padding: 4px;
  display: flex;
  position: relative;
  width: 100%;
  box-sizing: border-box;
}
.role-option {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  z-index: 1;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: #666;
  transition: color 0.3s;
}
.role-option.active { color: #764ba2; }
.slider-bg {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  transition: left 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

/* 输入框通用 */
.input-group { margin-bottom: 15px; }
.input-group label { display: block; font-size: 13px; color: #666; margin-bottom: 6px; font-weight: 500; }
.input-group input {
  width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px;
  transition: border-color 0.3s, box-shadow 0.3s; box-sizing: border-box;
}
.input-group input:focus { border-color: #764ba2; outline: none; box-shadow: 0 0 0 3px rgba(118, 75, 162, 0.1); }

/* 管理员 Token 特效 */
.admin-token-group {
  background: #fff9f0;
  padding: 10px;
  border-radius: 8px;
  border: 1px dashed #f59e0b;
}
.admin-label { color: #d97706 !important; }
.admin-input { border-color: #fcd34d !important; }
.admin-input:focus { box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1) !important; }
.hint { font-size: 12px; color: #d97706; margin-top: 4px; }

.error { color: #ff4d4f; font-size: 12px; margin-top: 4px; }

.submit-btn {
  width: 100%; padding: 12px; margin-top: 10px;
  background: linear-gradient(to right, #667eea, #764ba2);
  color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 600;
  cursor: pointer; box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3);
  transition: all 0.2s;
}
.submit-btn:hover { opacity: 0.9; transform: translateY(-1px); }
.submit-btn:disabled { background: #ccc; cursor: not-allowed; box-shadow: none; }

.footer-copyright { margin-top: 20px; color: rgba(255, 255, 255, 0.7); font-size: 12px; }

/* Vue Transitions */
.slide-fade-enter-active { transition: all 0.3s ease-out; }
.slide-fade-leave-active { transition: all 0.2s cubic-bezier(1.0, 0.5, 0.8, 1.0); }
.slide-fade-enter-from, .slide-fade-leave-to { transform: translateX(10px); opacity: 0; }

@media (max-width: 480px) {
  .login-box {
    width: 90%;
    margin-top: 20px;
    margin-bottom: 20px;
  }
  .form-content {
    padding: 20px;
  }
  .header {
    padding: 20px;
  }
  .logo {
    font-size: 40px;
  }
  .title h2 {
    font-size: 20px;
  }
  .role-option {
    font-size: 13px;
  }
}
</style>