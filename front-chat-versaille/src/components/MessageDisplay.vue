<template>
  <div class="message-area" ref="messageArea">
    <div
      v-for="message in messages"
      :key="message.id"
      class="message-wrapper"
      :class="message.sender"
    >
      <div class="message-bubble" v-html="renderMarkdown(message.text)"></div>
    </div>
  </div>
</template>

<script>
import { nextTick, ref, watch } from "vue";
import { marked } from "marked"; // Import the marked library
import DOMPurify from "dompurify"; // Import DOMPurify for security

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
      const rawHtml = marked.parse(text);
      const sanitizedHtml = DOMPurify.sanitize(rawHtml);
      return sanitizedHtml;
    };

    return { messageArea, renderMarkdown };
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
  max-width: 80%;
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
