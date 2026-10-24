import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "JENS MATTE – 5.–7.",
    short_name: "JENS MATTE",
    description: "Adaptivt mattespill med 500 oppgaver og forklaringer steg for steg.",
    start_url: "/",
    display: "standalone",
    background_color: "#0b1021",
    theme_color: "#0b1021",
    orientation: "portrait",
    lang: "nb",
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
