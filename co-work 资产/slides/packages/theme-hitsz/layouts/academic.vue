<script setup lang="ts">
defineProps<{ section?: string; background?: string }>()
</script>

<template>
  <div class="slidev-layout academic" :style="background ? { backgroundImage: `url(${JSON.stringify(background)})`, backgroundSize: 'cover', backgroundPosition: 'center' } : undefined">
    <main><slot /></main>
    <footer>
      <span>{{ section || '学术汇报' }}</span>
      <span><SlideCurrentNo /> / <SlidesTotal /></span>
    </footer>
  </div>
</template>
