// Dependency-free HTTP server for the prebuilt, offline presentation.
import { createServer } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { resolve, sep, extname, join } from 'node:path'
import { spawn } from 'node:child_process'
const root = fileURLToPath(new URL('../talks/filtering/dist/', import.meta.url))
const port = Number(process.argv[2] || 3030)
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Port must be 1024-65535')
await stat(join(root, 'index.html')).catch(() => { throw new Error('Missing built slides. Run: npm run build -- filtering') })
const mime = { '.html':'text/html; charset=utf-8', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp', '.gif':'image/gif', '.woff':'font/woff', '.woff2':'font/woff2', '.ttf':'font/ttf', '.pdf':'application/pdf', '.mp4':'video/mp4' }
export const server = createServer(async (req, res) => {
  try {
    if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return }
    const path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
    if (path.includes('\0')) throw new Error('Invalid path')
    let file = resolve(root, '.' + path)
    if (file !== resolve(root) && !file.startsWith(root.endsWith(sep) ? root : root + sep)) { res.writeHead(403); res.end(); return }
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
server.on('error', error => { console.error(error.code === 'EADDRINUSE' ? `Port ${port} is busy. Try: start-presentation.cmd 3031` : error.message); process.exitCode = 1 })
server.listen(port, '127.0.0.1', () => {
  const url = `http://127.0.0.1:${port}/`
  console.log(`Offline presentation: ${url}\nKeep this window open. Ctrl+C stops the server.`)
  if (process.platform === 'win32') spawn('cmd.exe', ['/d', '/c', 'start', '', url], { stdio: 'ignore' }).unref()
})
