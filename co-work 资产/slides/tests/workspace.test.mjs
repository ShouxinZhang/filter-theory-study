import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtemp, mkdir, cp, readFile, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createTalk } from '../scripts/new-talk.mjs'
import { loadDiagrams } from '../packages/addon-drawio/server/config.mjs'

test('new talks share code but own content; existing talks cannot be overwritten', async () => {
  const root = await mkdtemp(join(tmpdir(), 'academic-workspace-'))
  try {
    await mkdir(join(root, 'scaffolds'))
    await cp(new URL('../scaffolds/talk', import.meta.url), join(root, 'scaffolds/talk'), { recursive: true })
    const a = await createTalk(root, 'talk-a'), b = await createTalk(root, 'talk-b')
    assert.match(await readFile(join(a, 'slides.md'), 'utf8'), /theme: hitsz-academic/)
    await writeFile(join(a, 'slides.md'), 'user edits')
    await assert.rejects(createTalk(root, 'talk-a'), { code: 'EEXIST' })
    assert.equal(await readFile(join(a, 'slides.md'), 'utf8'), 'user edits')
    assert.match(await readFile(join(b, 'slides.md'), 'utf8'), /title: talk-b/)
    await assert.rejects(createTalk(root, '../escape'))
    assert.deepEqual(await loadDiagrams(a), {})
  } finally { await rm(root, { recursive: true, force: true }) }
})

test('diagram config is resolved per talk; paths outside the talk are rejected', async () => {
  const root = await mkdtemp(join(tmpdir(), 'academic-diagram-config-'))
  try {
    for (const name of ['a', 'b', 'invalid', 'empty']) await mkdir(join(root, name))
    for (const name of ['a', 'b']) {
      await writeFile(join(root, name, 'drawio.config.mjs'), `export default { flow: { source: '${name}.drawio', preview: '${name}.svg' } }`)
      assert.equal((await loadDiagrams(join(root, name))).flow.source, `${name}.drawio`)
    }
    await writeFile(join(root, 'invalid/drawio.config.mjs'), "export default { flow: { source: '../a/a.drawio', preview: 'x.svg' } }")
    await assert.rejects(loadDiagrams(join(root, 'invalid')), /inside this talk/)
    assert.deepEqual(await loadDiagrams(join(root, 'empty')), {})
  } finally { await rm(root, { recursive: true, force: true }) }
})
