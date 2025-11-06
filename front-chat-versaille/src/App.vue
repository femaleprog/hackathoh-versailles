<template>
  <div class="app-wrapper">
    <ConversationSidebar :conversations="conversations" @conversation-updated="loadConversations"/>
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <component :is="Component" @conversation-updated="loadConversations" />
      </router-view>

    </main>
  </div>
</template>

<script setup>
import ConversationSidebar from "@/components/ConversationSidebar.vue";
import { ref, onMounted } from "vue";

const conversations = ref([]);
const backendApiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin;

const loadConversations = async () => {
  const r = await fetch(`${backendApiUrl}/v1/conversations`, {
    headers: { "Cache-Control": "no-cache" },
  });
  conversations.value = await r.json();
};

onMounted(loadConversations);

</script>

<style>
@import url("https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;700&family=Source+Serif+Pro:ital@0;1&display=swap");

/* --- Versailles Light Theme Palette --- */
:root {
  /* Versailles Royal Palette */
  --ivory:        #FAF6EF; /* background */
  --antique-gold: #C4A052; /* titles, highlights */
  --bronze:       #B58E66; /* buttons, borders */
  --deep-brown:   #3B2F2F; /* text */
  --bordeaux:     #6A1F2B; /* accent/cta/hover */

  /* Semantic tokens */
  --bg-global: var(--ivory);
  --bg-surface: #fffaf1;
  --text: var(--deep-brown);
  --border: color-mix(in oklab, var(--bronze) 35%, white);
  --shadow: 0 10px 30px rgba(59, 47, 47, 0.08);
}

/* Global base */
body {
  margin: 0;
  background: var(--bg-global);
  color: var(--text);
  font-family: "Source Serif Pro", serif;
}

/* Layout */
.app-wrapper {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.main-content {
  flex: 1;
  background:
    radial-gradient(1200px 600px at -10% -20%, rgba(196,160,82,0.08), transparent 60%),
    radial-gradient(900px 500px at 120% 120%, rgba(181,142,102,0.08), transparent 60%),
    var(--bg-global);
  position: relative;
}

/* Utility components */
.btn {
  appearance: none;
  border: 1px solid var(--bronze);
  background: linear-gradient(180deg, #fffdf7, #f3e6d3);
  color: var(--deep-brown);
  padding: 8px 14px;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow);
  transition: transform .12s ease, box-shadow .2s ease, border-color .2s ease;
}
.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 26px rgba(59, 47, 47, 0.12);
  border-color: var(--bordeaux);
}
.btn:active { transform: translateY(0); }
.btn--accent {
  background: linear-gradient(180deg, #f7f0e1, #e8cfad);
  border-color: var(--bordeaux);
  color: var(--bordeaux);
}

.card {
  background: #fffdf7;
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow);
}
.header-image {
  background-image: url('@/assets/header-chateau-versailles.png');
  background-size: cover; 
  background-position: center; 
  height: 10%;
  width: 100%; 
}
</style>
