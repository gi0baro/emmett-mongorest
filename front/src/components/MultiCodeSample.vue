<template>
  <div class="code-sample-multi" v-show="visible">
    <div class="code-slot">
      <slot></slot>
    </div>
    <pre>
      <code v-html="highlightedCode">
      </code>
    </pre>
  </div>
</template>

<script>
import hljs from 'highlight.js';

export default {
  name: "MultiCodeSample",
  props: ["lang"],
  data() {
    return {
      bus: null,
      visible: this.lang == "curl",
      code: null,
      highlightMap: {
        curl: "bash"
      }
    }
  },
  created() {
    this.bindBus()
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
      return hljs.highlight(this.highlightMap[this.lang] || this.lang, this.code).value
    }
  },
  methods: {
    bindBus() {
      if (window._evbus === undefined) {
        setTimeout(() => {
          this.bindBus()
        }, 100)
      } else {
        this.bus = window._evbus
        this.bus.$on("code_language_change", this.languageChange)
      }
    },
    languageChange(language) {
      this.visible = language == this.lang
    },
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
.code-sample-multi pre {
  @apply flex w-full m-0;
}
.code-sample-multi pre code {
  @apply block m-0 px-2 py-0 w-full rounded-t-none rounded-b-md text-xs font-light bg-gray-700 text-gray-200;
}
.code-slot {
  @apply hidden;
}

.code-sample-multi code .hljs-comment,
.code-sample-multi code .hljs-quote {
  color: #7285b7;
}
.code-sample-multi code .hljs-variable,
.code-sample-multi code .hljs-template-variable,
.code-sample-multi code .hljs-tag,
.code-sample-multi code .hljs-name,
.code-sample-multi code .hljs-selector-id,
.code-sample-multi code .hljs-selector-class,
.code-sample-multi code .hljs-regexp,
.code-sample-multi code .hljs-deletion {
  color: #ff9da4;
}
.code-sample-multi code .hljs-number,
.code-sample-multi code .hljs-built_in,
.code-sample-multi code .hljs-builtin-name,
.code-sample-multi code .hljs-literal,
.code-sample-multi code .hljs-type,
.code-sample-multi code .hljs-params,
.code-sample-multi code .hljs-meta,
.code-sample-multi code .hljs-link {
  color: #ffc58f;
}
.code-sample-multi code .hljs-attribute {
  color: #ffeead;
}
.code-sample-multi code .hljs-string,
.code-sample-multi code .hljs-symbol,
.code-sample-multi code .hljs-bullet,
.code-sample-multi code .hljs-addition {
  color: #d1f1a9;
}
.code-sample-multi code .hljs-title,
.code-sample-multi code .hljs-section {
  color: #bbdaff;
}
.code-sample-multi code .hljs-keyword,
.code-sample-multi code .hljs-selector-tag {
  color: #ebbbff;
}
.code-sample-multi code .hljs-emphasis {
  font-style: italic;
}
.code-sample-multi code .hljs-strong {
  font-weight: bold;
}
</style>
