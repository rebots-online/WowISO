// Screen renderers for wowiso GUI. Each returns an HTMLElement tree
// and wires its controls to the Tauri backend via @tauri-apps/api/core invoke
// + event listening. The backend shells to `wowiso` (locally) or
// `wsl.exe -d Ubuntu-24.04 -- wowiso …` (Windows) — see src-tauri/src/wsl.rs.
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

function el(tag: string, cls?: string, text?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function logPane(): { node: HTMLElement; append: (s: string) => void } {
  const pre = el("pre", "log") as HTMLPreElement;
  pre.textContent = "(no output yet)";
  return {
    node: pre,
    append: (s: string) => {
      if (pre.textContent === "(no output yet)") pre.textContent = "";
      pre.textContent += s + "\n";
      pre.scrollTop = pre.scrollHeight;
    },
  };
}

async function runStreaming(
  cmd: "start_capture" | "start_build",
  args: Record<string, unknown>,
  log: (s: string) => void,
  status: (s: string) => void
): Promise<void> {
  const unlisten = await listen<string>("progress", (e) => log(e.payload));
  try {
    status("running…");
    const code = await invoke<number>(cmd, args);
    log(`[exit ${code}]`);
    status(code === 0 ? "done" : `failed (exit ${code})`);
  } catch (err) {
    log(`[error] ${String(err)}`);
    status("error");
  } finally {
    unlisten();
  }
}

export function captureScreen(): HTMLElement {
  const root = el("section");
  root.append(el("h2", undefined, "Capture this box"));
  root.append(el("p", undefined, "Run apt/snap/flatpak + tree + adapter capture into a profile."));
  const profile = el("input") as HTMLInputElement;
  profile.value = "dev";
  const f = el("div", "field", "Profile");
  f.append(profile);
  root.append(f);
  const log = logPane();
  const btn = el("button", "primary", "Capture") as HTMLButtonElement;
  btn.onclick = () =>
    runStreaming("start_capture", { profile: profile.value }, log.append, setStatus);
  root.append(btn, log.node);
  return root;
}

export function pickScreen(): HTMLElement {
  const root = el("section");
  root.append(el("h2", undefined, "Pick (tree picker)"));
  root.append(
    el("p", undefined, "The Textual/gum tree picker runs in your terminal. On Windows it opens inside the WSL distro.")
  );
  const btn = el("button", "primary", "Open picker") as HTMLButtonElement;
  const log = logPane();
  btn.onclick = () => runStreaming("start_pick", {}, log.append, setStatus);
  root.append(btn, log.node);
  return root;
}

export function buildScreen(): HTMLElement {
  const root = el("section");
  root.append(el("h2", undefined, "Build artifact"));
  const profile = el("input") as HTMLInputElement;
  profile.value = "dev";
  const base = el("input") as HTMLInputElement;
  base.placeholder = "/path/to/ubuntu-24.04-base.iso";
  const mode = el("select") as HTMLSelectElement;
  mode.append(...["repo", "live", "image"].map((m) => {
    const o = el("option") as HTMLOptionElement; o.value = m; o.textContent = m; return o;
  }));
  const emit = el("select") as HTMLSelectElement;
  emit.append(...["iso", "usb", "netboot"].map((m) => {
    const o = el("option") as HTMLOptionElement; o.value = m; o.textContent = m; return o;
  }));
  for (const [lbl, node] of [["Profile", profile], ["Base ISO", base], ["Mode", mode], ["Emit", emit]] as const) {
    const f = el("div", "field", lbl); f.append(node); root.append(f);
  }
  const log = logPane();
  const btn = el("button", "primary", "Build") as HTMLButtonElement;
  btn.onclick = () =>
    runStreaming(
      "start_build",
      { profile: profile.value, base: base.value, mode: mode.value, emit: emit.value },
      log.append,
      setStatus
    );
  root.append(btn, log.node);
  return root;
}

export function netbootScreen(): HTMLElement {
  const root = el("section");
  root.append(el("h2", undefined, "Netboot / iVentoy"));
  root.append(el("p", undefined, "Publish a profile's netboot artifacts (iPXE/HTTP)."));
  const profile = el("input") as HTMLInputElement; profile.value = "dev";
  const httpRoot = el("input") as HTMLInputElement; httpRoot.placeholder = "/var/www/netboot";
  for (const [lbl, node] of [["Profile", profile], ["HTTP root", httpRoot]] as const) {
    const f = el("div", "field", lbl); f.append(node); root.append(f);
  }
  const log = logPane();
  const btn = el("button", "primary", "Publish") as HTMLButtonElement;
  btn.onclick = () =>
    runStreaming("start_netboot", { profile: profile.value, httpRoot: httpRoot.value }, log.append, setStatus);
  root.append(btn, log.node);
  return root;
}

export function wslScreen(): HTMLElement {
  const root = el("section");
  root.append(el("h2", undefined, "WSL2 setup"));
  root.append(
    el("p", undefined, "On Windows, wowiso runs its Python core inside a WSL2 Ubuntu-24.04 distro. " +
      "Ensure the distro exists and the core + toolchain are installed.")
  );
  const log = logPane();
  const btn = el("button", "primary", "Ensure WSL ready") as HTMLButtonElement;
  btn.onclick = async () => {
    log.append("checking WSL2…");
    try {
      const msg = await invoke<string>("wsl_ensure_ready");
      log.append(msg);
      setStatus("WSL ready");
    } catch (err) {
      log.append(`[error] ${String(err)}`);
      setStatus("WSL not ready");
    }
  };
  root.append(btn, log.node);
  return root;
}

export async function aboutScreen(): Promise<HTMLElement> {
  const root = el("section");
  root.append(el("h2", undefined, "About"));
  let version = "v…";
  try { version = await invoke<string>("get_version"); } catch { /* keep fallback */ }
  root.append(
    el("p", undefined, `WowISO ${version}`),
    el("p", undefined, "Custom Ubuntu 24.04 installer / live-USB / bare-metal-restore builder."),
    el("p", undefined, "Copyright (C) 2025–2026 Robin L. M. Cheung, MBA. All rights reserved."),
    el("p", undefined, "Windows build hosts the Python core in WSL2; the Linux build runs it locally.")
  );
  return root;
}

// status reporter injected into the status bar by main.ts
let setStatus: (s: string) => void = () => {};
export function bindStatus(fn: (s: string) => void): void { setStatus = fn; }
