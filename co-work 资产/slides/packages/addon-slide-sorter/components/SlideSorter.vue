<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useNav } from '@slidev/client'
import SortThumbnail from './SortThumbnail.vue'
import { matchesPreview } from '../preview.mjs'

type Item = { id: string; no: number; title: string; revision: string; previewContent: string; previewFrontmatter: Record<string, unknown> }
type Operation = { action: 'reorder'; order: string[] } | { action: 'insert' | 'duplicate' | 'delete'; id: string }
type Deck = { version: string; slides: Item[] }
const { slides, currentSlideNo, go, isPrintMode } = useNav()
const enabled = computed(() => import.meta.env.DEV && !isPrintMode.value)
const opened = ref(false), busy = ref(false), error = ref(''), status = ref('')
const items = ref<Item[]>([]), version = ref(''), dragging = ref(''), target = ref('')
const insertAfter = ref(false), generation = ref(0), selected = ref(0)
const dialog = ref<HTMLElement>(), trigger = ref<HTMLButtonElement>()
let pending: Operation | null = null
let nextPage = 1, nextSelected = 0
let controller: AbortController | undefined
let alive = true
const endpoint = '/__slide_order'
const recoveryKey = 'academic-slide-sorter-panel'
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

async function request(operation?: Operation): Promise<Deck> {
  const activeController = new AbortController()
  controller = activeController
  const timeout = setTimeout(() => activeController.abort(), 15000)
  try {
    const response = await fetch(endpoint, operation ? {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...operation, version: version.value }), signal: controller.signal,
    } : { cache: 'no-store', signal: controller.signal })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '无法读取或保存页面。')
    return data
  } finally { clearTimeout(timeout) }
}
async function syncRoutes(deck: Deck) {
  // Wait until Slidev has recompiled the new page order before showing thumbnails.
  for (let i = 0; i < 100; i++) {
    if (!alive) return
    if (slides.value.length === deck.slides.length && deck.slides.every((item, index) =>
      matchesPreview(slides.value[index]?.meta?.slide, item))) return
    await sleep(100)
  }
  throw new Error('页序已读取，预览仍在更新。请点击“重新加载”同步缩略图。')
}
async function reload() {
  busy.value = true; error.value = ''; status.value = '正在加载页面…'
  try {
    const data = await request()
    await syncRoutes(data)
    items.value = data.slides; version.value = data.version; pending = null; selected.value = Math.max(0, Math.min(currentSlideNo.value - 1, data.slides.length - 1))
    generation.value++; status.value = '拖动缩略图，松手后自动保存'
  } catch (cause) { error.value = (cause as Error).message; status.value = '' }
  finally { busy.value = false; await restoreFocus() }
}
async function open() {
  opened.value = true
  await nextTick(); dialog.value?.focus()
  await reload()
  remember()
}
function close() {
  if (busy.value) return
  if (pending && !window.confirm('这次页面操作尚未确认保存。关闭面板并稍后重新加载？')) return
  opened.value = false; pending = null; error.value = ''
  try { sessionStorage.removeItem(recoveryKey) } catch {}
  nextTick(() => trigger.value?.focus())
}
async function save() {
  if (!pending || busy.value) return
  busy.value = true; error.value = ''; status.value = '正在保存页面…'
  remember(expectedPages())
  try {
    const data = await request(pending)
    if (!alive) return
    // A successful response means disk is saved even if compilation takes longer.
    version.value = data.version; pending = null
    await syncRoutes(data)
    if (!alive) return
    items.value = data.slides; generation.value++
    selected.value = Math.max(0, Math.min(nextSelected, data.slides.length - 1))
    go(Math.max(1, Math.min(nextPage, data.slides.length)))
    status.value = '已保存到 Markdown'
    remember()
    await nextTick()
    dialog.value?.querySelector(`[data-sort-index="${selected.value}"]`)?.scrollIntoView({ block: 'nearest' })
  } catch (cause) {
    error.value = (cause as Error).name === 'AbortError'
      ? '保存请求超时。请重新加载页面列表，确认结果后再操作。'
      : (cause as Error).message
    status.value = pending ? '页面操作尚未确认保存' : '文件已保存，请重新加载预览'
  } finally { busy.value = false; await restoreFocus() }
}
function move(from: number, to: number) {
  if (busy.value || error.value || from < 1 || to < 1 || to >= items.value.length || from === to) return
  const currentId = items.value[currentSlideNo.value - 1]?.id
  const next = [...items.value]
  const [item] = next.splice(from, 1); next.splice(to, 0, item)
  items.value = next; pending = { action: 'reorder', order: next.map(item => item.id) }
  nextPage = next.findIndex(item => item.id === currentId) + 1
  nextSelected = to
  void save()
}
function expectedPages(): (string | null)[] {
  const ids: (string | null)[] = items.value.map(item => item.id.split(':')[0])
  if (!pending || pending.action === 'reorder') return ids
  const operation = pending
  const index = items.value.findIndex(item => item.id === operation.id)
  if (pending.action === 'delete') ids.splice(index, 1)
  else ids.splice(index + 1, 0, pending.action === 'insert' ? null : ids[index])
  return ids
}
function remember(expected?: (string | null)[]) {
  try {
    sessionStorage.setItem(recoveryKey, JSON.stringify({ selected: expected ? nextSelected : selected.value, page: nextPage, expected }))
  } catch {}
}
async function recoverPanel() {
  if (!enabled.value) return
  let stored
  try { stored = JSON.parse(sessionStorage.getItem(recoveryKey) || 'null') } catch {}
  if (!stored) return
  opened.value = true
  await reload()
  if (error.value) return
  selected.value = Math.max(0, Math.min(Number(stored.selected) || 0, items.value.length - 1))
  // Vite can reload the whole page when adding/removing slide modules. Read disk;
  // never resend an operation whose response may have been lost during reload.
  if (Array.isArray(stored.expected) && stored.expected.length === items.value.length
    && stored.expected.every((id: string | null, index: number) => id === null || id === items.value[index].id.split(':')[0])) {
    go(Math.max(1, Math.min(Number(stored.page) || 1, items.value.length)))
    status.value = '已保存到 Markdown'
  }
  remember()
}
function modify(action: 'insert' | 'duplicate' | 'delete', index: number) {
  if (busy.value || error.value || !items.value[index] || (action !== 'insert' && index === 0)) return
  const item = items.value[index]
  if (action === 'delete' && !window.confirm(`删除第 ${index + 1} 页「${item.title}」？\n删除前会自动备份 Markdown。`)) return
  pending = { action, id: item.id }
  if (action === 'delete') {
    nextPage = currentSlideNo.value > index + 1 ? currentSlideNo.value - 1 : currentSlideNo.value
    nextSelected = Math.min(index, items.value.length - 2)
  } else {
    nextPage = index + 2
    nextSelected = index + 1
  }
  void save()
}
function dragStart(event: DragEvent, item: Item, index: number) {
  if (index === 0 || busy.value || error.value) { event.preventDefault(); return }
  dragging.value = item.id
  event.dataTransfer!.effectAllowed = 'move'
  event.dataTransfer!.setData('text/plain', item.id)
}
function dragOver(event: DragEvent, item: Item, index: number) {
  if (!dragging.value || index === 0 || busy.value || error.value) return
  event.preventDefault()
  event.dataTransfer!.dropEffect = 'move'
  target.value = item.id
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  insertAfter.value = event.clientX > rect.left + rect.width / 2
}
function dragEnd() { dragging.value = ''; target.value = '' }
function drop(event: DragEvent, item: Item) {
  event.preventDefault()
  const from = items.value.findIndex(slide => slide.id === dragging.value)
  const anchor = items.value.findIndex(slide => slide.id === item.id)
  let to = anchor + (insertAfter.value ? 1 : 0)
  if (from < to) to--
  dragEnd(); move(from, to)
}
async function restoreFocus() {
  await nextTick()
  if (opened.value && !dialog.value?.contains(document.activeElement)) dialog.value?.focus()
}
function captureKey(event: KeyboardEvent) {
  if (!opened.value) return
  event.stopImmediatePropagation()
  keydown(event)
}
function keydown(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); close() }
  if (event.key !== 'Tab') return
  const buttons = [...(dialog.value?.querySelectorAll<HTMLElement>('button:not(:disabled),[tabindex="0"]') || [])]
  const first = buttons[0], last = buttons.at(-1)
  if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.value)) {
    event.preventDefault(); last?.focus()
  } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialog.value)) {
    event.preventDefault(); first?.focus()
  }
}
onMounted(() => {
  window.addEventListener('keydown', captureKey, true)
  void recoverPanel()
})
onBeforeUnmount(() => { alive = false; controller?.abort(); window.removeEventListener('keydown', captureKey, true) })
</script>

