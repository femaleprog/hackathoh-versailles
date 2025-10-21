<template>
  <div class="main-layout-container" :class="{ 'map-is-open': isMapOpen }">
    <div id="chat-container">
      <header class="chat-header">
        <h1>Feels like Royalty</h1>
        <p>I plan your visit to Chateau de versailles so that you don't have to</p>
        <button @click="newConversation" class="new-chat-btn">
          New conversation
        </button>
        <button @click="toggleMap" class="map-toggle-btn">
          {{ isMapOpen ? "Fermer la Carte" : "Ouvrir la Carte" }}
        </button>
        <!-- Persona selection dropdown added here -->
         <select v-model="persona" class="persona-select">
          <option v-for="p in personas" :key="p.value" :value="p.value">
            {{ p.label }}
          </option>
         </select>
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

const props = defineProps({
  uuid: {
    type: String,
    required: true,
  },
});
const router = useRouter();

const isMapOpen = ref(false);
const routeJson = ref(null);
const selectedLegIndex = ref(0);
const messages = ref([]);

const backendApiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin;

const personas = [
  { value: "default", label: "Neutral" },
  { value: "marie_antoinette", label: "Marie-Antoinette" },
  { value: "louis_xiv", label: "Louis XIV" },
];
const persona = ref(localStorage.getItem("persona") || "default");
watch(persona, (v) => localStorage.setItem("persona", v));

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
  // 1) add user message
  messages.value.push({ id: Date.now(), text: newMessageText, sender: "user" });
  if (messages.value.length === 1) {
    await saveConversation();
    
  }
  // 2) build OpenAI-style history
  const apiMessages = messages.value.map((m) => ({
    role: m.sender === "bot" ? "assistant" : "user",
    content: m.text,
  }));

  // 3) placeholder bot message to stream into
  const botId = Date.now() + 1;
  messages.value.push({ id: botId, text: "", sender: "bot" });

  try {
    const res = await fetch(`${backendApiUrl}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        "X-Persona": persona.value,            // send selected persona
      },
      body: JSON.stringify({
        model: "mistral-medium",               // backend can override
        messages: apiMessages,
        stream: true,
      }),
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${body}`);
    }

    const getBot = () => messages.value.find((m) => m.id === botId);
    const ct = res.headers.get("content-type") || "";

    // 4) non-stream fallback
    if (!ct.includes("text/event-stream") || !res.body) {
      const data = await res.json().catch(() => null);
      getBot().text = data?.choices?.[0]?.message?.content ?? "(pas de réponse)";
      return;
    }

    // 5) SSE streaming
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop(); // keep last incomplete part

      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const data = part.slice(6).trim();
        if (!data || data === "[DONE]") continue;

        try {
          const j = JSON.parse(data);

          if (j.object === "custom.walking_route") {
            routeJson.value = j.data;
            isMapOpen.value = true;
            selectedLegIndex.value = 0;
          } else {
            const delta = j?.choices?.[0]?.delta?.content;
            if (delta) getBot().text += delta;
          }
        } catch (e) {
          console.error("SSE parse error:", e, data);
        }
      }
    }
  } catch (err) {
    console.error(err);
    const b = messages.value.find((m) => m.id === botId);
    if (b) b.text = "Hélas, une erreur est survenue. Veuillez réessayer.";
  } finally {
    await saveConversation();
    emit("conversation-updated");
  }
};

// Function to refresh conversation list (optional)
const fetchConversationsList = async () => {
  const response = await fetch(`${backendApiUrl}/v1/conversations`);
  const data = await response.json();
  conversations.value = data;  // Refresh the conversation list with updated data
};

onMounted(loadConversation);
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
.persona-select 
{ position: absolute;
 right: 160px; top: 50%;
  transform: translateY(-50%);
  padding: 6px 10px;
  border: 1px solid var(--border-light); 
  border-radius: 6px; 
  background: #fff; 
  font-family: "Source Serif Pro", serif; }
  /* Add position relative to the list item to ensure absolute positioning works correctly */
.conversation-item {
  position: relative;  /* Add this to allow absolute positioning of the 3 dots */
}

.conversation-item:hover .three-dots-menu {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  z-index: 10; /* Increase z-index for visibility */
}

/* Styling for the 3 dots menu */
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
  z-index: 1; /* Ensuring it's above other content */
}

</style>
