<template>
  <div class="admin-dashboard-container">
    <div class="layout-container">
      <el-card class="placeholder-card" shadow="hover">
        <div class="placeholder-content">
          <h2 class="page-title">管理员运营看板</h2>
          <p class="page-subtitle">
            该页面预留用于后续运营数据展示，目前暂未开放。
          </p>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.admin-dashboard-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.layout-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
}

.placeholder-card {
  border-radius: 12px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.page-title {
  margin: 0;
  font-size: 20px;
}

.page-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--muted-text-color);
}
</style>
