// Keep the editor synchronized even while focused; protect unsaved drafts.
const tab = ref<'content' | 'note'>('content')
const content = ref('')
const note = ref('')
const dirty = ref(false)
const saving = ref(false)
const saveError = ref('')
let baseSource: string | undefined
let editorPage = currentSlideNo.value

const { info, update } = useDynamicSlideInfo(currentSlideNo)

function sourceVersion(v: typeof info.value) {
  return JSON.stringify([v?.source.content?.trim() || '', v?.frontmatterRaw?.trim() || '', v?.note?.trim() || ''])
}

function loadEditor(v: typeof info.value) {
  note.value = (v?.note || '').trim()
  const frontmatterPart = v?.frontmatterRaw?.trim() ? `---\n${v.frontmatterRaw.trim()}\n---\n\n` : ''
  content.value = frontmatterPart + (v?.source.contentRaw || '').trim()
  baseSource = sourceVersion(v)
  editorPage = currentSlideNo.value
  dirty.value = false
  saveError.value = ''
}

watch(info, (v) => {
  // Focus alone is not an unsaved edit. External changes must reach the textarea.
  if (!dirty.value && !saving.value)
    loadEditor(v)
}, { immediate: true })

async function reloadEditor() {
  try {
    const response = await fetch(`/__slidev/slides/${currentSlideNo.value}.json`)
    if (!response.ok) throw new Error('读取失败，请稍后重试。')
    info.value = await response.json()
    loadEditor(info.value)
  }
  catch (error) {
    saveError.value = error instanceof Error ? error.message : String(error)
  }
}

async function save() {
  if (saving.value || saveError.value || !info.value) return
  const pageNo = editorPage
  const { content: contentOnly, frontmatterRaw } = parseSideEditorContent(content.value)
  const patch = { note: note.value, content: contentOnly, frontmatterRaw, expectedSource: baseSource }
  saving.value = true
  dirty.value = false
  try {
    const saved = await update(patch, pageNo)
    if (saved) baseSource = sourceVersion(saved)
  }
  catch (error) {
    dirty.value = true
    saveError.value = error instanceof Error ? error.message : String(error)
  }
  finally {
    saving.value = false
    if (dirty.value && !saveError.value) void save()
  }
}

