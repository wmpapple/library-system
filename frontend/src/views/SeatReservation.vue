<template>
  <div class="seat-reservation-page">
    <header class="page-header">
      <h1>自习室座位预约</h1>
      <p>点击楼层查看座位，选择心仪的位置吧</p>
    </header>

    <div class="tab-controls">
      <button :class="{ active: activeTab === 'current' }" @click="activeTab = 'current'">当前预约</button>
      <button :class="{ active: activeTab === 'seats' }" @click="activeTab = 'seats'">座位预约</button>
      <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">历史预约</button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      <!-- Current Reservation Tab -->
      <div v-if="activeTab === 'current'" class="my-reservation-container">
        <div v-if="myReservation" class="card">
          <div class="card-header">
            <span class="icon">✅</span>
            <h2>我的预约</h2>
          </div>
          <div class="card-content">
            <div class="info-row">
              <strong>楼层:</strong>
              <span>{{ getSeatDetails(myReservation.seat_id).floor }} 层</span>
            </div>
            <div class="info-row">
              <strong>座位号:</strong>
              <span>{{ getSeatDetails(myReservation.seat_id).code }}</span>
            </div>
            <div class="info-row">
              <strong>预约时间:</strong>
              <span>{{ formatTimestamp(myReservation.reserved_at) }}</span>
            </div>
            <div class="info-row">
              <strong>过期时间:</strong>
              <span>{{ formatTimestamp(myReservation.expires_at) }}</span>
            </div>
          </div>
          <div class="card-footer">
            <button @click="cancelMyReservation" class="cancel-btn">取消预约</button>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>您当前没有有效的座位预约。</p>
        </div>
      </div>

      <!-- Seat Reservation Tab -->
      <div v-if="activeTab === 'seats'">
        <div class="floor-controls">
          <div class="floor-selector">
            <button
              v-for="floor in floors"
              :key="floor"
              class="floor-tab"
              :class="{ 'active': selectedFloor === floor }"
              @click="selectedFloor = floor"
            >
              {{ floor }} 层
            </button>
          </div>
          <div class="seat-filters">
            <button :class="{ active: seatFilter === 'all' }" @click="seatFilter = 'all'">所有</button>
            <button :class="{ active: seatFilter === 'available' }" @click="seatFilter = 'available'">空闲</button>
          </div>
        </div>

        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>座位加载中...</p>
        </div>

        <div v-else-if="seatsOnSelectedFloor.length > 0" class="seats-grid-container">
          <div class="seats-grid">
            <div
              v-for="seat in filteredSeatsOnSelectedFloor"
              :key="seat.id"
              class="seat"
              :class="getSeatClass(seat)"
              @click="handleSeatClick(seat)"
            >
              <span class="seat-icon">🪑</span>
              <span class="seat-code">{{ seat.code }}</span>
            </div>
          </div>
        </div>
        
        <div v-else class="empty-state">
          <p>😢 楼层正在装修中，暂无座位信息</p>
        </div>
      </div>

      <!-- Historical Reservations Tab -->
      <div v-if="activeTab === 'history'" class="historical-reservations-container">
        <div class="filters-history">
          <button :class="{ active: filterType === 'all' }" @click="filterType = 'all'">所有</button>
          <button :class="{ active: filterType === 'normal' }" @click="filterType = 'normal'">正常情况</button>
          <button :class="{ active: filterType === 'defaulted' }" @click="filterType = 'defaulted'">违约情况</button>
        </div>
        <div v-if="filteredHistoricalReservations.length > 0" class="history-list">
          <div v-for="record in filteredHistoricalReservations" :key="record.id" class="history-item card">
            <div class="card-header">
              <span :class="['status-dot', record.status]"></span>
              <h2>{{ getSeatDetails(record.seat_id).code }} - {{ getSeatDetails(record.seat_id).floor }}层</h2>
            </div>
            <div class="card-content">
              <div class="info-row">
                <strong>预约开始:</strong>
                <span>{{ formatTimestamp(record.reserved_at) }}</span>
              </div>
              <div class="info-row">
                <strong>{{ record.status === 'cancelled' ? '取消时间:' : '预约结束:' }}</strong>
                <span>{{ record.status === 'cancelled' && record.cancelled_at ? formatTimestamp(record.cancelled_at) : formatTimestamp(record.expires_at) }}</span>
              </div>
              <div class="info-row">
                <strong>状态:</strong>
                <span :class="['reservation-status-text', record.status]">{{ getReservationStatusText(record.status) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>您还没有历史座位预约记录。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch } from 'vue';
import apiClient from '@/api';

export default {
  name: 'SeatReservation',
  setup() {
    const seats = ref([]);
    const floors = ref([1, 2, 3, 4, 5, 6, 7]);
    const selectedFloor = ref(1);
    const loading = ref(true);
    const currentUser = ref(null);
    const myReservation = ref(null);
    const activeTab = ref('seats'); // Default to 'seats' tab
    const historicalReservations = ref([]); // New ref for historical data
    const filterType = ref('all'); // 'all', 'normal', 'defaulted'
    const seatFilter = ref('all'); // 'all', 'available'

    const fetchCurrentUser = async () => {
      try {
        const res = await apiClient.get(`/users/me`);
        currentUser.value = res.data;
      } catch (e) {
        console.error('Failed to fetch user:', e);
      }
    };
    
    const fetchMyReservation = async () => {
        try {
            const res = await apiClient.get(`/seats/reservations/me`);
            myReservation.value = res.data;
        } catch (e) {
            console.error('Failed to fetch active reservation:', e);
        }
    };

    const fetchSeats = async () => {
      loading.value = true;
      try {
        const res = await apiClient.get(`/seats`);
        seats.value = res.data;
      } catch (e) {
        console.error('Failed to fetch seats:', e);
      } finally {
        loading.value = false;
      }
    };

    const fetchHistoricalReservations = async () => {
      try {
        const res = await apiClient.get(`/seats/reservations/history`);
        historicalReservations.value = res.data;
      } catch (e) {
        console.error('Failed to fetch historical reservations:', e);
      }
    };

    onMounted(async () => {
      await fetchCurrentUser();
      await fetchMyReservation();
      // Always fetch seats, as the user might switch to the 'seats' tab later
      await fetchSeats(); 
      
      if (myReservation.value) {
        activeTab.value = 'current'; // If there's an active reservation, show current tab
      } else {
        activeTab.value = 'seats'; // If no active reservation, default to seats tab
      }
      loading.value = false; // All initial data should be loaded now
    });

    watch(activeTab, (newTab) => {
      if (newTab === 'history') {
        fetchHistoricalReservations();
      }
    });

    const seatsOnSelectedFloor = computed(() => {
      return seats.value.filter(s => s.floor === selectedFloor.value).sort((a, b) => a.code.localeCompare(b.code));
    });

    const filteredSeatsOnSelectedFloor = computed(() => {
      if (seatFilter.value === 'available') {
        return seatsOnSelectedFloor.value.filter(s => s.status === 'available');
      }
      return seatsOnSelectedFloor.value;
    });
    
    const getSeatDetails = (seatId) => {
        const seat = seats.value.find(s => s.id === seatId);
        return seat || { code: 'N/A', floor: 'N/A' };
    };

    const getSeatClass = (seat) => {
      return seat.status === 'available' ? 'available' : 'occupied';
    };
    
    const formatTimestamp = (ts) => {
      if (!ts) return 'N/A';
      return new Date(ts).toLocaleString('zh-CN');
    };

    const handleSeatClick = (seat) => {
      if (seat.status === 'available') {
        reserveSeat(seat);
      } else {
        alert(`座位 ${seat.code} 已被占用，请选择其他座位。`);
      }
    };

    const reserveSeat = async (seat) => {
      if (!currentUser.value) {
        alert('无法获取用户信息，请先登录。');
        return;
      }
      if (!confirm(`确认预约 ${selectedFloor.value} 层 ${seat.code} 号座位吗？`)) return;

      try {
        const expires = new Date();
        expires.setMinutes(expires.getMinutes() + 1);

        await apiClient.post(`/seats/reservations`, {
          seat_id: seat.id,
          user_id: currentUser.value.id,
          expires_at: expires.toISOString(),
        });

        alert('🎉 预约成功！座位将为您保留1分钟。');
        await fetchMyReservation(); // Refresh to show the reservation card
        await fetchSeats(); // Refresh seats to show the newly occupied seat
        activeTab.value = 'current'; // Switch to current reservation tab
      } catch (e) {
        console.error('Reservation failed:', e);
        const errorMsg = e.response?.data?.detail || '预约失败，请稍后再试。';
        alert(`❌ ${errorMsg}`);
      }
    };
    
    const cancelMyReservation = async () => {
        if (!myReservation.value) return;
        if (!confirm('您确定要取消当前的预约吗？')) return;
        
        try {
            await apiClient.post(`/seats/reservations/${myReservation.value.id}/cancel`);
            alert('预约已成功取消。');
            myReservation.value = null;
            await fetchSeats(); // Show the seat map again
        } catch(e) {
            console.error('Failed to cancel reservation:', e);
            const errorMsg = e.response?.data?.detail || '取消失败，请稍后再试。';
            alert(`❌ ${errorMsg}`);
        }
    };

    const getReservationStatusText = (status) => {
      switch (status) {
        case 'active': return '进行中';
        case 'cancelled': return '已取消';
        case 'expired': return '已过期';
        default: return status;
      }
    };

    const filteredHistoricalReservations = computed(() => {
      if (filterType.value === 'all') {
        return historicalReservations.value;
      } else if (filterType.value === 'normal') {
        return historicalReservations.value.filter(record => record.status === 'active' || record.status === 'cancelled');
      } else if (filterType.value === 'defaulted') {
        return historicalReservations.value.filter(record => record.status === 'expired');
      }
      return [];
    });

    return {
      seats,
      floors,
      selectedFloor,
      loading,
      myReservation,
      seatsOnSelectedFloor,
      filteredSeatsOnSelectedFloor,
      getSeatClass,
      getSeatDetails,
      handleSeatClick,
      cancelMyReservation,
      formatTimestamp,
      activeTab, // Add activeTab here
      historicalReservations, // Add historicalReservations here
      getReservationStatusText, // Add getReservationStatusText here
      filterType,
      filteredHistoricalReservations,
      seatFilter,
    };
  },
};
</script>

<style scoped>
.seat-reservation-page {
  padding: 24px;
  background-color: #f9fafb;
  min-height: 100vh;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
}
.page-header h1 {
  font-size: 2rem;
  font-weight: bold;
  color: #1f2937;
}
.page-header p {
  font-size: 1rem;
  color: #6b7280;
}

.tab-controls {
  display: flex;
  justify-content: center;
  margin-bottom: 32px;
  background-color: white;
  padding: 8px;
  border-radius: 9999px;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.tab-controls button {
  flex: 1;
  padding: 10px 20px;
  border: none;
  background-color: transparent;
  border-radius: 9999px;
  font-weight: 600;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-controls button:hover {
  background-color: #f3f4f6;
}

.tab-controls button.active {
  background-color: #4f46e5;
  color: white;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}

.tab-content {
  margin-top: 24px;
}

.floor-controls {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 32px;
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;
}

.floor-selector {
  display: flex;
  gap: 8px;
}

.floor-tab {
  padding: 10px 20px;
  border: 1px solid #d1d5db;
  background-color: white;
  border-radius: 9999px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
}
.floor-tab:hover {
  background-color: #f3f4f6;
}
.floor-tab.active {
  background-color: #4f46e5;
  color: white;
  border-color: #4f46e5;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 60px 0;
  color: #6b7280;
}

.spinner {
  border: 4px solid #e5e7eb;
  border-top: 4px solid #4f46e5;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.seats-grid-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}

.seat-filters {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  gap: 10px;
}

.seat-filters button {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 9999px;
  background-color: white;
  color: #374151;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.seat-filters button:hover {
  background-color: #f3f4f6;
}

.seat-filters button.active {
  background-color: #4f46e5;
  color: white;
  border-color: #4f46e5;
}

.seats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 16px;
}

.seat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 80px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 600;
  border: 2px solid transparent;
}

.seat-icon {
  font-size: 1.75rem;
}
.seat-code {
  font-size: 0.875rem;
}

.seat.available {
  background-color: #d1fae5;
  color: #065f46;
}
.seat.available:hover {
  border-color: #10b981;
  transform: translateY(-2px);
}

.seat.occupied {
  background-color: #fee2e2;
  color: #991b1b;
  cursor: not-allowed;
  opacity: 0.7;
}

.seat.my-reservation {
  background-color: #dbeafe;
  color: #1e40af;
}
.seat.my-reservation:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
}

/* My Reservation Card Styles */
.my-reservation-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 4rem;
}

