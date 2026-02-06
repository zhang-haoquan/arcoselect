<script setup lang="ts">
import { ref, watch, nextTick, onMounted, computed } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'confirm', config: ChartConfig): void;
  (e: 'cancel'): void;
}>();

interface ChartConfig {
  chartType: string;
  xAxisDimension: string;
  sortBy: string;
  sortOrder: string;
  yAxisMetric: string;
  groupBy?: string;
  groupSortOrder?: string;
  valueField?: string;
  aggregationType?: string;
}

interface BugDataItem {
  [key: string]: string | number | null;
}

interface BugDataResponse {
  metadata: {
    total_records: number;
    fields: string[];
    field_count: number;
  };
  data: BugDataItem[];
}

const activeTab = ref('data');
const chartContainer = ref<HTMLDivElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

// 数据存储
const bugData = ref<BugDataItem[]>([]);
const dataFields = ref<string[]>([]);
const dataLoadError = ref<string>('');
const isLoading = ref<boolean>(false);

const chartConfig = ref<ChartConfig>({
  chartType: 'bar-basic',
  xAxisDimension: '任务类型',
  sortBy: 'xAxis',
  sortOrder: 'asc',
  yAxisMetric: 'count',
  groupBy: '优先级',
  groupSortOrder: 'asc',
  valueField: '',
  aggregationType: 'sum'
});

const chartTypeOptions = [
  { label: '柱状图', value: 'bar' },
  { label: '折线图', value: 'line' },
  { label: '饼图', value: 'pie' },
  { label: '散点图', value: 'scatter' }
];

const sortByOptions = [
  { label: '横轴值', value: 'xAxis' },
  { label: '纵轴值', value: 'yAxis' }
];

const sortOrderOptions = [
  { label: '正序', value: 'asc' },
  { label: '倒序', value: 'desc' }
];

const metricOptions = [
  { label: '统计记录总数', value: 'count' },
  { label: '统计记录的值', value: 'value' }
];

// 统计字段选项（数字类型字段）
const valueFieldOptions = [
  { label: '工时1', value: '工时1' },
  { label: '工时2', value: '工时2' }
];

// 计算方式选项
const aggregationOptions = [
  { label: '求和', value: 'sum' },
  { label: '最大值', value: 'max' },
  { label: '最小值', value: 'min' },
  { label: '平均值', value: 'avg' }
];

// 获取计算方式标签
const getAggregationLabel = (type?: string): string => {
  const option = aggregationOptions.find(opt => opt.value === type);
  return option?.label || '求和';
};

// 判断是否显示统计字段配置面板
const showValueFieldConfig = computed(() => {
  return chartConfig.value.yAxisMetric === 'value';
});

// 判断计算方式选择器是否可用
const isAggregationEnabled = computed(() => {
  return !!chartConfig.value.valueField;
});

// 动态字段选项（从JSON数据加载）
const dimensionOptions = computed(() => {
  return dataFields.value.map(field => ({ label: field, value: field }));
});

// 分组字段选项（从JSON数据加载）
const groupByOptions = computed(() => {
  return dataFields.value.map(field => ({ label: field, value: field }));
});

// 加载BUG统计数据
const loadBugData = async () => {
  isLoading.value = true;
  dataLoadError.value = '';
  
  try {
    const response = await fetch('/BUG统计数据.json');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const jsonData: BugDataResponse = await response.json();
    
    // 验证数据结构
    if (!jsonData.metadata || !jsonData.data || !Array.isArray(jsonData.data)) {
      throw new Error('数据格式错误：缺少必要的字段');
    }
    
    dataFields.value = jsonData.metadata.fields;
    bugData.value = jsonData.data;
    
    console.log('数据加载成功:', {
      fields: dataFields.value,
      recordCount: bugData.value.length
    });
    
  } catch (error) {
    console.error('加载数据失败:', error);
    dataLoadError.value = error instanceof Error ? error.message : '未知错误';
  } finally {
    isLoading.value = false;
  }
};

// 需要显示分组配置的图表类型
const needGroupConfigTypes = ['bar-stack', 'bar-cluster', 'horizontal-bar-stack', 'horizontal-bar-cluster', 'line-stack'];

// 判断是否需要显示分组配置
const showGroupConfig = computed(() => {
  return needGroupConfigTypes.includes(chartConfig.value.chartType);
});

const initChart = () => {
  if (chartContainer.value && !chartInstance) {
    chartInstance = echarts.init(chartContainer.value);
    updateChart();
  }
};

// 获取分组字段的排序值（用于自定义排序）
const getGroupSortValue = (groupName: string, groupField: string): number => {
  // 优先级字段的特殊排序：P0 < P1 < P2 < P3
  if (groupField === '优先级') {
    const priorityMap: { [key: string]: number } = {
      'P0': 0, 'p0': 0,
      'P1': 1, 'p1': 1,
      'P2': 2, 'p2': 2,
      'P3': 3, 'p3': 3,
      '未分组': 999
    };
    return priorityMap[groupName] ?? 999;
  }
  
  // 其他字段使用字符串的字符码排序
  return groupName.charCodeAt(0) || 0;
};

