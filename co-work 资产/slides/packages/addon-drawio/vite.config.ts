import { defineConfig } from 'vite'
import { talkDrawioPlugin } from './server/config.mjs'

export default defineConfig({ plugins: [talkDrawioPlugin()] })
