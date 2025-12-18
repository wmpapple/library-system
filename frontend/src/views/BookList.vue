<template>
  <div class="page-container">
    <div class="toolbar">
      <div class="filter-container">
        <div class="filter-item">
          <span class="filter-icon">🔍</span>
          <input v-model="titleQuery" placeholder="书名" class="filter-input" />
        </div>
        <div class="filter-item">
          <span class="filter-icon">🔍</span>
          <input v-model="authorQuery" placeholder="作者" class="filter-input" />
        </div>
        <div class="filter-item">
          <span class="filter-icon">🔍</span>
          <input v-model="categoryQuery" placeholder="分类" class="filter-input" />
        </div>
        <div class="filter-item">
          <span class="filter-icon">🔍</span>
          <input v-model="isbnQuery" placeholder="ISBN" class="filter-input" />
        </div>
      </div>
      <button class="btn-primary" v-if="isAdmin" @click="showAddModal = true">
        ➕ 新增图书
      </button>
    </div>

    <div class="data-display-container">
      <!-- Desktop Table -->
      <div class="table-card desktop-view">
        <table class="styled-table">
          <thead>
            <tr>
              <th width="80">ID</th>
              <th>图书信息</th>
              <th>作者</th>
              <th>分类</th>
              <th>库存状态</th>
              <th width="200">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="book in filteredBooks" :key="book.id">
              <td class="id-col">#{{ book.id }}</td>
              <td>
                <div class="book-info">
                  <span class="book-icon">📖</span>
                  <span class="book-title">{{ book.title }}</span>
                </div>
              </td>
              <td>{{ book.author }}</td>
              <td><span class="tag">{{ book.category || '综合' }}</span></td>
              <td>
                <div class="stock-badge" :class="book.available_copies > 0 ? 'in-stock' : 'out-stock'">
                  <span class="dot"></span>
                  {{ book.available_copies }} / {{ book.total_copies }}
                </div>
              </td>
              <td>
                <div class="action-buttons-group">
                <button 
                    class="btn-sm btn-blue"
                    :class="{ 'btn-disabled': book.available_copies <= 0 }"
                    @click="handleBorrow(book)" 
                    :disabled="book.available_copies <= 0"
                  >
                    {{ book.available_copies > 0 ? '借阅' : '缺货' }}
                </button>
                <template v-if="isAdmin">
                  <button class="btn-sm btn-orange" @click="openEditModal(book)">编辑</button>
                  <button class="btn-sm btn-red" @click="handleDeleteBook(book)">删除</button>
                </template>
              </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Mobile Card List -->
      <div class="mobile-view">
        <div v-for="book in filteredBooks" :key="book.id" class="book-card">
          <div class="book-card-header">
            <span class="book-icon">📖</span>
            <h3 class="book-title">{{ book.title }}</h3>
          </div>
          <div class="book-card-body">
            <div class="card-row">
              <span class="card-label">作者:</span>
              <span class="card-value">{{ book.author }}</span>
            </div>
            <div class="card-row">
              <span class="card-label">分类:</span>
              <span class="card-value"><span class="tag">{{ book.category || '综合' }}</span></span>
            </div>
             <div class="card-row">
              <span class="card-label">ISBN:</span>
              <span class="card-value">{{ book.isbn }}</span>
            </div>
            <div class="card-row">
              <span class="card-label">库存:</span>
              <span class="card-value">
                <div class="stock-badge" :class="book.available_copies > 0 ? 'in-stock' : 'out-stock'">
                  <span class="dot"></span>
                  {{ book.available_copies }} / {{ book.total_copies }}
                </div>
              </span>
            </div>
          </div>
          <div class="book-card-footer">
             <button 
                class="btn-sm btn-blue"
                :class="{ 'btn-disabled': book.available_copies <= 0 }"
                @click="handleBorrow(book)" 
                :disabled="book.available_copies <= 0"
              >
                {{ book.available_copies > 0 ? '借阅' : '缺货' }}
            </button>
            <template v-if="isAdmin">
              <button class="btn-sm btn-orange" @click="openEditModal(book)">编辑</button>
              <button class="btn-sm btn-red" @click="handleDeleteBook(book)">删除</button>
            </template>
          </div>
        </div>
      </div>

      <div v-if="filteredBooks.length === 0" class="empty-state">
        🍃 没有找到相关图书
      </div>
    </div>

    <!-- Add Book Modal -->
    <div class="modal-overlay" v-if="showAddModal" @click.self="showAddModal = false">
      <div class="modal-box">
        <div class="modal-header">
          <h3>📦 入库新书</h3>
          <button class="close-btn" @click="showAddModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>书名 <span style="color:red">*</span></label>
            <input v-model="newBook.title" placeholder="请输入书名" />
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>作者 <span style="color:red">*</span></label>
              <input v-model="newBook.author" placeholder="作者姓名" />
            </div>
            <div class="form-group">
              <label>ISBN <span style="color:red">*</span></label>
              <input v-model="newBook.isbn" placeholder="国际标准书号" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>数量</label>
              <input v-model.number="newBook.total_copies" type="number" min="1" />
            </div>
            <div class="form-group">
              <label>分类</label>
              <input v-model="newBook.category" placeholder="如: 计算机" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-text" @click="showAddModal = false">取消</button>
          <button class="btn-primary" @click="handleAddBook">确认入库</button>
        </div>
      </div>
    </div>

    <!-- Edit Book Modal -->
    <div class="modal-overlay" v-if="showEditModal" @click.self="showEditModal = false">
      <div class="modal-box">
        <div class="modal-header">
          <h3>✏️ 修改图书信息</h3>
          <button class="close-btn" @click="showEditModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>书名 <span style="color:red">*</span></label>
            <input v-model="editingBook.title" placeholder="请输入书名" />
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>作者 <span style="color:red">*</span></label>
              <input v-model="editingBook.author" placeholder="作者姓名" />
            </div>
            <div class="form-group">
              <label>ISBN <span style="color:red">*</span></label>
              <input v-model="editingBook.isbn" placeholder="国际标准书号" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>数量</label>
              <input v-model.number="editingBook.total_copies" type="number" min="1" />
            </div>
            <div class="form-group">
              <label>分类</label>
              <input v-model="editingBook.category" placeholder="如: 计算机" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-text" @click="showEditModal = false">取消</button>
          <button class="btn-primary" @click="handleUpdateBook">确认修改</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, reactive } from 'vue'
