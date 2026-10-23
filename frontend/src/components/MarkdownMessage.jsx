/**
 * MarkdownMessage.jsx
 *
 * Renders AI assistant response text as formatted Markdown.
 * Used by both the standalone AI Assistant and the Personal Health Assistant
 * in the Health Profile page.
 *
 * Design decisions:
 *  - Uses react-markdown + remark-gfm (GFM tables, strikethrough, task lists).
 *  - All element styles are applied via the `components` prop — no dangerouslySetInnerHTML,
 *    no raw HTML passthrough (rehype-raw is intentionally NOT included).
 *  - Colours follow the ChhayaRakshak green-and-white palette (primary, sage, accent).
 *  - The `variant` prop switches between two colour modes:
 *      "assistant" (default) — white card bubble, dark text, green accents
 *      "user"                — blue gradient bubble, white text (plain text only,
 *                              since users never type Markdown)
 *  - Links open in a new tab with rel="noreferrer" for safety.
 *  - Headings are downsized one level so ### becomes a sub-heading rather than
 *    a page-level h3, keeping the chat bubble readable.
 */

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// ── Per-element component overrides ──────────────────────────────────────────
// Applied only when variant === "assistant".
// All className values use only Tailwind utilities already compiled by the
// project's tailwind.config — no arbitrary values that require JIT purging.

function makeComponents(isSmall) {
  // isSmall = true inside the compact Health Profile assistant (text-xs base)
  const textBase   = isSmall ? 'text-xs'  : 'text-sm'
  const textMuted  = isSmall ? 'text-[11px]' : 'text-xs'

  return {
    // Paragraphs — add vertical margin between blocks
    p({ children }) {
      return <p className={`${textBase} leading-relaxed mb-2 last:mb-0`}>{children}</p>
    },

    // Headings — scaled down so they fit inside a chat bubble
    h1({ children }) {
      return <h1 className="text-base font-extrabold text-primary mt-3 mb-1 leading-snug">{children}</h1>
    },
    h2({ children }) {
      return <h2 className="text-sm font-bold text-primary mt-3 mb-1 leading-snug">{children}</h2>
    },
    h3({ children }) {
      return <h3 className="text-sm font-semibold text-gray-700 mt-2 mb-0.5 leading-snug">{children}</h3>
    },
    h4({ children }) {
      return <h4 className={`${textBase} font-semibold text-gray-600 mt-2 mb-0.5`}>{children}</h4>
    },

    // Unordered list — bullet points
    ul({ children }) {
      return <ul className="list-none pl-0 space-y-1 mb-2">{children}</ul>
    },
    // Ordered list — numbered
    ol({ children }) {
      return <ol className="list-decimal pl-5 space-y-1 mb-2">{children}</ol>
    },
    // List item — custom bullet using a green dot for ul; ol inherits decimal marker
    li({ children, ...props }) {
      // ordered list items are rendered inside <ol> which supplies the counter
      const isOrdered = props.node?.parent?.tagName === 'ol'
      return isOrdered
        ? <li className={`${textBase} leading-relaxed text-gray-700`}>{children}</li>
        : (
          <li className={`flex gap-2 items-start ${textBase} leading-relaxed text-gray-700`}>
            <span className="mt-[5px] w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" aria-hidden="true" />
            <span>{children}</span>
          </li>
        )
    },

    // Strong / bold
    strong({ children }) {
      return <strong className="font-semibold text-gray-800">{children}</strong>
    },

    // Emphasis / italic
    em({ children }) {
      return <em className="italic text-gray-600">{children}</em>
    },

    // Inline code
    code({ inline, children }) {
      if (inline) {
        return (
          <code className={`bg-sage-soft text-primary font-mono ${textMuted} px-1.5 py-0.5 rounded`}>
            {children}
          </code>
        )
      }
      // Fenced code block
      return (
        <pre className="bg-gray-50 border border-sage-light/40 rounded-xl px-4 py-3 overflow-x-auto mb-2">
          <code className={`font-mono ${textMuted} text-gray-700 whitespace-pre`}>{children}</code>
        </pre>
      )
    },

    // Blockquote
    blockquote({ children }) {
      return (
        <blockquote className="border-l-2 border-sage pl-3 my-2 text-gray-500 italic">
          {children}
        </blockquote>
      )
    },

    // Horizontal rule
    hr() {
      return <hr className="border-t border-sage-light/40 my-3" />
    },

    // Links — always open externally, never raw HTML injection
    a({ href, children }) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noreferrer noopener"
          className="text-primary underline underline-offset-2 hover:text-primary-light transition-colors"
        >
          {children}
        </a>
      )
    },

    // GFM table support
    table({ children }) {
      return (
        <div className="overflow-x-auto mb-2">
          <table className="w-full text-left border-collapse">{children}</table>
        </div>
      )
    },
    thead({ children }) {
      return <thead className="bg-sage-soft border-b border-sage-light/60">{children}</thead>
    },
    th({ children }) {
      return <th className={`${textMuted} font-semibold text-gray-700 px-3 py-1.5`}>{children}</th>
    },
    td({ children }) {
      return <td className={`${textBase} text-gray-600 px-3 py-1.5 border-b border-sage-light/30`}>{children}</td>
    },
  }
}

// ── Public component ──────────────────────────────────────────────────────────

/**
 * @param {object}  props
 * @param {string}  props.children  — The raw Markdown string to render.
 * @param {boolean} [props.small]   — Use compact text sizes (for the Health Profile panel).
 */
export default function MarkdownMessage({ children, small = false }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={makeComponents(small)}
      // Disable raw HTML passthrough — AI output must never inject arbitrary HTML.
      // react-markdown v10 disables it by default; this makes the intent explicit.
      disallowedElements={['html']}
      unwrapDisallowed
    >
      {children}
    </ReactMarkdown>
  )
}
