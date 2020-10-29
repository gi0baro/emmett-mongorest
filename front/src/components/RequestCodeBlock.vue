<template>
  <div class="request-code-block">
    <div class="request-code-block-topbar">
      <div class="request-code-block-path">
        {{ method }} {{ endpoint }}
      </div>
      <div class="lang-selector-wrapper">
        <select class="request-code-block-lang-selector" v-model="lang" @change="changeLang">
          <option v-for="lang in langs" v-bind:key="lang" :value="lang">{{ lang }}</option>
        </select>
        <div class="lang-selector-icon-block">
          <svg class="lang-selector-icon" viewBox="0 0 20 20">
            <path d="M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z" />
          </svg>
        </div>
      </div>
    </div>
    <div class="request-code-block-body">
      <slot></slot>
    </div>
  </div>
</template>

<script>
export default {
  name: "RequestCodeBlock",
  props: ["method", "endpoint"],
  data() {
    return {
      bus: null,
      langs: [],
      lang: null
    }
  },
  created() {
    this.bindBus()
    this.langs = window._code_langs || this.langs
    this.lang = this.langs[0]
  },
  methods: {
    bindBus() {
      if (window._evbus === undefined) {
        setTimeout(() => {
          this.bindBus()
        }, 100)
      } else {
        this.bus = window._evbus
        this.bus.$on("code_language_change", this.langChanged)
      }
    },
    changeLang(ev) {
      this.bus.$emit("code_language_change", ev.target.value)
    },
    langChanged(lang) {
      this.lang = lang
    }
  }
}
</script>

<style>
.request-code-block {
  @apply rounded-md mt-20 border-solid border border-gray-800;
}
.request-code-block-topbar {
  @apply py-2 px-2 bg-gray-800 text-gray-200 rounded-t-md flex flex-row flex-wrap;
}
.request-code-block-path {
  @apply w-4/5 text-sm font-light;
}
.request-code-block-lang-selector {
  @apply appearance-none block bg-gray-700 text-gray-200 cursor-pointer pl-1 w-full rounded-md leading-normal;
}
.request-code-block-lang-selector:focus {
  @apply outline-none;
}
.lang-selector-wrapper {
  @apply relative w-1/5 bg-gray-700 rounded-md;
}
.lang-selector-icon-block {
  @apply pointer-events-none absolute inset-y-0 right-0 flex items-center px-2;
}
.lang-selector-icon {
  @apply h-4 w-4 fill-current;
}
</style>