// 数据聚合计算函数
const aggregateValues = (values: number[], type: string): number => {
  const validValues = values.filter(v => typeof v === 'number' && !isNaN(v));
  if (validValues.length === 0) return 0;

  switch (type) {
    case 'sum':
      return validValues.reduce((sum, val) => sum + val, 0);
    case 'max':
      return Math.max(...validValues);
    case 'min':
      return Math.min(...validValues);
    case 'avg':
      return validValues.reduce((sum, val) => sum + val, 0) / validValues.length;
    default:
      return validValues.reduce((sum, val) => sum + val, 0);
  }
};

// 获取数值（处理异常数据）
const getNumericValue = (value: string | number | null): number => {
  if (value === null || value === undefined) return 0;
  const num = Number(value);
  return isNaN(num) ? 0 : num;
};

// 处理堆积柱状图数据
const processStackBarData = (xField: string, groupField: string, config: ChartConfig) => {
  if (!bugData.value.length) return { xAxisData: [], series: [] };

  // 获取所有唯一的X轴值和分组值
  const xAxisSet = new Set<string>();
  const groupSet = new Set<string>();

  bugData.value.forEach(item => {
    const xValue = String(item[xField] ?? '未分类');
    const groupValue = String(item[groupField] ?? '未分组');
    xAxisSet.add(xValue);
    groupSet.add(groupValue);
  });

  let xAxisData = Array.from(xAxisSet);
  let groupNames = Array.from(groupSet);

  // 判断是使用计数还是数值统计
  const useValueField = config.yAxisMetric === 'value' && config.valueField;
  const aggregationType = config.aggregationType || 'sum';

  if (useValueField) {
    // 使用数值字段进行聚合统计
    const valueMap: { [key: string]: { [key: string]: number[] } } = {};

    xAxisData.forEach(x => {
      valueMap[x] = {};
      groupNames.forEach(g => {
        valueMap[x][g] = [];
      });
    });

    bugData.value.forEach(item => {
      const xValue = String(item[xField] ?? '未分类');
      const groupValue = String(item[groupField] ?? '未分组');
      const fieldValue = getNumericValue(item[config.valueField!]);
      valueMap[xValue][groupValue].push(fieldValue);
    });

    // 聚合计算
    const aggregatedMap: { [key: string]: { [key: string]: number } } = {};
    xAxisData.forEach(x => {
      aggregatedMap[x] = {};
      groupNames.forEach(g => {
        aggregatedMap[x][g] = aggregateValues(valueMap[x][g], aggregationType);
      });
    });

    // 横轴排序逻辑（按聚合值总和）
    if (config.sortBy === 'xAxis') {
      xAxisData.sort((a, b) => {
        return config.sortOrder === 'asc'
          ? a.localeCompare(b)
          : b.localeCompare(a);
      });
    } else {
      xAxisData.sort((a, b) => {
        const sumA = Object.values(aggregatedMap[a]).reduce((sum, val) => sum + val, 0);
        const sumB = Object.values(aggregatedMap[b]).reduce((sum, val) => sum + val, 0);
        return config.sortOrder === 'asc' ? sumA - sumB : sumB - sumA;
      });
    }

    // 纵轴（分组）排序逻辑
    groupNames.sort((a, b) => {
      const sortValueA = getGroupSortValue(a, groupField);
      const sortValueB = getGroupSortValue(b, groupField);
      return config.groupSortOrder === 'asc'
        ? sortValueA - sortValueB
        : sortValueB - sortValueA;
    });

    // 生成series数据
    const colors = ['#165DFF', '#14C9C9', '#F7BA1E', '#F53F3F', '#722ED1', '#86909C'];
    const series = groupNames.map((groupName, index) => ({
      name: groupName,
      type: 'bar' as const,
      stack: 'total',
      emphasis: {
        focus: 'series'
      },
      data: xAxisData.map(x => Number(aggregatedMap[x][groupName].toFixed(2))),
      itemStyle: {
        color: colors[index % colors.length]
      },
      label: {
        show: true,
        position: 'inside',
        formatter: '{c}',
        fontSize: 10
      },
      animationDuration: 500,
      animationEasing: 'cubicOut'
    }));

    return { xAxisData, series, groupNames, useValueField: true };
  } else {
    // 使用计数统计（原有逻辑）
    const countMap: { [key: string]: { [key: string]: number } } = {};

    xAxisData.forEach(x => {
      countMap[x] = {};
      groupNames.forEach(g => {
        countMap[x][g] = 0;
      });
    });

    bugData.value.forEach(item => {
      const xValue = String(item[xField] ?? '未分类');
      const groupValue = String(item[groupField] ?? '未分组');
      countMap[xValue][groupValue] = (countMap[xValue][groupValue] || 0) + 1;
    });

    // 横轴排序逻辑
    if (config.sortBy === 'xAxis') {
      xAxisData.sort((a, b) => {
        return config.sortOrder === 'asc'
          ? a.localeCompare(b)
          : b.localeCompare(a);
      });
    } else {
      xAxisData.sort((a, b) => {
        const sumA = Object.values(countMap[a]).reduce((sum, val) => sum + val, 0);
        const sumB = Object.values(countMap[b]).reduce((sum, val) => sum + val, 0);
        return config.sortOrder === 'asc' ? sumA - sumB : sumB - sumA;
      });
    }

    // 纵轴（分组）排序逻辑
    groupNames.sort((a, b) => {
      const sortValueA = getGroupSortValue(a, groupField);
      const sortValueB = getGroupSortValue(b, groupField);
      return config.groupSortOrder === 'asc'
        ? sortValueA - sortValueB
        : sortValueB - sortValueA;
    });

    // 生成series数据
    const colors = ['#165DFF', '#14C9C9', '#F7BA1E', '#F53F3F', '#722ED1', '#86909C'];
    const series = groupNames.map((groupName, index) => ({
      name: groupName,
      type: 'bar' as const,
      stack: 'total',
      emphasis: {
        focus: 'series'
      },
      data: xAxisData.map(x => countMap[x][groupName] || 0),
      itemStyle: {
        color: colors[index % colors.length]
      },
      animationDuration: 500,
      animationEasing: 'cubicOut'
    }));

    return { xAxisData, series, groupNames, useValueField: false };
  }
};

