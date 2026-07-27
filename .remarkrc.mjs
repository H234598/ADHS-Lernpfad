import remarkFrontmatter from 'remark-frontmatter'
import remarkGfm from 'remark-gfm'
import remarkPresetLintRecommended from 'remark-preset-lint-recommended'

export default {
  plugins: [
    remarkFrontmatter,
    remarkGfm,
    remarkPresetLintRecommended,
  ],
}
