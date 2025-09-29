// src/views/ChatView.vue

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
      <MapDisplay
        v-if="routeJson"
        :route-data="routeJson"
        :selected-leg-index="selectedLegIndex"
      />
      <div class="leg-selector" v-if="routeJson?.routes?.[0]?.legs">
        <button
          v-for="(leg, index) in routeJson.routes[0].legs"
          :key="index"
          @click="selectLeg(index)"
          :class="{ active: index === selectedLegIndex }"
        >
          {{ index + 1 }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import MessageDisplay from "@/components/MessageDisplay.vue";
import UserInput from "@/components/UserInput.vue";
import MapDisplay from "@/components/MapDisplay.vue";
import { ref } from "vue";
import routeJsonData from "@/route-data.json";

export default {
  name: "ChatView",
  components: {
    MessageDisplay,
    UserInput,
    MapDisplay,
  },
  setup() {
    const routeJson = ref(routeJsonData);

    // NEW: State to track the currently selected leg index
    const selectedLegIndex = ref(0); // Default to the first leg

    const messages = ref([
      {
        id: 1,
        text: "Bonjour, Noble Visiteur. Comment puis-je vous assister en ce jour radieux ?",
        sender: "bot",
      },
    ]);

    // NEW: Function to update the selected leg index
    const selectLeg = (index) => {
      selectedLegIndex.value = index;
    };

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
      routeJson,
      selectedLegIndex, // Expose to the template
      selectLeg, // Expose to the template
    };
  },
};
</script>
// src/views/ChatView.vue -> replace the
<style>
section with this

<style scoped>
/* --- Versailles Color Palette --- */
:root {
  --background-main: #f8f5ed;
  --text-primary: #3a3a3a;
  --color-gold: #b38e55;
  --color-dark-blue: #0a192f;
  --border-light: #e0d8c5;
}

/* MODIFIED: Reverted to the original side-by-side layout */
.main-layout-container {
  display: flex;
  /* flex-direction: row; is the default, so this line isn't strictly needed */
  height: 100vh;
  width: 100vw;
  background-color: var(--background-main);
}

/* MODIFIED: Map area now contains map + buttons, stacked vertically */
.map-area {
  flex: 1; /* The map area will take 1 part of the available space */
  height: 100vh;
  display: flex;
  flex-direction: column; /* Stacks the map on top of the button selector */
}

/* MODIFIED: Reverted to its original state for the side-by-side layout */
#chat-container {
  flex: 1; /* The chat will take 1 part of the space. */
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0;
  background-color: var(--background-main);
  border-right: 1px solid var(--border-light); /* Back to border-right */
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

/* Styles for the leg selector buttons (no changes needed here) */
.leg-selector {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px;
  background-color: #fff;
  border-top: 1px solid var(--border-light);
  flex-shrink: 0;
}

.leg-selector button {
  font-family: "Source Serif Pro", serif;
  font-size: 1rem;
  font-weight: bold;
  margin: 0 5px;
  padding: 8px 15px;
  border: 1px solid var(--border-light);
  border-radius: 5px;
  background-color: #f8f5ed;
  color: var(--text-primary);
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
}

.leg-selector button:hover {
  background-color: var(--color-gold);
  color: white;
}

.leg-selector button.active {
  background-color: var(--color-gold);
  color: white;
  border-color: var(--color-gold);
}
</style>
