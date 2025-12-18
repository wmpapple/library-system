<template>
  <div class="borrow-page">
    <div class="category-tabs" ref="tabsContainer">
      <div class="slider" :style="sliderStyle"></div>
      <button
        v-for="(cat, key) in categories"
        :key="key"
        :ref="el => { if (el) tabButtons[key] = el }"
        @click="activeCategory = key"
        :class="{ active: activeCategory === key }"
        class="tab-button"
      >
        {{ cat.label }}
        <span class="count-badge">{{ cat.data.value.length }}</span>
      </button>
    </div>

    <div class="content-area">
      <!-- New Sub-tabs for History -->
      <div class="sub-category-tabs" v-if="activeCategory === 'history'">
        <button
          :class="{ 'active': activeHistorySubCategory === 'all' }"
          @click="activeHistorySubCategory = 'all'"
        >
          全部
        </button>
        <button
          :class="{ 'active': activeHistorySubCategory === 'normal' }"
          @click="activeHistorySubCategory = 'normal'"
        >
          正常归还
        </button>
        <button
          :class="{ 'active': activeHistorySubCategory === 'overdue' }"
          @click="activeHistorySubCategory = 'overdue'"
        >
          逾期归还
        </button>

      </div>

      <!-- New Fine Filter Toggle (moved outside sub-category-tabs) -->
      <div class="fine-filter-container"
           v-if="activeCategory === 'history' && activeHistorySubCategory === 'overdue'">
        <button
          :class="{ 'active': fineFilterMode === 'unpaid' }"
          @click="fineFilterMode = (fineFilterMode === 'unpaid' ? 'all' : 'unpaid')"
          class="filter-fine-button"
        >
          {{ fineFilterMode === 'unpaid' ? '全部逾期记录' : '只看未支付' }}
        </button>
      </div>

      <div v-if="computedActiveRecords.length > 0" class="cards-container">
        <div v-for="record in computedActiveRecords" :key="record.id" class="borrow-card">
          <div class="card-status" :class="getCardStatusClass(record)"></div>
          <div class="card-content">
            <div class="card-header">
              <span class="book-id">记录 #{{ record.displayId }}</span>
              <span class="date">{{ formatDate(record.borrowed_at) }} 借出</span>
            </div>
            <div class="card-body">
              <h3>📖 {{ getBookTitle(record.book_id) }}</h3>
              
              <!-- Conditional Date Info based on status -->
              <p v-if="wasReturnedLate(record)" class="return-info returned-late">
                ⚠️ 逾期归还于 {{ formatDate(record.returned_at) }}
                <span v-if="record.fine && !record.fine.paid" class="fine-amount">
                  罚金: {{ record.fine.amount }} 元
                </span>
              </p>
              <p v-else-if="record.returned_at" class="return-info">
                ✅ 正常归还于 {{ formatDate(record.returned_at) }}
              </p>
              <p v-else-if="isOverdue(record)" class="due-info overdue">
                🚨 已于 {{ formatDate(record.due_at) }} 逾期
                <span v-if="record.fine && !record.fine.paid" class="fine-amount">
                  罚金: {{ record.fine.amount }} 元
                </span>
              </p>
              <p v-else class="due-info">
                ⚠️ 应还日期: {{ formatDate(record.due_at) }}
              </p>
            </div>
            <div class="card-action">
              <button class="return-btn" @click="handleReturn(record.id)" v-if="!record.returned_at">📦 立即归还</button>
              <button class="pay-fine-btn" @click="handlePayFine(record.fine.id)" v-if="record.returned_at && record.fine && !record.fine.paid">💰 支付罚金</button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        <p>{{ emptyMessages[activeCategory] }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import apiClient from '@/api';

export default {
  name: 'MyBorrow',
  setup() {
    const records = ref([]);
    const books = ref([]);
    const activeCategory = ref('current');
    const activeHistorySubCategory = ref('all'); // New ref
    const fineFilterMode = ref('all'); // 'all' or 'unpaid'

    const tabButtons = ref({});
    const sliderStyle = ref({});


    const fetchRecords = async () => {
      try {
        const res = await apiClient.get(`/borrow/me`);
        // Sort records to ensure consistent client-side indexing
        const sortedRecords = res.data.sort((a, b) => new Date(b.borrowed_at) - new Date(a.borrowed_at));
        // Add a client-side displayId for sequential numbering
        records.value = sortedRecords.map((record, index) => ({
          ...record,
          displayId: index + 1
        }));
      } catch (e) { console.error(e); }
    };

    const fetchBooks = async () => {
      try {
        const res = await apiClient.get(`/books`);
        books.value = res.data;
      } catch (e) { console.error(e); }
    };

    const updateSlider = () => {
      nextTick(() => {
        const activeTabEl = tabButtons.value[activeCategory.value];
        if (activeTabEl) {
          sliderStyle.value = {
            width: `${activeTabEl.offsetWidth}px`,
            transform: `translateX(${activeTabEl.offsetLeft}px)`,
          };
        }
      });
    };

    onMounted(async () => {
      await Promise.all([fetchRecords(), fetchBooks()]);
      updateSlider();
    });
    
    watch([activeCategory, records], updateSlider);

    const isOverdue = (record) => record.status === 'overdue';
    const wasReturnedLate = (record) => record.returned_at && new Date(record.returned_at) > new Date(record.due_at);

    const currentBorrows = computed(() => records.value.filter(r => !r.returned_at && !isOverdue(r)));
    const overdueBorrows = computed(() => records.value.filter(r => isOverdue(r)));
    const historyBorrows = computed(() => records.value.filter(r => r.returned_at).sort((a, b) => new Date(b.borrowed_at) - new Date(a.borrowed_at)));

    // New computed properties for history sub-categories
    const allReturnedBorrows = computed(() => historyBorrows.value);
    const overdueReturnedBorrows = computed(() => {
      const lateReturned = historyBorrows.value.filter(r => wasReturnedLate(r));
      if (fineFilterMode.value === 'unpaid') {
        return lateReturned.filter(r => r.fine && !r.fine.paid && r.fine.amount > 0);
      }
      return lateReturned;
    });
    const normalReturnedBorrows = computed(() => historyBorrows.value.filter(r => !wasReturnedLate(r)));

    const categories = {
      current: { label: '当前借阅', data: currentBorrows },
      overdue: { label: '逾期未还', data: overdueBorrows },
      history: { label: '历史记录', data: historyBorrows },
    };
    const emptyMessages = {
      current: '👍 当前没有借阅中的图书。',
      overdue: '🎉 太棒了！没有逾期未还的记录。',
      history: '📭 暂无历史借阅记录。',
    };
    // Corrected computed property for active records
    const computedActiveRecords = computed(() => {
      if (activeCategory.value === 'history') {
        if (activeHistorySubCategory.value === 'all') {
          return allReturnedBorrows.value;
        } else if (activeHistorySubCategory.value === 'overdue') {
          return overdueReturnedBorrows.value;
        } else if (activeHistorySubCategory.value === 'normal') {
          return normalReturnedBorrows.value;
        }
      }
      return categories[activeCategory.value].data.value;
    });


    const getBookTitle = (bookId) => {
      const book = books.value.find(b => b.id === bookId);
      return book ? book.title : `图书 ID: ${bookId}`;
    };

    const getCardStatusClass = (record) => {
      if (record.returned_at) {
        if (wasReturnedLate(record)) {
          // Check fine status for returned late records
          if (record.fine && record.fine.amount > 0 && !record.fine.paid) {
            return 'returned-late-unpaid'; // Red for unpaid late fines
          } else if (record.fine && record.fine.amount > 0 && record.fine.paid) {
            return 'returned-late-paid'; // Yellow for paid late fines
          }
          return 'returned-late'; // Default orange if no fine info or fine is zero
        }
        return 'done'; // Green for returned on time
      }
      if (isOverdue(record)) {
        // Check fine status for currently overdue records
        if (record.fine && record.fine.amount > 0 && !record.fine.paid) {
            return 'overdue-unpaid'; // Red for unpaid currently overdue
        } else if (record.fine && record.fine.amount > 0 && record.fine.paid) {
            return 'overdue-paid'; // Yellow for paid overdue (shouldn't happen for active overdue, but for completeness)
        }
        return 'overdue'; // Default red if no fine info or fine is zero
      }
      return 'active'; // Blue for active (not returned, not overdue)
    };

    const handleReturn = async (id) => {
      if (!confirm('📦 确认归还这本书吗？')) return;
      try {
        await apiClient.post(`/borrow/return/${id}`, {});
        alert('🎉 归还成功！');
        fetchRecords();
      } catch (e) { 
        alert('❌ 归还失败: ' + (e.response?.data?.detail || e.message));
      }
    };

    const handlePayFine = async (fineId) => {
      if (!confirm('💰 确认支付罚金吗？')) return;
      try {
        await apiClient.patch(`/borrow/fines/${fineId}`, { paid: true });
        alert('✅ 罚金支付成功！');
        fetchRecords(); // Refresh records to update fine status
      } catch (e) {
        alert('❌ 罚金支付失败: ' + (e.response?.data?.detail || e.message));
      }
    };

    const formatDate = (str) => {
      if (!str) return 'N/A';
      const date = new Date(str);
      if (isNaN(date)) return 'Invalid Date';
      return date.toLocaleString();
    };

    return { 
      activeCategory, categories, emptyMessages, computedActiveRecords,
      handleReturn, formatDate, getBookTitle, getCardStatusClass, 
      isOverdue, wasReturnedLate,
      tabButtons, sliderStyle,
      activeHistorySubCategory, fineFilterMode,
      allReturnedBorrows,
      overdueReturnedBorrows,
      normalReturnedBorrows,
      handlePayFine
    };
  }
};
</script>

<style scoped>
.borrow-page { padding: 20px; background-color: #f9fafb; }
.category-tabs { position: relative; display: flex; justify-content: center; margin-bottom: 24px; background-color: white; padding: 8px; border-radius: 9999px; box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1); max-width: 500px; margin-left: auto; margin-right: auto; }
.slider { position: absolute; top: 8px; left: 0; height: calc(100% - 16px); background-color: #4f46e5; border-radius: 9999px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1); transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1); }
.tab-button { flex: 1; padding: 10px 20px; border: none; background-color: transparent; border-radius: 9999px; font-weight: 600; color: #4b5563; cursor: pointer; transition: color 0.3s ease; display: flex; align-items: center; justify-content: center; gap: 8px; position: relative; z-index: 1; }
.tab-button.active { color: white; }
.count-badge { background-color: rgba(75, 85, 99, 0.1); color: #4b5563; font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 12px; transition: all 0.3s ease; }
.tab-button.active .count-badge { background-color: rgba(255, 255, 255, 0.2); color: white; }
.content-area { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); }
.cards-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.borrow-card { background: white; border-radius: 12px; overflow: hidden; display: flex; border: 1px solid #e5e7eb; transition: all 0.2s ease; position: relative; }
.borrow-card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1); }
.card-status { width: 8px; }
.card-status.active { background: #3b82f6; } /* Blue for active */
.card-status.overdue { background: #ef4444; } /* Red for currently overdue */
.card-status.returned-late { background: #f97316; } /* Orange for returned late */
.card-status.done { background: #10b981; }  /* Green for returned on time */
/* New fine status colors */
.card-status.returned-late-unpaid { background: #ef4444; } /* Red */
.card-status.returned-late-paid { background: #facc15; } /* Yellow */
.card-status.overdue-unpaid { background: #ef4444; } /* Red */
.card-status.overdue-paid { background: #facc15; } /* Yellow */
.card-content { flex: 1; padding: 20px; }
.card-header { display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; margin-bottom: 10px; }
.card-body h3 { margin: 0 0 10px 0; font-size: 16px; color: #333; }
.return-info { color: #10b981; font-size: 13px; margin: 0; font-weight: 500; }
.return-info.returned-late { color: #f97316; }
.due-info { color: #3b82f6; font-size: 13px; margin: 0; font-weight: 500; }
.due-info.overdue { color: #ef4444; }
.card-action { margin-top: 15px; text-align: right; }
.return-btn { background: #eff6ff; color: #3b82f6; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.return-btn:hover { background: #3b82f6; color: white; }
.empty-state { text-align: center; padding: 40px 20px; color: #6b7280; font-size: 1.1rem; }

.fine-amount {
  background-color: #fee2e2;
  color: #ef4444;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  margin-left: 10px;
  font-weight: 600;
}

.pay-fine-btn {
  background: #fdf2f8; /* Light pink/purple */
  color: #db2777; /* Darker pink/purple */
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 10px; /* Space from return button */
}

.pay-fine-btn:hover {
  background: #db2777;
  color: white;
  box-shadow: 0 4px 10px rgba(219, 39, 119, 0.2);
}

.filter-fine-button {
  padding: 8px 15px;
  border: none;
  border-radius: 6px;
  background-color: #e2e8f0; /* Neutral background */
  color: #4b5563; /* Dark gray text */
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-left: 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05); /* Subtle shadow */
}

.filter-fine-button:hover {
  background-color: #cbd5e1; /* Slightly darker neutral */
  color: #334155; /* Darker text */
}

.filter-fine-button.active {
  background-color: #4f46e5; /* Active purple color, consistent with category tabs */
  color: white;
  box-shadow: 0 4px 8px rgba(79, 70, 229, 0.3); /* Stronger shadow for active */
}

.fine-filter-container {
  display: flex;
  justify-content: flex-end; /* Align to the right */
  margin-top: -10px; /* Adjust spacing with cards-container */
  margin-bottom: 20px;
  padding-right: 10px; /* Some padding from the edge */
}

/* Styles for sub-category tabs (for history) */
.sub-category-tabs {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 10px;
  margin-bottom: 20px;
  padding: 8px;
  background-color: #f1f5f9;
  border-radius: 8px;
}

.sub-category-tabs button {
  padding: 8px 15px;
  border: none;
  border-radius: 6px;
  background-color: transparent;
  color: #4b5563;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sub-category-tabs button:hover {
  background-color: #e2e8f0;
}

.sub-category-tabs button.active {
  background-color: #4f46e5;
  color: white;
  box-shadow: 0 2px 5px rgba(79, 70, 229, 0.2);
}

@media (max-width: 768px) {
  .borrow-page {
    padding: 10px;
  }
  .category-tabs, .sub-category-tabs {
    justify-content: flex-start;
    overflow-x: auto;
    -ms-overflow-style: none;  /* IE and Edge */
    scrollbar-width: none;  /* Firefox */
  }
  .category-tabs::-webkit-scrollbar, .sub-category-tabs::-webkit-scrollbar {
    display: none; /* Chrome, Safari, Opera */
  }
  .tab-button, .sub-category-tabs button {
    white-space: nowrap;
  }

  .content-area {
    padding: 15px;
  }

  .cards-container {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 15px;
  }

  .borrow-card {
    flex-direction: column;
  }
  .card-status {
    width: 100%;
    height: 6px;
  }
  .card-content {
    padding: 15px;
  }
  .card-body h3 {
    font-size: 15px;
  }
  
  .fine-filter-container {
    justify-content: center;
    margin-top: 15px;
    margin-bottom: 15px;
    padding-right: 0;
  }
}
</style>