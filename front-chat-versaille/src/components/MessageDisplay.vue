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
.message-area {
  flex-grow: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message-wrapper {
  display: flex;
  max-width: 70%;
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
  border-radius: 20px;
  font-family: "Source Serif Pro", serif;
  line-height: 1.5;
}

.user .message-bubble {
  background-color: #003366; /* Deep Royal Blue */
  color: #f0e6d2; /* Cream */
  border-bottom-right-radius: 5px;
}

.bot .message-bubble {
  background-color: #fdf6e3; /* Light Cream */
  color: #3a2d0b;
  border: 1px solid #d4af37;
  border-bottom-left-radius: 5px;
}
</style>
