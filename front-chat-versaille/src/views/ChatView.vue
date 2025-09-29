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
#chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: auto;
  background-color: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(212, 175, 55, 0.4);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
}

.chat-header {
  padding: 20px;
  background-color: rgba(10, 25, 47, 0.8);
  color: #d4af37; /* Gold */
  text-align: center;
  border-bottom: 2px solid #d4af37;
  font-family: "Cormorant Garamond", serif;
}

.chat-header h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
}

.chat-header p {
  margin: 0;
  font-style: italic;
  opacity: 0.8;
}
</style>
