<template>
  <div class="data-sync-container">
    <h2><span class="section-icon">🔄</span> 数据同步</h2>
    <p class="subtitle">这里显示了所有数据库总体的同步状态。点击有冲突的条目来解决冲突。</p>
    
    <!-- START: New Filter UI -->
    <div class="filter-controls">
      <strong>筛选源数据库:</strong>
      <button
        v-for="db in dbSources"
        :key="db"
        @click="toggleSource(db)"
        :class="['db-filter-btn', { active: selectedSources.has(db) }]"
      >
        <span class="btn-icon"></span>
        {{ db }}
      </button>
    </div>
    <!-- END: New Filter UI -->
    
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div class="log-table-wrapper">
      <table class="log-table">
        <thead>
          <tr>
            <th style="width: 20px;"></th>
            <th>源数据库</th>
            <th>操作表</th>
            <th>记录 ID</th>
            <th>主状态</th>
            <th>操作时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="6" class="loading-state">正在加载日志...</td>
          </tr>
          <tr v-else-if="filteredLogs.length === 0">
            <td colspan="6" class="empty-state">
              <span v-if="groupedLogs.length === 0">没有可显示的日志记录。</span>
              <span v-else>没有符合筛选条件的日志记录。</span>
            </td>
          </tr>
          <template v-for="log in filteredLogs" :key="log.key">
            <tr class="log-group-header" @click="toggleDetails(log.key)">
              <td>
                <span class="expand-icon" :class="{ expanded: expandedGroups.has(log.key) }">▶</span>
              </td>
              <td><span class="db-tag">{{ log.source_db }}</span></td>
              <td>{{ log.table_name }}</td>
              <td>#{{ log.record_id }}</td>
              <td>
                <span :class="['status-badge', getGroupStatusClass(log.replicas)]">
                  {{ getGroupStatusText(log.replicas) }}
                </span>
              </td>
              <td>{{ formatTimestamp(log.logged_at) }}</td>
            </tr>
            <tr v-if="expandedGroups.has(log.key)" class="details-row">
              <td colspan="6" class="details-cell">
                <table class="details-table">
                  <thead>
                    <tr>
                      <th>目标库</th>
                      <th>同步状态</th>
                      <th>详细信息 / 操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="replica in log.replicas" :key="replica.target_db">
                      <td><span class="db-tag">{{ replica.target_db }}</span></td>
                      <td>
                        <span :class="['status-badge', `status-badge-${replica.status}`]">
                          {{ getStatusText(replica.status) }}
                        </span>
                      </td>
                      <td class="details">
                        <!-- Case 1: Unresolved conflict -->
                        <div v-if="replica.conflict_id && replica.status !== 'resolved'">
                          <button class="btn btn-sm btn-resolve" @click.stop="toggleConflictDetails(replica.conflict_id)">
                            {{ conflictDetails[replica.conflict_id] ? '隐藏冲突详情' : '解决冲突' }}
                          </button>
                        </div>
                        <!-- Case 2: Resolved conflict -->
                        <div v-else-if="replica.status === 'resolved'" class="resolved-info">
                          <span class="resolved-icon">✔️</span> {{ replica.details || '冲突已解决' }}
                        </div>
                        <!-- Case 3: No conflict or other statuses -->
                        <div v-else>{{ replica.details || '-' }}</div>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <!-- Conflict Resolution UI -->
                <template v-for="replica in log.replicas" :key="replica.target_db">
                  <div v-if="replica.conflict_id && conflictDetails[replica.conflict_id]" class="conflict-resolver-wrapper">
                    <div class="card-body">
                      <div v-if="conflictDetails[replica.conflict_id].isLoading" class="loading">加载中...</div>
                      <div v-else-if="conflictDetails[replica.conflict_id].error" class="error-message">
                        {{ conflictDetails[replica.conflict_id].error }}
                      </div>
                      <div v-else class="data-comparison">
                        <!-- Dynamic display for all conflicting versions -->
                        <div v-for="(dbData, dbKey) in conflictDetails[replica.conflict_id].data.conflicting_data" :key="dbKey" class="data-source">
                          <h4>
                            数据库版本: <span class="db-tag-xl">{{ dbKey }}</span>
                          </h4>
                          <div class="data-as-json">
                            <div 
                              v-for="(value, key) in dbData" 
                              :key="key"
                              :class="{ 'diff-highlight': conflictDetails[replica.conflict_id].differingKeys.has(key) }"
                            >
                              <span class="json-key">"{{ key }}"</span>: <span class="json-value">"{{ value }}"</span>
                            </div>
                          </div>
                          <div class="actions">
                            <button @click="resolveConflict(replica.conflict_id, dbKey, log.source_db)" class="btn btn-resolve-source">
                              <span class="btn-icon">✅</span> 保留这个版本
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </template>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import apiClient from '@/api';