<template>
  <button v-if="enabled" ref="trigger" class="icon-btn sorter-trigger" title="页面排序" aria-label="页面排序" @click="open">
    <span class="i-carbon:drag-vertical" aria-hidden="true" /><span>排序</span>
  </button>
  <Teleport to="body">
    <div v-if="enabled && opened" class="sorter-overlay" @click.stop @dblclick.stop @pointerdown.stop>
      <section ref="dialog" role="dialog" aria-modal="true" aria-label="页面排序" tabindex="-1" class="sorter-dialog">
        <header class="sorter-header">
          <div><h2>页面排序与管理</h2><p>拖动换序，选中缩略图后新增 · 修改自动保存</p></div>
          <div class="sorter-header-actions">
            <button class="sorter-add" :disabled="busy || !!error || !items.length" @click="modify('insert', selected)">＋ 新增页</button>
            <button :disabled="busy" @click="close">关闭</button>
          </div>
        </header>
        <div class="sorter-status"><div><span role="status">{{ status }}</span><span v-if="items.length" class="sorter-insert-hint">选中第 {{ selected + 1 }} 页 · 新页面插在其后 · 共 {{ items.length }} 页</span></div><button :disabled="busy" @click="reload">重新加载</button></div>
        <div v-if="error" role="alert" class="sorter-error">{{ error }} <button v-if="pending" :disabled="busy" @click="save">重试保存</button></div>
        <div class="sorter-grid" :aria-busy="busy" :class="{ 'sorter-busy': busy }">
          <article v-for="(item, index) in items" :key="item.id" class="sorter-card"
            :data-sort-id="item.id" :data-sort-index="index" :aria-label="`第 ${index + 1} 页：${item.title}`"
            :class="{ 'sorter-selected': selected === index, 'sorter-fixed': index === 0, 'sorter-dragging': dragging === item.id, 'sorter-before': target === item.id && !insertAfter, 'sorter-after': target === item.id && insertAfter }"
            :draggable="index !== 0 && !busy && !error" @dragstart="dragStart($event, item, index)" @dragover="dragOver($event, item, index)" @drop="drop($event, item)" @dragend="dragEnd">
            <button class="sorter-select" :aria-label="`选择第 ${index + 1} 页`" :aria-pressed="selected === index" :disabled="busy || !!error" @click="selected = index">
            <div class="sorter-preview">
              <SortThumbnail v-if="slides[item.no - 1] && !busy && !error" :key="`${generation}-${item.id}`" :route="slides[item.no - 1]" :frontmatter="item.previewFrontmatter" />
              <span v-else>{{ error ? '预览待同步' : '正在更新预览…' }}</span>
            </div>
            <div class="sorter-caption"><strong>{{ index + 1 }}</strong><span :title="item.title">{{ item.title }}</span></div>
            </button>
            <div class="sorter-actions">
              <span v-if="index === 0">封面 · 固定</span>
              <template v-else>
                <button :disabled="busy || !!error || index === 1" :aria-label="`前移第 ${index + 1} 页`" @click="move(index, index - 1)">← 前移</button>
                <button :disabled="busy || !!error || index === items.length - 1" :aria-label="`后移第 ${index + 1} 页`" @click="move(index, index + 1)">后移 →</button>
              </template>
            </div>
            <div class="sorter-actions sorter-edit-actions">
              <button :disabled="busy || !!error || index === 0" :aria-label="`复制第 ${index + 1} 页`" @click="modify('duplicate', index)">复制页</button>
              <button class="sorter-delete" :disabled="busy || !!error || index === 0" :aria-label="`删除第 ${index + 1} 页`" @click="modify('delete', index)">删除页</button>
            </div>
          </article>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.sorter-trigger { display: inline-flex; align-items: center; gap: 3px; font-size: 13px; white-space: nowrap; }