.card {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  text-align: left;
}

.card-header {
  background-color: #ecfdf5;
  padding: 1.5rem;
  text-align: center;
}
.card-header .icon {
  font-size: 2.5rem;
}
.card-header h2 {
  margin: 0.5rem 0 0;
  color: #065f46;
  font-size: 1.5rem;
  font-weight: bold;
}

.card-content {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 1rem;
  color: #374151;
}
.info-row strong {
  font-weight: 600;
  color: #1f2937;
}

.card-footer {
  padding: 1.5rem;
  background-color: #f9fafb;
  text-align: center;
}

.cancel-btn {
  width: 100%;
  padding: 0.75rem 1rem;
  background-color: #ef4444;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}
.cancel-btn:hover {
  background-color: #dc2626;
}

/* Historical Reservations Styles */
.historical-reservations-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
}

.filters-history {
  display: flex;
  justify-content: flex-end; /* Align to the right */
  margin-bottom: 24px;
  gap: 8px; /* Space between buttons */
  padding: 10px 0; /* Add some vertical padding */
}

.filters-history button {
  padding: 8px 12px; /* Smaller padding for smaller buttons */
  border: 1px solid #d1d5db;
  border-radius: 9999px; /* Pill shape */
  background-color: white;
  color: #374151;
  font-size: 0.875rem; /* Smaller font size */
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap; /* Prevent text wrapping */
}

