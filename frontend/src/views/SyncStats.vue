<template>
  <div class="stats-container">
    <header class="stats-header">
      <h1><span class="header-icon">📊</span>同步统计报表</h1>
      <p>近7日同步操作的统计数据和错误汇总</p>
    </header>

    <!-- START: New Filter UI -->
    <div class="filter-controls">
      <strong>筛选数据库:</strong>
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

    <div v-if="isLoading" class="loading-container">
      <div class="spinner"></div>
      <p>正在加载报表...</p>
    </div>

    <div v-if="error" class="error-container">
      <p>加载失败: {{ error }}</p>
    </div>

    <main v-if="!isLoading && !error" class="stats-grid">
      <!-- Daily Stats Chart -->
      <section class="chart-card">
        <v-chart
          class="chart"
          :option="dailyChartOption"
          autoresize
          @click="handleDailyChartClick"
          :key="dailyChartKey"
          :not-merge="true"
        />
      </section>

      <!-- Error by Table Chart -->
      <section class="chart-card">
        <v-chart class="chart" :option="errorByTableChartOption" autoresize />
      </section>
    </main>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch } from 'vue';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { BarChart, PieChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent,
} from 'echarts/components';
import VChart, { THEME_KEY } from 'vue-echarts';
import apiClient from '@/api';

// Register ECharts components
use([
  CanvasRenderer,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent,
]);

