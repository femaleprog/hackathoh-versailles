<template>
  <div class="message-area" ref="messageArea">
    <div
      v-for="message in messages"
      :key="message.id"
      class="message-wrapper"
      :class="message.sender"
    >
      <div class="message-bubble">
        <p>{{ message.text }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { nextTick, ref, watch } from "vue";

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

    // Auto-scroll to the bottom when new messages are added
    watch(
      () => props.messages.length,
      async () => {
        await nextTick();
        if (messageArea.value) {
          messageArea.value.scrollTop = messageArea.value.scrollHeight;
        }
      }
    );

    return { messageArea };
  },
};
</script>

<style scoped>
/* Inherit colors from ChatView */
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
  max-width: 80%; /* Modern chat UIs use a wider bubble */
}

.message-wrapper.user {
  align-self: flex-end;
  justify-content: flex-end;
}

.message-wrapper.bot {
  align-self: flex-start;
  justify-content: flex-start;
}

.message-bubble {
  padding: 12px 18px;
  border-radius: 12px; /* Softer, more modern radius */
  font-family: "Source Serif Pro", serif;
  line-height: 1.6;
  font-size: 1rem;
}

/* Modern, clean look inspired by ChatGPT/Mistral */
.user .message-bubble {
  background-color: #e9e9eb; /* Neutral grey for user */
  color: #000;
}

.bot .message-bubble {
  background-color: #ffffff; /* Clean white for bot */
  color: var(--text-primary);
  border: 1px solid var(--border-light);
}

.message-bubble p {
  margin: 0;
}
</style>
