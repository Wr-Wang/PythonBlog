import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { initFontSize, initTheme } from "./theme.js";
import "./style.css";

initTheme();
initFontSize();

createApp(App).use(router).mount("#app");
