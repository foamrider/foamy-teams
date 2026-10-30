"""Load the real Panel.qml twice (two monitors) in an isolated offscreen shell
on a chosen Omarchy host and check: one leader owns IPC and the window
tracker, the popup body builds lazily, the width does not change when
Settings opens, and quick successive saves are queued, never dropped, on both
the inline and the `omarchy bar set` paths.

  python3 tests/runtime.py [4.0|4.5]      (default: both)

Uses foamy-kit's preview harness (FOAMY_KIT, default ~/GitHub/Personal/foamy-kit):
temp HOME/XDG dirs, no Wayland/Hyprland variables, no host scripts run. The
`omarchy` CLI is a stub that only logs its arguments.
"""
import json
import os
import sys
from pathlib import Path

plugin = Path(__file__).resolve().parents[1]
kit = Path(os.environ.get("FOAMY_KIT", Path.home() / "GitHub/Personal/foamy-kit"))
sys.path.insert(0, str(kit / "preview"))
import harness  # noqa: E402

SHELL = r'''import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "harness"
import "plugin" as Plugin
import "plugin/kit" as Kit

ShellRoot {
  id: shell
  property int step: 0
  property var calls: []
  property bool inline: true
  function fail(message) { console.log("FOAMY FAIL " + message); Qt.quit() }
  function check(condition, message) { if (!condition) fail(message); return condition }

  FloatingWindow {
    implicitWidth: 1920; implicitHeight: 1080
    ScreenSim { id: sim; fullScreenBar: Quickshell.env("FOAMY_HOST") === "4.5" }
    Plugin.Panel { id: one; x: 1400; y: 4; width: 30; height: 26 }
    Plugin.Panel { id: two; x: 1440; y: 4; width: 30; height: 26 }
  }

  MockBar {
    id: bar
    shell: QtObject {
      function updateEntryInline(id, settings) {
        shell.calls = shell.calls.concat([{ id: id, settings: JSON.parse(JSON.stringify(settings)) }])
        return shell.inline
      }
    }
  }

  readonly property var accounts: [{ id: "work", name: "Work", appId: "teams-work", enabled: true, browser: "omarchy-launch-webapp", profile: "", url: "https://teams.microsoft.com", command: [] }]

  Component.onCompleted: {
    for (var p of [one, two]) { p.bar = bar; p.moduleName = "foamy.teams"; p.settings = { accounts: shell.accounts, showCount: true } }
    tick.start()
  }

  function ipcEnabled(panel) {
    for (var i = 0; i < panel.data.length; i++) {
      var o = panel.data[i]
      if (o && String(o).indexOf("FoamyIpc") === 0) return o.enabled
    }
    return null
  }

  Timer {
    id: tick
    interval: 300; repeat: true
    onTriggered: {
      var popup = one.popup
      switch (shell.step++) {
      case 0:
        if (!check(ipcEnabled(one) !== ipcEnabled(two) && ipcEnabled(one) !== null, "exactly one IPC leader " + ipcEnabled(one) + " " + ipcEnabled(two))) return
        if (!check(JSON.stringify(Plugin.TeamsService.trackedAppIds) === '["teams-work"]', "tracker follows configured ids: " + JSON.stringify(Plugin.TeamsService.trackedAppIds))) return
        if (!check(popup && popup.bodyItem === null, "body not built before first open " + popup + " " + one.data.concat(one.children).map(String).join(","))) return
        if (!check(Plugin.TeamsService.candidatesWanted === false, "no picker list while closed")) return
        one.open()
        break
      case 1:
        if (!check(popup.bodyItem !== null, "body built on open")) return
        shell.width0 = popup.contentWidth
        one.openSettings()
        break
      case 2:
        if (!check(popup.contentWidth === shell.width0, "width stays " + shell.width0 + " in Settings, got " + popup.contentWidth)) return
        if (!check(Plugin.TeamsService.candidatesWanted === true, "picker list while Settings is open")) return
        // Inline path: the shell entry does not update yet; the second save must carry the first.
        one.savePreference("showCount", false)
        one.savePreference("showContext", true)
        if (!check(shell.calls.length === 2, "two inline saves, got " + shell.calls.length)) return
        if (!check(shell.calls[1].settings.showCount === false && shell.calls[1].settings.showContext === true, "second inline save keeps the first: " + JSON.stringify(shell.calls[1].settings))) return
        if (!check(shell.calls[1].settings.accounts.length === 1, "inline save keeps accounts")) return
        // CLI path: both saves run, one after another.
        shell.inline = false
        two.savePreference("unreadFirst", true)
        two.savePreference("showClosed", false)
        if (!check(two.saving, "second CLI save queued while the first runs")) return
        break
      case 3: case 4: case 5:
        break
      case 6:
        var log = Quickshell.env("FOAMY_CLI_LOG")
        logView.path = log
        logView.reload()
        var lines = logView.text().trim().split("\n")
        if (!check(lines.length === 2, "two CLI saves, got " + JSON.stringify(lines))) return
        if (!check(lines[0] === "bar set foamy.teams unreadFirst true --json" && lines[1] === "bar set foamy.teams showClosed false --json", "CLI order: " + JSON.stringify(lines))) return
        if (!check(!two.saving && two.settingsError === "", "queue drained without error")) return
        one.closeSettings(); one.close()
        console.log("FOAMY DONE")
        Qt.quit()
      }
    }
  }
  property real width0: 0
  FileView { id: logView; blockLoading: true; printErrors: false }
}
'''


def run(host):
    r = harness.Run(host, SHELL,
                    plugin=plugin, prefix=f"foamy-teams-runtime-{host}-")
    stub = r.base / "bin"
    stub.mkdir()
    log = r.base / "cli.log"
    (stub / "omarchy").write_text('#!/bin/sh\nsleep 0.2\necho "$*" >> "$FOAMY_CLI_LOG"\n')
    (stub / "omarchy").chmod(0o755)
    r.env["PATH"] = f"{stub}:{r.env['PATH']}"
    r.env["FOAMY_CLI_LOG"] = str(log)
    r.run(timeout=30)
    ok = r.ok
    for line in r.log.splitlines():
        if ("WARN" in line or "rror" in line) and "wl_display" not in line and "window masks" not in line:
            print("  log:", line.strip())
    if not ok:
        print(r.log)
    print(f"foamy-teams runtime {host}: {'pass' if ok else 'FAIL'}")
    r.cleanup()
    return ok


hosts = sys.argv[1:] or ["4.0", "4.5"]
sys.exit(0 if all([run(h) for h in hosts]) else 1)