.filters-history button:hover {
  background-color: #f3f4f6;
  border-color: #9ca3af;
}

.filters-history button.active {
  background-color: #4f46e5;
  color: white;
  border-color: #4f46e5;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}


.history-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.history-item {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  overflow: hidden;
  transition: transform 0.2s;
}

.history-item:hover {
  transform: translateY(-4px);
}

.history-item .card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: #f9fafb;
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.history-item .card-header h2 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #ccc; /* Default grey */
}

.status-dot.active { background-color: #3b82f6; } /* Blue */
.status-dot.cancelled { background-color: #6b7280; } /* Grey */
.status-dot.expired { background-color: #ef4444; } /* Red */

.reservation-status-text {
  font-weight: 600;
}
.reservation-status-text.active { color: #3b82f6; }
.reservation-status-text.cancelled { color: #6b7280; }
.reservation-status-text.expired { color: #ef4444; }

/* Responsive Styles */
@media (max-width: 768px) {
  .seat-reservation-page {
    padding: 16px;
  }

  .page-header h1 {
    font-size: 1.5rem;
  }
  .page-header p {
    font-size: 0.875rem;
  }

  .tab-controls {
    max-width: 100%;
    overflow-x: auto;
    justify-content: flex-start;
  }
  .tab-controls button {
    padding: 8px 16px;
    font-size: 0.875rem;
    white-space: nowrap;
  }

  .floor-controls {
    flex-direction: column;
    gap: 16px;
    position: static;
  }

  .floor-selector {
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .seat-filters {
    position: static;
    transform: none;
    justify-content: center;
  }

  .seats-grid-container {
    padding: 16px;
  }

  .seats-grid {
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 12px;
  }

  .seat {
    height: 65px;
  }
  .seat-icon {
    font-size: 1.25rem;
  }
  .seat-code {
    font-size: 0.75rem;
  }

  .my-reservation-container {
    padding: 1rem;
  }
  
  .card {
    max-width: 100%;
  }
  
  .historical-reservations-container {
    padding: 16px 0;
  }

  .history-list {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}
</style>
