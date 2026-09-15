import { defineConfig } from 'vite'
import { slideSorterPlugin } from './server/sorter.mjs'
export default defineConfig({ plugins: [slideSorterPlugin()] })
