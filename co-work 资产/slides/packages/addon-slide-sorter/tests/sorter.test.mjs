import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtemp, readFile, writeFile, readdir, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createServer } from 'node:http'
import { matchesPreview } from '../preview.mjs'
import { inspectDeck, reorderDeck, modifyDeck, createSorterMiddleware } from '../server/sorter.mjs'

const source = '---\ntheme: hitsz-academic\n---\n# Cover\n\n---\nlayout: academic\ndragPos:\n  x: 12,34,56,78\n---\n# A\n\n$$x^2$$\n```md\n---\nnot a slide\n```\n<!-- speaker note\n---\nkept -->\n\n---\n\n# B\n\n---\n\n# C'
test('moving whole slides preserves headmatter, formulas, coordinates, fences and speaker notes', () => {
  const deck = inspectDeck(source)
  assert.equal(deck.slides.length, 4)
  const order = [0, 3, 1, 2].map(i => deck.slides[i].id)
  const output = reorderDeck(source, order), after = inspectDeck(output)
  assert.deepEqual(after.slides.map(s => s.title), ['Cover','C','A','B'])
  assert.equal(after.slides[0].raw, deck.slides[0].raw)
  assert.equal(after.slides[2].raw, deck.slides[1].raw)
  assert.match(output, /dragPos:\n  x: 12,34,56,78/)
  const restored = inspectDeck(reorderDeck(output, deck.slides.map(s => s.id)))
  assert.deepEqual(restored.slides.map(s => s.id), deck.slides.map(s => s.id))
  assert.throws(() => reorderDeck(source, [...order].reverse()), /封面/)
  assert.throws(() => reorderDeck(source, [order[0],order[1],order[1],order[3]]), /页面列表/)
})
test('CRLF and identical slides remain valid; imported slides are rejected', () => {
  const crlf=source.replaceAll('\n','\r\n'), deck=inspectDeck(crlf)
  const output=reorderDeck(crlf,[0,2,1,3].map(i=>deck.slides[i].id))
  assert.equal(output.replaceAll('\r\n','').includes('\n'),false)
  const duplicate=source+'\n\n---\n\n# B\n'
  const repeated = inspectDeck(duplicate)
  assert.equal(new Set(repeated.slides.map(s=>s.id)).size,5)
  const moved = reorderDeck(duplicate, [0,4,1,2,3].map(i=>repeated.slides[i].id))
  assert.deepEqual(inspectDeck(moved).slides.map(s=>s.title), ['Cover','B','A','B','C'])
  assert.throws(()=>inspectDeck('---\nsrc: ./pages.md\n---\n'),/导入/)
})
test('HTTP saves atomically, backs up, rejects stale/foreign/invalid requests', async () => {
  const root=await mkdtemp(join(tmpdir(),'slide-sorter-')),file=join(root,'slides.md')
  await writeFile(file,source)
  const server=createServer(createSorterMiddleware(file))
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
  const url=`http://127.0.0.1:${server.address().port}`
  const post=(payload,origin=url)=>fetch(url,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify(payload)})
  try {
    const initial=await(await fetch(url)).json(),order=[0,2,1,3].map(i=>initial.slides[i].id)
    assert.equal('raw' in initial.slides[0],false)
    const response=await post({version:initial.version,order})
    assert.equal(response.status,200)
    const saved=await response.json()
    assert.deepEqual(inspectDeck(await readFile(file,'utf8')).slides.map(s=>s.title),['Cover','B','A','C'])
    const backups=await readdir(join(root,'.slide-order-history'))
    assert.equal(await readFile(join(root,'.slide-order-history',backups[0]),'utf8'),source)
    assert.equal((await post({version:initial.version,order})).status,409)
    assert.equal((await post({version:saved.version,order},'https://example.com')).status,403)
    assert.equal((await post({version:saved.version,order:[]})).status,409)
    await writeFile(file,(await readFile(file,'utf8'))+'\nUser edit\n')
    assert.equal((await post({version:saved.version,order})).status,409)
    assert.match(await readFile(file,'utf8'),/User edit/)
  } finally {await new Promise(resolve=>server.close(resolve));await rm(root,{recursive:true,force:true})}
})

test('note-only edits keep preview identity while invalidating the save version', () => {
  const a = inspectDeck(source), b = inspectDeck(source + '\n<!-- note 1 -->\n<!-- note 2 -->\n')
  assert.notEqual(a.version, b.version)
  assert.notEqual(a.slides.at(-1).id, b.slides.at(-1).id)
  assert.equal(a.slides.at(-1).previewContent, b.slides.at(-1).previewContent)
})


