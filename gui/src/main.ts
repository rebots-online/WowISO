// wowiso GUI entry. Wires navigation, theme toggle, platform token,
// and the version tag in the status bar (bottom-right, per CLAUDE.md).
import { invoke } from "@tauri-apps/api/core";
import {
  captureScreen, pickScreen, buildScreen, netbootScreen, wslScreen,
  aboutScreen, bindStatus,
} from "./screens";

const platform = detectPlatform();
document.body.dataset.platform = platform;

function detectPlatform(): "windows" | "linux" | "darwin" {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("win")) return "windows";
  if (ua.includes("mac")) return "darwin";
  return "linux";
}

function applyTheme(mode: "system" | "light" | "dark"): void {
  const root = document.documentElement;
  root.classList.remove("auto", "light", "dark");
  if (mode === "system") root.classList.add("auto");
  else root.classList.add(mode);
}

const stored = (localStorage.getItem("theme") as "system" | "light" | "dark") || "system";
applyTheme(stored);
(document.getElementById("theme-mode") as HTMLSelectElement).value = stored;
(document.getElementById("theme-mode") as HTMLSelectElement).onchange = (e) => {
  const v = (e.target as HTMLSelectElement).value as "system" | "light" | "dark";
  localStorage.setItem("theme", v);
  applyTheme(v);
};

const main = document.getElementById("main")!;
const statusText = document.getElementById("status-text")!;
bindStatus((s: string) => { statusText.textContent = s; });

const screens: Record<string, () => HTMLElement | Promise<HTMLElement>> = {
  capture: captureScreen,
  pick: pickScreen,
  build: buildScreen,
  netboot: netbootScreen,
  wsl: wslScreen,
  about: aboutScreen,
};

async function show(name: string): Promise<void> {
  main.replaceChildren();
  const factory = screens[name] ?? aboutScreen;
  main.append(await factory());
}

document.querySelectorAll("#nav button").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll("#nav button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    show(b.dataset.screen!);
  });
});

// initial screen + version
(async () => {
  const first = document.querySelector("#nav button") as HTMLButtonElement;
  first.classList.add("active");
  await show(first.dataset.screen!);
  try {
    document.getElementById("version-tag")!.textContent = await invoke<string>("get_version");
  } catch {
    document.getElementById("version-tag")!.textContent = "wowiso (local)";
  }
})();
