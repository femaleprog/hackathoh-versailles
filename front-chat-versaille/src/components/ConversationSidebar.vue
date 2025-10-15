<template>
  <nav class="conversation-sidebar">
    <h2>Mes Conversations</h2>
    <ul>
      <li v-for="conv in conversations" :key="conv.uuid">

        <RouterLink
          :to="`/chat_interface/${conv.uuid}`"
          class="conversation-link"
        >
          {{ conv.title }}
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>

<script setup>
import { RouterLink } from "vue-router";

const props = defineProps({
  conversations: { type: Array, default: () => [] },
});
</script>


<style scoped>
/* ... styles remain unchanged ... */
.conversation-sidebar {
  --sidebar-bg: #e8e2d4;
  --text-primary: #3a3a3a;
  --color-gold: #b38e55;
  --border-light: #d3cabd;

  flex-shrink: 0;
  width: 260px;
  height: 100vh;
  background-color: var(--sidebar-bg);
  border-right: 1px solid var(--border-light);
  padding: 20px;
  overflow-y: auto;
  font-family: "Source Serif Pro", serif;
  box-sizing: border-box;
}

h2 {
  font-family: "Cormorant Garamond", serif;
  font-weight: 700;
  color: var(--color-gold);
  text-align: center;
  margin-top: 0;
  margin-bottom: 25px;
  font-size: 1.8rem;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

li {
  margin-bottom: 8px;
}

.conversation-link {
  display: block;
  padding: 10px 15px;
  border-radius: 6px;
  text-decoration: none;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out;
  border: 1px solid transparent;
}

.conversation-link:hover {
  background-color: #fdfaf2;
  border-color: var(--border-light);
}

.router-link-exact-active {
  background-color: var(--color-gold);
  color: white;
  font-weight: 600;
  border-color: var(--color-gold);
}
.router-link-exact-active:hover {
  color: var(--text-primary);
}
</style>
