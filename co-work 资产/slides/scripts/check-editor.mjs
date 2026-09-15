// Run only against this starter's demo server, without concurrent editing.
import assert from 'node:assert/strict'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { chromium } from 'playwright-chromium'
if (!process.env.SLIDEV_TEST_FILE || !process.env.SLIDEV_TEST_URL) throw new Error('Set SLIDEV_TEST_FILE and SLIDEV_TEST_URL to an isolated test talk and server.')
const file = process.env.SLIDEV_TEST_FILE
const original = await readFile(file, 'utf8')
const pos = text => text.match(/density-findings: (.*)/)?.[1].split(',').map(Number).slice(0, 4)
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(predicate) {
  for (let i = 0; i < 60; i++) { if (await predicate()) return; await pause(100) }
  throw new Error('Timed out waiting for the source file to update')
}
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto(`${process.env.SLIDEV_TEST_URL}/8`)
  await page.locator('.slidev-layout:visible [data-drag-id="density-findings"]').dblclick()
  const box = await page.locator('#drag-control-container').boundingBox()
  const x = box.x + box.width / 2, y = box.y + box.height / 2
  await page.mouse.move(x, y)
  await page.mouse.down()
  await page.mouse.move(x - 30, y + 15, { steps: 8 })
  await page.mouse.up()
  let dragged
  await until(async () => {
    const candidate = await readFile(file, 'utf8')
    // Slidev can briefly truncate the file while writing; that is not a saved position.
    if (!pos(candidate) || JSON.stringify(pos(candidate)) === JSON.stringify(pos(original))) return false
    dragged = candidate
    return true
  })
  await page.mouse.click(180, 140)
  await page.getByTitle('Show editor', { exact: true }).click()
  const editor = page.getByPlaceholder('Create slide content...')
  const content = await editor.inputValue()
  assert.deepEqual(pos(content), pos(dragged), 'Editor must see the saved drag coordinates')
  const updated = content.replace('# 后验形状与串行计算代价', '# 后验形状与串行计算代价（编辑验证）')
  assert.notEqual(updated, content, 'Expected demo text to be present')
  await editor.fill(updated)
  await until(async () => (await readFile(file, 'utf8')).includes('后验形状与串行计算代价（编辑验证）'))
  const edited = await readFile(file, 'utf8')
  assert.deepEqual(pos(edited), pos(dragged), 'Editing prose must preserve the dragged layout')
  await page.getByTitle('Hide editor', { exact: true }).click()
  await page.reload()
  const style = await page.locator('.slidev-layout:visible [data-drag-id="density-findings"]').getAttribute('style')
  assert.ok(style.includes(`left: ${pos(dragged)[0]}px`))
  await mkdir('output/qa', { recursive: true })
  await page.screenshot({ path: 'output/qa/editor-regression.png' })
  await writeFile('output/qa/editor-regression.json', JSON.stringify({
    passed: true, initial: pos(original), dragged: pos(dragged), editor: pos(content), afterEdit: pos(edited), afterReload: style,
  }, null, 2))
  console.log('PASS: drag -> editor text change -> source persistence -> reload')
} finally {
  await browser.close()
  await writeFile(file, original)
}
