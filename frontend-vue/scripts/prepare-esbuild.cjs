/**
 * Windows: unblock esbuild.exe (fixes "spawn EPERM" from SmartScreen / MOTW).
 * Re-runs esbuild install if the platform binary is missing.
 */
const { execSync, spawnSync } = require("child_process");
const { existsSync } = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const platformPkg =
  process.platform === "win32"
    ? "@esbuild/win32-x64"
    : process.platform === "darwin"
      ? process.arch === "arm64"
        ? "@esbuild/darwin-arm64"
        : "@esbuild/darwin-x64"
      : "@esbuild/linux-x64";

const binName = process.platform === "win32" ? "esbuild.exe" : "esbuild";
const esbuildBin = path.join(root, "node_modules", platformPkg, binName);

if (process.platform === "win32" && existsSync(esbuildBin)) {
  try {
    execSync(
      `powershell -NoProfile -Command "Unblock-File -LiteralPath '${esbuildBin.replace(/'/g, "''")}'"`,
      { stdio: "ignore" },
    );
  } catch {
    /* ignore */
  }
}

if (!existsSync(esbuildBin)) {
  const install = path.join(root, "node_modules", "esbuild", "install.js");
  if (existsSync(install)) {
    spawnSync(process.execPath, [install], { cwd: root, stdio: "inherit" });
  }
}
