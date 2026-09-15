<script setup lang="ts">
import { computed } from 'vue'
import type { SlideRoute } from '@slidev/types'
import { createFixedClicks } from '@slidev/client/composables/useClicks.ts'
import { CLICKS_MAX } from '@slidev/client/constants.ts'
import SlideContainer from '@slidev/client/internals/SlideContainer.vue'
import SlideWrapper from '@slidev/client/internals/SlideWrapper.vue'
const props = defineProps<{ route: SlideRoute; frontmatter: Record<string, unknown> }>()
// Read the persisted coordinates even if native dragging skipped route HMR.
const previewRoute = computed(() => ({
  ...props.route,
  meta: {
    ...props.route.meta,
    slide: { ...props.route.meta.slide, frontmatter: { ...props.route.meta.slide.frontmatter, ...props.frontmatter } },
  },
}))
const clicks = createFixedClicks(props.route, CLICKS_MAX)
</script>
<template>
  <SlideContainer :width="260">
    <SlideWrapper :route="previewRoute" :clicks-context="clicks" render-context="overview" />
  </SlideContainer>
</template>