// 处理普通柱状图数据
const processNormalBarData = (xField: string) => {
  if (!bugData.value.length) return { xAxisData: [], series: [] };

  const countMap: { [key: string]: number } = {};
  
  bugData.value.forEach(item => {
    const xValue = String(item[xField] ?? '未分类');
    countMap[xValue] = (countMap[xValue] || 0) + 1;
  });

  const entries = Object.entries(countMap);
  
  // 排序
  const config = chartConfig.value;
  if (config.sortBy === 'xAxis') {
    entries.sort((a, b) => {
      return config.sortOrder === 'asc' 
        ? a[0].localeCompare(b[0])
        : b[0].localeCompare(a[0]);
    });
  } else {
    entries.sort((a, b) => {
      return config.sortOrder === 'asc' 
        ? a[1] - b[1]
        : b[1] - a[1];
    });
  }

  const xAxisData = entries.map(e => e[0]);
  const data = entries.map(e => e[1]);

  const series = [{
    name: '计数',
    type: 'bar' as const,
    data: data,
    label: {
      show: true,
      position: 'top'
    },
    itemStyle: {
      color: '#165DFF'
    },
    animationDuration: 500,
    animationEasing: 'cubicOut'
  }];

  return { xAxisData, series };
};

// 处理簇状图数据
const processClusterBarData = (xField: string, groupField: string, config: ChartConfig) => {
  if (!bugData.value.length) return { xAxisData: [], series: [] };

  // 获取所有唯一的X轴值和分组值
  const xAxisSet = new Set<string>();
  const groupSet = new Set<string>();

  bugData.value.forEach(item => {
    const xValue = String(item[xField] ?? '未分类');
    const groupValue = String(item[groupField] ?? '未分组');
    xAxisSet.add(xValue);
    groupSet.add(groupValue);
  });

  let xAxisData = Array.from(xAxisSet);
  let groupNames = Array.from(groupSet);

  // 判断是使用计数还是数值统计
  const useValueField = config.yAxisMetric === 'value' && config.valueField;
  const aggregationType = config.aggregationType || 'sum';

  if (useValueField) {
    // 使用数值字段进行聚合统计
    const valueMap: { [key: string]: { [key: string]: number[] } } = {};

    xAxisData.forEach(x => {
      valueMap[x] = {};
      groupNames.forEach(g => {
        valueMap[x][g] = [];
      });
    });

    bugData.value.forEach(item => {
      const xValue = String(item[xField] ?? '未分类');
      const groupValue = String(item[groupField] ?? '未分组');
      const fieldValue = getNumericValue(item[config.valueField!]);
      valueMap[xValue][groupValue].push(fieldValue);
    });

    // 聚合计算
    const aggregatedMap: { [key: string]: { [key: string]: number } } = {};
    xAxisData.forEach(x => {
      aggregatedMap[x] = {};
      groupNames.forEach(g => {
        aggregatedMap[x][g] = aggregateValues(valueMap[x][g], aggregationType);
      });
    });

    // 横轴排序逻辑
    if (config.sortBy === 'xAxis') {
      xAxisData.sort((a, b) => {
        return config.sortOrder === 'asc'
          ? a.localeCompare(b)
          : b.localeCompare(a);
      });
    } else {
      xAxisData.sort((a, b) => {
        const sumA = Object.values(aggregatedMap[a]).reduce((sum, val) => sum + val, 0);
        const sumB = Object.values(aggregatedMap[b]).reduce((sum, val) => sum + val, 0);
        return config.sortOrder === 'asc' ? sumA - sumB : sumB - sumA;
      });
    }

    // 纵轴（分组）排序逻辑
    groupNames.sort((a, b) => {
      const sortValueA = getGroupSortValue(a, groupField);
      const sortValueB = getGroupSortValue(b, groupField);
      return config.groupSortOrder === 'asc'
        ? sortValueA - sortValueB
        : sortValueB - sortValueA;
    });

    // 生成series数据（簇状图不设置stack，让柱子并排显示）
    const colors = ['#165DFF', '#14C9C9', '#F7BA1E', '#F53F3F', '#722ED1', '#86909C'];
    const series = groupNames.map((groupName, index) => ({
      name: groupName,
      type: 'bar' as const,
      // 簇状图不设置stack属性，让柱子并排显示
      emphasis: {
        focus: 'series'
      },
      data: xAxisData.map(x => Number(aggregatedMap[x][groupName].toFixed(2))),
      itemStyle: {
        color: colors[index % colors.length]
      },
      label: {
        show: true,
        position: 'top',
        formatter: '{c}',
        fontSize: 10
      },
      animationDuration: 500,
      animationEasing: 'cubicOut'
    }));

    return { xAxisData, series, groupNames, useValueField: true };
  } else {
    // 使用计数统计
    const countMap: { [key: string]: { [key: string]: number } } = {};

    xAxisData.forEach(x => {
      countMap[x] = {};
      groupNames.forEach(g => {
        countMap[x][g] = 0;
      });
    });

    bugData.value.forEach(item => {
      const xValue = String(item[xField] ?? '未分类');
      const groupValue = String(item[groupField] ?? '未分组');
      countMap[xValue][groupValue] = (countMap[xValue][groupValue] || 0) + 1;
    });

    // 横轴排序逻辑
    if (config.sortBy === 'xAxis') {
      xAxisData.sort((a, b) => {
        return config.sortOrder === 'asc'
          ? a.localeCompare(b)
          : b.localeCompare(a);
      });
    } else {
      xAxisData.sort((a, b) => {
        const sumA = Object.values(countMap[a]).reduce((sum, val) => sum + val, 0);
        const sumB = Object.values(countMap[b]).reduce((sum, val) => sum + val, 0);
        return config.sortOrder === 'asc' ? sumA - sumB : sumB - sumA;
      });
    }

    // 纵轴（分组）排序逻辑
    groupNames.sort((a, b) => {
      const sortValueA = getGroupSortValue(a, groupField);
      const sortValueB = getGroupSortValue(b, groupField);
      return config.groupSortOrder === 'asc'
        ? sortValueA - sortValueB
        : sortValueB - sortValueA;
    });

    // 生成series数据（簇状图不设置stack）
    const colors = ['#165DFF', '#14C9C9', '#F7BA1E', '#F53F3F', '#722ED1', '#86909C'];
    const series = groupNames.map((groupName, index) => ({
      name: groupName,
      type: 'bar' as const,
      // 簇状图不设置stack属性
      emphasis: {
        focus: 'series'
      },
      data: xAxisData.map(x => countMap[x][groupName] || 0),
      itemStyle: {
        color: colors[index % colors.length]
      },
      label: {
        show: true,
        position: 'top',
        formatter: '{c}',
        fontSize: 10
      },
      animationDuration: 500,
      animationEasing: 'cubicOut'
    }));

    return { xAxisData, series, groupNames, useValueField: false };
  }
};

