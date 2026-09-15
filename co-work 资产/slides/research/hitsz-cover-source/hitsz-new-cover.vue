<script setup>
// public/ 目录文件通过绝对 URL 引用，不能用 import。
const logoUrl = '/hitsz-logo-genimage-hd.svg'
</script>

<template>
  <div class="slidev-layout hitsz-new-cover w-full h-full bg-white flex flex-col justify-between items-center relative overflow-hidden font-sans pb-12 pt-8">
    <!-- 外边框 -->
    <div class="absolute inset-x-3 inset-y-3 border-[2px] border-[#0F3466]/80 pointer-events-none z-10"></div>

    <!-- Header logo: keep official HITSZ emblem and wordmark instead of rebuilding fonts. -->
    <div class="w-full flex justify-center mt-6 z-20">
      <img :src="logoUrl" class="hitsz-cover-logo object-contain" alt="哈尔滨工业大学（深圳）" />
    </div>

    <!-- 上分割线 -->
    <div class="w-[85%] mx-auto border-b-[1.5px] border-gray-400 mt-6"></div>

    <!-- 标题区 -->
    <div class="text-center px-12 z-0 flex flex-col justify-center items-center flex-1 w-full mt-8">
      <slot name="default">
        <h1 class="text-4xl md:text-[50px] font-extrabold !text-[#0F3466] tracking-wide mb-6 leading-[1.3] font-sans">
          联合优化下的非线性滤波<br/>神经网络与输运方法
        </h1>
      </slot>
    </div>

    <!-- 下分割线 -->
    <div class="w-[85%] mx-auto border-b-[1.5px] border-gray-400 mb-6 mt-4"></div>

    <!-- 细节区 -->
    <div class="hitsz-cover-details text-center text-gray-800 text-[1.05rem] md:text-[1.12rem] font-medium space-y-1 mb-20 z-0">
      <p>汇报人：张守信</p>
      <p>导师：严质彬</p>
      <p>哈尔滨工业大学（深圳）理学院数学系</p>
      <p>硕士中期报告 · 2026 年 6 月 26 日</p>
    </div>

    <!-- 页脚 -->
    <div class="absolute bottom-5 left-0 w-full flex justify-between px-10 text-[#0F3466] font-semibold text-sm z-0">
      <div class="w-24"></div> <!-- 占位保持居中对称 -->
      <div class="w-24"></div>
      <div class="w-24 text-right pt-0.5">Page 1</div>
    </div>
  </div>
</template>

<style>
.slidev-layout.hitsz-new-cover h1 {
  color: #0F3466 !important;
  border-bottom: none !important;
}

.hitsz-cover-logo {
  width: 500px;
  height: 103px;
  image-rendering: auto;
}

.slidev-layout.hitsz-new-cover .hitsz-cover-details p {
  margin: 0;
  line-height: 1.4;
}
</style>
