// Use an isolated talk: this regression test intentionally edits its Markdown.
import assert from 'node:assert/strict'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { chromium } from 'playwright-chromium'
const file = process.env.SLIDEV_TEST_FILE
const url = process.env.SLIDEV_TEST_URL
if (!file || !url) throw new Error('Set SLIDEV_TEST_FILE and SLIDEV_TEST_URL to an isolated filtering talk copy.')
const original = await readFile(file, 'utf8')
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(predicate) {
  for (let i = 0; i < 100; i++) {
    if (await predicate()) return
    await pause(100)
  }
  throw new Error('Timed out waiting for editor/file synchronization')
}
const output = 'validation/editor-sync'
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ headless: true })
let page
try {
  const starting = original.replaceAll('\\bm', '\\mathbf')
  await writeFile(file, starting)
  page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto(`${url}/6`)
  await page.getByTitle('Show editor', { exact: true }).click()
  const editor = page.getByPlaceholder('Create slide content...')
  await until(async () => (await editor.inputValue()).includes('\\mathbf'))
  await editor.click()
  await writeFile(file, starting.replaceAll('\\mathbf', '\\bm'))
  await until(async () => !(await editor.inputValue()).includes('\\mathbf'))
  assert.equal(await editor.evaluate(e => e === document.activeElement), true)
  await editor.fill((await editor.inputValue()).replace('固定边缘时', '固定边缘时（网页编辑）'))
  await until(async () => (await readFile(file, 'utf8')).includes('固定边缘时（网页编辑）'))
  assert.equal((await readFile(file, 'utf8')).includes('\\mathbf'), false)
  await page.screenshot({ path: `${output}/focused-fixed.png` })

  // Hold a normal user save while another editor changes the same source.
  let held
  await page.route('**/__slidev/slides/6.json', async route => {
    if (route.request().method() === 'POST') held = route
    else await route.continue()
  })
  await editor.fill((await editor.inputValue()).replace('固定边缘时（网页编辑）', '固定边缘时（未保存的网页草稿）'))
  await until(() => Boolean(held))
  const external = (await readFile(file, 'utf8')).replace('固定边缘时（网页编辑）', '固定边缘时（本地文件修改）')
  await writeFile(file, external)
  await held.continue()
  await page.getByRole('alert').waitFor()
  assert.match(await page.getByRole('alert').innerText(), /已阻止旧内容覆盖/)
  assert.equal(await readFile(file, 'utf8'), external)
  assert.match(await editor.inputValue(), /未保存的网页草稿/)
  await page.screenshot({ path: `${output}/conflict.png` })
  await page.unroute('**/__slidev/slides/6.json')
  await page.getByRole('button', { name: '放弃当前草稿，载入本地文件' }).click()
  await until(async () => (await editor.inputValue()).includes('本地文件修改'))
  await editor.fill((await editor.inputValue()).replace('本地文件修改', '恢复后继续编辑'))
  await until(async () => (await readFile(file, 'utf8')).includes('恢复后继续编辑'))
  assert.equal(await page.getByRole('alert').count(), 0)
  await page.reload()
  await until(async () => (await editor.inputValue()).includes('恢复后继续编辑'))
  assert.equal((await editor.inputValue()).includes('\\mathbf'), false)

  // Notes edits must not restore a cached body, either.
  await page.getByTitle('Switch to notes tab', { exact: true }).click()
  const notes = page.getByPlaceholder('Write some notes...')
  await notes.fill('备注编辑同步测试')
  await until(async () => (await readFile(file, 'utf8')).includes('备注编辑同步测试'))
  assert.equal((await readFile(file, 'utf8')).includes('\\mathbf'), false)
  await page.getByTitle('Switch to content tab', { exact: true }).click()
  await page.setViewportSize({ width: 1024, height: 768 })
  await page.screenshot({ path: `${output}/fixed-tablet.png` })
  await writeFile(`${output}/results.json`, JSON.stringify({
    focusedExternalSync: true, editingPreservesBm: true, staleSaveRejected: true,
    draftRetained: true, reloadAndResume: true, refreshPersistence: true,
    notesPreserveBody: true,
  }, null, 2))
  console.log('PASS: focused external update; stale-save conflict; recovery; reload; notes preserve bm')
}
finally {
  await browser.close()
  await writeFile(file, original)
}
