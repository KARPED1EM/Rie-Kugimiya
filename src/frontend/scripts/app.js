// @ts-check
import { createApp } from "./core/appCore.js";

window.addEventListener("DOMContentLoaded", () => {
  createApp()
    .init()
    .catch((error) => {
      // eslint-disable-next-line no-console
      console.error("Fatal init error", error);
    });
});

