<template>
  <form @submit.prevent="sendMessage" class="input-form">
    <input
      type="text"
      v-model="newMessage"
      placeholder="Écrivez votre message ici..."
      class="text-input"
    />
    <button type="submit" class="send-button">Envoyer</button>
  </form>
</template>

<script>
import { ref } from "vue";

export default {
  name: "UserInput",
  emits: ["send-message"],
  setup(props, { emit }) {
    const newMessage = ref("");

    const sendMessage = () => {
      if (newMessage.value.trim() !== "") {
        emit("send-message", newMessage.value);
        newMessage.value = "";
      }
    };

    return {
      newMessage,
      sendMessage,
    };
  },
};
</script>

<style scoped>
/* Inherit colors from ChatView */
:root {
  --background-main: #f8f5ed;
  --text-primary: #3a3a3a;
  --color-gold: #b38e55;
  --border-light: #e0d8c5;
}

.input-form {
  display: flex;
  padding: 20px;
  background-color: var(--background-main);
  border-top: 1px solid var(--border-light);
  flex-shrink: 0; /* Prevents input area from shrinking */
}

.text-input {
  flex-grow: 1;
  padding: 12px 20px;
  border-radius: 8px; /* Less rounded for a more formal look */
  border: 1px solid var(--border-light);
  background-color: #ffffff;
  color: var(--text-primary);
  font-family: "Source Serif Pro", serif;
  font-size: 1rem;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.text-input::placeholder {
  color: #999;
}

.text-input:focus {
  outline: none;
  border-color: var(--color-gold);
  box-shadow: 0 0 0 3px rgba(179, 142, 85, 0.2); /* Focus ring for accessibility */
}

.send-button {
  margin-left: 12px;
  padding: 12px 25px;
  border-radius: 8px;
  border: none;
  background-color: var(--color-gold);
  color: #ffffff;
  font-family: "Cormorant Garamond", serif;
  font-weight: bold;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.send-button:hover {
  background-color: #a17d4a; /* A darker shade of gold for hover */
}
</style>
