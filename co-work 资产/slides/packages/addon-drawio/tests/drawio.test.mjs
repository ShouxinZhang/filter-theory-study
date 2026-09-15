import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createServer } from 'node:http'
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { drawioPlugin } from '../server/drawio.mjs'

const original = '<mxfile><diagram><mxGraphModel><root><mxCell id="0"/></root></mxGraphModel></diagram></mxfile>'
const changed = original.replace('id="0"', 'id="0" value="测试修改"')
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80"><text x="1" y="20">测试修改</text></svg>'
test('save synchronizes source and preview; conflicts and invalid requests preserve files', async () => {
  const root = await mkdtemp(join(tmpdir(), 'slidev-drawio-'))
  let middleware; const events = []
  const entry = { source: 'source.drawio', copy: 'copy.drawio', preview: 'preview.svg', sourcePreview: 'source.svg' }
  for (const [key, path] of Object.entries(entry)) await writeFile(join(root, path), key.includes('review') ? svg : original)
  drawioPlugin(root, { test: entry }).configureServer({
    middlewares: { use(_prefix, fn) { middleware = fn } },
    ws: { send(event) { events.push(event) } }, config: { logger: { error() {} } },
  })
  const server = createServer((req, res) => middleware(req, res))
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const base = `http://127.0.0.1:${server.address().port}`
  const post = (data, extra = {}) => fetch(`${base}/test`, { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: base, ...extra }, body: JSON.stringify(data) })
  try {
    const initial = await (await fetch(`${base}/test`)).json()
    assert.equal(initial.xml, original)
    const response = await post({ xml: changed, svg, version: initial.version })
    assert.equal(response.status, 200, await response.clone().text())
    const saved = await response.json()
    assert.notEqual(saved.version, initial.version)
    assert.equal(await readFile(join(root, 'source.drawio'), 'utf8'), changed)
    assert.equal(await readFile(join(root, 'copy.drawio'), 'utf8'), changed)
    assert.equal(await readFile(join(root, 'preview.svg'), 'utf8'), await readFile(join(root, 'source.svg'), 'utf8'))
    assert.match(await readFile(join(root, 'preview.svg'), 'utf8'), /color-scheme:only light/)
    assert.equal(events[0].event, 'drawio:saved')
    assert.equal((await readdir(join(root, '.drawio-history/test'))).length, 1)
    assert.equal((await post({ xml: original, svg, version: initial.version })).status, 409)
    assert.equal((await post({ xml: original, svg, version: saved.version }, { Origin: 'https://example.com' })).status, 403)
    assert.equal((await fetch(`${base}/unknown`)).status, 404)
    assert.equal((await post({ xml: '<mxfile><oops></mxfile>', svg, version: saved.version })).status, 400)
    assert.equal((await post({ xml: original, svg: '<svg><script>alert(1)</script></svg>', version: saved.version })).status, 400)
    assert.equal(await readFile(join(root, 'source.drawio'), 'utf8'), changed)
  } finally {
    await new Promise(resolve => server.close(resolve))
    await rm(root, { recursive: true, force: true })
  }
})
