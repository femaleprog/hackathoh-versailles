<template>
  <nav class="conversation-sidebar">
    <h2>Mes Conversations</h2>
    <ul>
      <li v-for="conv in conversations" :key="conv.uuid"
        class="conversation-item"
        @mouseenter="hoveredConversation = conv.uuid"
        @mouseleave="hoveredConversation = null">

        <RouterLink
          :to="`/chat_interface/${conv.uuid}`"
          class="conversation-link"
        >
          {{ conv.title }}
        </RouterLink>

        <div v-if="hoveredConversation === conv.uuid" class="three-dots-menu" @click.stop="showMenu(conv)" title="Options">
          &#x22EF;  <!-- ⋯ -->
          <!-- small dropdown menu -->
          <div v-if="menuOpenFor === conv.uuid" class="conv-menu" @click.stop>
            <button class="conv-menu-item danger" @click="onAskDelete(conv)">Delete</button>
            <button class="conv-menu-item" @click="onStartRename(conv)">Rename</button>
          </div>
        </div>
        <!-- Delete Confirmation Popup -->
        <div v-if="showDeleteConfirm && currentConversation === conv" class="delete-popup">
          <p>Are you sure you want to delete this conversation?</p>
          <button @click="deleteConversation(conv.uuid)">Delete</button>
          <button @click="cancelDelete">Cancel</button>
        </div>
        <!-- Rename input (shown when 'Rename' is clicked) -->
        <div v-if="showRename && currentConversation === conv" class="rename-popup">
          <input type="text" v-model="newTitle" @keyup.enter="saveRename(conv.uuid)" />
        </div>
      </li>
    </ul>
  </nav>
</template>

<script setup>
const backendApiUrl =
  import.meta.env.VITE_API_BASE_URL || window.location.origin;

import { ref } from "vue";
import { RouterLink } from "vue-router";

const props = defineProps({
  conversations: { type: Array, default: () => [] },
});
const emit = defineEmits(["conversation-updated"]);

const hoveredConversation = ref(null); // Add this line to track hover state
const menuOpenFor = ref(null);
const showDeleteConfirm = ref(false);
const showRename = ref(false);
const currentConversation = ref(null);
const newTitle = ref("");

// The function to handle showing the menu
const showMenu = (conversation) => {
  currentConversation.value = conversation;
  menuOpenFor.value = 
     menuOpenFor.value === conversation.uuid ? null : conversation.uuid;
};

// from the menu: ask delete -> open confirm; close menu
const onAskDelete = (conversation) => {
  currentConversation.value = conversation;
  showDeleteConfirm.value = true;
  menuOpenFor.value = null;
};

// from the menu: start rename -> show inline input; close menu
const onStartRename = (conversation) => {
  currentConversation.value = conversation;
  newTitle.value = conversation.title || "";
  showRename.value = true;
  menuOpenFor.value = null;
};

const cancelDelete = () => {
  showDeleteConfirm.value = false;
  currentConversation.value = null;
};

const renameConversation = (uuid) => {
  showRename.value = true;
   if (currentConversation.value) onStartRename(currentConversation.value);
};
const saveRename = async (uuid) => {
  try {
    const title = newTitle.value.trim();
    if (!title) {
      showRename.value = false;
      return;
    }
    const r = await fetch(`${backendApiUrl}/v1/conversations/${uuid}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    showRename.value = false;
    currentConversation.value = null;
    emit("conversation-updated"); // let App.vue refresh the list
  } catch (error) {
    console.error("Failed to rename conversation:", error);
  }
};
const deleteConversation = async (uuid) => {
  try {
    const r = await fetch(`${backendApiUrl}/v1/conversations/${uuid}`, {
      method: "DELETE",
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    showDeleteConfirm.value = false;
    currentConversation.value = null;
    emit("conversation-updated"); // let App.vue refresh the list
  } catch (error) {
    console.error("Failed to delete conversation:", error);
  }
};
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

h2::after {
  content: "";
  display: block;
  width: 64%;
  height: 2px;
  margin: 8px auto 0;
  background: linear-gradient(90deg, transparent, var(--bordeaux), transparent);
  opacity: .65; /* was .35 */
}


ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

li {
  margin-bottom: 8px;
}
.conversation-item {
  position: relative; /* Added this line */
}

.conversation-item:hover .three-dots-menu {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  z-index: 10;
}

.conversation-item:hover .conversation-link {
  background: #fff5f7;              /* light Bordeaux wash */
  border-color: var(--bordeaux);     /* <-- stronger border */
}

.three-dots-menu {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  cursor: pointer;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.15s ease;
  z-index: 1; /* Ensure visibility */
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
  background: #fff5f7;
  border-color: var(--bordeaux);
  color: var(--deep-brown);
  box-shadow: 0 0 0 2px rgba(106,31,43,0.18); /* Bordeaux glow */
}
.router-link-exact-active:hover {
  color: var(--text-primary);
}

.delete-popup {
  background-color: #f8d7da;
  padding: 10px;
  border-radius: 5px;
}

.delete-popup button {
  background-color: #dc3545;
  color: white;
  border: none;
  margin-right: 10px;
  padding: 5px 10px;
  border-radius: 5px;
}

.rename-popup input {
  padding: 5px;
  margin-top: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  width: 200px;
}
.three-dots-menu:hover {
  background: rgba(106,31,43,0.12);
  color: var(--bordeaux);
}
.conv-menu-item:hover { background: rgba(106,31,43,0.10); }
.conv-menu-item.danger { color: var(--bordeaux); }
</style>
