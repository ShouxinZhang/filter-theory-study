// Run against an isolated copy of the filtering talk; never the live talk.
import assert from 'node:assert/strict'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { chromium } from 'playwright-chromium'
import { inspectDeck } from '../packages/addon-slide-sorter/server/sorter.mjs'
const file = process.env.SLIDEV_TEST_FILE, url = process.env.SLIDEV_TEST_URL
if (!file || !url) throw new Error('Set SLIDEV_TEST_FILE and SLIDEV_TEST_URL to an isolated filtering copy.')
const original = await readFile(file, 'utf8'), output = 'validation/page-management'
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.setDefaultTimeout(15000)
const errors = []
page.on('pageerror', error => { if (!error.message.includes('Wake Lock')) errors.push(error.message) })
const add = () => page.getByRole('button', { name: '＋ 新增页', exact: true })
const read = async () => inspectDeck(await readFile(file, 'utf8'))
async function until(predicate) {
  for (let i = 0; i < 200; i++) {
    try { if (await predicate()) return } catch {}
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  throw new Error('Timeout waiting for saved page management state')
}
async function ready(count) {
  await until(async () => await page.locator('.sorter-card').count() === count && await add().isEnabled())
}
try {
  await mkdir(output, { recursive: true })
  const initial = await read(), count = initial.slides.length
  await page.goto(`${url}/6`)
  await page.getByRole('button', { name: '页面排序', exact: true }).click()
  await ready(count)
  assert.equal(await page.getByRole('button', { name: '删除第 1 页', exact: true }).isDisabled(), true)
  assert.equal(await page.getByRole('button', { name: '复制第 1 页', exact: true }).isDisabled(), true)
  await page.getByRole('button', { name: '选择第 1 页', exact: true }).click()
  await add().click()
  await ready(count + 1)
  assert.equal(new URL(page.url()).pathname, '/2')
  assert.equal((await read()).slides[1].title, '新页面')
  await page.screenshot({ path: `${output}/inserted.png` })
  await page.getByRole('button', { name: '复制第 2 页', exact: true }).click()
  await ready(count + 2)
  assert.equal(new URL(page.url()).pathname, '/3')
  assert.equal((await read()).slides[1].raw, (await read()).slides[2].raw)
  const beforeCancel = await readFile(file, 'utf8')
  page.once('dialog', dialog => dialog.dismiss())
  await page.getByRole('button', { name: '删除第 3 页', exact: true }).click()
  assert.equal(await readFile(file, 'utf8'), beforeCancel)
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: '删除第 3 页', exact: true }).click()
  await ready(count + 1)
  assert.equal(new URL(page.url()).pathname, '/3')
  assert.equal((await read()).slides[2].title, initial.slides[1].title)
  await page.getByRole('button', { name: '前移第 3 页', exact: true }).click()
  await until(async () => (await read()).slides[1].title === initial.slides[1].title && await add().isEnabled())
  assert.equal(new URL(page.url()).pathname, '/2')
  await page.getByRole('button', { name: '后移第 2 页', exact: true }).click()
  await until(async () => (await read()).slides[1].title === '新页面' && await add().isEnabled())
  await page.getByRole('button', { name: '关闭', exact: true }).click()
  await page.goto(`${url}/2`)
  await page.getByTitle('Show editor', { exact: true }).click()
  const editor = page.getByPlaceholder('Create slide content...')
  await until(async () => (await editor.inputValue()).includes('left-column'))
  await editor.fill((await editor.inputValue()).replaceAll('新页面', '网页创建与编辑验证'))
  await until(async () => (await read()).slides[1].title === '网页创建与编辑验证')
  await page.getByTitle('Hide editor', { exact: true }).click()
  await page.getByRole('button', { name: '页面排序', exact: true }).click()
  await ready(count + 1)
  // The new page remains draggable, and its saved positions reach thumbnails.
  await page.getByRole('button', { name: '关闭', exact: true }).click()
  await page.locator('.slidev-layout:visible [data-drag-id="left-column"]').dblclick()
  const box = await page.locator('#drag-control-container').boundingBox()
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2 + 40, box.y + box.height / 2 + 25, { steps: 10 })
  await page.mouse.up()
  await until(async () => (await read()).slides[1].previewFrontmatter.dragPos['left-column'] !== '42,100,432,350,0')
  const draggedX = (await read()).slides[1].previewFrontmatter.dragPos['left-column'].split(',')[0]
  await page.mouse.click(30, 30)
  await page.getByRole('button', { name: '页面排序', exact: true }).click()
  await ready(count + 1)
  assert.match(await page.locator('[data-sort-index="1"] [data-drag-id="left-column"]').getAttribute('style'), new RegExp(`left: ${draggedX}px`))
  const from = await page.locator('[data-sort-index="2"]').boundingBox()
  const to = await page.locator('[data-sort-index="1"]').boundingBox()
  await page.mouse.move(from.x + 130, from.y + 60)
  await page.mouse.down()
  await page.mouse.move(to.x + 15, to.y + 60, { steps: 15 })
  await page.mouse.up()
  await until(async () => (await read()).slides[1].title === initial.slides[1].title && await add().isEnabled())
  await page.getByRole('button', { name: '前移第 3 页', exact: true }).click()
  await until(async () => (await read()).slides[1].title === '网页创建与编辑验证' && await add().isEnabled())
  // External changes while the panel is open must be protected.
  const external = (await readFile(file, 'utf8')) + '\n<!-- external management test -->\n'
  await writeFile(file, external)
  await add().click()
  await page.getByRole('alert').waitFor()
  assert.equal(await readFile(file, 'utf8'), external)
  await page.screenshot({ path: `${output}/conflict.png` })
  await page.getByRole('button', { name: '重新加载', exact: true }).click()
  await ready(count + 1)
  // A failed request can be retried exactly once without adding extra pages.
  await page.route('**/__slide_order', async route => {
    if (route.request().method() === 'POST') await route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":"测试保存失败"}' })
    else await route.continue()
  })
  await add().click()
  await page.getByRole('alert').waitFor()
  assert.equal((await read()).slides.length, count + 1)
  await page.unroute('**/__slide_order')
  await page.getByRole('button', { name: '重试保存', exact: true }).click()
  await ready(count + 2)
  await page.reload()
  await ready(count + 2)
  assert.equal((await read()).slides[0].raw, initial.slides[0].raw)
  assert.equal((await read()).slides.at(-1).title, initial.slides.at(-1).title)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: `${output}/narrow.png` })
  const rect = await add().boundingBox()
  assert.ok(rect.x >= 0 && rect.x + rect.width <= 390)
  await page.setViewportSize({ width: 1024, height: 768 })
  await page.screenshot({ path: `${output}/tablet.png` })
  await page.keyboard.press('Escape')
  assert.equal(await page.getByRole('dialog').count(), 0)
  assert.deepEqual(errors, [])
  await writeFile(`${output}/results.json`, JSON.stringify({ insert: true, duplicate: true, cancelDelete: true, deleteActive: true, moveCurrent: true, editNewPage: true, dragNewPage: true, savedDragPreview: true, mouseReorder: true, conflict: true, retry: true, refreshPersistence: true, coverProtected: true, thanksPreserved: true, narrow: true, tablet: true }, null, 2))
  console.log('PASS: page creation, copying, deletion, editing, reordering, conflicts, retry, reload and responsive controls')
} finally {
  await browser.close()
  await writeFile(file, original)
}