test('insert, duplicate and delete preserve complete blocks and global configuration', () => {
  for (const input of [source, source.replaceAll('\n', '\r\n')]) {
    const before = inspectDeck(input)
    const inserted = modifyDeck(input, { action: 'insert', id: before.slides[1].id })
    const next = inspectDeck(inserted)
    assert.deepEqual(next.slides.map(s => s.title), ['Cover', 'A', '新页面', 'B', 'C'])
    assert.match(next.slides[2].raw, /left-column: 42,100,432,350,0/)
    assert.match(next.slides[2].raw, /<v-drag pos="right-column"/)
    assert.equal(next.slides[0].raw, before.slides[0].raw)
    assert.equal(next.slides[1].raw, before.slides[1].raw)
    assert.equal(modifyDeck(inserted, { action: 'delete', id: next.slides[2].id }), input)
    const twice = inspectDeck(modifyDeck(inserted, { action: 'insert', id: next.slides[2].id }))
    assert.equal(twice.slides[3].title, '新页面 2')
    const copied = inspectDeck(modifyDeck(input, { action: 'duplicate', id: before.slides[1].id }))
    assert.equal(copied.slides[1].raw, before.slides[1].raw)
    assert.equal(copied.slides[2].raw, before.slides[1].raw)
    assert.notEqual(copied.slides[1].id, copied.slides[2].id)
    const lastCopy = inspectDeck(modifyDeck(input, { action: 'duplicate', id: before.slides.at(-1).id }))
    assert.deepEqual(lastCopy.slides.map(s => s.title), ['Cover', 'A', 'B', 'C', 'C'])
    const lastNew = modifyDeck(input, { action: 'insert', id: before.slides.at(-1).id })
    assert.equal(inspectDeck(lastNew).slides.at(-1).title, '新页面')
    if (input.includes('\r\n')) assert.equal(lastNew.replaceAll('\r\n', '').includes('\n'), false)
    assert.throws(() => modifyDeck(input, { action: 'delete', id: before.slides[0].id }), /封面/)
    assert.throws(() => modifyDeck(input, { action: 'duplicate', id: before.slides[0].id }), /封面/)
    assert.throws(() => modifyDeck(input, { action: 'insert', id: 'missing' }), /目标页面/)
    assert.throws(() => modifyDeck(input, { action: 'unknown', id: before.slides[1].id }), /不支持/)
  }
  const coverOnly = '---\ntheme: hitsz-academic\n---\n# Cover'
  const cover = inspectDeck(coverOnly).slides[0]
  const added = modifyDeck(coverOnly, { action: 'insert', id: cover.id })
  const removed = modifyDeck(added, { action: 'delete', id: inspectDeck(added).slides[1].id })
  assert.equal(inspectDeck(removed).slides.length, 1)
  assert.equal(inspectDeck(removed).slides[0].id, cover.id)
})

test('HTTP page mutations share version checks and backup history; retries cannot duplicate twice', async () => {
  const root = await mkdtemp(join(tmpdir(), 'slide-management-')), file = join(root, 'slides.md')
  await writeFile(file, source)
  const server = createServer(createSorterMiddleware(file))
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const url = `http://127.0.0.1:${server.address().port}`
  const post = payload => fetch(url, { method: 'POST', headers: { Origin: url, 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
  try {
    let deck = await (await fetch(url)).json()
    for (const action of ['insert', 'duplicate', 'delete']) {
      const original = await readFile(file, 'utf8')
      const payload = { version: deck.version, action, id: deck.slides[1].id }
      const response = await post(payload)
      assert.equal(response.status, 200)
      const next = await response.json()
      assert.equal(next.slides.length, deck.slides.length + (action === 'delete' ? -1 : 1))
      assert.equal((await post(payload)).status, 409)
      const backups = await readdir(join(root, '.slide-order-history'))
      const content = await Promise.all(backups.map(name => readFile(join(root, '.slide-order-history', name), 'utf8')))
      assert.ok(content.includes(original))
      deck = next
    }
    assert.equal((await post({ version: deck.version, action: 'delete', id: deck.slides[0].id })).status, 400)
    const updated = (await readFile(file, 'utf8')) + '\n<!-- local edit -->\n'
    await writeFile(file, updated)
    assert.equal((await post({ version: deck.version, action: 'insert', id: deck.slides[1].id })).status, 409)
    assert.equal(await readFile(file, 'utf8'), updated)
  } finally {
    await new Promise(resolve => server.close(resolve))
    await rm(root, { recursive: true, force: true })
  }
})


test('thumbnail sync accepts saved drag coordinates while requiring current text and layout', () => {
  const item = { previewContent: '# A', previewFrontmatter: { layout: 'academic', dragPos: { x: '20,30,40,50' } } }
  assert.equal(matchesPreview({ content: '# A', frontmatter: { layout: 'academic', dragPos: { x: '1,2,3,4' } } }, item), true)
  assert.equal(matchesPreview({ content: '# Old', frontmatter: item.previewFrontmatter }, item), false)
  assert.equal(matchesPreview({ content: '# A', frontmatter: { layout: 'cover' } }, item), false)
})
