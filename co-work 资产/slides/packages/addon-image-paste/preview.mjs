// Native v-drag updates inline positions without always refreshing route metadata.
// Ignore only numeric positions when checking the visible page identity; the
// full Markdown version still protects every byte when the upload is committed.
export function preview(text = '') {
  return text.replaceAll('\r\n', '\n').replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\bpos=(["'])[-\d.,\s]+\1/g, 'pos="$position"').trim()
}
