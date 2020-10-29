<template>
  <div class="api-docs">
    <div class="sidebar">
      <div class="title">
        {{ title }}
      </div>
      <side-menu :titles="titles" :active_title="activeTitle" :expanded_title="expandedTitle" @selected="onTitleSelected"></side-menu>
    </div>
    <div ref="content" class="content" @scroll="scrollHandler">
      <slot></slot>
    </div>
  </div>
</template>

<script>
import SideMenu from './SideMenu.vue'

export default {
  name: "ApiDocs",
  props: ["title"],
  components: {
    SideMenu
  },
  data() {
    return {
      bus: null,
      scrollHandler: null,
      titles: [],
      offsets: {},
      activeOffset: null,
      activeTitle: null,
      expandedTitle: null
    }
  },
  created() {
    this.scrollHandler = this.debounce(this.handleScroll, 200)
  },
  mounted() {
    this.$nextTick(() => {
      this.fetchContents()
    })
  },
  watch: {
    activeOffset(val) {
      if (val === null) {
        this.activeTitle = null
      }
      let offset = this.offsets[val]
      if (offset.cls == "h2") {
        this.activeTitle = offset.el
        this.expandedTitle = offset.el
      } else {
        this.activeTitle = offset.el
        this.expandedTitle = offset.parent.el
      }
    }
  },
  methods: {
    debounce(f, wait) {
      var timeout = false
      return function() {
        if (timeout === false) {
          setTimeout(function() {
            f()
            timeout = false
          }, wait)
          timeout = true
        }
      }
    },
    fetchContents() {
      if (this.$slots.default === undefined) {
        // weird, but happens..
        setTimeout(() => {
          this.fetchContents()
        }, 100)
      } else {
        this.$slots.default.map((el) => {
          if (el.tag !== undefined) {
            this.fetchTree(el.elm)
          }
        })
      }
    },
    fetchTree(el) {
      if (el.tagName == "H2") {
        let key = "h2__" + el.innerHTML.toLowerCase().replace(/\s/g, "__")
        let prev_offset = this.titles.length != 0 ? this.offsets[this.titles[this.titles.length - 1].key] : null
        this.titles.push({
          content: el.innerHTML,
          key: key,
          ref: el.id,
          subs: []
        })
        this.offsets[key] = {cls: "h2", el: key, begin: el.getBoundingClientRect().top}
        if (prev_offset !== null) {
          prev_offset.end = this.offsets[key].begin
        } else {
          this.activeOffset = key
        }
      } else if (el.tagName == "H3") {
        if (this.titles.length > 0) {
          let key = "h3__" + el.innerHTML.toLowerCase().replace(/\s/g, "__")
          let parent = this.titles[this.titles.length - 1]
          let prev_offset = parent.subs.length != 0 ? this.offsets[parent.subs[parent.subs.length - 1].key] : null
          parent.subs.push({
            content: el.innerHTML,
            key: key,
            ref: el.id
          })
          this.offsets[key] = {cls: "h3", el: key, parent: this.offsets[parent.key], begin: el.getBoundingClientRect().top}
          if (prev_offset !== null) {
            prev_offset.end = this.offsets[key].begin
          }
        }
      } else {
        [...el.children].map((child) => {
          this.fetchTree(child)
        })
      }
    },
    handleScroll() {
      let scrollTop = this.$refs.content.scrollTop
      let matchingTitle = null

      for (let key in this.offsets) {
        if ((this.offsets[key].begin <= scrollTop) && ((this.offsets[key].end || scrollTop) >= scrollTop)) {
          matchingTitle = key
        }
      }
      if ((matchingTitle === null) || (matchingTitle === this.activeOffset)) {
        return
      }
      this.activeOffset = matchingTitle
    },
    onTitleSelected(key) {
      this.$refs.content.scroll({top: this.offsets[key].begin})
    }
  }
}
</script>

<style>
.api-docs {
  @apply w-full h-screen flex flex-row;
}
.sidebar {
  @apply h-screen pl-2 py-2 border-solid border-0 border-r border-gray-300;
}
.sidebar .title {
  @apply mt-8 text-2xl text-gray-800 ml-2;
}
.content {
  @apply h-screen overflow-y-auto box-border text-gray-800 px-12 pt-2 pb-16;
}
.content .doc-block {
  @apply flex flex-row flex-wrap pb-4;
}
.content .doc-block .doc-block-text {
  @apply pl-2 pr-2 box-border;
}
.content .doc-block .doc-block-samples {
  @apply pr-2 box-border;
}
.content h2 {
  @apply text-3xl font-normal pt-16 mb-6 mt-0;
}
.content h3 {
  @apply text-2xl font-normal pt-8 mb-4 mt-0;
}
.content h4 {
  @apply text-xl font-normal pt-4 mb-2 mt-0;
}
.content table {
  @apply mb-4;
}
.content table th {
  @apply p-2 font-medium text-left;
}
.content table td {
  @apply p-2 border-solid border-0 border-t border-gray-300;
}
.content p {
  @apply mb-4;
}
.content ul {
  @apply mb-4 list-none p-0;
}
.content code {
  @apply font-light bg-gray-200 px-1 py-1 rounded;
}
.content pre {
  @apply flex w-full;
}
.content pre code {
  @apply block m-0 px-2 py-0 w-full bg-gray-700 text-gray-100 text-sm font-normal overflow-x-auto overflow-y-hidden;
}
.content .doc-block .doc-block-text ul.parameters li {
  @apply block border-solid border-0 border-t border-gray-300 py-2;
}
.content .doc-block .doc-block-text ul.parameters .param {
  @apply text-sm font-bold mr-2;
}
.content .doc-block .doc-block-text .param-details {
  @apply text-sm text-gray-600;
}
.content .doc-block .doc-block-text .param-desc {
  @apply block text-sm pt-1;
}
.content .doc-block .doc-block-text ul.attributes li {
  @apply block border-solid border-0 border-t border-gray-300 py-2;
}
.content .doc-block .doc-block-text ul.attributes .attr {
  @apply text-sm font-bold mr-2;
}
.content .doc-block .doc-block-text .attr-details {
  @apply text-sm text-gray-600;
}
.content .doc-block .doc-block-text .attr-desc {
  @apply block text-sm pt-1;
}
.content .doc-block .doc-block-text ul.attributes ul {
  @apply pt-2 pl-6 mb-0;
}
@screen port {
  .doc-block-text {
    @apply w-full;
  }
  .doc-block-samples {
    @apply w-full pl-2;
  }
  .sidebar {
    @apply hidden;
  }
  .content {
    @apply w-full;
  }
}
@screen land {
  .doc-block-text {
    @apply w-1/2;
  }
  .doc-block-samples {
    @apply w-1/2 pl-8;
  }
  .sidebar {
    @apply w-1/6;
  }
  .content {
    @apply w-5/6;
  }
}
</style>
