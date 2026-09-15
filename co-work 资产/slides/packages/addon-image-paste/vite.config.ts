import { defineConfig } from 'vite'
import { imagePastePlugin } from './server/images.mjs'
export default defineConfig({ plugins: [imagePastePlugin()] })