// 处理堆叠折线图数据
const processStackLineData = (xField: string, groupField: string, config: ChartConfig) => {
  if (!bugData.value.length) return { xAxisData: [], series: [] };

  // 获取所有唯一的X轴值和分组值
  const xAxisSet = new Set<string>();
  const groupSet = new Set<string>();

  bugData.value.forEach(item => {
    const xValue = String(item[xField] ?? '未分类');
    const groupValue = String(item[groupField] ?? '未分组');
    xAxisSet.add(xValue);
    groupSet.add(groupValue);
  });

  let xAxisData = Array.from(xAxisSet);
  let groupNames = Array.from(groupSet);

  // 判断是使用计数还是数值统计
  const useValueField = config.yAxisMetric === 'value' && config.valueField;
  const aggregationType = config.aggregationType || 'sum';

  if (useValueField) {
    // 使用数值字段进行聚合统计
    const valueMap: { [key: string]: { [key: string]: number[] } } = {};

    xAxisData.forEach(x => {
      valueMap[x] = {};
      groupNames.forEach(g => {
        valueMap[x][g] = [];
      });
    });

    bugData.value.forEach(item => {
      const xValue = String(item[xField] ?? '未分类');
      const groupValue = String(item[groupField] ?? '未分组');
      const fieldValue = getNumericValue(item[config.valueField!]);
      valueMap[xValue][groupValue].push(fieldValue);
    });

    // 聚合计算
    const aggregatedMap: { [key: string]: { [key: string]: number } } = {};
    xAxisData.forEach(x => {
      aggregatedMap[x] = {};
      groupNames.forEach(g => {
        aggregatedMap[x][g] = aggregateValues(valueMap[x][g], aggregationType);
      });
    });

    // 横轴排序逻辑
    if (config.sortBy === 'xAxis') {
      xAxisData.sort((a, b) => {
        return config.sortOrder === 'asc'
          ? a.localeCompare(b)
          : b.localeCompare(a);
      });
    } else {
      xAxisData.sort((a, b) => {
        const sumA = Object.values(aggregatedMap[a]).reduce((sum, val) => sum + val, 0);
        const sumB = Object.values(aggregatedMap[b]).reduce((sum, val) => sum + val, 0);
        return config.sortOrder === 'asc' ? sumA - sumB : sumB - sumA;
      });
    }

    // 纵轴（分组）排序逻辑
    groupNames.sort((a, b) => {
      const sortValueA = getGroupSortValue(a, groupField);
      const sortValueB = getGroupSortValue(b, groupField);
      return config.groupSortOrder === 'asc'
        ? sortValueA - sortValueB
        : sortValueB - sortValueA;
    });

    // 生成series数据（堆叠折线图 - 只有线条，无面积填充）
    const colors = ['#165DFF', '#14C9C9', '#F7BA1E', '#F53F3F', '#722ED1', '#86909C'];
    const series = groupNames.map((groupName, index) => ({
      name: groupName,
      type: 'line' as const,
      stack: 'total',
      // 不设置areaStyle，只显示线条
      emphasis: {
        focus: 'series'
      },
      data: xAxisData.map(x => Number(aggregatedMap[x][groupName].toFixed(2))),
      itemStyle: {
        color: colors[index % colors.length]
      },
      lineStyle: {
        width: 2
      },
      smooth: false,
      symbol: 'circle',
      symbolSize: 6,
      animationDuration: 500,
      animationEasing: 'cubicOut'
    }));

    return { xAxisData, series, groupNames, useValueField: true };
  } else {
    // 使用计数统计
    const countMap: { [key: string]: { [key: string]: number } } = {};

    xAxisData.forEach(x => {
      countMap[x] = {};
      groupNames.forEach(g => {
        countMap[x][g] = 0;
      });
    });

    bugData.value.forEach(item => {
      const xValue = String(item[xField] ?? '未分类');
      const groupValue = String(item[groupField] ?? '未分组');
      countMap[xValue][groupValue] = (countMap[xValue][groupValue] || 0) + 1;
    });

    // 横轴排序逻辑
    if (config.sortBy === 'xAxis') {
      xAxisData.sort((a, b) => {
        return config.sortOrder === 'asc'
          ? a.localeCompare(b)
          : b.localeCompare(a);
      });
    } else {
      xAxisData.sort((a, b) => {
        const sumA = Object.values(countMap[a]).reduce((sum, val) => sum + val, 0);
        const sumB = Object.values(countMap[b]).reduce((sum, val) => sum + val, 0);
        return config.sortOrder === 'asc' ? sumA - sumB : sumB - sumA;
      });
    }

    // 纵轴（分组）排序逻辑
    groupNames.sort((a, b) => {
      const sortValueA = getGroupSortValue(a, groupField);
      const sortValueB = getGroupSortValue(b, groupField);
      return config.groupSortOrder === 'asc'
        ? sortValueA - sortValueB
        : sortValueB - sortValueA;
    });

    // 生成series数据（堆叠折线图 - 只有线条，无面积填充）
    const colors = ['#165DFF', '#14C9C9', '#F7BA1E', '#F53F3F', '#722ED1', '#86909C'];
    const series = groupNames.map((groupName, index) => ({
      name: groupName,
      type: 'line' as const,
      stack: 'total',
      // 不设置areaStyle，只显示线条
      emphasis: {
        focus: 'series'
      },
      data: xAxisData.map(x => countMap[x][groupName] || 0),
      itemStyle: {
        color: colors[index % colors.length]
      },
      lineStyle: {
        width: 2
      },
      smooth: false,
      symbol: 'circle',
      symbolSize: 6,
      animationDuration: 500,
      animationEasing: 'cubicOut'
    }));

    return { xAxisData, series, groupNames, useValueField: false };
  }
};