import apiClient from '@/api'

export default {
  name: 'BookList',
  setup() {
    const books = ref([])
    const titleQuery = ref('')
    const authorQuery = ref('')
    const categoryQuery = ref('')
    const isbnQuery = ref('')

    const showAddModal = ref(false)
    const showEditModal = ref(false)
    const user = JSON.parse(sessionStorage.getItem('user') || '{}')
    const isAdmin = user.role === 'admin'
    
    const newBook = reactive({ title: '', author: '', isbn: '', total_copies: 1, category: '综合', available_copies: 1 })
    const editingBook = ref(null)

    const fetchBooks = async () => {
      try {
        const res = await apiClient.get(`/books/`)
        books.value = res.data
      } catch(e) { console.error(e) }
    }

    const handleBorrow = async (book) => {
      if(!confirm(`📚 确认借阅《${book.title}》吗？`)) return
      try {
        const dueAt = new Date(Date.now() + 2 * 60 * 1000).toISOString()
        await apiClient.post(`/borrow/`, {
          book_id: book.id,
          due_at: dueAt
        })
        alert('✅ 借阅成功！请在2分钟内归还。')
        fetchBooks()
      } catch (e) {
        alert('❌ 借阅失败: ' + (e.response?.data?.detail || e.message))
      }
    }

    const handleAddBook = async () => {
      if (!newBook.title || !newBook.author || !newBook.isbn) {
        alert('❌ 请填写所有必填项！');
        return;
      }
      try {
        newBook.available_copies = newBook.total_copies
        await apiClient.post(`/books/`, newBook)
        alert('✅ 添加成功')
        showAddModal.value = false
        fetchBooks()
      } catch (e) { 
        alert('❌ 添加失败: ' + (e.response?.data?.detail || e.message)) 
      }
    }

    const openEditModal = (book) => {
      editingBook.value = { ...book }
      showEditModal.value = true
    }

    const handleUpdateBook = async () => {
      if (!editingBook.value) return;
      const { id, ...bookData } = editingBook.value
      try {
        await apiClient.put(`/books/${id}`, bookData)
        alert('✅ 修改成功')
        showEditModal.value = false
        fetchBooks()
      } catch (e) {
        alert('❌ 修改失败: ' + (e.response?.data?.detail || e.message))
      }
    }

    const handleDeleteBook = async (book) => {
      if (!confirm(`🗑️ 确认删除《${book.title}》吗？此操作不可恢复。`)) return;
      try {
        await apiClient.delete(`/books/${book.id}`)
        alert('✅ 删除成功')
        fetchBooks()
      } catch (e) {
        alert('❌ 删除失败: ' + (e.response?.data?.detail || e.message))
      }
    }

    const filteredBooks = computed(() => {
      let filtered = books.value;
      
      const tq = titleQuery.value.toLowerCase()
      if (tq) {
        filtered = filtered.filter(b => b.title.toLowerCase().includes(tq))
      }

      const aq = authorQuery.value.toLowerCase()
      if (aq) {
        filtered = filtered.filter(b => b.author.toLowerCase().includes(aq))
      }

      const cq = categoryQuery.value.toLowerCase()
      if (cq) {
        filtered = filtered.filter(b => (b.category || '').toLowerCase().includes(cq))
      }

      const iq = isbnQuery.value.toLowerCase()
      if (iq) {
        filtered = filtered.filter(b => b.isbn.toLowerCase().includes(iq))
      }

      return filtered;
    })

    onMounted(fetchBooks)
    return { 
      books,
      titleQuery,
      authorQuery,
      categoryQuery,
      isbnQuery,
      isAdmin, 
      showAddModal,
      showEditModal,
      newBook,
      editingBook, 
      filteredBooks, 
      handleBorrow, 
      handleAddBook,
      openEditModal,
      handleUpdateBook,
      handleDeleteBook
    }
  }
}
</script>

