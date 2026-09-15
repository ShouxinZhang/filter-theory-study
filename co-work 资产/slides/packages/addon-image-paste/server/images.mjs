import { createHash, randomUUID } from 'node:crypto'
import { readFile, writeFile, mkdir, rename, rm, stat } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { parseSync } from '@slidev/parser'
import { imageSize } from 'image-size'
import { preview } from '../preview.mjs'

const LIMIT = 20 * 1024 * 1024
const hash = text => createHash('sha256').update(text).digest('hex')
const fail = (message, status = 400) => Object.assign(new Error(message), { status })
const types = { png: 'image/png', jpg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp' }

export function inspectPage(source, page) {
  const deck = parseSync(source, 'slides.md', { preserveCR: true })
  if (deck.slides.some(slide => slide.frontmatter.src || slide.frontmatter.hide === true || slide.frontmatter.disabled === true))
    throw fail('导入或隐藏页面暂不支持直接粘贴图片，请使用单文件汇报。', 422)
  if (!Number.isInteger(page) || page < 1 || page > deck.slides.length) throw fail('页面已变化，请刷新后重新粘贴。', 409)
  const offsets = [0]
  for (let i = 0; i < source.length; i++) if (source[i] === '\n') offsets.push(i + 1)
  const slide = deck.slides[page - 1]
  const start = page === 1 ? 0 : offsets[deck.slides[page - 2].end]
  const end = page === deck.slides.length ? source.length : offsets[slide.end]
  return { deck, slide, start, end, raw: source.slice(start, end), content: preview(slide.content), version: hash(source) }
}

export function decodeImages(images, canvas) {
  if (!Array.isArray(images) || images.length < 1 || images.length > 5) throw fail('每次可粘贴 1–5 张图片。')
  if (!Array.isArray(canvas) || canvas.length !== 2 || canvas.some(n => !Number.isFinite(n) || n < 180 || n > 4096)) throw fail('幻灯片尺寸无效。')
  let total = 0
  return images.map((image, index) => {
    if (!image || typeof image.data !== 'string' || !/^[A-Za-z0-9+/]*={0,2}$/.test(image.data)) throw fail('图片数据无效。')
    const bytes = Buffer.from(image.data, 'base64')
    if (!bytes.length || bytes.toString('base64') !== image.data) throw fail('图片数据无效。')
    total += bytes.length
    if (total > LIMIT) throw fail('图片总大小不能超过 20 MB。', 413)
    let dimensions
    try { dimensions = imageSize(bytes) } catch { throw fail('无法读取图片，请重新复制。') }
    const { width, height, type } = dimensions
    if (!types[type] || image.type !== types[type]) throw fail('支持 PNG、JPEG、WebP 和 GIF 图片。', 415)
    if (!width || !height || width * height > 50_000_000) throw fail('图片尺寸过大或无效。', 413)
    const id = `pasted-${randomUUID()}`, filename = `${id}.${type}`, url = `/images/${filename}`
    const scale = Math.min(1, canvas[0] * .6 / width, canvas[1] * .6 / height)
    const w = Math.max(1, Math.round(width * scale)), h = Math.max(1, Math.round(height * scale))
    const x = Math.round(Math.min(canvas[0] - w - 12, (canvas[0] - w) / 2 + index * 18))
    const y = Math.round(Math.min(canvas[1] - h - 40, (canvas[1] - h) / 2 + index * 18))
    const markdown = `<v-drag id="${id}" pos="${x},${y},${w},${h}" class="pasted-image">\n\n![粘贴图片](${url})\n\n</v-drag>`
    return { bytes, filename, url, markdown, width, height }
  })
}

export function insertImages(source, page, markdown) {
  const info = inspectPage(source, page)
  const newline = source.includes('\r\n') ? '\r\n' : '\n'
  const comments = [...info.raw.matchAll(/<!--[\s\S]*?-->/g)]
  const last = comments.at(-1)
  const at = last && last.index + last[0].length === info.raw.trimEnd().length ? last.index : info.raw.length
  const raw = info.raw.slice(0, at) + newline + newline + markdown.replaceAll('\n', newline) + newline + newline + info.raw.slice(at)
  const updated = source.slice(0, info.start) + raw + source.slice(info.end)
  const result = inspectPage(updated, page)
  if (result.deck.slides.length !== info.deck.slides.length || result.slide.note !== info.slide.note)
    throw fail('无法安全插入图片，Markdown 未修改。', 422)
  return updated
}

export function createImageMiddleware(root) {
  const file = join(root, 'slides.md')
  let queue = Promise.resolve()
  return async (req, res) => {
    const send = (code, body) => { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(body)) }
    try {
      const url = new URL(req.url, 'http://localhost')
      if (url.pathname !== '/') throw fail('接口不存在。', 404)
      if (req.method === 'GET') {
        const info = inspectPage(await readFile(file, 'utf8'), Number(url.searchParams.get('page')))
        return send(200, { version: info.version, content: info.content })
      }
      if (req.method !== 'POST') throw fail('不支持此操作。', 405)
      if (![`http://${req.headers.host}`, `https://${req.headers.host}`].includes(req.headers.origin)) throw fail('请从当前汇报页面粘贴图片。', 403)
      if (!req.headers['content-type']?.startsWith('application/json')) throw fail('需要 JSON 数据。', 415)
      const chunks = []; let size = 0
      for await (const chunk of req) {
        size += chunk.length
        if (size > LIMIT * 1.4 + 10000) throw fail('图片总大小不能超过 20 MB。', 413)
        chunks.push(chunk)
      }
      let payload
      try { payload = JSON.parse(Buffer.concat(chunks).toString('utf8')) } catch { throw fail('图片请求无效。') }
      if (!payload || !['slide', 'editor'].includes(payload.mode)) throw fail('粘贴方式无效。')
      const task = queue.catch(() => {}).then(async () => {
        const original = await readFile(file, 'utf8'), info = inspectPage(original, payload.page)
        if (payload.version !== info.version) throw fail('Markdown 已更新，未覆盖原内容。请重新粘贴。', 409)
        if (payload.mode === 'slide' && payload.content !== info.content) throw fail('当前页面已更新，请刷新后重新粘贴。', 409)
        const images = decodeImages(payload.images, payload.canvas)
        const markdown = images.map(image => image.markdown).join('\n\n')
        const updated = payload.mode === 'slide' ? insertImages(original, payload.page, markdown) : original
        const created = [], temp = `${file}.${randomUUID()}.tmp`
        let committed = false
        try {
          await mkdir(join(root, 'public/images'), { recursive: true })
          for (const image of images) {
            const path = join(root, 'public/images', image.filename)
            await writeFile(path, image.bytes, { flag: 'wx' }); created.push(path)
          }
          if (updated !== original) {
            const history = join(root, '.image-paste-history')
            await mkdir(history, { recursive: true })
            await writeFile(join(history, `${Date.now()}-${randomUUID()}.md`), original, { flag: 'wx' })
            await writeFile(temp, updated, { mode: (await stat(file)).mode })
          }
          if (hash(await readFile(file, 'utf8')) !== info.version) throw fail('保存期间 Markdown 已更新，请重新粘贴。', 409)
          if (updated !== original) await rename(temp, file)
          committed = true
          return { markdown, page: payload.page, saved: payload.mode === 'slide', images: images.map(({ url, width, height }) => ({ url, width, height })) }
        } finally {
          await rm(temp, { force: true })
          if (!committed) await Promise.all(created.map(path => rm(path, { force: true })))
        }
      })
      queue = task
      send(200, await task)
    } catch (error) { send(error.status || 500, { error: error.status ? error.message : '图片保存失败，请重试。' }) }
  }
}

export function imagePastePlugin() {
  let root
  return {
    name: 'academic-image-paste',
    config(config) { root = resolve(config.root || process.cwd()); return { server: { watch: { ignored: [join(root, '.image-paste-history/**')] } } } },
    configureServer(server) { server.middlewares.use('/__image_paste', createImageMiddleware(root)) },
  }
}