const updateChart = () => {
  if (!chartInstance) return;

  const config = chartConfig.value;
  
  // 如果没有数据，显示空状态
  if (!bugData.value.length) {
    chartInstance.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#86909C',
          fontSize: 16
        }
      },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: []
    }, true);
    return;
  }

  let option: echarts.EChartsOption;

  // 堆积柱状图
  if (config.chartType === 'bar-stack') {
    const xField = config.xAxisDimension || '任务类型';
    const groupField = config.groupBy || '优先级';
    const { xAxisData, series, groupNames, useValueField } = processStackBarData(xField, groupField, config);

    // 根据统计类型设置Y轴名称
    const yAxisName = useValueField
      ? `${config.valueField} (${getAggregationLabel(config.aggregationType)})`
      : '数量';

    option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#E5E6EB',
        borderWidth: 1,
        textStyle: {
          color: '#1D2129'
        },
        formatter: function(params: any) {
          let result = params[0].name + '<br/>';
          params.forEach((param: any) => {
            if (param.value > 0) {
              result += param.marker + param.seriesName + ': ' + param.value.toFixed(2) + '<br/>';
            }
          });
          return result;
        }
      },
      legend: {
        data: groupNames,
        top: 10,
        type: 'scroll'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: xAxisData,
        axisLabel: {
          rotate: 30,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        name: yAxisName,
        axisLabel: {
          formatter: useValueField ? '{value}' : '{value}'
        }
      },
      series: series,
      animationDuration: 800,
      animationEasing: 'cubicOut'
    };
  } else if (config.chartType === 'bar-cluster') {
    // 簇状图
    const xField = config.xAxisDimension || '任务类型';
    const groupField = config.groupBy || '优先级';
    const { xAxisData, series, groupNames, useValueField } = processClusterBarData(xField, groupField, config);

    // 根据统计类型设置Y轴名称
    const yAxisName = useValueField
      ? `${config.valueField} (${getAggregationLabel(config.aggregationType)})`
      : '数量';

    option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#E5E6EB',
        borderWidth: 1,
        textStyle: {
          color: '#1D2129'
        },
        formatter: function(params: any) {
          let result = params[0].name + '<br/>';
          params.forEach((param: any) => {
            if (param.value > 0) {
              result += param.marker + param.seriesName + ': ' + param.value.toFixed(2) + '<br/>';
            }
          });
          return result;
        }
      },
      legend: {
        data: groupNames,
        top: 10,
        type: 'scroll'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: xAxisData,
        axisLabel: {
          rotate: 30,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        name: yAxisName,
        axisLabel: {
          formatter: useValueField ? '{value}' : '{value}'
        }
      },
      series: series,
      animationDuration: 800,
      animationEasing: 'cubicOut'
    };
  } else if (config.chartType === 'line-stack') {
    // 堆叠折线图
    const xField = config.xAxisDimension || '任务类型';
    const groupField = config.groupBy || '优先级';
    const { xAxisData, series, groupNames, useValueField } = processStackLineData(xField, groupField, config);

    // 根据统计类型设置Y轴名称
    const yAxisName = useValueField
      ? `${config.valueField} (${getAggregationLabel(config.aggregationType)})`
      : '数量';

    option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#E5E6EB',
        borderWidth: 1,
        textStyle: {
          color: '#1D2129'
        },
        formatter: function(params: any) {
          let result = params[0].name + '<br/>';
          params.forEach((param: any) => {
            if (param.value > 0) {
              result += param.marker + param.seriesName + ': ' + param.value.toFixed(2) + '<br/>';
            }
          });
          return result;
        }
      },
      legend: {
        data: groupNames,
        top: 10,
        type: 'scroll'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: xAxisData,
        axisLabel: {
          rotate: 30,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        name: yAxisName,
        axisLabel: {
          formatter: useValueField ? '{value}' : '{value}'
        }
      },
      series: series,
      animationDuration: 800,
      animationEasing: 'cubicOut'
    };
  } else {
    // 普通柱状图
    const xField = config.xAxisDimension || '任务类型';
    const { xAxisData, series } = processNormalBarData(xField);

    option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#E5E6EB',
        borderWidth: 1,
        textStyle: {
          color: '#1D2129'
        },
        formatter: '{b}: {c}'
      },
      legend: {
        data: ['计数'],
        top: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: xAxisData,
        axisLabel: {
          rotate: 30,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        name: '数量'
      },
      series: series,
      animationDuration: 800,
      animationEasing: 'cubicOut'
    };
  }

  chartInstance.setOption(option, true);
};

