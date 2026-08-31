/// <reference types="vite/client" />

// Déclaration pour @tailwindcss/vite qui utilise .d.mts
declare module "@tailwindcss/vite" {
  import { Plugin } from "vite";
  export default function tailwindcss(options?: any): Plugin;
}
