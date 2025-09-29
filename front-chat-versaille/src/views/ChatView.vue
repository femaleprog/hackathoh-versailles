<template>
  <div id="chat-container">
    <header class="chat-header">
      <h1>Le Scribe Royal</h1>
      <p>Votre humble serviteur digital</p>
    </header>
    <MessageDisplay :messages="messages" />
    <UserInput @send-message="handleNewMessage" />
  </div>
</template>

<script>
import MessageDisplay from "@/components/MessageDisplay.vue";
import UserInput from "@/components/UserInput.vue";
import { ref } from "vue";

export default {
  name: "ChatView",
  components: {
    MessageDisplay,
    UserInput,
  },
  setup() {
    const messages = ref([
      {
        id: 1,
        text: "Bonjour, Noble Visiteur. Comment puis-je vous assister en ce jour radieux ?",
        sender: "bot",
      },
    ]);

    const handleNewMessage = (newMessageText) => {
      // Add user's message
      messages.value.push({
        id: Date.now(),
        text: newMessageText,
        sender: "user",
      });

      // Placeholder bot response after a short delay
      setTimeout(() => {
        messages.value.push({
          id: Date.now() + 1,
          text: "Votre requête a été dûment notée. Je médite sur une réponse digne de votre rang. ✨",
          sender: "bot",
        });
      }, 1200);
    };

    return {
      messages,
      handleNewMessage,
    };
  },
};
</script>

<style scoped>
/* --- Versailles Color Palette --- */
:root {
  --background-main: #f8f5ed; /* Creamy white from the website */
  --text-primary: #3a3a3a; /* Dark, soft black for text */
  --color-gold: #b38e55; /* Muted gold for accents and buttons */
  --color-dark-blue: #0a192f;
  --border-light: #e0d8c5;
}

#chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: auto;
  background-color: var(--background-main);
  border-left: 1px solid var(--border-light);
  border-right: 1px solid var(--border-light);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  /* Removed backdrop-filter for an opaque, readable background like ChatGPT */
}

.chat-header {
  padding: 20px;
  background-color: #fff;
  color: var(--text-primary);
  text-align: center;
  border-bottom: 1px solid var(--border-light);
  font-family: "Cormorant Garamond", serif;
  flex-shrink: 0; /* Prevents header from shrinking */
}

.chat-header h1 {
  margin: 0;
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--color-gold);
}

.chat-header p {
  margin: 5px 0 0;
  font-style: italic;
  font-family: "Source Serif Pro", serif;
  opacity: 0.7;
}
</style>
