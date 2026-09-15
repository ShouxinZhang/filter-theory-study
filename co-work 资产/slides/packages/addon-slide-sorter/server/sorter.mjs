import { createHash, randomUUID } from 'node:crypto'
import { readFile, writeFile, mkdir, rename, rm, stat } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { parseSync } from '@slidev/parser'
import { previewText } from '../preview.mjs'

const newSlideTemplate = await readFile(new URL('../templates/new-slide.md', import.meta.url), 'utf8')

const hash = text => createHash('sha256').update(text).digest('hex')
const fail = (message, status = 400) => Object.assign(new Error(message), { status })

export function inspectDeck(source) {
  const parsed = parseSync(source, 'slides.md', { preserveCR: true })
  if (!parsed.slides.length) throw fail('没有可排序的页面。')
  if (parsed.slides.some(slide => slide.frontmatter.src || slide.frontmatter.hide === true || slide.frontmatter.disabled === true))
    throw fail('这份汇报含导入或隐藏页面，请在 Markdown 中调整顺序。', 422)
  const offsets = [0]
  for (let i = 0; i < source.length; i++) if (source[i] === '\n') offsets.push(i + 1)
  const starts = parsed.slides.map((slide, index) => index === 0 ? 0 : offsets[parsed.slides[index - 1].end])
  const seen = new Map()
  const slides = parsed.slides.map((slide, index) => {
    const fingerprint = hash(slide.raw.trim())
    const occurrence = seen.get(fingerprint) || 0
    seen.set(fingerprint, occurrence + 1)
    return {
      id: `${fingerprint}:${occurrence}`, no: index + 1,
      title: String(slide.title || `第 ${index + 1} 页`), revision: slide.revision,
      previewContent: previewText(slide.content), previewFrontmatter: slide.frontmatter,
      raw: source.slice(starts[index], starts[index + 1] ?? source.length),
    }
  })
  return { version: hash(source), slides }
}
const publicDeck = deck => ({ version: deck.version, slides: deck.slides.map(({ raw, ...slide }) => slide) })

export function reorderDeck(source, order) {
  const deck = inspectDeck(source), ids = deck.slides.map(slide => slide.id)
  if (!Array.isArray(order) || order.length !== ids.length || new Set(order).size !== ids.length || order.some(id => !ids.includes(id)))
    throw fail('页面列表已变化，请重新加载排序面板。', 409)
  if (order[0] !== ids[0]) throw fail('封面含全局配置，需要保留在首位。')
  if (order.every((id, index) => id === ids[index])) return source
  const blocks = new Map(deck.slides.map(slide => [slide.id, slide]))
  return assembleSlides(source, order.map(id => blocks.get(id)))
}

function assembleSlides(source, blocks) {
  const newline = source.includes('\r\n') ? '\r\n' : '\n'
  const result = blocks.map((slide, index) =>
    index < blocks.length - 1 && !slide.raw.endsWith('\n') ? slide.raw + newline : slide.raw).join('')
  const output = inspectDeck(result)
  if (output.slides.length !== blocks.length || output.slides.some((slide, index) => slide.id.split(':')[0] !== blocks[index].id.split(':')[0]))
    throw fail('此文件的分隔符格式无法安全修改页面，未保存。', 422)
  return result
}

export function modifyDeck(source, operation) {
  if (!operation || !['insert', 'duplicate', 'delete'].includes(operation.action))
    throw fail('不支持此页面操作。')
  const deck = inspectDeck(source)
  const index = deck.slides.findIndex(slide => slide.id === operation.id)
  if (index < 0) throw fail('目标页面已变化，请重新加载页面列表。', 409)
  if (operation.action !== 'insert' && index === 0)
    throw fail('封面含全局配置，不能删除或复制。')
  const blocks = [...deck.slides]
  if (operation.action === 'delete') blocks.splice(index, 1)
  else if (operation.action === 'duplicate') blocks.splice(index + 1, 0, blocks[index])
  else {
    let title = '新页面', number = 2
    const titles = new Set(blocks.map(slide => slide.title))
    while (titles.has(title)) title = `新页面 ${number++}`
    let raw = newSlideTemplate.replaceAll('__TITLE__', title)
    if (source.includes('\r\n')) raw = raw.replaceAll('\n', '\r\n')
    const placeholder = inspectDeck('# Placeholder\n\n' + raw).slides[1]
    blocks.splice(index + 1, 0, { ...placeholder, raw })
  }
  return assembleSlides(source, blocks)
}

export function createSorterMiddleware(file) {
  let queue = Promise.resolve()
  return async (req, res) => {
    const send = (code, body) => {
      res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' })
      res.end(JSON.stringify(body))
    }
    try {
      if ((req.url || '/').split('?')[0] !== '/') throw fail('接口不存在。', 404)
      if (req.method === 'GET') { send(200, publicDeck(inspectDeck(await readFile(file, 'utf8')))); return }
      if (req.method !== 'POST') throw fail('不支持此操作。', 405)
      if (![ `http://${req.headers.host}`, `https://${req.headers.host}` ].includes(req.headers.origin))
        throw fail('请从当前 Slidev 页面保存。', 403)
      if (!req.headers['content-type']?.startsWith('application/json')) throw fail('需要 JSON 数据。', 415)
      let text = '', size = 0
      for await (const chunk of req) {
        size += chunk.length
        if (size > 256 * 1024) throw fail('请求过大。', 413)
        text += chunk.toString()
      }
      let payload
      try { payload = JSON.parse(text) } catch { throw fail('页面操作数据格式不正确。') }
      const task = queue.catch(() => {}).then(async () => {
        const original = await readFile(file, 'utf8')
        if (payload.version !== hash(original)) throw fail('Markdown 已在其他窗口修改，未覆盖。请重新加载页面列表后再操作。', 409)
        const updated = payload.action && payload.action !== 'reorder'
          ? modifyDeck(original, payload)
          : reorderDeck(original, payload.order)
        if (updated !== original) {
          const history = join(file, '..', '.slide-order-history')
          await mkdir(history, { recursive: true })
          await writeFile(join(history, `${Date.now()}-${randomUUID()}.md`), original, { flag: 'wx' })
          const temp = `${file}.${randomUUID()}.tmp`
          try {
            await writeFile(temp, updated, { mode: (await stat(file)).mode })
            if (hash(await readFile(file, 'utf8')) !== payload.version)
              throw fail('保存期间 Markdown 已变化，未覆盖。请重新加载页面列表。', 409)
            await rename(temp, file)
          } finally { await rm(temp, { force: true }) }
        }
        return publicDeck(inspectDeck(updated))
      })
      queue = task
      send(200, await task)
    } catch (error) {
      send(error.status || 500, { error: error.status ? error.message : '无法保存页面。请重试；原稿备份保存在汇报目录中。' })
    }
  }
}

export function slideSorterPlugin() {
  let root
  return {
    name: 'academic-slide-sorter',
    config(config) {
      root = resolve(config.root || process.cwd())
      return { server: { watch: { ignored: [join(root, '.slide-order-history/**')] } } }
    },
    configureServer(server) {
      server.middlewares.use('/__slide_order', createSorterMiddleware(join(root, 'slides.md')))
    },
  }
}
