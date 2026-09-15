<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useNav, useSlideContext } from '@slidev/client'

const props = defineProps<{ id: string; src: string; alt?: string }>()
const { $renderContext } = useSlideContext()
const { isPrintMode } = useNav()
const editable = computed(() => import.meta.env.DEV && !isPrintMode.value && ['slide', 'presenter'].includes($renderContext.value))
const previewVersion = ref(''), opened = ref(false), loaded = ref(false), busy = ref(false)
const error = ref(''), status = ref(''), confirmClose = ref(false), dirty = ref(false)
const iframe = ref<HTMLIFrameElement>(), trigger = ref<HTMLButtonElement>(), previewImage = ref<HTMLImageElement>()
const origin = 'https://embed.diagrams.net'
const editorUrl = `${origin}/?embed=1&proto=json&spin=1&ui=kennedy&lang=zh&dark=0&configure=1&libraries=1&saveAndExit=1`
const imageUrl = computed(() => `${props.src}${previewVersion.value ? `?v=${previewVersion.value}` : ''}`)
let xml = '', version = '', pending: { xml: string; exit: boolean } | null = null
let timer: ReturnType<typeof setTimeout> | undefined
let generation = 0
function post(message: object) { iframe.value?.contentWindow?.postMessage(JSON.stringify(message), origin) }
function fitEditor() {
  const image = previewImage.value
  const maxScale = Math.min(1, Math.max(240, window.innerWidth - (window.innerWidth >= 1200 ? 500 : 80)) / (image?.naturalWidth || 1600), Math.max(200, window.innerHeight - 210) / (image?.naturalHeight || 1210))
  post({ action: 'fit', border: 24, maxScale })
}
function stopTimer() { clearTimeout(timer); timer = undefined }
function deadline(message: string, delay: number) {
  stopTimer()
  timer = setTimeout(() => { busy.value = false; error.value = message }, delay)
}
async function open() {
  const thisGeneration = ++generation
  opened.value = true; loaded.value = false; error.value = ''; status.value = '正在加载流程图…'
  dirty.value = false; confirmClose.value = false; pending = null; xml = ''; version = ''
  try {
    const response = await fetch(`/__drawio/${encodeURIComponent(props.id)}`, { cache: 'no-store' })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '无法读取流程图。')
    if (thisGeneration !== generation) return
    xml = data.xml; version = data.version
    await nextTick()
    // Render the iframe only after source loading, so init cannot race with GET.
    readyToMount.value = true
    deadline('编辑器加载较慢，请检查网络后重试。已保存的流程图仍可正常播放。', 30000)
  } catch (cause) { if (thisGeneration === generation) error.value = (cause as Error).message }
}
const readyToMount = ref(false)
function close() {
  if (busy.value) return
  ++generation; stopTimer(); opened.value = false; readyToMount.value = false
  pending = null; confirmClose.value = false
  nextTick(() => trigger.value?.focus())
}
function requestClose(modified = dirty.value) {
  if (busy.value) return
  if (modified) confirmClose.value = true
  else close()
}
function downloadDraft() {
  const url = URL.createObjectURL(new Blob([pending?.xml || xml], { type: 'application/xml' }))
  const a = document.createElement('a'); a.href = url; a.download = `${props.id}-draft.drawio`; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
function decodeSvg(data: string) {
  const comma = data.indexOf(',')
  if (!data.startsWith('data:image/svg+xml') || comma < 0) throw new Error('编辑器未返回 SVG，未保存。')
  if (data.slice(0, comma).includes(';base64')) {
    const bytes = Uint8Array.from(atob(data.slice(comma + 1)), c => c.charCodeAt(0))
    return new TextDecoder().decode(bytes)
  }
  return decodeURIComponent(data.slice(comma + 1))
}
async function receive(event: MessageEvent) {
  if (!opened.value || event.origin !== origin || event.source !== iframe.value?.contentWindow) return
  let message: any
  try { message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data } catch { return }
  if (!message || typeof message !== 'object') return
  if (message.error) {
    stopTimer(); busy.value = false; error.value = '编辑器处理失败，请重试保存。'; return
  }
  if (message.event === 'configure') {
    post({ action: 'configure', config: { defaultFonts: ['Noto Serif CJK SC', 'Noto Sans CJK SC'], preserveViewState: true } })
  } else if (message.event === 'init') {
    post({ action: 'load', xml, title: `${props.id}.drawio`, autosave: 1, dark: false, background: '#FFFFFF', saveAndExit: 1 })
  } else if (message.event === 'load') {
    loaded.value = true; stopTimer(); error.value = ''; status.value = '拖动节点或连线，双击文字编辑；完成后点击保存。'
    fitEditor()
  } else if (message.event === 'autosave' && typeof message.xml === 'string') {
    xml = message.xml; dirty.value = true; status.value = '有未保存的修改'
  } else if (message.event === 'save' && typeof message.xml === 'string' && !busy.value) {
    pending = { xml: message.xml, exit: !!message.exit }; xml = message.xml
    busy.value = true; error.value = ''; status.value = '正在生成白底预览并保存…'
    iframe.value?.blur()
    deadline('预览生成超时，修改尚未写入。可再次点击保存或下载当前修改。', 60000)
    post({ action: 'export', format: 'svg', embedImages: true, embedFonts: false, theme: 'light', keepTheme: false, background: '#FFFFFF' })
  } else if (message.event === 'export' && pending && busy.value) {
    stopTimer()
    try {
      const svg = decodeSvg(message.data)
      const response = await fetch(`/__drawio/${encodeURIComponent(props.id)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ xml: pending.xml, svg, version }), signal: AbortSignal.timeout(20000),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || '保存失败，请重试。')
      version = data.version; previewVersion.value = version; dirty.value = false
      status.value = '已保存'; post({ action: 'status', message: '已保存', modified: false })
      const exit = pending.exit; pending = null; busy.value = false
      if (exit) close()
    } catch (cause) {
      busy.value = false; dirty.value = true; error.value = (cause as Error).message
      post({ action: 'status', message: '未保存，请重试', modified: true })
    }
  } else if (message.event === 'exit') requestClose(!!message.modified || dirty.value)
}
function beforeUnload(event: BeforeUnloadEvent) {
  if (opened.value && (dirty.value || busy.value)) { event.preventDefault(); event.returnValue = '' }
}
function saved(data: { id: string; version: string }) { if (data.id === props.id) previewVersion.value = data.version }
onMounted(() => {
  window.addEventListener('message', receive); window.addEventListener('beforeunload', beforeUnload)
  import.meta.hot?.on('drawio:saved', saved)
})
onBeforeUnmount(() => {
  ++generation; stopTimer(); window.removeEventListener('message', receive)
  window.removeEventListener('beforeunload', beforeUnload); import.meta.hot?.off('drawio:saved', saved)
})
</script>

<template>
  <div class="drawio-diagram">
    <img ref="previewImage" :src="imageUrl" :alt="alt || '可编辑流程图'" />
    <button v-if="editable" ref="trigger" class="drawio-edit" type="button" @pointerdown.stop @dblclick.stop @click.stop="open">编辑流程图</button>
    <Teleport to="body">
      <div v-if="opened" class="drawio-overlay" @pointerdown.stop @click.stop @keydown.stop>
        <section class="drawio-dialog" role="dialog" aria-modal="true" aria-label="编辑流程图">
          <header class="drawio-header">
            <strong>编辑流程图</strong>
            <span role="status">{{ status }}</span>
            <button v-if="loaded" :disabled="busy" @click="fitEditor">适应窗口</button>
            <button v-if="error && xml" @click="downloadDraft">下载当前修改</button>
            <button :disabled="busy" @click="requestClose()">关闭编辑器</button>
          </header>
          <div v-if="error" class="drawio-error" role="alert">
            {{ error }}
            <button v-if="!loaded" @click="readyToMount = false; open()">重新加载</button>
          </div>
          <iframe v-if="readyToMount" ref="iframe" :src="editorUrl" title="draw.io 流程图编辑器" :class="{ 'drawio-saving': busy }" />
          <div v-if="confirmClose" class="drawio-confirm">
            <p>放弃未保存的修改？</p>
            <button @click="confirmClose = false">继续编辑</button>
            <button @click="close">放弃修改并关闭</button>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.drawio-diagram { position: relative; width: 100%; }
.drawio-diagram img { width: 100%; height: auto; display: block; background: #fff; }
.drawio-edit { position: absolute; right: -116px; top: 18px; font: 13px/1.4 sans-serif; padding: 7px 10px; border: 1px solid #cbd5e1; border-radius: 5px; background: white; color: #0f3466; cursor: pointer; }
.drawio-edit:hover { background: #eaf2fa; }
.drawio-overlay { position: fixed; inset: 0; z-index: 10000; padding: 12px; background: #0008; color: #182638; font: 14px/1.5 'Noto Sans CJK SC', sans-serif; color-scheme: only light; }
.drawio-dialog { position: relative; display: flex; flex-direction: column; height: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 10px 50px #0004; }
.drawio-header { display: flex; align-items: center; gap: 16px; padding: 10px 14px; border-bottom: 1px solid #d8e0e5; flex-wrap: wrap; }
.drawio-header strong { font-size: 17px; }
.drawio-header span { flex: 1; color: #526174; }
.drawio-dialog button { background: white; color: #0f3466; border: 1px solid #bcc9d7; border-radius: 4px; padding: 5px 10px; cursor: pointer; }
.drawio-dialog button:disabled { opacity: .5; cursor: wait; }
.drawio-dialog iframe { width: 100%; flex: 1; min-height: 0; border: 0; background: white; }
.drawio-saving { pointer-events: none; }
.drawio-error { padding: 8px 14px; color: #9b2525; background: #fff1ef; }
.drawio-confirm { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); padding: 24px; background: white; border: 1px solid #cbd5e1; box-shadow: 0 0 0 100vmax #0005; }
.drawio-confirm p { margin: 0 0 16px; }
.drawio-confirm button + button { margin-left: 10px; }
@media print { .drawio-edit, .drawio-overlay { display: none !important; } }
</style>
