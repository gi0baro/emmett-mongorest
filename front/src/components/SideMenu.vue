<template>
  <ul class="side-menu-items">
    <li v-for="title in titles" v-bind:key="title.key" :class="title.key == active_title ? 'active' : ''">
      <a :href="`#${ title.ref }`" class="menu-item" @click="onClick(title.key)">{{ title.content }}</a>
      <ul class="side-menu-subitems" v-if="title.key == expanded_title">
        <li v-for="sub in title.subs" v-bind:key="sub.key" :class="sub.key == active_title ? 'active' : ''">
          <a :href="`#${ sub.ref }`" class="menu-subitem" @click="onClick(sub.key)">{{ sub.content }}</a>
        </li>
      </ul>
    </li>
  </ul>
</template>

<script>
export default {
  name: "SideMenu",
  props: ["titles", "active_title", "expanded_title"],
  methods: {
    onClick(key) {
      this.$emit("selected", key)
    }
  }
}
</script>

<style scoped>
a {
  @apply text-gray-600;
}
a:hover {
  @apply text-gray-800;
}
ul.side-menu-items {
  @apply list-none mr-2 my-4 p-0;
}
ul.side-menu-items li {
  @apply mr-4;
}
ul.side-menu-items li a {
  @apply no-underline block px-2 rounded;
}
ul.side-menu-items li.active a.menu-item {
  @apply font-semibold bg-gray-200 text-indigo-500;
}
ul.side-menu-subitems {
  @apply list-none ml-2 p-0;
}
ul.side-menu-subitems li.active a.menu-subitem {
  @apply font-semibold bg-gray-200 text-indigo-500;
}
</style>
