<template>
  <div class="main-layout-container">
    <div id="chat-container">
      <header class="chat-header">
        <h1>Le Scribe Royal</h1>
        <p>Votre humble serviteur digital</p>
      </header>
      <MessageDisplay :messages="messages" />
      <UserInput @send-message="handleNewMessage" />
    </div>

    <div class="map-area">
      <MapDisplay v-if="routeJson" :route-data="routeJson" />
    </div>
  </div>
</template>

<script>
import MessageDisplay from "@/components/MessageDisplay.vue";
import UserInput from "@/components/UserInput.vue";
import MapDisplay from "@/components/MapDisplay.vue"; // 1. Import the new component
import { ref } from "vue";

// 2. Import your JSON data
import routeJsonData from "@/route-data.json"; // Assuming you save the JSON in 'src/route-data.json'

export default {
  name: "ChatView",
  components: {
    MessageDisplay,
    UserInput,
    MapDisplay, // 3. Register the new component
  },
  setup() {
    // 4. Store your JSON data in a ref
    const routeJson = ref(routeJsonData);

    const messages = ref([
      {
        id: 1,
        text: "Bonjour, Noble Visiteur. Comment puis-je vous assister en ce jour radieux ?",
        sender: "bot",
      },
    ]);

    const apiKey = import.meta.env.VITE_MISTRAL_API_KEY;
    const mistralApiUrl = "https://api.mistral.ai/v1/chat/completions";

    const handleNewMessage = async (newMessageText) => {
      messages.value.push({
        id: Date.now(),
        text: newMessageText,
        sender: "user",
      });

      if (!apiKey) {
        messages.value.push({
          id: Date.now() + 1,
          text: "Hélas, la clé API de Mistral n'est pas configurée côté client.",
          sender: "bot",
        });
        return;
      }

      try {
        const response = await fetch(mistralApiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({
            model: "mistral-large-latest",
            messages: [{ role: "user", content: newMessageText }],
          }),
        });

        if (!response.ok) {
          throw new Error(`API request failed with status ${response.status}`);
        }

        const data = await response.json();
        const botReply = data.choices[0].message.content;

        messages.value.push({
          id: Date.now() + 1,
          text: botReply,
          sender: "bot",
        });
      } catch (error) {
        console.error("Error calling Mistral API:", error);
        messages.value.push({
          id: Date.now() + 1,
          text: "Hélas, une erreur est survenue lors de la communication avec le Scribe. Veuillez réessayer.",
          sender: "bot",
        });
      }
    };

    return {
      messages,
      handleNewMessage,
      routeJson, // 5. Expose the data to the template
    };
  },
};
</script>

<style scoped>
/* --- Versailles Color Palette --- */
:root {
  --background-main: #f8f5ed;
  --text-primary: #3a3a3a;
  --color-gold: #b38e55;
  --color-dark-blue: #0a192f;
  --border-light: #e0d8c5;
}

/* New styles for the two-column layout */
.main-layout-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: var(--background-main);
}

.map-area {
  flex: 1; /* The map will take 1 part of the available space */
  height: 100vh;
}

/* Modified styles for the chat container */
#chat-container {
  flex: 1; /* The chat will take 1 part of the space. Change to flex: 2; to make it wider */
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px; /* You might want to adjust or remove this */
  margin: 0; /* Remove auto margin */
  background-color: var(--background-main);
  border-right: 1px solid var(--border-light);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.chat-header {
  padding: 20px;
  background-color: #fff;
  color: var(--text-primary);
  text-align: center;
  border-bottom: 1px solid var(--border-light);
  font-family: "Cormorant Garamond", serif;
  flex-shrink: 0;
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
