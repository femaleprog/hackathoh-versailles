<template>
  <div class="chat-container card">
    <div class="chat-header">
      <h2>ROYALTY CHATBOT</h2>
    </div>

    <div class="message-list" ref="messageList">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message-wrapper"
        :class="message.sender === 'user' ? 'sent' : 'received'"
      >
        <div class="message-bubble">
          <p>{{ message.text }}</p>
        </div>
      </div>
    </div>

    <div class="input-area">
      <input
        type="text"
        v-model="newMessage"
        placeholder="Type your message..."
        @keyup.enter="sendMessage"
      />
      <button class="button-primary" @click="sendMessage">SEND</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";

// Reference to the message list DOM element for scrolling
const messageList = ref(null);

// Reactive state for the list of messages
const messages = ref([
  { id: 1, text: "Hello", sender: "bot" },
  { id: 2, text: "I'm a good chatbot", sender: "bot" },
  { id: 3, text: "thank you", sender: "user" },
]);

// Reactive state for the new message input
const newMessage = ref("");

// Function to scroll the message list to the bottom
const scrollToBottom = () => {
  nextTick(() => {
    const listEl = messageList.value;
    if (listEl) {
      listEl.scrollTop = listEl.scrollHeight;
    }
  });
};

// Function to add a new message to the list
const sendMessage = () => {
  if (newMessage.value.trim() === "") return;

  messages.value.push({
    id: Date.now(),
    text: newMessage.value,
    sender: "user", // For this demo, all new messages are from the user
  });

  newMessage.value = ""; // Clear the input field
  scrollToBottom();
};

// Scroll to bottom when the component is first mounted
onMounted(() => {
  scrollToBottom();
});
</script>

<style scoped>
/* Typography from Guideline */
h2 {
  font-family: "Playfair Display", serif;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: #34302d;
  font-weight: 600;
  margin: 0;
  text-align: center;
}

p {
  font-family: "Lato", sans-serif;
  font-size: 16px;
  line-height: 1.6;
  color: #34302d;
  margin: 0;
}

/* Layout & Spacing */
.chat-container {
  max-width: 600px;
  width: 100%;
  height: 80vh;
  max-height: 700px;
  display: flex;
  flex-direction: column;
  margin: 2rem;
  box-shadow: 0 4px 15px rgba(52, 48, 45, 0.05);
}

.chat-header {
  padding: 1.5rem;
  border-bottom: 1px solid #eae8e1;
}

.message-list {
  flex-grow: 1;
  padding: 2rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.input-area {
  display: flex;
  padding: 1.5rem;
  border-top: 1px solid #eae8e1;
  gap: 1rem;
}

/* Components: Cards (used for main container) */
.card {
  border: 1px solid #eae8e1;
  border-radius: 8px;
  background-color: #ffffff; /* Slightly whiter than body for contrast */
}

/* Chat-specific components */
.message-wrapper {
  display: flex;
  max-width: 75%;
}

.message-bubble {
  padding: 0.75rem 1.25rem;
  border-radius: 18px;
}

/* Sent Messages (User) */
.message-wrapper.sent {
  align-self: flex-end;
}
.message-wrapper.sent .message-bubble {
  background-color: #c5b38e; /* Accent / Call-to-Action color */
  color: #fdfbf5; /* Use light background color for text */
  border-bottom-right-radius: 4px;
}
.message-wrapper.sent .message-bubble p {
  color: #fdfbf5;
}

/* Received Messages (Bot) */
.message-wrapper.received {
  align-self: flex-start;
}
.message-wrapper.received .message-bubble {
  background-color: #eae8e1; /* Subtle Border/Line color */
  border-bottom-left-radius: 4px;
}

/* Input & Buttons */
input[type="text"] {
  flex-grow: 1;
  border: 1px solid #eae8e1;
  border-radius: 20px;
  padding: 0.75rem 1.25rem;
  font-family: "Lato", sans-serif;
  font-size: 16px;
  background-color: #fdfbf5;
  color: #34302d;
  transition: border-color 0.3s ease;
}

input[type="text"]:focus {
  outline: none;
  border-color: #c5b38e;
}

.button-primary {
  background-color: #c5b38e;
  color: #34302d;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 20px;
  font-family: "Lato", sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.button-primary:hover {
  background-color: #b9a57e; /* Slightly darker gold on hover */
}
</style>
