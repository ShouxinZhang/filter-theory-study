// Run Slidev as a CLI even when this shell inherits VS Code extension variables.
// UnoCSS 66.10.1 treats VSCODE_CWD as an extension-host marker and skips its
// Node icon loader, leaving toolbar buttons clickable but their icons empty.
// Only this process is affected; the parent editor environment is unchanged.
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const require = createRequire(import.meta.url)
const packagePath = require.resolve('@slidev/cli/package.json')
const { bin } = require(packagePath)
const entry = resolve(dirname(packagePath), bin.slidev)
delete process.env.VSCODE_CWD
process.argv[1] = entry
await import(pathToFileURL(entry).href)
