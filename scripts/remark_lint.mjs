#!/usr/bin/env node

import {existsSync, readFileSync} from 'node:fs'
import {relative, resolve, sep} from 'node:path'
import {spawnSync} from 'node:child_process'
import {remark} from 'remark'
import remarkFrontmatter from 'remark-frontmatter'
import remarkGfm from 'remark-gfm'
import remarkPresetLintRecommended from 'remark-preset-lint-recommended'

const ROOT = resolve(import.meta.dirname, '..')
const EXCLUDED_PARTS = new Set(['.git', 'build', 'site', 'node_modules', '__pycache__'])
const FENCE_RE = /^\s*(```+|~~~+)/
const WIKILINK_RE = /\[\[([\s\S]*?)\]\]/g
const EMBED_RE = /!\[\[([\s\S]*?)\]\]/g
const CALLOUT_RE = /^(\s*>\s*)\[!([A-Za-z0-9_-]+)\](.*)$/gm

function git(args, {allowFailure = false} = {}) {
  const result = spawnSync('git', args, {
    cwd: ROOT,
    encoding: 'utf8',
    maxBuffer: 16 * 1024 * 1024,
  })
  if (result.status !== 0 && !allowFailure) {
    process.stderr.write(result.stderr || result.stdout)
    process.exit(result.status || 1)
  }
  return result
}

function splitNull(value) {
  return value.split('\0').filter(Boolean)
}

function safeRelativePath(path) {
  const absolute = resolve(ROOT, path)
  const repoRelative = relative(ROOT, absolute)
  if (
    repoRelative === '' ||
    repoRelative === '..' ||
    repoRelative.startsWith(`..${sep}`) ||
    repoRelative.split(sep).some((part) => EXCLUDED_PARTS.has(part))
  ) {
    throw new Error(`Unzulässiger Markdownpfad: ${path}`)
  }
  return repoRelative.split(sep).join('/')
}

function relevant(path) {
  if (!path.endsWith('.md')) return false
  return !path.split('/').some((part) => EXCLUDED_PARTS.has(part))
}

function changedFiles() {
  let base = process.env.REMARK_BASE_SHA || 'origin/main'
  const head = process.env.REMARK_HEAD_SHA || 'HEAD'
  if (/^0+$/.test(base)) base = `${head}^`

  const baseCheck = git(['rev-parse', '--verify', base], {allowFailure: true})
  if (baseCheck.status !== 0) base = `${head}^`

  const diff = git([
    'diff',
    '--name-only',
    '-z',
    '--diff-filter=ACMR',
    `${base}...${head}`,
    '--',
    '*.md',
  ], {allowFailure: true})
  if (diff.status !== 0) {
    const fallback = git([
      'diff',
      '--name-only',
      '-z',
      '--diff-filter=ACMR',
      `${head}^`,
      head,
      '--',
      '*.md',
    ])
    return splitNull(fallback.stdout).filter(relevant)
  }
  return splitNull(diff.stdout).filter(relevant)
}

function allFiles() {
  return splitNull(git(['ls-files', '-z', '--', '*.md']).stdout).filter(relevant)
}

function requestedFiles() {
  const index = process.argv.indexOf('--files')
  if (index < 0) return null
  const values = process.argv.slice(index + 1)
  if (values.length === 0) throw new Error('--files benötigt mindestens einen Pfad')
  return values.filter(relevant)
}

function visibleLabel(raw) {
  const normalized = raw.replace(/\s+/g, ' ').trim()
  const [targetPart, aliasPart] = normalized.split('|', 2)
  const target = targetPart.trim()
  const alias = aliasPart?.trim()
  if (alias) return alias
  const heading = target.includes('#') ? target.split('#', 2)[1].trim() : ''
  return heading || target || 'interner Link'
}

function sanitizeTextBlock(value) {
  let sanitized = value.replace(
    CALLOUT_RE,
    (_match, prefix, kind, rest) => `${prefix}**${kind}**${rest}`,
  )
  sanitized = sanitized.replace(
    EMBED_RE,
    (_match, raw) => `![${visibleLabel(raw)}](https://example.invalid/obsidian-embed)`,
  )
  sanitized = sanitized.replace(
    WIKILINK_RE,
    (_match, raw) => `[${visibleLabel(raw)}](https://example.invalid/obsidian-link)`,
  )
  return sanitized
}

function sanitizeObsidianMarkdown(content) {
  const output = []
  let prose = []
  let fence = null

  function flushProse() {
    if (prose.length === 0) return
    output.push(sanitizeTextBlock(prose.join('')))
    prose = []
  }

  for (const line of content.split(/(?<=\n)/)) {
    const fenceMatch = line.match(FENCE_RE)
    if (fenceMatch) {
      flushProse()
      const marker = fenceMatch[1][0]
      fence = fence === null ? marker : fence === marker ? null : fence
      output.push(line)
    } else if (fence === null) {
      prose.push(line)
    } else {
      output.push(line)
    }
  }
  flushProse()
  return output.join('')
}

function formatMessage(path, message) {
  const line = message.line || message.place?.start?.line || 1
  const column = message.column || message.place?.start?.column || 1
  const rule = [message.source, message.ruleId].filter(Boolean).join(':')
  return `${path}:${line}:${column} ${message.reason}${rule ? ` [${rule}]` : ''}`
}

const explicit = requestedFiles()
const mode = explicit ? 'files' : process.argv.includes('--all') ? 'all' : 'changed'
const sourceFiles = (explicit || (mode === 'all' ? allFiles() : changedFiles()))
  .map(safeRelativePath)
  .filter((path, index, values) => values.indexOf(path) === index)
  .filter((path) => existsSync(resolve(ROOT, path)))

if (sourceFiles.length === 0) {
  console.log('Remark-lint: keine relevanten Markdown-Dateien.')
  process.exit(0)
}

console.log(`Remark-lint (${mode}): ${sourceFiles.length} Datei(en)`)
for (const file of sourceFiles) console.log(`- ${file}`)

const processor = remark()
  .use(remarkFrontmatter)
  .use(remarkGfm)
  .use(remarkPresetLintRecommended)
  .freeze()

let issueCount = 0
for (const path of sourceFiles) {
  try {
    const file = await processor.process({
      path,
      value: sanitizeObsidianMarkdown(readFileSync(resolve(ROOT, path), 'utf8')),
    })
    if (file.messages.length === 0) {
      console.log(`${path}: no issues found`)
      continue
    }
    for (const message of file.messages) {
      console.error(formatMessage(path, message))
      issueCount += 1
    }
  } catch (error) {
    console.error(`${path}: Remark-Verarbeitung fehlgeschlagen: ${error.stack || error}`)
    issueCount += 1
  }
}

if (issueCount > 0) {
  console.error(`Remark-lint: ${issueCount} blockierende Meldung(en).`)
  process.exit(1)
}
console.log('Remark-lint: alle geprüften Dateien sind sauber.')
