<template>
  <div class="code-block">
    <div class="code-block-topbar">
      <div class="code-block-title">
        {{ title }}
      </div>
    </div>
    <div class="code-block-body">
      <div class="code-slot">
        <slot></slot>
      </div>
      <pre>
        <code v-html="highlightedCode">
        </code>
      </pre>
    </div>
  </div>
</template>

<script>
import hljs from 'highlight.js';

export default {
  name: "CodeBlock",
  props: ["title", "lang"],
  data() {
    return {
      code: null,
      highlightMap: {
        curl: "bash"
      }
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.fetchCode()
    })
  },
  computed: {
    highlightedCode() {
      if (this.code === null) {
        return ""
      }
      if (this.lang === null) {
        return this.code
      }
      return hljs.highlight(this.highlightMap[this.lang] || this.lang, this.code).value
    }
  },
  methods: {
    fetchCode() {
      if (this.$slots.default === undefined) {
        // weird, but happens..
        setTimeout(() => {
          this.fetchCode()
        }, 100)
      } else {
        if (this.$slots.default[0].tag == "PRE") {
          [...this.$slots.default[0].elm.children].map((child) => {
            if (child.tagName == "CODE") {
              this.code = child.innerHTML
            }
          })
        }
      }
    }
  }
}
</script>

<style>
.code-block {
  @apply rounded-md mt-4 border-solid border border-gray-300;
}
.code-block-topbar {
  @apply py-2 px-2 bg-gray-300 text-gray-800 rounded-t-md flex flex-row flex-wrap;
}
.code-block-title {
  @apply w-4/5 text-sm font-light uppercase;
}
.code-block-body pre {
  @apply flex w-full m-0;
}
.code-block-body pre code {
  @apply block m-0 px-2 py-0 w-full rounded-t-none rounded-b-md text-xs font-light bg-gray-100 text-gray-700;
}
.code-slot {
  @apply hidden;
}

.code-block-body code .hljs-comment,
.code-block-body code .hljs-quote {
  color: #8e908c;
}
.code-block-body code .hljs-variable,
.code-block-body code .hljs-template-variable,
.code-block-body code .hljs-tag,
.code-block-body code .hljs-name,
.code-block-body code .hljs-selector-id,
.code-block-body code .hljs-selector-class,
.code-block-body code .hljs-regexp,
.code-block-body code .hljs-deletion {
  color: #c82829;
}
.code-block-body code .hljs-number,
.code-block-body code .hljs-built_in,
.code-block-body code .hljs-builtin-name,
.code-block-body code .hljs-literal,
.code-block-body code .hljs-type,
.code-block-body code .hljs-params,
.code-block-body code .hljs-meta,
.code-block-body code .hljs-link {
  color: #f5871f;
}
.code-block-body code .hljs-attribute {
  color: #eab700;
}
.code-block-body code .hljs-string,
.code-block-body code .hljs-symbol,
.code-block-body code .hljs-bullet,
.code-block-body code .hljs-addition {
  color: #718c00;
}
.code-block-body code .hljs-title,
.code-block-body code .hljs-section {
  color: #4271ae;
}
.code-block-body code .hljs-keyword,
.code-block-body code .hljs-selector-tag {
  color: #8959a8;
}
.code-block-body code .hljs-emphasis {
  font-style: italic;
}
.code-block-body code .hljs-strong {
  font-weight: bold;
}
</style>