export default {
  name: 'DataSynchronization',
  setup() {
    const groupedLogs = ref([]);
    const isLoading = ref(true);
    const error = ref('');
    const expandedGroups = ref(new Set());
    const conflictDetails = ref({});

    // --- START: New Filtering Logic ---
    const dbSources = ref(['MySQL', 'PostgreSQL', 'SQLServer']); // Hardcoded list of DB sources
    const selectedSources = ref(new Set(dbSources.value));

    const toggleSource = (db) => {
      if (selectedSources.value.has(db)) {
        selectedSources.value.delete(db);
      } else {
        selectedSources.value.add(db);
      }
    };

    const filteredLogs = computed(() => {
      if (selectedSources.value.size === dbSources.value.length) {
        return groupedLogs.value; // No filter active, return all
      }
      return groupedLogs.value.filter(log => selectedSources.value.has(log.source_db));
    });
    // --- END: New Filtering Logic ---

    const fetchLogs = async () => {
      isLoading.value = true;
      error.value = '';
      try {
        const response = await apiClient.get('/sync/logs');
        groupedLogs.value = response.data;
      } catch (err) {
        const message = err.response?.data?.detail || '无法获取同步日志。';
        error.value = `错误: ${message}`;
        console.error(err);
      } finally {
        isLoading.value = false;
      }
    };
    
    const toggleConflictDetails = async (conflictId) => {
        if (conflictDetails.value[conflictId] && !conflictDetails.value[conflictId].isLoading) {
            delete conflictDetails.value[conflictId];
            return;
        }
        if (conflictDetails.value[conflictId]?.isLoading) return; // Prevent re-clicking while loading

        conflictDetails.value[conflictId] = { isLoading: true, data: null, error: null, differingKeys: new Set() };

        try {
            const response = await apiClient.get(`/conflicts/${conflictId}`);
            const conflictData = response.data;

            // --- Find differing keys ---
            const differingKeysSet = new Set();
            const versions = Object.values(conflictData.conflicting_data);
            if (versions.length > 1) {
                const allKeys = new Set(versions.flatMap(v => Object.keys(v)));
                for (const key of allKeys) {
                    const firstValue = versions[0]?.[key];
                    for (let i = 1; i < versions.length; i++) {
                        if (versions[i]?.[key] !== firstValue) {
                            differingKeysSet.add(key);
                            break;
                        }
                    }
                }
            }
            // --- End find ---

            conflictDetails.value[conflictId] = { 
                data: conflictData, 
                isLoading: false, 
                error: null,
                differingKeys: differingKeysSet 
            };
        } catch (err) {
            console.error(`Failed to fetch details for conflict ${conflictId}`, err);
            conflictDetails.value[conflictId] = { 
                isLoading: false, 
                error: `无法加载冲突 #${conflictId} 的详细信息。`,
                data: null,
                differingKeys: new Set(),
            };
        }
    };

    const resolveConflict = async (conflictId, dbKeyToKeep, sourceDb) => {
      // Immediately mark as loading to prevent double clicks
      if (conflictDetails.value[conflictId]) {
        conflictDetails.value[conflictId].isLoading = true;
      }

      try {
        await apiClient.post(`/conflicts/${conflictId}/resolve`, { 
          resolution_db_key: dbKeyToKeep,
          source_db: sourceDb
        });

        // The UI will now be updated on the next refresh, which is simpler and more reliable.
        // We will just re-fetch the logs to show the true state from the backend.
        await fetchLogs();

        // Close the conflict details view
        if (conflictDetails.value[conflictId]) {
          delete conflictDetails.value[conflictId];
        }

      } catch (err) {
        if (conflictDetails.value[conflictId]) {
          conflictDetails.value[conflictId].error = `处理冲突 #${conflictId} 失败。`;
          conflictDetails.value[conflictId].isLoading = false; // Reset loading on error
        }
        console.error(err);
      }
    };

    const getStatusText = (status) => {
      const map = { 'synced': '已同步', 'conflict': '冲突', 'failed': '失败', 'deleted': '已删除', 'resolved': '已解决', 'unresolved': '存在冲突' };
      return map[status] || status;
    };
    
    const getGroupStatus = (replicas) => {
      if (!replicas || replicas.length === 0) {
        return 'synced'; // Default for empty group
      }

      const statuses = new Set(replicas.map(r => r.status));

      if (statuses.has('failed')) {
        return 'failed';
      }
      // After fix, 'unresolved' is the key state from backend for an active conflict
      if (statuses.has('unresolved')) {
        return 'conflict';
      }
      if (statuses.has('conflict')) { // Legacy or other conflict types
        return 'conflict';
      }

      // If all replicas are 'resolved' or 'synced', the conflict is resolved.
      if (replicas.every(r => r.status === 'synced' || r.status === 'resolved')) {
         // If there's at least one 'resolved' status, we show the group as resolved.
         if (statuses.has('resolved')) {
           return 'resolved';
         }
         return 'synced';
      }

      return 'synced'; // Fallback
    };
    
    const getGroupStatusText = (replicas) => {
      const status = getGroupStatus(replicas);
      if (status === 'failed') return '部分失败';
      if (status === 'conflict') return '存在冲突';
      if (status === 'resolved') return '冲突已解决';
      return '全部同步';
    };

    const getGroupStatusClass = (replicas) => {
      const status = getGroupStatus(replicas);
      if (status === 'failed') return 'status-badge-failed';
      if (status === 'conflict') return 'status-badge-conflict';
      if (status === 'resolved') return 'status-badge-resolved';
      return 'status-badge-synced';
    };

    const formatTimestamp = (ts) => {
      if (!ts) return '';
      return new Date(ts).toLocaleString('zh-CN', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    };
    
    const toggleDetails = (key) => {
      if (expandedGroups.value.has(key)) {
        expandedGroups.value.delete(key);
      } else {
        expandedGroups.value.add(key);
      }
    };

    onMounted(fetchLogs);

    return {
      filteredLogs,
      dbSources,
      selectedSources,
      toggleSource,
      groupedLogs,
      isLoading,
      error,
      expandedGroups,
      conflictDetails,
      getStatusText,
      getGroupStatusClass,
      getGroupStatusText,
      formatTimestamp,
      toggleDetails,
      toggleConflictDetails,
      resolveConflict,
    };
  },
};
</script>

<style scoped>
/* General Container */
.data-sync-container {
  padding: 2rem;
  background-color: #f4f7f6;
}

h2 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.5rem;
}
.subtitle {
  color: #666;
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1rem;
}
.section-icon { font-size: 1.8rem; }

