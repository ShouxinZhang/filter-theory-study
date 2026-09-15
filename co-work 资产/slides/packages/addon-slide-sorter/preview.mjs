// Notes/comments do not affect thumbnail order and may not invalidate Slidev metadata.
export function previewText(text = '') {
  return text.replaceAll('\r\n', '\n').replace(/<!--[\s\S]*?-->/g, '').trim()
}


export function matchesPreview(slide, item) {
  // Native dragging intentionally skips HMR. Its saved coordinates are supplied
  // directly to SortThumbnail; all other compiled content must still match.
  return previewText(slide?.content) === item.previewContent
    && Object.entries(item.previewFrontmatter).every(([key, value]) =>
      key === 'dragPos' || JSON.stringify(slide?.frontmatter?.[key]) === JSON.stringify(value))
}
