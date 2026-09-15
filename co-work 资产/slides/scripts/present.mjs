// Offline presentation: bundled Node + Windows Edge, with no npm dependencies.
import { createServer } from 'node:http'
import { readFile, stat, mkdtemp, rm } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { resolve, sep, extname, join } from 'node:path'
import { tmpdir } from 'node:os'
import { spawn } from 'node:child_process'

const defaultRoot = fileURLToPath(new URL('../talks/filtering/dist/', import.meta.url))
const mime = { '.html':'text/html; charset=utf-8', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp', '.gif':'image/gif', '.woff':'font/woff', '.woff2':'font/woff2', '.ttf':'font/ttf', '.pdf':'application/pdf', '.mp4':'video/mp4', '.wasm':'application/wasm' }

export function createPresentationServer(directory) {
  const root = resolve(directory)
  return createServer(async (req, res) => {
    try {
      if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return }
      const path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
      if (path.includes('\0')) throw new Error('Invalid path')
      let file = resolve(root, '.' + path)
      if (file !== root && !file.startsWith(root + sep)) { res.writeHead(403); res.end(); return }
      try { if ((await stat(file)).isDirectory()) file = join(file, 'index.html') }
      catch {
        if (!extname(path)) file = join(root, 'index.html')
        else { res.writeHead(404); res.end('Not found'); return }
      }
      const body = await readFile(file)
      res.writeHead(200, { 'Content-Type': mime[extname(file)] || 'application/octet-stream', 'Content-Length': body.length, 'Cache-Control': 'no-cache' })
      res.end(req.method === 'HEAD' ? undefined : body)
    } catch { res.writeHead(400); res.end('Bad request') }
  })
}

export async function startPresentation({ root = defaultRoot, port = 0, openBrowser = true } = {}) {
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('Invalid port')
  await stat(join(root, 'index.html')).catch(() => { throw new Error('Missing slides. Extract the complete ZIP before starting.') })
  const server = createPresentationServer(root)
  await new Promise((ok, fail) => {
    function onError(error) {
      // Never ask a presenter to diagnose or choose a free port.
      if (error.code === 'EADDRINUSE' && port !== 0) { server.listen(0, '127.0.0.1'); return }
      fail(error)
    }
    server.on('error', onError)
    server.once('listening', () => { server.off('error', onError); ok() })
    server.listen(port, '127.0.0.1')
  })
  const url = `http://127.0.0.1:${server.address().port}/1`
  console.log(`Offline presentation: ${url}\nUse arrow keys to change slides. Alt+F4 closes the presentation.`)
  if (openBrowser && process.platform === 'win32') await openWindowsBrowser(url, server)
  return { server, url }
}

async function openWindowsBrowser(url, server) {
  const edge = [process.env['ProgramFiles(x86)'], process.env.ProgramFiles, process.env.LOCALAPPDATA]
    .filter(Boolean).map(base => join(base, 'Microsoft/Edge/Application/msedge.exe')).find(existsSync)
  const fallback = () => {
    const launcher = spawn(join(process.env.SystemRoot || 'C:\\Windows', 'System32/rundll32.exe'), ['url.dll,FileProtocolHandler', url], { stdio: 'ignore' })
    launcher.on('error', error => console.error(`Cannot open browser automatically: ${error.message}\n${url}`))
    console.log('Keep this command window open while presenting; close it when finished.')
  }
  if (!edge) { fallback(); return }
  // An isolated temporary profile avoids handing the URL to a pre-existing Edge
  // process, makes full-screen launch reliable and lets us stop when it closes.
  const profile = await mkdtemp(join(tmpdir(), 'slidev-offline-'))
  const child = spawn(edge, [
    '--kiosk', url, '--edge-kiosk-type=fullscreen', '--no-first-run',
    '--no-default-browser-check', '--disable-background-networking',
    `--user-data-dir=${profile}`,
  ], { stdio: 'ignore' })
  let failed = false
  child.once('error', () => { failed = true; fallback() })
  child.once('exit', async (code) => {
    if (failed) return
    if (code !== 0 && code !== null) { fallback(); return }
    server.close()
    await rm(profile, { recursive: true, force: true }).catch(() => {})
  })
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  startPresentation({ port: Number(process.argv[2] || 0) }).catch(error => { console.error(error.message); process.exitCode = 1 })
}