// 监听弹窗显示，加载数据并初始化图表
watch(() => props.visible, async (newVal) => {
  if (newVal) {
    // 加载数据
    await loadBugData();
    
    nextTick(() => {
      initChart();
    });
  } else {
    if (chartInstance) {
      chartInstance.dispose();
      chartInstance = null;
    }
  }
});

// 监听图表类型变化，自动设置堆积柱状图、簇状图和堆叠折线图的默认值
watch(() => chartConfig.value.chartType, (newType) => {
  if (newType === 'bar-stack' || newType === 'bar-cluster' || newType === 'line-stack') {
    // 堆积柱状图、簇状图和堆叠折线图默认设置
    chartConfig.value.xAxisDimension = '任务类型';
    chartConfig.value.groupBy = '优先级';
  }
  // 图表类型变化时更新图表
  updateChart();
});

// 监听配置变化，排除图表类型（已单独监听）
watch(
  () => ({
    xAxisDimension: chartConfig.value.xAxisDimension,
    sortBy: chartConfig.value.sortBy,
    sortOrder: chartConfig.value.sortOrder,
    groupBy: chartConfig.value.groupBy,
    groupSortOrder: chartConfig.value.groupSortOrder,
    yAxisMetric: chartConfig.value.yAxisMetric,
    valueField: chartConfig.value.valueField,
    aggregationType: chartConfig.value.aggregationType
  }),
  (newVal, oldVal) => {
    console.log('配置变更:', newVal);
    updateChart();
  },
  { deep: true }
);