/* Filter Controls */
.filter-controls {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  display: flex;
  align-items: center;
  gap: 1rem;
}

.filter-controls strong {
  color: #333;
  font-weight: 600;
}

.db-filter-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background-color: #f9f9f9;
  color: #666;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.db-filter-btn:hover {
  border-color: #ccc;
  background-color: #f0f0f0;
}

.db-filter-btn .btn-icon {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #aaa;
  background-color: white;
  transition: all 0.2s ease;
}

.db-filter-btn.active {
  background-color: #4f46e5;
  color: white;
  border-color: #4f46e5;
}

.db-filter-btn.active .btn-icon {
  background-color: #6ee7b7; /* A light green for the 'on' state */
  border-color: #4f46e5;
}


.loading, .loading-state, .empty-state {
  text-align: center;
  font-size: 1.1rem;
  color: #7f8c8d;
  padding: 2rem;
}
.error-message {
  margin-top: 1rem;
  color: #c0392b;
  background-color: #fbeae5;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #e74c3c;
}

/* Logs Section */
.log-table-wrapper {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  overflow-x: auto;
}
.log-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}
.log-table th, .log-table td {
  padding: 12px 15px;
  border-bottom: 1px solid #eee;
  font-size: 0.9rem;
  vertical-align: middle;
}
.log-table th {
  background-color: #fafafa;
  font-weight: 600;
  color: #333;
}
.log-group-header {
  cursor: pointer;
  transition: background-color 0.2s;
}
.log-group-header:hover { background-color: #f9f9f9; }

.expand-icon {
  display: inline-block;
  transition: transform 0.2s;
  font-size: 0.7rem;
  color: #999;
}
.expand-icon.expanded { transform: rotate(90deg); }

.details-row { background-color: #fafcff; }
.details-cell { padding: 0 !important; }
.details-table { width: 100%; }
.details-table th, .details-table td {
    padding: 10px 15px;
    border-bottom: 1px solid #eaf2ff;
}
.details-table th { background-color: #f0f5ff; }
.details-table td {
  vertical-align: middle;
}
.details { max-width: 300px; white-space: pre-wrap; word-break: break-all; }

.db-tag {
  background-color: #eef2ff;
  color: #4f46e5;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}
.db-tag-xl {
  background-color: #e0e7ff;
  color: #3730a3;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
}
.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: capitalize;
}
.status-badge-synced { background-color: #dcfce7; color: #166534; }
.status-badge-deleted { background-color: #f1f5f9; color: #475569; }
.status-badge-conflict { background-color: #fffbeb; color: #b45309; }
.status-badge-resolved { background-color: #d1fae5; color: #065f46; } /* Tailwind green-100/green-800 */
.status-badge-failed { background-color: #fee2e2; color: #991b1b; }


.resolved-info {
  color: #065f46; /* Tailwind green-800 */
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.resolved-icon {
  font-size: 1.1rem;
}

/* Conflict Resolver Styles */
.btn-sm {
  padding: 4px 8px;
  font-size: 0.8rem;
  border-radius: 4px;
}
.btn-resolve {
    background-color: #f39c12;
    color: white;
    border: none;
    cursor: pointer;
}
.conflict-resolver-wrapper {
  padding: 1.5rem;
  background-color: #fff;
  border-top: 2px dashed #ffeeba;
}
.card-body {
  padding: 0;
}
.data-comparison {
  display: flex;
  flex-direction: row;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.data-source {
  flex: 1;
  min-width: 0; /* Prevents flex items from overflowing */
  display: flex;
  flex-direction: column;
}
.data-source h4 { color: #2980b9; }
.data-replica h4 { color: #27ae60; }
h4 {
  margin-top: 0;
  border-bottom: 2px solid #ecf0f1;
  padding-bottom: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}
pre, .data-as-json {
  white-space: pre-wrap;
  word-wrap: break-word;
  background-color: #ecf0f1;
  color: #2c3e50;
  padding: 1rem;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.75rem; /* Smaller font */
  max-height: 250px; /* Constrain height */
  overflow-y: auto;  /* Add scroll for long content */
  flex-grow: 1;
}
.data-as-json .json-key {
  color: #9b59b6; /* Amethyst for key */
}
.data-as-json .json-value {
  color: #2980b9; /* Belize Hole for value */
}
.diff-highlight {
  color: #c0392b !important; /* Pomegranate red for highlighted rows */
  font-weight: 600;
}
.diff-highlight .json-key, .diff-highlight .json-value {
  color: inherit; /* Make key and value inherit the red color */
}

.actions {
  display: flex;
  justify-content: center; /* Center the button */
  border-top: 1px solid #ecf0f1;
  padding-top: 1rem;
  margin-top: auto; /* Push actions to the bottom */
}
.btn {
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.btn:not(.btn-sm):hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
.btn-resolve-source { background-color: #3498db; color: white; padding: 0.6rem 1.2rem; font-size: 0.9rem;}
.btn-resolve-replica { background-color: #2ecc71; color: white; padding: 0.6rem 1.2rem; font-size: 0.9rem;}
</style>
