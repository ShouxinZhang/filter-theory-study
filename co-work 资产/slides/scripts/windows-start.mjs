import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'
const root = fileURLToPath(new URL('../', import.meta.url))
const [talk = 'filtering', ...args] = process.argv.slice(2)
if (!/^[a-z0-9][a-z0-9_-]*$/.test(talk)) throw new Error('Invalid talk name')
const [major, minor] = process.versions.node.split('.').map(Number)
if (major < 20 || (major === 20 && minor < 12)) throw new Error('Node.js >=20.12 required; this bundle was tested with Node.js 24.')
if (!existsSync(join(root, 'node_modules/@slidev/cli/package.json'))) {
  console.log('Installing dependencies from package-lock.json (internet required on first run)...')
  const install = spawnSync(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['ci'], {
    cwd: root, stdio: 'inherit', shell: process.platform === 'win32',
    env: { ...process.env, PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD: '1' },
  })
  if (install.error || install.status !== 0) process.exit(install.status || 1)
}
if (/^\d+$/.test(args[0] || '')) args.splice(0, 1, '--port', args[0])
const run = spawnSync(process.execPath, [join(root, 'scripts/talk.mjs'), 'dev', talk, '--open', ...args], { cwd: root, stdio: 'inherit' })
process.exitCode = run.status ?? 1
