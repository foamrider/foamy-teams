"""Load the real Panel.qml twice (two monitors) in an isolated offscreen shell
on Omarchy 4.5 and check: one leader owns IPC and the window
tracker, the popup body builds lazily, the width does not change when
Settings opens, and quick successive saves are queued, never dropped, on both
the inline and the `omarchy bar set` paths.

  python3 tests/runtime.py

Runs on the installed /usr/share/omarchy/shell, or the tree in FOAMY_HOST_45.

Uses foamy-kit's preview harness (FOAMY_KIT, default ~/GitHub/Personal/foamy-kit):
temp HOME/XDG dirs, no Wayland/Hyprland variables, no host scripts run. The
`omarchy` CLI is a stub that only logs its arguments.
"""
import os
import sys
from pathlib import Path

plugin = Path(__file__).resolve().parents[1]
kit = Path(os.environ.get("FOAMY_KIT", Path.home() / "GitHub/Personal/foamy-kit"))
# The installed shell is 4.5; set before the harness reads it.
os.environ.setdefault("FOAMY_HOST_45", "/usr/share/omarchy/shell")
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
    ScreenSim { id: sim }
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
        if (!check(one.visible && shell.find(one, "teamsButton").dimmed, "closed accounts default to a clickable dim icon")) return
        shell.find(one, "teamsButton").triggerPress(Qt.LeftButton)
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
        // Each stub call sleeps 0.2 s; under load, wait for the queue (up to 18 s).
        if (two.saving && shell.waits++ < 60) { shell.step--; return }
        var log = Quickshell.env("FOAMY_CLI_LOG")
        logView.path = log
        logView.reload()
        var lines = logView.text().trim().split("\n")
        if (!check(lines.length === 2, "two CLI saves, got " + JSON.stringify(lines))) return
        if (!check(lines[0] === "bar set foamy.teams unreadFirst true --json" && lines[1] === "bar set foamy.teams showClosed false --json", "CLI order: " + JSON.stringify(lines))) return
        if (!check(!two.saving && two.prefs.error === "", "queue drained without error")) return
        // Dropdowns stay bound after a pick (kit 0.2.0 no longer assigns value).
        var pick = shell.find(popup.bodyItem, "defaultAccount")
        if (!check(pick.compact, "middle-click account uses the settings row form")) return
        shell.inline = true
        pick.changed("work")
        if (!check(pick.value === "work", "middle-click dropdown follows the saved value, got " + pick.value)) return
        popup.bodyItem.editAccount(shell.accounts[0])
        break
      case 7:
        var picker = shell.find(popup.bodyItem, "appIdPicker")
        picker.changed("teams-other")
        if (!check(picker.value === "teams-other", "picker shows the chosen window, got " + picker.value)) return
        popup.bodyItem.editAccount(shell.accounts[0])   // reopen the editor: draft resets
        if (!check(picker.value === "teams-work", "picker follows the draft after reopening, got " + picker.value)) return
        shell.find(popup.bodyItem, "teamsSettings").leaveEditor()
        var mode = shell.find(popup.bodyItem, "closedMode")
        if (!check(mode && mode.visible && mode.compact && mode.value === "mute", "closed mode defaults to Dim")) return
        mode.changed("hide")
        if (!check(mode.value === "hide" && one.preference("hideWhenClosed"), "Hide saves the existing preference")) return
        if (!check(one.visible, "open settings stay reachable in Hide mode")) return
        one.closeSettings(); one.close()
        break
      case 8:
        if (!check(!one.visible, "Hide removes the closed widget")) return
        // A running but unfocused window must restore the icon in either mode.
        Plugin.TeamsService.windows = [{ appId: "teams-work", title: "(3) Chat | Microsoft Teams", activated: false, toplevel: null }]
        break
      case 9:
        if (!check(one.visible && !shell.find(one, "teamsButton").dimmed && one.summary.totalUnread === 3, "unfocused running account restores the normal unread icon")) return
        Plugin.TeamsService.windows = []
        break
      case 10:
        if (!check(!one.visible && shell.find(one, "teamsButton").dimmed && one.summary.totalUnread === 0, "closing the last window clears unread and hides")) return
        one.openSettings()
        break
      case 11:
        if (!check(one.visible && one.editingSettings, "hidden widget remains reachable through settings")) return
        var mode = shell.find(popup.bodyItem, "closedMode")
        mode.changed("mute")
        if (!check(mode.value === "mute" && !one.preference("hideWhenClosed"), "Dim selection stays bound to saved preference")) return
        one.closeSettings(); one.close()
        break
      case 12:
        if (!check(one.visible && shell.find(one, "teamsButton").dimmed, "Dim keeps closed widget visible")) return
        // Invalid stored configuration must not hide the only repair path.
        two.settings = { accounts: [null], hideWhenClosed: true }
        if (!check(two.visible && two.configurationError !== "", "invalid configuration remains reachable")) return
        two.settings = { accounts: [], hideWhenClosed: true }
        if (!check(two.visible, "initial setup remains reachable")) return
        two.settings = { accounts: shell.accounts }
        break
      case 13:
        // A running account is focused through its toplevel; nothing launches.
        Plugin.TeamsService.windows = [{ appId: "teams-work", title: "Chat | Microsoft Teams", activated: false, toplevel: fakeWindow }]
        one.open()
        break
      case 14:
        one.openAccount(one.accounts[0])
        if (!check(fakeWindow.activations === 1 && !one.opened && one.launchingId === "" && one.launchError === "", "focus activates the window and closes the popup: " + fakeWindow.activations + " " + one.opened + " " + one.launchingId)) return
        Plugin.TeamsService.windows = []
        // A launcher that cannot start the client reports it (exit 127), never success.
        two.settings = { accounts: [Object.assign({}, shell.accounts[0], { command: ["foamy-teams-no-such-client"] })] }
        two.openAccount(two.accounts[0])
        if (!check(two.launchingId === "work", "launch starts, got " + two.launchingId)) return
        shell.waits = 0
        break
      case 15:
        // Up to 9 s: the exit-127 error, well before the 15 s no-window timeout.
        if (two.launchingId !== "" && shell.waits++ < 30) { shell.step--; return }
        if (!check(two.launchingId === "" && two.launchError === two.tr("Could not launch the account. Check its browser or launch arguments.") && two.opened, "failed launch shows its error: " + JSON.stringify([two.launchingId, two.launchError, two.opened]))) return
        two.close()
        // A title that keeps changing faster than the settle window must still
        // publish while it changes, not only after it stops.
        Plugin.TeamsService.matched = [fakeWindow]
        churn.start()
        break
      case 16:
        if (churn.running && shell.waits++ < 120) { shell.step--; return }
        if (!check(shell.publishedDuringChurn > 0, "settled updates publish during constant title changes, got " + shell.publishedDuringChurn)) return
        Plugin.TeamsService.matched = []
        console.log("FOAMY DONE")
        Qt.quit()
      }
    }
  }
  property real width0: 0
  property int waits: 0
  property int published: 0
  property int publishedDuringChurn: -1
  QtObject {
    id: fakeWindow
    property string appId: "teams-work"
    property string title: "(1) Chat | Microsoft Teams"
    property bool activated: false
    property int activations: 0
    function activate() { activations++ }
  }
  Connections {
    target: Plugin.TeamsService
    function onWindowsChanged() { if (churn.running) shell.published++ }
  }
  // 30 title changes 50 ms apart (1.5 s), each well inside the 250 ms settle window.
  Timer {
    id: churn
    interval: 50; repeat: true
    property int n: 0
    onTriggered: {
      fakeWindow.title = "(" + (++n) + ") Chat | Microsoft Teams"
      if (n >= 30) { shell.publishedDuringChurn = shell.published; stop() }
    }
  }
  function find(item, name) {
    if (!item) return null
    if (item.objectName === name) return item
    var kids = item.children || []
    for (var i = 0; i < kids.length; i++) { var hit = find(kids[i], name); if (hit) return hit }
    return null
  }
  FileView { id: logView; blockLoading: true; printErrors: false }
}
'''


def run():
    r = harness.Run("4.5", SHELL, plugin=plugin, prefix="foamy-teams-runtime-")
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
    print(f"foamy-teams runtime: {'pass' if ok else 'FAIL'}")
    r.cleanup()
    return ok


sys.exit(0 if run() else 1)