onMounted(() => {
  window.addEventListener('resize', () => {
    chartInstance?.resize();
  });
});

const handleClose = () => {
  emit('update:visible', false);
  emit('cancel');
};

const handleCancel = () => {
  emit('update:visible', false);
  emit('cancel');
};

const handleConfirm = () => {
  emit('confirm', chartConfig.value);
  emit('update:visible', false);
};
</script>

<template>
  <a-modal
    :visible="visible"
    :width="900"
    :footer="false"
    :closable="true"
    :mask-closable="false"
    @cancel="handleClose"
    class="chart-config-modal"
  >
    <template #title>
      <span class="modal-title">柱状图</span>
    </template>
    
    <div class="modal-content">
      <!-- 左侧图表预览区域 -->
      <div class="chart-preview-area">
        <div ref="chartContainer" class="chart-container"></div>
      </div>
      
      <!-- 右侧配置区域 -->
      <div class="config-area">
        <a-tabs v-model:active-key="activeTab" class="config-tabs">
          <a-tab-pane key="data" title="数据与类型">
            <div class="config-form">
              <!-- 图表类型 -->
              <div class="form-item">
                <label class="form-label">图表类型</label>
                <a-select
                  v-model="chartConfig.chartType"
                  placeholder="请选择图表类型"
                  class="form-select"
                >
                  <a-optgroup label="柱状图">
                    <a-option value="bar-basic">基础柱状图</a-option>
                    <a-option value="bar-stack">堆积柱状图</a-option>
                    <a-option value="bar-cluster">簇状图</a-option>
                  </a-optgroup>
                  <a-optgroup label="条形图">
                    <a-option value="horizontal-bar-basic">基础条形图</a-option>
                    <a-option value="horizontal-bar-stack">堆积条形图</a-option>
                    <a-option value="horizontal-bar-cluster">簇状条形图</a-option>
                  </a-optgroup>
                  <a-optgroup label="折线图">
                    <a-option value="line-basic">基础折线图</a-option>
                    <a-option value="line-stack">堆叠折线图</a-option>
                  </a-optgroup>
                  <a-optgroup label="其他">
                    <a-option value="number">数字</a-option>
                    <a-option value="pie">饼图</a-option>
                    <a-option value="funnel">漏斗图</a-option>
                    <a-option value="nps">净推荐值NPS图</a-option>
                  </a-optgroup>
                </a-select>
              </div>
              
              <!-- 数据范围 -->
              <div class="form-item">
                <div class="form-label-row">
                  <label class="form-label">数据范围</label>
                  <a-link class="filter-link">筛选</a-link>
                </div>
              </div>
              
              <a-divider class="form-divider" />
              
              <!-- 横轴配置 -->
              <div class="form-item">
                <label class="form-label">横轴</label>
                <a-select
                  v-model="chartConfig.xAxisDimension"
                  :options="dimensionOptions"
                  placeholder="请选择维度"
                  class="form-select"
                />
              </div>
              
              <!-- 排序 -->
              <div class="form-item">
                <label class="form-label">排序</label>
                <a-radio-group v-model="chartConfig.sortBy" type="button" class="form-radio-group">
                  <a-radio value="xAxis">横轴值</a-radio>
                  <a-radio value="yAxis">纵轴值</a-radio>
                </a-radio-group>
              </div>
              
              <!-- 排序规则 -->
              <div class="form-item">
                <label class="form-label">排序规则</label>
                <a-radio-group v-model="chartConfig.sortOrder" type="button" class="form-radio-group">
                  <a-radio value="asc">正序</a-radio>
                  <a-radio value="desc">倒序</a-radio>
                </a-radio-group>
              </div>
              
              <a-divider class="form-divider" />
              
              <!-- 纵轴配置 -->
              <div class="form-item">
                <label class="form-label">纵轴</label>
                <a-select
                  v-model="chartConfig.yAxisMetric"
                  :options="metricOptions"
                  placeholder="请选择统计指标"
                  class="form-select"
                />
              </div>
              
              <!-- 统计字段配置面板（仅在纵轴选择"统计记录的值"时显示） -->
              <template v-if="showValueFieldConfig">
                <div class="form-item">
                  <label class="form-label">统计字段与计算方式</label>
                  <div class="field-aggregation-row">
                    <a-select
                      v-model="chartConfig.valueField"
                      :options="valueFieldOptions"
                      placeholder="请选择统计字段"
                      class="field-select"
                    />
                    <a-select
                      v-model="chartConfig.aggregationType"
                      :options="aggregationOptions"
                      placeholder="计算方式"
                      class="aggregation-select"
                      :disabled="!isAggregationEnabled"
                    />
                  </div>
                </div>
              </template>
              
              <!-- 分组配置（仅堆积/簇状/堆叠图表类型显示） -->
              <template v-if="showGroupConfig">
                <div class="form-item">
                  <label class="form-label">分组</label>
                  <a-select
                    v-model="chartConfig.groupBy"
                    :options="groupByOptions"
                    placeholder="请选择分组字段"
                    class="form-select"
                  />
                </div>
                
                <div class="form-item">
                  <label class="form-label">排序规则</label>
                  <a-radio-group v-model="chartConfig.groupSortOrder" type="button" class="form-radio-group">
                    <a-radio value="asc">正序</a-radio>
                    <a-radio value="desc">倒序</a-radio>
                  </a-radio-group>
                </div>
              </template>
            </div>
          </a-tab-pane>
          
          <a-tab-pane key="style" title="自定义样式">
            <div class="style-placeholder">
              <a-empty description="样式配置功能开发中..." />
            </div>
          </a-tab-pane>
        </a-tabs>
        
        <!-- 底部按钮 -->
        <div class="form-actions">
          <a-button @click="handleCancel">取消</a-button>
          <a-button type="primary" @click="handleConfirm">确定</a-button>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script lang="ts">