<style scoped>
/* Page Styles */
.page-container { padding: 0 10px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
.filter-container {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-item {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 30px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 10px rgba(0,0,0,0.03);
  padding: 0 15px;
  transition: border-color 0.2s;
}
.filter-item:focus-within {
  border-color: #667eea;
}
.filter-icon {
  opacity: 0.5;
  margin-right: 8px;
}
.filter-input {
  border: none;
  outline: none;
  background: transparent;
  padding: 10px 0;
  font-size: 14px;
  width: 120px; /* Adjust as needed */
}


/* Buttons */
.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none;
  padding: 10px 20px; border-radius: 30px; cursor: pointer; font-weight: 600;
  box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3); transition: transform 0.2s;
}
.btn-primary:hover { transform: translateY(-2px); }
.btn-text { background: none; border: none; cursor: pointer; color: #666; margin-right: 10px; }

/* Table Styles */
.table-card { background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); overflow: hidden; }
.styled-table { width: 100%; border-collapse: collapse; }
.styled-table th { background: #f8f9fa; padding: 15px 20px; text-align: left; color: #64748b; font-weight: 600; font-size: 13px; }
.styled-table td { padding: 15px 20px; border-bottom: 1px solid #f1f5f9; color: #333; font-size: 14px; }
.book-info { display: flex; align-items: center; gap: 10px; }
.book-icon { font-size: 20px; background: #e0f2fe; padding: 8px; border-radius: 8px; }
.book-title { font-weight: 600; }
.tag { background: #f1f5f9; padding: 4px 10px; border-radius: 20px; font-size: 12px; color: #64748b; }
.stock-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; }
.stock-badge.in-stock { background: #dcfce7; color: #166534; }
.stock-badge.out-stock { background: #fee2e2; color: #991b1b; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.id-col { color: #94a3b8; font-family: monospace; }

.btn-sm { padding: 6px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.btn-blue { background: #e0e7ff; color: #4338ca; }
.btn-blue:hover { background: #4338ca; color: white; }
.btn-orange { background: #ffedd5; color: #9a3412; }
.btn-orange:hover { background: #f97316; color: white; }
.btn-red { background: #fee2e2; color: #991b1b; }
.btn-red:hover { background: #ef4444; color: white; }
.btn-disabled { background: #f1f5f9; color: #94a3b8; cursor: not-allowed; }
.action-buttons-group { display: flex; gap: 10px; }

.empty-state { padding: 40px; text-align: center; color: #94a3b8; }

/* Modal */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); display: flex; justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(2px); }
.modal-box { background: white; width: 400px; border-radius: 16px; padding: 25px; box-shadow: 0 20px 50px rgba(0,0,0,0.1); animation: modalUp 0.3s ease-out; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.modal-header h3 { margin: 0; }
.close-btn { background: none; border: none; font-size: 24px; cursor: pointer; color: #999; }
.form-group { margin-bottom: 15px; }
.form-row { display: flex; gap: 15px; }
.form-group label { display: block; margin-bottom: 8px; font-size: 13px; color: #64748b; }
.form-group input { width: 100%; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; box-sizing: border-box; transition: border-color 0.2s; }
.form-group input:focus { border-color: #667eea; outline: none; }
.modal-footer { display: flex; justify-content: flex-end; margin-top: 20px; }

@keyframes modalUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

/* Mobile Card View */
.mobile-view { display: none; }
.book-card {
  background: white;
  border-radius: 12px;
  margin-bottom: 15px;
  padding: 15px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.05);
}
.book-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f1f5f9;
}
.book-card-header h3 {
  margin: 0;
  font-size: 16px;
}
.book-card-body {
  padding: 15px 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}
.card-label {
  color: #64748b;
  font-weight: 500;
}
.book-card-footer {
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* Responsive Styles */
@media (max-width: 768px) {
  .page-container {
    padding: 0;
  }
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    padding: 15px;
    background: white;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 15px;
  }
  .filter-container {
    flex-direction: column;
    width: 100%;
  }
  .filter-item {
    width: 100%;
    box-sizing: border-box;
  }
  .filter-input {
    width: 100%;
  }

  .desktop-view { display: none; }
  .mobile-view { display: block; padding: 0 15px; }

  .table-card {
    box-shadow: none;
    border-radius: 0;
    background: transparent;
  }

  .modal-box {
    width: 90%;
    margin: 0 auto;
  }
  .form-row {
    flex-direction: column;
    gap: 0;
  }
}
</style>