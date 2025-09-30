<template>
  <div class="app-wrapper">
    <ConversationSidebar />
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import ConversationSidebar from "@/components/ConversationSidebar.vue";
</script>

<style>
@import url("https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;700&family=Source+Serif+Pro:ital@0;1&display=swap");

/* --- Versailles Light Theme Palette --- */
:root {
  --background-global: #fdfcf9; /* A very light, warm off-white */
  --background-container: #f8f5ed; /* Creamy parchment for the chat area */
  --text-primary: #4a443a; /* A softer, brownish-black for text */
  --color-gold: #b38e55; /* Muted gold for accents */
  --border-light: #e0d8c5; /* Light border color */
  --user-message-bg: #ebe3d5; /* Warm beige for user messages */
}

body {
  margin: 0;
  font-family: "Source Serif Pro", serif;
  background-color: var(--background-global);
  color: var(--text-primary);
}

/* --- New Layout Styles --- */
.app-wrapper {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.main-content {
  flex-grow: 1;
  height: 100vh;
  position: relative; /* Provides a positioning context for child elements */
}
</style>
