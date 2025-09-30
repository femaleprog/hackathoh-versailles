<template>
  <div class="message-area" ref="messageArea">
    <div
      v-for="message in messages"
      :key="message.id"
      class="message-wrapper"
      :class="message.sender"
    >
      <div class="message-bubble">
        <div
          v-if="message.sender === 'bot' && !message.text"
          class="thinking-indicator"
        >
          Thinking...
        </div>
        <div v-else v-html="renderMarkdown(message.text)"></div>
      </div>
      <button
        v-if="message.sender === 'bot' && message.text"
        @click="speakMessage(message.text)"
        class="speak-button"
        aria-label="Speak message"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          class="speak-icon"
        >
          <path
            d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"
          />
        </svg>
      </button>
    </div>
  </div>
</template>

<script>
import { nextTick, ref, watch } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

export default {
  name: "MessageDisplay",
  props: {
    messages: {
      type: Array,
      required: true,
    },
  },
  setup(props) {
    const messageArea = ref(null);

    watch(
      () => props.messages.length,
      async () => {
        await nextTick();
        if (messageArea.value) {
          messageArea.value.scrollTop = messageArea.value.scrollHeight;
        }
      }
    );

    const renderMarkdown = (text) => {
      if (!text) return ""; // Ensure text is not null/undefined
      const rawHtml = marked.parse(text);
      const sanitizedHtml = DOMPurify.sanitize(rawHtml);
      return sanitizedHtml;
    };

    const speakMessage = (text) => {
      if (!text || !("speechSynthesis" in window)) {
        console.error("Speech synthesis not supported or no text provided.");
        return;
      }

      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = marked.parse(text);
      const textToSpeak = tempDiv.textContent || tempDiv.innerText || "";

      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      window.speechSynthesis.speak(utterance);
    };

    return { messageArea, renderMarkdown, speakMessage }; // ADDED speakMessage to return
  },
};
</script>

<style scoped>
:root {
  --text-primary: #3a3a3a;
  --border-light: #e0d8c5;
}

.message-area {
  flex-grow: 1;
  overflow-y: auto;
  padding: 25px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.message-wrapper {
  display: flex;
  flex-direction: column; /* MODIFIED: to stack bubble and button */
  max-width: 80%;
}

.message-wrapper.user {
  align-self: flex-end;
  align-items: flex-end; /* MODIFIED: align content to the right */
}

.message-wrapper.bot {
  align-self: flex-start;
  align-items: flex-start; /* MODIFIED: align content to the left */
}

.message-bubble {
  padding: 12px 18px;
  border-radius: 12px;
  font-family: "Source Serif Pro", serif;
  line-height: 1.6;
  font-size: 1rem;
}

.user .message-bubble {
  background-color: #e9e9eb;
  color: #000;
}

.bot .message-bubble {
  background-color: #ffffff;
  color: var(--text-primary);
  border: 1px solid var(--border-light);
}

.speak-button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  margin-top: 6px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  transition: background-color 0.2s ease;
}

.speak-button:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.speak-icon {
  width: 20px;
  height: 20px;
  fill: #555;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}

.thinking-indicator {
  color: #888;
  font-style: italic;
  animation: pulse 1.5s infinite;
}

.message-bubble :deep(p) {
  margin: 0 0 0.5em 0;
}
.message-bubble :deep(p:last-child) {
  margin-bottom: 0;
}

.message-bubble :deep(ul),
.message-bubble :deep(ol) {
  padding-left: 20px;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}
</style>
