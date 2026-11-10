const links = [...document.querySelectorAll('.toc a')]
const headings = [...document.querySelectorAll('.part h2')]

/**
 * 当前小节 = 视口 25% 线以上、离它最近的那个标题。
 * 不用 IntersectionObserver 的 rootMargin 划分「窄带」：沙箱 iframe 没有同源，
 * 隐式 root 出于隐私不提供边界（rootBounds 为 null），margin 会被忽略，
 * 观察到的就变成整个视口 —— 在预览里两节会同时算「进入」，高亮跳到下一节。
 * 按位置判断在沙箱内外行为一致。
 */
function currentHeading() {
  // 滚到底时最后一段可能永远到不了 25% 线（下面没有内容可滚了）—— 直接算最后一段
  const atBottom =
    window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2
  if (atBottom) return headings[headings.length - 1]

  const line = window.innerHeight * 0.25
  let current = headings[0]
  for (const h of headings) {
    if (h.getBoundingClientRect().top <= line) current = h
  }
  return current
}

let active = ''
function update() {
  const h = currentHeading()
  if (!h) return
  const id = '#' + h.parentElement.id
  if (id === active) return
  active = id
  links.forEach((a) => a.classList.toggle('is-on', a.getAttribute('href') === id))
  console.log('当前小节：' + h.textContent)
}

// 滚动事件很密：用 requestAnimationFrame 合并，一帧最多算一次位置，别让每帧都触发布局读取
let queued = false
window.addEventListener(
  'scroll',
  () => {
    if (queued) return
    queued = true
    requestAnimationFrame(() => {
      queued = false
      update()
    })
  },
  { passive: true },
)

window.addEventListener('resize', update)
update()
console.log('目录高亮已就绪，滚动正文试试')
