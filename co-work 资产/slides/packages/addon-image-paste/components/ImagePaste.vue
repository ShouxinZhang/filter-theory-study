<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useNav } from '@slidev/client'
import { slideWidth, slideHeight } from '@slidev/client/env.ts'
import { preview as normalize } from '../preview.mjs'

const { currentSlideNo, slides, isPrintMode } = useNav()
const enabled = computed(() => import.meta.env.DEV && !isPrintMode.value)
const busy = ref(false), status = ref(''), error = ref('')
const savedUrls = ref<string[]>([])
const endpoint = '/__image_paste'
let controller: AbortController | undefined
function editorTarget(target: EventTarget | null) {
  return target instanceof HTMLTextAreaElement && target.placeholder === 'Create slide content...' ? target : undefined
}
function inDialog() { return !!document.querySelector('[role="dialog"][aria-modal="true"]') }
function encode(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(',')[1])
    reader.onerror = () => reject(new Error('无法读取剪贴板图片。'))
    reader.readAsDataURL(file)
  })
}
async function upload(files: Blob[], textarea?: HTMLTextAreaElement) {
  if (busy.value) { error.value = '正在保存上一批图片，请稍后再粘贴。'; return }
  if (!files.length) { error.value = '剪贴板中没有图片。复制图片后按 Ctrl+V。'; return }
  if (files.length > 5 || files.reduce((size, file) => size + file.size, 0) > 20 * 1024 * 1024) {
    error.value = '每次最多 5 张图片，总大小不超过 20 MB。'; return
  }
  const page = currentSlideNo.value
  const content = normalize(slides.value[page - 1]?.meta?.slide?.content)
  const originalText = textarea?.value
  let selection = textarea ? [textarea.selectionStart, textarea.selectionEnd] : undefined
  // A freshly opened editor places the caret at the start of its YAML header.
  // Keep that configuration intact and insert at the start of the slide body.
  const header = originalText?.match(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/)
  if (selection && header && selection[0] < header[0].length) selection = [header[0].length, header[0].length]
  const mode = textarea ? 'editor' : 'slide'
  busy.value = true; error.value = ''; savedUrls.value = []; status.value = '正在保存图片…'
  controller = new AbortController()
  const activeController = controller
  const timer = setTimeout(() => activeController.abort(), 30000)
  try {
    const snapshotResponse = await fetch(`${endpoint}?page=${page}`, { cache: 'no-store', signal: activeController.signal })
    const snapshot = await snapshotResponse.json()
    if (!snapshotResponse.ok) throw new Error(snapshot.error || '无法读取当前页面。')
    if (mode === 'slide' && snapshot.content !== content) throw new Error('当前页面已更新，请刷新后重新粘贴。')
    const images = await Promise.all(files.map(async file => ({ type: file.type, data: await encode(file) })))
    const response = await fetch(endpoint, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: activeController.signal,
      body: JSON.stringify({ mode, page, content, version: snapshot.version, canvas: [slideWidth.value, slideHeight.value], images }),
    })
    const result = await response.json()
    if (!response.ok) throw new Error(result.error || '图片保存失败。')
    savedUrls.value = result.images.map((image: { url: string }) => image.url)
    if (textarea) {
      if (!textarea.isConnected || page !== currentSlideNo.value || textarea.value !== originalText)
        throw new Error('编辑内容已变化，已保留当前草稿。图片已保存，可从下方链接取用。')
      textarea.setRangeText(`\n\n${result.markdown}\n\n`, selection![0], selection![1], 'end')
      textarea.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertFromPaste', data: result.markdown }))
      textarea.focus()
      status.value = '图片代码已插入光标处，由 Markdown 编辑器自动保存。'
    } else status.value = `${files.length} 张图片已加入第 ${page} 页并保存。双击图片可拖动、缩放。`
    savedUrls.value = []
  } catch (cause) {
    error.value = (cause as Error).name === 'AbortError'
      ? '保存请求超时，请先检查当前页是否已插入图片，再重新粘贴。'
      : (cause as Error).message
    status.value = ''
  } finally { clearTimeout(timer); busy.value = false }
}
function paste(event: ClipboardEvent) {
  if (!enabled.value || inDialog()) return
  const target = event.target as HTMLElement | null
  const textarea = editorTarget(target)
  if (target?.closest('input, textarea, [contenteditable="true"]') && !textarea) return
  const files = Array.from(event.clipboardData?.items || [])
    .filter(item => item.kind === 'file' && item.type.startsWith('image/'))
    .map(item => item.getAsFile()).filter((file): file is File => !!file)
  if (!files.length) return // Let ordinary text paste use the browser/editor behavior.
  event.preventDefault()
  event.stopImmediatePropagation()
  void upload(files, textarea)
}
async function fromClipboard() {
  if (!enabled.value || busy.value || inDialog()) return
  try {
    if (!navigator.clipboard?.read) throw new Error('请复制图片后，在幻灯片画面按 Ctrl+V。')
    const items = await navigator.clipboard.read()
    const files: Blob[] = []
    for (const item of items) {
      const type = item.types.find(type => type.startsWith('image/'))
      if (type) files.push(await item.getType(type))
    }
    await upload(files)
  } catch (cause) {
    error.value = (cause as Error).name === 'NotAllowedError'
      ? '浏览器未允许读取剪贴板，请在幻灯片画面直接按 Ctrl+V。'
      : (cause as Error).message
  }
}
onMounted(() => window.addEventListener('paste', paste, true))
onBeforeUnmount(() => { controller?.abort(); window.removeEventListener('paste', paste, true) })
</script>

<template>
  <button v-if="enabled" class="icon-btn image-paste-trigger" title="粘贴图片（Ctrl+V）" aria-label="粘贴图片" :disabled="busy" @click="fromClipboard">
    <span class="i-carbon:image-copy" aria-hidden="true" /><span>贴图</span>
  </button>
  <Teleport to="body">
    <aside v-if="enabled && (status || error)" class="image-paste-notice" :class="{ 'image-paste-error': error }" :role="error ? 'alert' : 'status'">
      <span>{{ error || status }}</span>
      <a v-for="url in savedUrls" :key="url" :href="url" target="_blank" rel="noopener">打开已保存图片</a>
      <button v-if="!busy" aria-label="关闭图片粘贴提示" @click="status = ''; error = ''; savedUrls = []">×</button>
    </aside>
  </Teleport>
</template>

<style scoped>
.image-paste-trigger { display: inline-flex; align-items: center; gap: 3px; white-space: nowrap; font-size: 13px; }
.image-paste-notice { position: fixed; z-index: 90000; left: 50%; bottom: 65px; transform: translateX(-50%); max-width: min(620px, calc(100vw - 32px)); padding: 12px 40px 12px 16px; border: 1px solid #b9c9da; border-radius: 8px; background: #f4f9ff; color: #0f3466; box-shadow: 0 4px 18px #0002; font: 14px/1.5 sans-serif; }
.image-paste-notice a { display: block; text-decoration: underline; }
.image-paste-notice button { position: absolute; right: 10px; top: 8px; padding: 0 3px; font-size: 22px; }
.image-paste-error { background: #fff3f0; color: #8d3025; border-color: #e8bab0; }
</style>
