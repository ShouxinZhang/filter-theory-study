import { access } from 'node:fs/promises'
import { resolve, relative, isAbsolute } from 'node:path'
import { pathToFileURL } from 'node:url'
import { drawioPlugin } from './drawio.mjs'

// Resolve from Vite's slide directory, never from this shared addon's directory.
export async function loadDiagrams(root) {
  const path = resolve(root, 'drawio.config.mjs')
  try { await access(path) }
  catch (error) { if (error.code === 'ENOENT') return {}; throw error }
  const { default: diagrams } = await import(pathToFileURL(path).href)
  if (!diagrams || typeof diagrams !== 'object' || Array.isArray(diagrams))
    throw new Error('drawio.config.mjs must export an object.')
  for (const [id, paths] of Object.entries(diagrams)) {
    if (!/^[a-zA-Z0-9_-]+$/.test(id) || !paths?.source || !paths?.preview)
      throw new Error(`Diagram ${id}: provide source and preview paths.`)
    for (const path of Object.values(paths)) {
      if (typeof path !== 'string') throw new Error(`Diagram ${id}: paths must be strings.`)
      const local = relative(root, resolve(root, path))
      if (isAbsolute(local) || local === '..' || local.startsWith('../'))
        throw new Error(`Diagram ${id}: keep diagram files inside this talk.`)
    }
  }
  return diagrams
}

export function talkDrawioPlugin() {
  let delegate
  return {
    name: 'academic-talk-drawio-config',
    async config(config) {
      const root = resolve(config.root || process.cwd())
      delegate = drawioPlugin(root, await loadDiagrams(root))
      return delegate.config()
    },
    configureServer(server) { return delegate.configureServer(server) },
  }
}
