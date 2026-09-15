<script setup>
import logoUrl from "../assets/hitsz-logo-genimage-hd.svg"
</script>

<template>
  <div class="slidev-layout academic hitsz-academic-cover">
    <!-- 复用 HITSZ 首页原始标识，文字仍由 Markdown 的两个插槽管理。 -->
    <header>
      <img :src="logoUrl" alt="哈尔滨工业大学（深圳）" />
    </header>
    <main><slot /></main>
    <section class="cover-details"><slot name="details" /></section>
  </div>
</template>

<style scoped>
.slidev-layout.hitsz-academic-cover {
  position: relative;
  display: grid;
  grid-template-rows: 136px 180px 1fr;
  padding: 32px 74px 34px;
  text-align: center;
  color: #0f3466;
}
.hitsz-academic-cover::before {
  content: '';
  position: absolute;
  inset: 12px;
  border: 2px solid #0f3466cc;
  pointer-events: none;
}
header { display: flex; justify-content: center; align-items: center; }
header img { width: 500px; height: auto; object-fit: contain; }
main {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-top: 1px solid #98a5b7;
  border-bottom: 1px solid #98a5b7;
}
main :deep(h1) {
  color: #0f3466;
  font-size: 40px;
  font-weight: 700;
  line-height: 1.35;
  margin: 0 0 18px;
}
main :deep(h2) {
  color: #0f3466;
  font-size: 26px;
  font-weight: 400;
  margin: 0;
}
.cover-details {
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: #273548;
  font-size: 21px;
  line-height: 1.6;
}
.cover-details :deep(p) { margin: 0; }
</style>
