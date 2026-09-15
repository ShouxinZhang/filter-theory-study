import { createHash, randomUUID } from 'node:crypto'
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { DOMParser, XMLSerializer } from '@xmldom/xmldom'

const LIMIT = 12 * 1024 * 1024
const hash = text => createHash('sha256').update(text).digest('hex')
const fail = (message, status = 400) => Object.assign(new Error(message), { status })
function parse(text, roots) {
  if (typeof text !== 'string' || !text.trim() || /<!DOCTYPE|<!ENTITY/i.test(text))
    throw fail('图文件为空或格式不受支持。')
  let invalid = false
  let doc
  try { doc = new DOMParser({ onError: () => { invalid = true } }).parseFromString(text, 'text/xml') }
  catch { throw fail('图文件格式不正确，未保存。') }
  if (invalid || !roots.includes(doc.documentElement?.localName)) throw fail('图文件格式不正确，未保存。')
  return doc
}
export function whiteSvg(text) {
  const doc = parse(text, ['svg']), root = doc.documentElement
  for (const el of Array.from(doc.getElementsByTagName('*'))) {
    if (['script', 'iframe', 'object', 'embed'].includes(el.localName?.toLowerCase()))
      throw fail('SVG 包含不支持的活动内容。')
    for (const attr of Array.from(el.attributes || [])) {
      if (/^on/i.test(attr.name) || (/href$/i.test(attr.name) && /^\s*javascript:/i.test(attr.value)))
        throw fail('SVG 包含不支持的活动内容。')
    }
  }
  root.setAttribute('style', `${root.getAttribute('style') || ''};background:#FFFFFF;background-color:#FFFFFF;color-scheme:only light;`)
  return new XMLSerializer().serializeToString(doc)
}
async function body(req) {
  let size = 0; const chunks = []
  for await (const chunk of req) {
    size += chunk.length
    if (size > LIMIT) throw fail('图文件超过 12 MB，未保存。', 413)
    chunks.push(chunk)
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')) }
  catch { throw fail('保存数据格式不正确。') }
}
async function atomic(path, data) {
  await mkdir(dirname(path), { recursive: true })
  const temp = `${path}.${randomUUID()}.tmp`
  try { await writeFile(temp, data); await rename(temp, path) }
  finally { await rm(temp, { force: true }) }
}
export function drawioPlugin(root, diagrams) {
  const entries = Object.fromEntries(Object.entries(diagrams).map(([id, paths]) => [id,
    Object.fromEntries(Object.entries(paths).map(([key, value]) => [key, resolve(root, value)])),
  ]))
  const managed = new Set(Object.values(entries).flatMap(Object.values))
  const history = join(root, '.drawio-history')
  let queue = Promise.resolve()
  async function current(entry) {
    const [xml, svg] = await Promise.all([readFile(entry.source, 'utf8'), readFile(entry.preview, 'utf8')])
    return { xml, version: hash(xml + '\0' + svg) }
  }
  return {
    name: 'academic-drawio',
    // Managed diagram writes must not reload the page while Save is in flight.
    config() { return { server: { watch: { ignored: [...managed, `${history}/**`] } } } },
    configureServer(server) {
      server.middlewares.use('/__drawio', async (req, res) => {
        const send = (code, data) => {
          res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' })
          res.end(JSON.stringify(data))
        }
        try {
          const id = (req.url || '').split('?')[0].replace(/^\//, '')
          const entry = Object.hasOwn(entries, id) ? entries[id] : null
          if (!entry) throw fail('未配置这张流程图。', 404)
          if (req.method === 'GET') { send(200, await current(entry)); return }
          if (req.method !== 'POST') throw fail('不支持此操作。', 405)
          if (req.headers.origin !== `http://${req.headers.host}` && req.headers.origin !== `https://${req.headers.host}`)
            throw fail('请从当前 Slidev 页面保存。', 403)
          if (!req.headers['content-type']?.startsWith('application/json')) throw fail('需要 JSON 数据。', 415)
          const payload = await body(req)
          parse(payload.xml, ['mxfile', 'mxGraphModel'])
          const svg = whiteSvg(payload.svg)
          const run = queue.catch(() => {}).then(async () => {
            const initial = await current(entry)
            if (payload.version !== initial.version)
              throw fail('源文件已在其他窗口修改。请下载当前修改后重新打开，避免覆盖。', 409)
            const writes = new Map([[entry.source, payload.xml], [entry.preview, svg]])
            if (entry.copy) writes.set(entry.copy, payload.xml)
            if (entry.sourcePreview) writes.set(entry.sourcePreview, svg)
            const previous = new Map()
            for (const path of writes.keys()) previous.set(path, await readFile(path))
            const backup = join(history, id, `${Date.now()}-${initial.version.slice(0, 8)}`)
            await mkdir(backup, { recursive: true })
            await writeFile(join(backup, 'diagram.drawio'), initial.xml)
            await writeFile(join(backup, 'preview.svg'), previous.get(entry.preview))
            const committed = []
            try {
              for (const [path, data] of writes) { await atomic(path, data); committed.push(path) }
            } catch (error) {
              for (const path of committed.reverse()) await atomic(path, previous.get(path))
              throw error
            }
            const version = hash(payload.xml + '\0' + svg)
            server.ws.send({ type: 'custom', event: 'drawio:saved', data: { id, version } })
            return { version }
          })
          queue = run
          send(200, await run)
        } catch (error) {
          if (!error.status) server.config.logger.error(`[drawio] ${error.message}`)
          send(error.status || 500, { error: error.status ? error.message : '无法写入图文件。修改仍保留在编辑器中，请重试。' })
        }
      })
    },
  }
}
