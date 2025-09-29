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
    const selectedLegIndex = ref(0);

    const messages = ref([
      {
        id: 1,
        text: "Bonjour, Noble Visiteur. Comment puis-je vous assister en ce jour radieux ?",
        sender: "bot",
      },
    ]);

    const selectLeg = (index) => {
      selectedLegIndex.value = index;
    };

    const apiKey = import.meta.env.VITE_MISTRAL_API_KEY;
    const mistralApiUrl = "https://api.mistral.ai/v1/chat/completions";

    const handleNewMessage = async (newMessageText) => {
      // 1. Add user message to the UI
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

      // 2. Prepare the full conversation history for the API
      const apiMessages = messages.value.map((msg) => ({
        role: msg.sender === "bot" ? "assistant" : "user",
        content: msg.text,
      }));

      try {
        const response = await fetch(mistralApiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({
            model: "mistral-medium-latest",
            messages: apiMessages, // Send the entire history
            stream: true, // Enable streaming
          }),
        });

        if (!response.ok) {
          throw new Error(`API request failed with status ${response.status}`);
        }

        // 3. Handle the streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        // Add a new, empty bot message to the UI
        const botMessageId = Date.now() + 1;
        messages.value.push({
          id: botMessageId,
          text: "",
          sender: "bot",
        });

        // Find the message we just added to append chunks to it
        const currentBotMessage = messages.value.find(
          (m) => m.id === botMessageId
        );

        // Read the stream
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });

          // The API sends data in SSE (Server-Sent Events) format.
          // Each message is prefixed with "data: " and ends with "\n\n".
          const lines = chunk.split("\n\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.substring(6);
              if (data.trim() === "[DONE]") {
                return; // Stream finished
              }
              try {
                const parsed = JSON.parse(data);
                const content = parsed.choices[0]?.delta?.content;
                if (content && currentBotMessage) {
                  // Append the content chunk to the bot message's text
                  currentBotMessage.text += content;
                }
              } catch (e) {
                console.error("Could not parse stream chunk:", data, e);
              }
            }
          }
        }
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
      selectedLegIndex,
      selectLeg,
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
