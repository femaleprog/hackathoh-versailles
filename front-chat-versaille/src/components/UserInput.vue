<template>
  <form @submit.prevent="sendMessage" class="input-form">
    <div class="input-container">
      <input
        type="text"
        v-model="newMessage"
        placeholder="Écrivez votre message ou utilisez le micro..."
        class="text-input"
      />
      <button
        type="button"
        @click="toggleRecording"
        :class="{ 'mic-button': true, 'is-recording': isRecording }"
        aria-label="Start voice input"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          height="24"
          viewBox="0 0 24 24"
          width="24"
          fill="currentColor"
        >
          <path d="M0 0h24v24H0z" fill="none" />
          <path
            d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.49 6-3.31 6-6.72h-1.7z"
          />
        </svg>
      </button>
    </div>
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
    const isRecording = ref(false);

    const backendApiUrl =
      import.meta.env.VITE_API_BASE_URL || window.location.origin;

    let mediaRecorder = null;
    let audioChunks = [];

    const sendMessage = () => {
      if (newMessage.value.trim() !== "") {
        emit("send-message", newMessage.value);
        newMessage.value = "";
      }
    };

    const transcribeAudio = async (audioFile) => {
      try {
        newMessage.value = "Transcription en cours...";
        const formData = new FormData();
        formData.append(
          "file",
          audioFile,
          audioFile.name || "user_recording.webm"
        );
        const response = await fetch(`${backendApiUrl}/v1/audio/transcribe`, {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          const errorBody = await response.text().catch(() => "");
          throw new Error(
            `HTTP ${response.status}${errorBody ? `: ${errorBody}` : ""}`
          );
        }
        const data = await response.json();
        newMessage.value = data?.text || "";
      } catch (error) {
        console.error("Error during transcription:", error);
        newMessage.value = "Erreur de transcription. Veuillez réessayer.";
      }
    };

    const toggleRecording = async () => {
      if (isRecording.value) {
        // --- STOP RECORDING ---
        mediaRecorder.stop();
        isRecording.value = false;
        console.log("Recording stopped.");
      } else {
        // --- START RECORDING ---
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
          });
          isRecording.value = true;
          console.log("Recording started...");
          audioChunks = []; // Clear previous recording chunks

          mediaRecorder = new MediaRecorder(stream);

          mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
          };

          mediaRecorder.onstop = async () => {
            // Combine all chunks into a single audio file
            const audioBlob = new Blob(audioChunks, { type: "audio/mp3" }); // Or 'audio/webm', etc.
            const audioFile = new File([audioBlob], "user_recording.mp3", {
              type: "audio/mp3",
            });

            // Send the file for transcription
            await transcribeAudio(audioFile);

            // Stop the microphone track to turn off the browser's recording indicator
            stream.getTracks().forEach((track) => track.stop());
          };

          mediaRecorder.start();
        } catch (error) {
          console.error("Error accessing microphone:", error);
          alert(
            "L'accès au microphone est nécessaire pour l'enregistrement. Veuillez autoriser l'accès."
          );
          isRecording.value = false;
        }
      }
    };

    return {
      newMessage,
      isRecording,
      sendMessage,
      toggleRecording,
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
  align-items: center; /* Align items vertically */
  padding: 20px;
  background-color: var(--background-main);
  border-top: 1px solid var(--border-light);
  flex-shrink: 0; /* Prevents input area from shrinking */
  flex: 1 1 auto;
  width: 100%;
}

.input-container {
  position: relative;
  display: flex;
  flex-grow: 1;
  align-items: center;
  width: 100%;
  flex: 1 1 auto;
}

.text-input {
  flex-grow: 1;
  width: 100%;
  padding: 12px 50px 12px 20px; /* Increased right padding for the mic */
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

.mic-button {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  transition: color 0.3s ease;
}

.mic-button:hover {
  color: var(--text-primary);
}

.mic-button.is-recording {
  color: var(--color-gold);
  animation: pulse 1.5s infinite;
}

/* Optional pulse animation for recording state */
@keyframes pulse {
  0% {
    transform: translateY(-50%) scale(1);
  }
  50% {
    transform: translateY(-50%) scale(1.1);
  }
  100% {
    transform: translateY(-50%) scale(1);
  }
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
