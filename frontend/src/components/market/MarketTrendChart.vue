<template>
  <VChart :option="chartOption" autoresize class="market-chart-canvas" />
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps({
  priceSeries: {
    type: Array,
    default: () => [],
  },
})

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
  },
  legend: {
    data: ['???', '???'],
  },
  grid: {
    left: 28,
    right: 24,
    top: 48,
    bottom: 26,
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: props.priceSeries.map(item => item.trade_date),
    boundaryGap: false,
  },
  yAxis: [
    {
      type: 'value',
      name: '???',
      scale: true,
    },
    {
      type: 'value',
      name: '???',
      scale: true,
    },
  ],
  series: [
    {
      name: '???',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 3, color: '#1e7cf2' },
      areaStyle: { color: 'rgba(30,124,242,0.12)' },
      data: props.priceSeries.map(item => item.close),
    },
    {
      name: '???',
      type: 'bar',
      yAxisIndex: 1,
      itemStyle: { color: 'rgba(43,195,177,0.55)' },
      data: props.priceSeries.map(item => item.volume),
    },
  ],
}))
</script>

<style scoped>
.market-chart-canvas {
  height: 100%;
}
</style>
