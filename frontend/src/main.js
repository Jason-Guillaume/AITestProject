import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import Particles from "@tsparticles/vue3";
import { loadSlim } from "@tsparticles/slim";
import App from "./App.vue";
import router from "./router";

import "./style.css";
import "./styles/cyber-ui.css";
import "./styles/dark-tech-dropdown.css";

const pinia = createPinia();

createApp(App)
  .use(pinia)
  .use(router)
  .use(ElementPlus)
  .use(Particles, {
    init: async (engine) => {
      await loadSlim(engine);
    },
  })
  .mount("#app");
