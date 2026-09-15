import { spawn } from 'node:child_process'
import { access } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'

const root = fileURLToPath(new URL('../', import.meta.url))
const [action = 'dev', ...options] = process.argv.slice(2)
const name = options[0] && !options[0].startsWith('-') ? options.shift() : 'filtering'
if (!['dev', 'build', 'pdf', 'pptx'].includes(action) || !/^[a-z0-9][a-z0-9_-]*$/.test(name)) {
  console.error('Usage: node scripts/talk.mjs <dev|build|pdf|pptx> [talk-name] [Slidev options]')
  process.exit(1)
}
const cwd = join(root, 'talks', name)
try { await access(join(cwd, 'slides.md')) }
catch { console.error(`找不到汇报 ${name}。新建：npm run new -- ${name}`); process.exit(1) }
const commands = {
  dev: ['slides.md', '--port', '3030'],
  build: ['build', 'slides.md', '--out', 'dist'],
  pdf: ['export', 'slides.md', '--output', 'output/academic.pdf'],
  pptx: ['export', 'slides.md', '--format', 'pptx', '--with-clicks', 'false', '--output', 'output/academic.pptx'],
}
// A caller-specified port replaces the default rather than producing duplicate flags.
if (action === 'dev' && options.some(option => option === '--port' || option.startsWith('--port=')))
  commands.dev = ['slides.md']
const child = spawn(process.execPath, [join(root, 'scripts/slidev.mjs'), ...commands[action], ...options], { cwd, stdio: 'inherit' })
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal))
child.on('error', error => { console.error(error.message); process.exitCode = 1 })
child.on('exit', (code, signal) => { process.exitCode = code ?? (signal === 'SIGINT' ? 130 : 1) })
