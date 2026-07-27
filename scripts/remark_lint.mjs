#!/usr/bin/env node

import {existsSync} from 'node:fs'
import {resolve} from 'node:path'
import {spawnSync} from 'node:child_process'

const ROOT = resolve(import.meta.dirname, '..')
const EXCLUDED_PARTS = new Set(['.git', 'build', 'site', 'node_modules', '__pycache__'])

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

const mode = process.argv.includes('--all') ? 'all' : 'changed'
const files = (mode === 'all' ? allFiles() : changedFiles()).filter((path) => existsSync(resolve(ROOT, path)))
if (files.length === 0) {
  console.log('Remark-lint: keine relevanten Markdown-Dateien.')
  process.exit(0)
}

console.log(`Remark-lint (${mode}): ${files.length} Datei(en)`)
for (const file of files) console.log(`- ${file}`)

const binary = resolve(ROOT, 'node_modules', '.bin', process.platform === 'win32' ? 'remark.cmd' : 'remark')
const result = spawnSync(binary, ['--frail', '--no-stdout', ...files], {
  cwd: ROOT,
  stdio: 'inherit',
})
process.exit(result.status ?? 1)
