import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtemp, readFile, writeFile, readdir, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createServer } from 'node:http'
import { inspectPage, decodeImages, insertImages, createImageMiddleware } from '../server/images.mjs'
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jA1sAAAAASUVORK5CYII='
const image = { type: 'image/png', data: png }
const source = '---\ntheme: hitsz-academic\n---\n# Cover\n\n---\nlayout: academic\ndragPos:\n  a: 1,2,3,4\n---\n# Results\n\n$$x^2$$\n\n```md\n---\nfence\n```\n\n<!-- speaker notes -->\n\n---\n# Thanks'
test('inserted image is a draggable Markdown block; other pages, frontmatter and notes survive', () => {
  for (const input of [source, source.replaceAll('\n', '\r\n')]) {
    const images = decodeImages([image, image], [980, 552])
    assert.notEqual(images[0].url, images[1].url)
    assert.deepEqual(images[0].bytes, Buffer.from(png, 'base64'))
    const result = insertImages(input, 2, images.map(i => i.markdown).join('\n\n'))
    const before = inspectPage(input, 2), after = inspectPage(result, 2)
    assert.equal(after.deck.slides.length, 3)
    assert.equal(after.slide.note, before.slide.note)
    assert.deepEqual(after.slide.frontmatter, before.slide.frontmatter)
    assert.equal(inspectPage(result, 1).raw, inspectPage(input, 1).raw)
    assert.equal(inspectPage(result, 3).raw, inspectPage(input, 3).raw)
    assert.match(after.raw, /<v-drag id="pasted-/)
    assert.ok(after.raw.indexOf(images[0].url) < after.raw.indexOf('<!-- speaker notes -->'))
    if (input.includes('\r\n')) assert.equal(result.replaceAll('\r\n', '').includes('\n'), false)
    const tail = insertImages(input, 3, images[0].markdown)
    assert.equal(inspectPage(tail, 3).deck.slides.length, 3)
  }
})
test('reject invalid formats, excessive batches, dimensions and unsupported deck structures', () => {
  assert.throws(() => decodeImages([{ ...image, type: 'image/svg+xml' }], [980, 552]), /支持/)
  assert.throws(() => decodeImages([{ ...image, data: 'bad' }], [980, 552]), /无效|无法读取/)
  assert.throws(() => decodeImages(Array(6).fill(image), [980, 552]), /1–5/)
  assert.throws(() => decodeImages([image], [NaN, 552]), /尺寸/)
  assert.throws(() => inspectPage('---\nsrc: ./other.md\n---\n', 1), /导入/)
  assert.throws(() => inspectPage(source, 99), /页面/)
})
test('upload and Markdown save are versioned, backed up and isolated per talk; editor mode only stores assets', async () => {
  const root = await mkdtemp(join(tmpdir(), 'slide-images-')), file = join(root, 'slides.md')
  await writeFile(file, source)
  const server = createServer(createImageMiddleware(root))
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const url = `http://127.0.0.1:${server.address().port}`
  const post = (payload, origin = url) => fetch(url, { method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
  try {
    let snapshot = await (await fetch(`${url}/?page=2`)).json()
    const payload = { ...snapshot, mode: 'slide', page: 2, canvas: [980, 552], images: [image] }
    assert.equal((await post(payload, 'https://example.com')).status, 403)
    const saved = await post(payload)
    assert.equal(saved.status, 200)
    const data = await saved.json()
    assert.match(await readFile(file, 'utf8'), /class="pasted-image"/)
    assert.deepEqual(await readFile(join(root, 'public', data.images[0].url)), Buffer.from(png, 'base64'))
    const backups = await readdir(join(root, '.image-paste-history'))
    assert.equal(await readFile(join(root, '.image-paste-history', backups[0]), 'utf8'), source)
    assert.equal((await post(payload)).status, 409)
    assert.equal((await readdir(join(root, 'public/images'))).length, 1)
    snapshot = await (await fetch(`${url}/?page=2`)).json()
    const original = await readFile(file, 'utf8')
    assert.equal((await post({ ...payload, ...snapshot, mode: 'editor' })).status, 200)
    assert.equal(await readFile(file, 'utf8'), original)
    assert.equal((await readdir(join(root, 'public/images'))).length, 2)
    assert.equal((await post({ ...payload, ...snapshot, content: '# Stale page' })).status, 409)
    assert.equal((await post({ ...payload, ...snapshot, images: [{ ...image, type: 'image/svg+xml' }] })).status, 415)
    assert.equal((await readdir(join(root, 'public/images'))).length, 2)
  } finally { await new Promise(resolve => server.close(resolve)); await rm(root, { recursive: true, force: true }) }
})
