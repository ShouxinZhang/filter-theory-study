import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtemp, writeFile, mkdir, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { startPresentation } from '../scripts/present.mjs'

test('offline launch serves slides/assets without dependencies, and automatically avoids an occupied port', async () => {
  const root = await mkdtemp(join(tmpdir(), 'slidev 中文 portable '))
  let first, second
  try {
    await writeFile(join(root, 'index.html'), '<html>offline talk</html>')
    await mkdir(join(root, 'images'))
    await writeFile(join(root, 'images/photo.png'), Buffer.from([137,80,78,71]))
    first = await startPresentation({ root, openBrowser: false })
    const port = first.server.address().port
    second = await startPresentation({ root, port, openBrowser: false })
    assert.notEqual(second.server.address().port, port)
    assert.match(await (await fetch(second.url)).text(), /offline talk/)
    const base = new URL('/', second.url)
    assert.equal((await fetch(new URL('/13', base))).status, 200)
    const image = await fetch(new URL('/images/photo.png', base))
    assert.equal(image.headers.get('content-type'), 'image/png')
    assert.deepEqual(Buffer.from(await image.arrayBuffer()), Buffer.from([137,80,78,71]))
    assert.equal((await fetch(new URL('/missing.js', base))).status, 404)
    assert.equal((await fetch(new URL('/%ZZ', base))).status, 400)
    assert.equal((await fetch(base, {method:'POST'})).status, 405)
  } finally {
    for (const result of [first, second]) if (result) {
      result.server.closeAllConnections()
      await new Promise(resolve => result.server.close(resolve))
    }
    await rm(root, {recursive:true, force:true})
  }
})