// 确保滚动功能兼容性
export default {
  name: 'ChartConfigModal'
}
</script>

<style scoped>
.chart-config-modal :deep(.arco-modal) {
  border-radius: 8px;
  overflow: hidden;
}

.chart-config-modal :deep(.arco-modal-header) {
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border-2);
}

.modal-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-1);
}

.modal-content {
  display: flex;
  height: 520px;
  padding: 20px;
  gap: 20px;
}

/* 左侧图表预览区域 */
.chart-preview-area {
  flex: 0 0 58%;
  border: 1px solid var(--color-border-2);
  border-radius: 6px;
  padding: 16px;
  background-color: var(--color-fill-2);
}

.chart-container {
  width: 100%;
  height: 100%;
}

/* 右侧配置区域 */
.config-area {
  flex: 0 0 38%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.config-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.config-tabs :deep(.arco-tabs-nav) {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.config-tabs :deep(.arco-tabs-content) {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding-right: 4px;
}

.config-tabs :deep(.arco-tabs-pane) {
  height: 100%;
}

/* 自定义滚动条样式 */
.config-tabs :deep(.arco-tabs-content)::-webkit-scrollbar {
  width: 6px;
}

.config-tabs :deep(.arco-tabs-content)::-webkit-scrollbar-track {
  background: var(--color-fill-2);
  border-radius: 3px;
}

.config-tabs :deep(.arco-tabs-content)::-webkit-scrollbar-thumb {
  background: var(--color-fill-4);
  border-radius: 3px;
}

.config-tabs :deep(.arco-tabs-content)::-webkit-scrollbar-thumb:hover {
  background: var(--color-fill-6);
}

/* Firefox 滚动条 */
.config-tabs :deep(.arco-tabs-content) {
  scrollbar-width: thin;
  scrollbar-color: var(--color-fill-4) var(--color-fill-2);
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  color: var(--color-text-2);
  font-weight: 500;
}

.form-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-link {
  font-size: 13px;
}

.form-select {
  width: 100%;
}

.form-radio-group {
  display: flex;
  gap: 8px;
}

.form-radio-group :deep(.arco-radio-button) {
  flex: 1;
  text-align: center;
}

.form-divider {
  margin: 8px 0;
}

/* 统计字段与计算方式水平排列 */
.field-aggregation-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.field-select {
  flex: 1.2;
}

.aggregation-select {
  flex: 1;
}

/* 样式配置占位 */
.style-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
}

/* 底部按钮 */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-2);
  flex-shrink: 0;
  background-color: var(--color-bg-2);
}
</style>
