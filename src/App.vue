<script setup lang="ts">
import { ref } from 'vue';
import ChartConfigModal from './components/ChartConfigModal.vue';

const modalVisible = ref(false);

const openModal = () => {
  modalVisible.value = true;
};

const handleConfirm = (config: any) => {
  console.log('图表配置:', config);
};

const handleCancel = () => {
  console.log('取消配置');
};
</script>

<template>
  <div class="app-container">
    <a-button type="primary" size="large" @click="openModal">
      打开图表配置
    </a-button>
    
    <ChartConfigModal
      v-model:visible="modalVisible"
      @confirm="handleConfirm"
      @cancel="handleCancel"
    />
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--color-fill-2);
}
</style>
