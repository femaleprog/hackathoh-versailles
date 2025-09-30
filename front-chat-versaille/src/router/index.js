import { createRouter, createWebHistory } from "vue-router";
import ChatView from "../views/ChatView.vue";
import { v4 as uuidv4 } from "uuid"; // Import UUID generator

const routes = [
  {
    path: "/",
    name: "Home",
    // This route will now redirect to a new chat session
    redirect: () => {
      return { path: `/chat/${uuidv4()}` };
    },
  },
  {
    // The chat view now accepts a dynamic UUID in the URL
    path: "/chat_interface/:uuid",
    name: "Chat",
    component: ChatView,
    props: true, // Pass route params as props to the component
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
