/**
 * Application entry point.
 *
 * Fonts are bundled via @fontsource rather than loaded from a CDN, so the
 * application runs with no network access -- a requirement of the brief and a
 * practical benefit when demoing on university wifi.
 *
 * Latin subsets only. The full imports pull Cyrillic, Greek and Vietnamese
 * faces the interface never renders, adding ~26 files to the bundle for no
 * benefit. Add a subset here if the UI is ever localised.
 */

import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
import "@/index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "@/App";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root element #root not found in index.html");
}

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