.sorter-overlay { position: fixed; inset: 0; z-index: 100000; display: flex; align-items: center; justify-content: center; padding: 20px; background: #0009; color: #182638; font-family: var(--slidev-font-sans); }
.sorter-dialog { display: flex; flex-direction: column; width: min(1160px, 100%); max-height: calc(100dvh - 40px); border-radius: 12px; background: #f5f7fa; box-shadow: 0 16px 60px #0006; outline: none; overflow: hidden; text-align: left; }
.sorter-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 22px 10px; gap: 16px; background: white; }
.sorter-header h2 { margin: 0; font-size: 21px; font-weight: 700; }
.sorter-header p { margin: 5px 0 0; color: #596678; font-size: 13px; }
.sorter-dialog button { padding: 6px 11px; background: white; border: 1px solid #c5d0de; border-radius: 5px; font-size: 13px; color: #0f3466; cursor: pointer; white-space: nowrap; }
.sorter-dialog button:hover:not(:disabled) { background: #e6eef7; }
.sorter-dialog button:disabled { opacity: .4; cursor: default; }
.sorter-dialog button:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
.sorter-status { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 8px 22px; background: white; border-bottom: 1px solid #d8e0e5; font-size: 13px; min-height: 45px; }
.sorter-error { background: #fff0ed; color: #97331b; padding: 12px 22px; font-size: 14px; }
.sorter-grid { display: grid; grid-template-columns: repeat(auto-fit, 280px); gap: 18px; justify-content: center; padding: 20px; overflow: auto; overscroll-behavior: contain; min-height: 120px; }
.sorter-card { position: relative; width: 280px; border: 2px solid transparent; border-radius: 8px; padding: 8px; background: white; box-shadow: 0 1px 5px #152e491c; cursor: grab; }
.sorter-selected { border-color: #2563eb; }
.sorter-header-actions { display: flex; gap: 8px; flex-shrink: 0; }
.sorter-dialog .sorter-add { background: #0f3466; border-color: #0f3466; color: white; }
.sorter-dialog .sorter-add:hover:not(:disabled) { background: #194b89; }
.sorter-insert-hint { display: block; margin-top: 4px; color: #596678; font-size: 12px; }
.sorter-dialog .sorter-select { display: block; padding: 0; width: 260px; border: 0; text-align: left; white-space: normal; cursor: inherit; }
.sorter-dialog .sorter-select:hover:not(:disabled) { background: white; }
.sorter-edit-actions { border-top: 1px solid #e5eaf0; padding-top: 8px; }
.sorter-dialog .sorter-delete { color: #a52b25; }
.sorter-fixed { cursor: default; }
.sorter-dragging { opacity: .35; }
.sorter-before { border-left-color: #2563eb; background: #eff6ff; }
.sorter-after { border-right-color: #2563eb; background: #eff6ff; }
.sorter-preview { width: 260px; height: 146.25px; overflow: hidden; background: white; pointer-events: none; user-select: none; display: grid; place-items: center; font-size: 13px; color: #596678; }
.sorter-preview :deep(*) { pointer-events: none !important; user-select: none !important; }
.sorter-caption { display: flex; gap: 8px; align-items: baseline; margin-top: 9px; font-size: 13px; }
.sorter-caption strong { color: #0f3466; font-size: 16px; }
.sorter-caption span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sorter-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 9px; min-height: 31px; color: #6b7280; font-size: 12px; }
.sorter-busy { cursor: progress; }
@media (max-width: 640px) { .sorter-overlay { padding: 8px; } .sorter-dialog { max-height: calc(100dvh - 16px); } .sorter-header { flex-wrap: wrap; } .sorter-header, .sorter-status { padding-left: 12px; padding-right: 12px; } .sorter-grid { padding: 12px; } }
@media print { .sorter-overlay, .sorter-trigger { display: none !important; } }
</style>