export default {
  name: 'SyncStats',
  components: {
    VChart,
  },
  provide: {
    [THEME_KEY]: 'light', // or 'dark'
  },
  setup() {
    const isLoading = ref(true);
    const error = ref(null);
    const summaryData = ref(null);
    const selectedDate = ref(null);

    const dbSources = ref(['MySQL', 'PostgreSQL', 'SQLServer']);
    const selectedSources = ref(new Set(dbSources.value));

    const dailyChartKey = computed(() => (selectedDate.value ? `pie-${selectedDate.value}` : 'bar'));

    const toggleSource = (db) => {
      if (selectedSources.value.has(db)) {
        selectedSources.value.delete(db);
      } else {
        selectedSources.value.add(db);
      }
    };

    const fetchData = async () => {
      isLoading.value = true;
      error.value = null;
      try {
        const params = new URLSearchParams();
        params.append('days', 7);
        selectedSources.value.forEach(db => params.append('dbs', db));
        
        const response = await apiClient.get(`/stats/sync-summary?${params.toString()}`);
        summaryData.value = response.data;
      } catch (err) {
        error.value = err.response?.data?.detail || '无法获取统计数据';
        console.error(err);
      } finally {
        isLoading.value = false;
      }
    };

    onMounted(fetchData);

    watch(selectedSources, fetchData, { deep: true });

    const handleDailyChartClick = (params) => {
      if (params.componentType === 'series' && params.seriesType === 'bar') {
        selectedDate.value = params.name;
      }
    };

    const dailyChartOption = computed(() => {
      if (!summaryData.value) return {};

      if (selectedDate.value) {
        const dailyStats = summaryData.value.daily_stats;
        const dayData = dailyStats.find(s => s.date === selectedDate.value);
        if (!dayData) {
            selectedDate.value = null; // Reset if data not found
            return {};
        }

        const successCount = dayData.total_operations - dayData.conflicts;
        const pieData = [
            { value: successCount, name: '同步成功', itemStyle: { color: '#91CC75' } },
            { value: dayData.resolved_conflicts, name: '已解决冲突', itemStyle: { color: '#73C0DE' } },
            { value: dayData.unresolved_conflicts, name: '未解决冲突', itemStyle: { color: '#c23531' } },
        ];

        return {
          title: {
            text: `${selectedDate.value} 同步详情`,
            left: 'center',
            textStyle: { fontSize: 18, fontWeight: '600', color: '#333' }
          },
          tooltip: {
            trigger: 'item',
            formatter: '{a} <br/>{b}: {c} ({d}%)',
          },
          legend: {
            orient: 'vertical',
            left: 'left',
            data: pieData.map(p => p.name)
          },
          series: [{
            name: '同步状态',
            type: 'pie',
            radius: '55%',
            center: ['50%', '60%'],
            data: pieData,
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }],
          toolbox: {
            feature: {
              saveAsImage: { title: '保存' },
              myBack: {
                show: true,
                title: '返回',
                icon: 'path://M19.3 4.8c-1.5-1.5-3.5-2.3-5.6-2.3-4.4 0-8 3.6-8 8s3.6 8 8 8c2.1 0 4.1-0.8 5.6-2.3l-1.4-1.4c-1.2 1.2-2.8 1.7-4.2 1.7-3.3 0-6-2.7-6-6s2.7-6 6-6c1.4 0 3 0.6 4.2 1.7l-2.2 2.2h6v-6l-2 2z',
                onclick: () => {
                  selectedDate.value = null;
                }
              }
            }
          }
        };
      }

      // Bar chart view (default)
      const dailyStats = summaryData.value.daily_stats;
      return {
        title: {
          text: '每日同步趋势 (点击查看详情)',
          left: 'center',
          textStyle: { fontSize: 18, fontWeight: '600', color: '#333' }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
        },
        legend: {
          data: ['总操作', '同步成功', '冲突', '已解决冲突', '未解决冲突'],
          textStyle: { color: '#666' },
          top: '35px',
          right: '10px',
        },
        grid: {
          top: '85px',
          left: '10%',
          right: '5%',
          bottom: '3%',
        },
        xAxis: {
          type: 'category',
          data: dailyStats.map(s => s.date),
          axisTick: { alignWithLabel: true },
        },
        yAxis: {
          type: 'value',
        },
        series: [
          {
            name: '总操作',
            type: 'bar',
            barWidth: '20%',
            data: dailyStats.map(s => s.total_operations),
            itemStyle: { color: '#5470C6' }
          },
          {
            name: '同步成功',
            type: 'bar',
            barWidth: '20%',
            data: dailyStats.map(s => s.total_operations - s.conflicts),
            itemStyle: { color: '#91CC75' }
          },
          {
            name: '冲突',
            type: 'bar',
            barWidth: '20%',
            data: dailyStats.map(s => s.conflicts),
            itemStyle: { color: '#FAC858' }
          },
          {
            name: '已解决冲突',
            type: 'bar',
            barWidth: '20%',
            data: dailyStats.map(s => s.resolved_conflicts),
            itemStyle: { color: '#73C0DE' }
          },
          {
            name: '未解决冲突',
            type: 'bar',
            barWidth: '20%',
            data: dailyStats.map(s => s.unresolved_conflicts),
            itemStyle: { color: '#c23531' }
          },
        ],
        toolbox: {
          feature: {
            saveAsImage: { title: '保存' },
            magicType: { type: ['line', 'bar'], title: { line: '切换为折线图', bar: '切换为柱状图' } },
            restore: { title: '还原' },
          },
        },
      };
    });

    const errorByTableChartOption = computed(() => {
        if (!summaryData.value) return {};
        const errorSummary = summaryData.value.error_summary_by_table;

        const totalErrors = errorSummary.reduce((sum, item) => sum + item.conflict_count + item.failure_count, 0);
        if (totalErrors === 0) {
            return {
                title: {
                    text: '错误类型分布 (按表)',
                    left: 'center',
                    textStyle: { fontSize: 18, fontWeight: '600', color: '#333' }
                },
                graphic: { // Use graphic component for "no data" message
                    type: 'text',
                    left: 'center',
                    top: 'center',
                    style: {
                        text: '无错误记录',
                        fill: '#999',
                        fontSize: 20
                    }
                }
            };
        }

        return {
            title: {
              text: '错误类型分布 (按表)',
              left: 'center',
              textStyle: { fontSize: 18, fontWeight: '600', color: '#333' }
            },
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%)',
            },
            legend: {
                orient: 'vertical',
                left: '10px',
                top: 'bottom',
                data: errorSummary.map(s => s.table_name),
            },
            series: [
                {
                    name: '错误详情',
                    type: 'pie',
                    radius: ['50%', '70%'],
                    center: ['60%', '50%'], // Move pie chart to the right
                    avoidLabelOverlap: false,
                    label: {
                        show: false,
                        position: 'center',
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: '20',
                            fontWeight: 'bold',
                        },
                    },
                    labelLine: {
                        show: false,
                    },
                    data: errorSummary.map(s => ({
                        name: s.table_name,
                        value: s.conflict_count + s.failure_count
                    })),
                },
            ],
            toolbox: {
                feature: {
                    saveAsImage: { title: '保存' },
                },
            },
        };
    });

    return {
      isLoading,
      error,
      dailyChartOption,
      errorByTableChartOption,
      handleDailyChartClick,
      dailyChartKey,
      dbSources,
      selectedSources,
      toggleSource,
    };
  },
};
</script>

<style scoped>
.stats-container {
  padding: 1rem;
  background-color: #f0f2f5;
  min-height: 100vh;
}

.stats-header {
  text-align: center;
  margin-bottom: 2rem;
}
.stats-header h1 {
  color: #333;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}
.stats-header .header-icon {
    font-size: 2.5rem;
    vertical-align: middle;
}
.stats-header p {
  color: #666;
  font-size: 1rem;
}

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
  justify-content: center;
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

.loading-container {
  text-align: center;
  padding: 4rem 0;
  color: #555;
}
.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border-left-color: #4B79A1;
  animation: spin 1s ease infinite;
  margin: 0 auto 1rem;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-container {
  text-align: center;
  padding: 2rem;
  background-color: #fff3f3;
  color: #d9534f;
  border-radius: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

.chart-card {
  background: #fff;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.card-title {
  font-size: 1.2rem;
  color: #333;
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-weight: 600;
}

.chart {
  height: 400px;
}

/* Responsive design for mobile */
@media (min-width: 768px) {
  .stats-container {
    padding: 2rem;
  }
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (min-width: 1200px) {
  .stats-grid {
    grid-template-columns: 2fr 1fr;
  }
}
</style>