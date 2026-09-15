// Slidev 52.19.1: drag patches update frontmatterDoc but leave frontmatterRaw stale.
// The side editor reads frontmatterRaw and can overwrite freshly dragged coordinates.
// Keep the serialized frontmatter synchronized in the dev server's save handler.
import { readFile, readdir, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
const packagePath = require.resolve('@slidev/cli/package.json')
const pkg = JSON.parse(await readFile(packagePath, 'utf8'))
if (pkg.version !== '52.19.1')
  throw new Error(`Review the editor workaround for Slidev ${pkg.version}; expected 52.19.1.`)
const dir = join(dirname(packagePath), 'dist')
const files = (await readdir(dir)).filter(name => /^serve-.*\.mjs$/.test(name))
const marker = '// academic-template: synchronize raw frontmatter after dragging'
const anchor = '\t\t\t\t\tparser.prettifySlide(slide.source);'
let found = 0
for (const file of files) {
  const path = join(dir, file)
  const source = await readFile(path, 'utf8')
  if (source.includes(marker)) { found++; continue }
  const occurrences = source.split(anchor).length - 1
  if (!occurrences) continue
  if (occurrences !== 1) throw new Error(`Ambiguous patch anchor in ${file}`)
  const patch = `${anchor}\n\t\t\t\t\t${marker}\n\t\t\t\t\tslide.frontmatterRaw = slide.source.frontmatterRaw = slide.source.frontmatterDoc?.toString() || "";`
  await writeFile(path, source.replace(anchor, patch))
  found++
}
if (found !== 1) throw new Error(`Expected one save handler, found ${found}`)
console.log('Slidev 52.19.1 side-editor coordinate synchronization patch ready.')

// Keep this version-pinned workaround reproducible after npm install.
const clientDir = dirname(require.resolve('@slidev/client/package.json'))
const editorPath = join(clientDir, 'internals/SideEditor.vue')
let editor = await readFile(editorPath, 'utf8')
const clientMarker = '// academic-template: focused editor synchronization and conflict handling'
if (!editor.includes(clientMarker)) {
  const start = editor.indexOf("const tab = ref<'content' | 'note'>('content')")
  const end = editor.indexOf('function close() {', start)
  if (start < 0 || end < 0) throw new Error('SideEditor patch anchor changed')
  const replacement = await readFile(new URL('./patches/side-editor-sync.ts', import.meta.url), 'utf8')
  editor = editor.slice(0, start) + clientMarker + '\n' + replacement + editor.slice(end)
  editor = editor.replace('activeElement, editorHeight, editorWidth, isInputting, showEditor', 'activeElement, editorHeight, editorWidth, showEditor')
  editor = editor.replace('grid-rows-[max-content_1fr]', 'grid-rows-[max-content_max-content_1fr]')
  const alertAnchor = '    <div class="relative overflow-hidden rounded"'
  if (!editor.includes(alertAnchor)) throw new Error('Editor alert anchor changed')
  editor = editor.replace(alertAnchor, `    <div v-if="saveError" role="alert" style="font-size: 14px; color: #991b1b; background: #fef2f2; padding: 10px; margin-bottom: 8px;">
      {{ saveError }} 当前草稿仍保留在编辑框中，可先复制保存。
      <button type="button" style="text-decoration: underline; display: block; margin-top: 6px;" @click="reloadEditor">放弃当前草稿，载入本地文件</button>
    </div>
    <div v-else />
` + alertAnchor)
  await writeFile(editorPath, editor)
}
const infoPath = join(clientDir, 'composables/useSlideInfo.ts')
let infoSource = await readFile(infoPath, 'utf8')
const errorMarker = '// academic-template: surface rejected saves without replacing editor state'
if (!infoSource.includes(errorMarker)) {
  const anchor = ').then(r => r.json())'
  if (!infoSource.includes(anchor)) throw new Error('useSlideInfo patch anchor changed')
  infoSource = infoSource.replace(anchor, `).then(async (r) => {
      ${errorMarker}
      const result = await r.json()
      if (!r.ok) throw new Error(result.error || '保存失败，请复制草稿后重新载入。')
      return result
    })`)
  await writeFile(infoPath, infoSource)
}
for (const file of files) {
  const path = join(dir, file)
  let source = await readFile(path, 'utf8')
  const guardMarker = '// academic-template: reject stale side-editor saves'
  if (source.includes(guardMarker)) continue
  const anchor = '\t\t\t\t\tconst slide = data.slides[idx];'
  if (!source.includes(anchor)) continue
  source = source.replace(anchor, anchor + `
                    ${guardMarker}
                    if (body.expectedSource != null) {
                        const version = JSON.stringify([slide.source.content?.trim() || "", slide.frontmatterRaw?.trim() || "", slide.note?.trim() || ""]);
                        const disk = await readFile(slide.source.filepath, "utf-8");
                        if (body.expectedSource !== version || disk !== data.markdownFiles[slide.source.filepath].raw) {
                            res.statusCode = 409;
                            res.setHeader("Content-Type", "application/json");
                            return res.end(JSON.stringify({ error: "本地 Markdown 已更新，已阻止旧内容覆盖。" }));
                        }
                    }
`)
  const savedAnchor = '\t\t\t\t\tconst fileContent = await parser.save(data.markdownFiles[slide.source.filepath]);'
  if (!source.includes(savedAnchor)) throw new Error('Save result anchor changed')
  source = source.replace(savedAnchor, savedAnchor + '\n\t\t\t\t\tdata.markdownFiles[slide.source.filepath].raw = fileContent;\n\t\t\t\t\tslide.source.contentRaw = slide.source.content;')
  await writeFile(path, source)
}
console.log('Side-editor external-change synchronization and stale-save guard ready.')

// Page count changes can resurrect cached source modules for reused page numbers.
for (const file of files) {
  const path = join(dir, file)
  let source = await readFile(path, 'utf8')
  const countMarker = '// academic-template: refresh page modules after structural edits'
  if (source.includes(countMarker)) continue
  const anchor = '\t\t\tif (data.slides.length !== newData.slides.length) moduleIds.add(templateSlides.id);'
  if (!source.includes(anchor)) continue
  source = source.replace(anchor, `\t\t\t${countMarker}
            const academicPageCountChanged = data.slides.length !== newData.slides.length;
            if (academicPageCountChanged) moduleIds.add(templateSlides.id);`)
  const resultAnchor = '\t\t\tupdateServerWatcher();\n\t\t\treturn moduleEntries;'
  if (!source.includes(resultAnchor)) throw new Error('Slide loader HMR result anchor changed')
  source = source.replace(resultAnchor, `\t\t\tupdateServerWatcher();
            if (academicPageCountChanged) {
                ctx.server.moduleGraph.invalidateAll();
                ctx.server.hot.send({ type: "full-reload" });
                return [];
            }
            return moduleEntries;`)
  await writeFile(path, source)
}
console.log('Slide module refresh after page count changes ready.')
