<template>
  <div class="app-container">
    <router-view></router-view>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: system-ui, Avenir, Helvetica, Arial, sans-serif;
  background-color: var(--primary-color);
  color: var(--text-color);
}

.app-container {
  width: 100%;
  height: 100vh;
}
</style>
