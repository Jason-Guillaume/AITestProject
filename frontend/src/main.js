import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import Particles from "@tsparticles/vue3";
import { loadSlim } from "@tsparticles/slim";
import App from "./App.vue";
import router from "./router";
import { vContextmenuBlockNative } from "./directives/contextmenuBlockNative.js";

import "./style.css";
import "./styles/cyber-ui.css";
import "./styles/dark-tech-dropdown.css";
import "./assets/styles/theme.css";

const pinia = createPinia();

const app = createApp(App);
app.directive("contextmenu-block-native", vContextmenuBlockNative);
app
  .use(pinia)
  .use(router)
  .use(ElementPlus)
  .use(Particles, {
    init: async (engine) => {
      await loadSlim(engine);
    },
  })
  .mount("#app");
