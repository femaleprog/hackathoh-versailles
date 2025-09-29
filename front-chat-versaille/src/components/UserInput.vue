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
.input-form {
  display: flex;
  padding: 15px;
  background-color: rgba(10, 25, 47, 0.8);
  border-top: 2px solid #d4af37;
}

.text-input {
  flex-grow: 1;
  padding: 12px 15px;
  border-radius: 20px;
  border: 1px solid #d4af37;
  background-color: #fdf6e3;
  color: #3a2d0b;
  font-family: "Source Serif Pro", serif;
  font-size: 1rem;
}

.text-input::placeholder {
  color: #8c7d5b;
}

.send-button {
  margin-left: 10px;
  padding: 12px 25px;
  border-radius: 20px;
  border: none;
  background-color: #d4af37; /* Gold */
  color: #0a192f; /* Dark Blue */
  font-family: "Cormorant Garamond", serif;
  font-weight: bold;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.send-button:hover {
  background-color: #c09d2e;
}
</style>
