<template>
  <div class="main-layout-container" :class="{ 'map-is-open': isMapOpen }">
    <div id="chat-container">
      <header class="chat-header">
        <h1>Le Scribe Royal</h1>
        <p>Votre humble serviteur digital</p>
        <button @click="newConversation" class="new-chat-btn">
          Nouvelle Conversation
        </button>
        <button @click="toggleMap" class="map-toggle-btn">
          {{ isMapOpen ? "Fermer la Carte" : "Ouvrir la Carte" }}
        </button>
      </header>
      <MessageDisplay :messages="messages" />
      <UserInput @send-message="handleNewMessage" />
    </div>

    <div class="map-area" :class="{ 'is-open': isMapOpen }">
      <MapDisplay
        v-if="routeJson"
        :route-data="routeJson"
        :selected-leg-index="selectedLegIndex"
      />
      <div class="leg-details" v-if="currentLegDetails">
        <p>
          <span class="location-start">{{ currentLegDetails.start }}</span>
          <span class="arrow">→</span>
          <span class="location-end">{{ currentLegDetails.end }}</span>
        </p>
      </div>
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

<script setup>
import MessageDisplay from "@/components/MessageDisplay.vue";
import UserInput from "@/components/UserInput.vue";
import MapDisplay from "@/components/MapDisplay.vue";
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";

const emit = defineEmits(["conversation-updated"]);

// --- Props and Router ---
const props = defineProps({
  uuid: {
    type: String,
    required: true,
  },
});
const router = useRouter();

// --- Reactive State ---
const isMapOpen = ref(false);

const routeJson = ref(null);
const selectedLegIndex = ref(0);
const messages = ref([]);

// Backend base URL: use env if provided, else same origin
const backendApiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin;

// --- Functions ---
const selectLeg = (index) => {
  selectedLegIndex.value = index;
};

const toggleMap = () => {
  isMapOpen.value = !isMapOpen.value;
};

const newConversation = () => {
  router.push("/");
};

const currentLegDetails = computed(() => {
  const leg = routeJson.value?.routes?.[0]?.legs?.[selectedLegIndex.value];
  if (!leg) return null;
  return {
    start: leg.startPlaceDetails,
    end: leg.endPlaceDetails,
  };
});

// --- Conversation Memory Functions ---
const loadConversation = async () => {
  messages.value = [];
  try {
    const response = await fetch(
      `${backendApiUrl}/v1/conversations/${props.uuid}`
    );
    if (response.ok) {
      const history = await response.json();
      messages.value = history.map((msg) => ({
        id: Date.now() + Math.random(),
        text: msg.content,
        sender: msg.role === "assistant" ? "bot" : "user",
      }));
    } else if (response.status !== 404) {
      console.error("Failed to load conversation:", response.statusText);
    }
  } catch (error) {
    console.error("Error fetching conversation:", error);
  }
};

const saveConversation = async () => {
  if (messages.value.length === 0) return;
  const payload = messages.value.map((msg) => ({
    role: msg.sender === "bot" ? "assistant" : "user",
    content: msg.text,
  }));
  try {
    await fetch(`${backendApiUrl}/v1/conversations/${props.uuid}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    console.error("Failed to save conversation:", error);
  }
};

const handleNewMessage = async (newMessageText) => {
  messages.value.push({
    id: Date.now(),
    text: newMessageText,
    sender: "user",
  });

  // Build the OpenAI-style messages array from current history
  const apiMessages = messages.value.map((msg) => ({
    role: msg.sender === "bot" ? "assistant" : "user",
    content: msg.text,
  }));

  // Prepare a placeholder bot message to stream into
  const botMessageId = Date.now() + 1;
  messages.value.push({ id: botMessageId, text: "", sender: "bot" });

  try {
    const response = await fetch(`${backendApiUrl}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Accept streaming from backend; Authorization not needed (key stays server-side)
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        model: "mistral-medium", // backend ignores or selects appropriate model
        messages: apiMessages,
        stream: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    const currentBotMessage = messages.value.find((m) => m.id === botMessageId);

    // If backend doesn't stream, handle non-stream JSON once
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("text/event-stream") || !response.body) {
      const data = await response.json().catch(() => null);
      const reply =
        data?.choices?.[0]?.message?.content ??
        "(pas de réponse du serveur)";
      if (currentBotMessage) currentBotMessage.text = reply;
    } else {
      // Stream (SSE) handling
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.substring(6).trim();
          if (!data || data === "[DONE]") continue;

          try {
            const parsed = JSON.parse(data);

            if (parsed.object === "custom.walking_route") {
              routeJson.value = parsed.data;
              isMapOpen.value = true;
              selectLeg(0);
            } else {
              const delta = parsed?.choices?.[0]?.delta?.content;
              if (delta && currentBotMessage) {
                currentBotMessage.text += delta;
              }
            }
          } catch (e) {
            console.error("Could not parse stream chunk:", data, e);
          }
        }
      }
    }
  } catch (error) {
    console.error("Error calling backend:", error);
    const errorBotMessage = messages.value.find((m) => m.id === botMessageId);
    if (errorBotMessage) {
      errorBotMessage.text =
        "Hélas, une erreur est survenue lors de la communication avec le Scribe. Veuillez réessayer.";
    }
  } finally {
    await saveConversation();
    emit("conversation-updated");
  }
};

onMounted(() => {
  loadConversation();
});
watch(() => props.uuid, loadConversation);
</script>

<style scoped>
:root {
  --background-main: #f8f5ed;
  --text-primary: #3a3a3a;
  --color-gold: #b38e55;
  --color-dark-blue: #0a192f;
  --border-light: #e0d8c5;
}

.main-layout-container {
  display: flex;
  height: 100vh;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  border-left: 1px solid var(--border-light);
  border-right: 1px solid var(--border-light);
  background-color: var(--background-main);
  overflow: hidden;
  transition: max-width 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.main-layout-container.map-is-open {
  max-width: 100%;
  border-left: none;
  border-right: none;
}

#chat-container {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-width: 450px;
  background-color: var(--background-main);
  border-right: 1px solid var(--border-light);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  z-index: 2;
  position: relative;
}

.map-area {
  flex: 0 0 0;
  width: 0;
  opacity: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: flex-basis 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94),
    opacity 0.4s ease-in-out;
}

.map-area.is-open {
  flex-basis: 50%;
  opacity: 1;
}

.chat-header {
  position: relative;
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

.map-toggle-btn,
.new-chat-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  padding: 8px 16px;
  font-family: "Source Serif Pro", serif;
  font-weight: 600;
  border: 1px solid var(--border-light);
  background-color: white;
  color: var(--text-primary);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.map-toggle-btn {
  right: 20px;
}

.new-chat-btn {
  left: 20px;
}

.map-toggle-btn:hover,
.new-chat-btn:hover {
  background-color: var(--color-gold);
  border-color: var(--color-gold);
  color: white;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.leg-details {
  padding: 12px 20px;
  background-color: #fff;
  border-top: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
  text-align: center;
  flex-shrink: 0;
}

.leg-details p {
  margin: 0;
  font-family: "Source Serif Pro", serif;
  color: var(--text-primary);
  font-size: 1rem;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
}

.leg-details .arrow {
  color: var(--color-gold);
  font-weight: bold;
  font-size: 1.2rem;
}

.leg-selector {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px;
  background-color: #fff;
  flex-shrink: 0;
  white-space: nowrap;
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
