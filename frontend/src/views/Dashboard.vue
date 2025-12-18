<template>
  <div class="dashboard-container">
    <!-- View selection buttons for admin -->
    <div v-if="isAdmin && !loading" class="dashboard-controls">
      <div class="slider" :style="sliderStyle"></div>
      <button :ref="el => { if (el) tabButtons['personal'] = el }"
              :class="{ active: activeView === 'personal' }" 
              @click="switchView('personal')"
              class="tab-button">
        📊 个人总览
      </button>
      <button :ref="el => { if (el) tabButtons['system'] = el }"
              :class="{ active: activeView === 'system' }" 
              @click="switchView('system')"
              class="tab-button">
        ⚙️ 系统概览
      </button>
    </div>

    <div v-if="loading" class="loading-state">🔄 数据加载中...</div>


    
    <!-- Main Content Area with Transition -->
    <Transition name="fade" mode="out-in">
      <!-- Personal Dashboard View -->
      <div v-if="activeView === 'personal' && !loading" key="personal-view">
        <div class="stats-grid">
          <div class="stat-card blue">
            <div class="icon-bg">📚</div>
            <div class="stat-content">
              <h3>馆藏图书</h3>
              <p class="number">{{ data.summary.total_books }}</p>
            </div>
          </div>
          
          <div class="stat-card green">
            <div class="icon-bg">📤</div>
            <div class="stat-content">
              <h3>当前借出</h3>
              <p class="number">{{ data.summary.borrowed_books }}</p>
              <p v-if="data.summary.borrowed_books > 0 && data.summary.overdue_loans > 0" class="overdue-count">
                其中逾期: {{ data.summary.overdue_loans }}
              </p>
            </div>
          </div>
          
          <div class="stat-card purple">
            <div class="icon-bg">🪑</div>
            <div class="stat-content">
              <h3>活跃预约</h3>
              <p class="number">{{ data.summary.active_reservations }}</p>
            </div>
          </div>

          <div class="stat-card red">
            <div class="icon-bg">⚠️</div>
            <div class="stat-content">
              <h3>历史逾期</h3>
              <p class="number">{{ data.summary.historical_overdue_records }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Admin System Stats Section -->
      <div v-else-if="activeView === 'system'" key="system-view">
        <div v-if="systemLoading" class="loading-state">🔄 系统数据加载中...</div>
        <div v-else-if="systemStats && Object.keys(systemStats).length > 0">
          <div class="stats-grid">
            <div class="stat-card blue">
              <div class="icon-bg">📚</div>
              <div class="stat-content">
                <h3>总图书种类</h3>
                <p class="number">{{ systemStats.total_book_titles }}</p>
              </div>
            </div>
            <div class="stat-card purple">
              <div class="icon-bg">📖</div>
              <div class="stat-content">
                <h3>总图书数量 (所有副本)</h3>
                <p class="number">{{ systemStats.total_book_copies }}</p>
              </div>
            </div>
            <div class="stat-card green">
              <div class="icon-bg">👨‍👩‍👧‍👦</div>
              <div class="stat-content">
                <h3>当前所有用户借出</h3>
                <p class="number">{{ systemStats.total_borrowed_books }}</p>
              </div>
            </div>
            <div class="stat-card red">
              <div class="icon-bg">🚨</div>
              <div class="stat-content">
                <h3>总历史逾期</h3>
                <p class="number">{{ systemStats.historical_overdue_count }}</p>
              </div>
            </div>
            <div class="stat-card yellow">
              <div class="icon-bg">🪑</div>
              <div class="stat-content">
                <h3>总座位预约</h3>
                <p class="number">{{ systemStats.active_seat_reservations }}</p>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>暂无系统概览数据。</p>
        </div>
      </div>
    </Transition>

    <!-- Popular Books - always visible for admin, or when activeView is personal for non-admin -->
    <div class="chart-section" v-if="!loading && (activeView === 'personal' || (isAdmin && activeView === 'system' && systemStats && Object.keys(systemStats).length > 0))">
      <h3>🔥 热门借阅榜单</h3>
      <div class="list-container">
        <div v-for="(book, index) in data.popular_books" :key="book.book_id" class="list-item">
          <span class="rank" :class="'rank-'+(index+1)">{{ index + 1 }}</span>
          <span class="book-name">{{ book.title }}</span>
          <span class="borrow-count">总借阅 {{ book.borrow_count }} 次</span>
        </div>
        <div v-if="data.popular_books.length === 0" class="empty-tip">暂无数据</div>
      </div>
    </div>
  </div>
</template>

<script>
import apiClient from '@/api'
import { ref, onMounted, computed, watch, nextTick } from 'vue'

export default {
  name: 'SystemDashboard',
  setup() {
    const data = ref({ summary: {}, popular_books: [] })
    const systemStats = ref(null)
    const loading = ref(true)
    const systemLoading = ref(false)
    const activeView = ref('personal')

    const tabButtons = ref({}) // To store refs to the buttons
    const sliderStyle = ref({}) // For the slider's dynamic styles

    const isAdmin = computed(() => {
      const user = JSON.parse(sessionStorage.getItem('user'))
      return user && user.role === 'admin'
    })

    const fetchSystemStats = async () => {
      if (isAdmin.value && !systemStats.value) {
        systemLoading.value = true
        try {
          const systemRes = await apiClient.get(`/dashboard/system`)
          systemStats.value = systemRes.data
        } catch (e) {
          console.error("Failed to fetch system stats:", e)
          systemStats.value = {}
        } finally {
          systemLoading.value = false
        }
      }
    }

    const updateSlider = () => {
      nextTick(() => { // Ensure DOM is updated before calculating positions
        const activeTabEl = tabButtons.value[activeView.value]
        if (activeTabEl) {
          sliderStyle.value = {
            width: `${activeTabEl.offsetWidth}px`,
            transform: `translateX(${activeTabEl.offsetLeft}px)`,
          }
        }
      })
    }

    const switchView = (viewName) => {
      activeView.value = viewName
      if (viewName === 'system') {
        fetchSystemStats()
      }
      updateSlider() // Update slider position immediately after switching view
    }

    onMounted(async () => {
      try {
        const res = await apiClient.get(`/dashboard/`)
        data.value = res.data
      } catch (e) {
        console.error("Failed to fetch personal dashboard data:", e)
      } finally {
        loading.value = false
        updateSlider() // Initial slider position update
      }
    })

    watch(activeView, () => {
      updateSlider()
    })

    return { data, loading, isAdmin, systemStats, systemLoading, activeView, switchView, tabButtons, sliderStyle }
  }
}
</script>

<style scoped>
.dashboard-controls {
  margin-bottom: 20px;
  display: flex;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  position: relative; /* Added for slider positioning */
  padding: 8px; /* Added to make space for the slider */
  background-color: #f0f4f8; /* Set background for the controls container */
  max-width: 300px; /* Optional: adjust as needed */
  margin-left: auto;
  margin-right: auto;
}

.dashboard-controls .slider {
  position: absolute;
  top: 8px; /* Matches padding */
  left: 0;
  height: calc(100% - 16px); /* Calc(100% - 2 * top/bottom padding) */
  background-color: #4299e1; /* Active color */
  border-radius: 8px; /* Matches control container border-radius */
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); /* Smooth transition */
  z-index: 0; /* Ensure slider is behind buttons */
}

