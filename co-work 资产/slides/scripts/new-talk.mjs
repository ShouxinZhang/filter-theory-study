import { cp, mkdir, readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { join, resolve } from 'node:path'

export async function createTalk(root, name) {
  if (!name || !/^[a-z0-9][a-z0-9_-]*$/.test(name))
    throw new Error('汇报名使用小写英文字母、数字、短横线或下划线，例如 seminar-2026。')
  const target = join(root, 'talks', name)
  await mkdir(join(root, 'talks'), { recursive: true })
  // Exclusive mkdir prevents overwriting an existing talk, even if creation races.
  await mkdir(target)
  await cp(join(root, 'scaffolds/talk'), target, { recursive: true })
  const file = join(target, 'slides.md')
  await writeFile(file, (await readFile(file, 'utf8')).replaceAll('__TALK_NAME__', name))
  return target
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const root = fileURLToPath(new URL('../', import.meta.url))
  try {
    const name = process.argv[2]
    if (process.argv.length !== 3) throw new Error('用法：npm run new -- seminar-2026')
    const target = await createTalk(root, name)
    console.log(`已新建 ${target}\n启动：bash talks/${name}/start.sh（默认 3030）\n编辑：talks/${name}/slides.md`)
  } catch (error) {
    console.error(error.code === 'EEXIST' ? '该汇报目录已存在，未覆盖任何文件。' : error.message)
    process.exitCode = 1
  }
}