.dashboard-controls .tab-button { /* Renamed from button to tab-button */
  flex: 1;
  padding: 12px 20px;
  border: none;
  background-color: transparent; /* Make buttons transparent to show slider */
  color: #4a5568;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.3s ease; /* Only color transition needed now */
  position: relative; /* Needed for z-index */
  z-index: 1; /* Ensure buttons are above slider */
  border-radius: 8px; /* Match slider border-radius for aesthetic */
}

.dashboard-controls .tab-button:hover {
  color: #2b6cb0; /* Darker hover color for better contrast */
}

.dashboard-controls .tab-button.active {
  color: white; /* Active text color */
}

.section-title {
  margin-top: 30px;
  margin-bottom: 20px;
  color: #333;
  font-size: 24px;
  font-weight: 600;
}

/* Vue Transition styles for fade effect */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 25px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  padding: 25px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.04);
  display: flex;
  align-items: center;
  transition: transform 0.3s, box-shadow 0.3s;
}
.stat-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.08); }

.icon-bg {
  font-size: 30px;
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
}

.stat-card.blue .icon-bg { background: #e0f2fe; }
.stat-card.green .icon-bg { background: #dcfce7; }
.stat-card.red .icon-bg { background: #fee2e2; }
.stat-card.purple .icon-bg { background: #f3e8ff; }
.stat-card.yellow .icon-bg { background: #fffbeb; } /* New style for yellow stat card */

.stat-content h3 { margin: 0; color: #64748b; font-size: 14px; font-weight: 500; }
.stat-content .number { margin: 5px 0 0 0; font-size: 28px; font-weight: 700; color: #1e293b; }
.stat-content .overdue-count {
  margin: 8px 0 0;
  font-size: 14px;
  font-weight: 500;
  color: #ef4444;
}



.chart-section { background: white; padding: 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); }
.chart-section h3 { margin-top: 0; margin-bottom: 20px; color: #333; }

.list-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.list-item:last-child { border-bottom: none; }

.rank {
  width: 24px;
  height: 24px;
  background: #cbd5e1;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  margin-right: 15px;
}
.rank-1 { background: #f59e0b; }
.rank-2 { background: #94a3b8; }
.rank-3 { background: #b45309; }

.book-name { flex: 1; font-weight: 500; color: #333; }
.borrow-count { color: #64748b; font-size: 14px; background: #f1f5f9; padding: 4px 8px; border-radius: 6px; }
.empty-tip { color: #999; text-align: center; padding: 20px; }

/* Responsive Styles */
@media (max-width: 768px) {
  .dashboard-controls {
    max-width: 100%;
    flex-direction: column;
    padding: 6px;
  }
  .dashboard-controls .slider {
    display: none; /* Hide slider on mobile, direct feedback is enough */
  }
  .dashboard-controls .tab-button {
    background-color: #f0f4f8;
    color: #4a5568;
    margin: 4px 0;
  }
  .dashboard-controls .tab-button.active {
    background-color: #4299e1;
    color: white;
  }

  .stats-grid {
    grid-template-columns: 1fr; /* Stack cards in a single column */
    gap: 15px;
  }

  .stat-card {
    padding: 15px;
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }
  .icon-bg {
    margin-right: 0;
    margin-bottom: 15px;
  }
  .stat-content .number {
    font-size: 24px;
  }

  .chart-section {
    padding: 15px;
  }

  .list-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
  .borrow-count {
    font-size: 12px;
  }
}
</style>