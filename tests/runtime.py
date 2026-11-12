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
    shell.next()
  }

  function ipcEnabled(panel) {
    for (var i = 0; i < panel.data.length; i++) {
      var o = panel.data[i]
      if (o && String(o).indexOf("FoamyIpc") === 0) return o.enabled
    }
    return null
  }

  FoamyWait { id: wait }

  // Each step acts, then waits for the state it expects instead of a fixed
  // tick, so a loaded machine only makes the run slower, never wrong.
  function next() {
    var run = shell.steps[shell.step++]
    if (run) Qt.callLater(run)
  }
  // Waits up to `ms` for `condition`; on timeout fails with `message` plus detail().
  function expect(condition, ms, message, detail) {
    wait.waitFor(condition, ms, function(ok) {
      if (shell.check(ok, message + (detail ? ": " + detail() : ""))) shell.next()
    })
  }

  readonly property var steps: [
    function() {
      if (!check(ipcEnabled(one) !== ipcEnabled(two) && ipcEnabled(one) !== null, "exactly one IPC leader " + ipcEnabled(one) + " " + ipcEnabled(two))) return
      if (!check(JSON.stringify(Plugin.TeamsService.trackedAppIds) === '["teams-work"]', "tracker follows configured ids: " + JSON.stringify(Plugin.TeamsService.trackedAppIds))) return
      if (!check(one.popup && one.popup.bodyItem === null, "body not built before first open")) return
      if (!check(Plugin.TeamsService.candidatesWanted === false, "no picker list while closed")) return
      if (!check(one.visible && shell.find(one, "teamsButton").dimmed, "closed accounts default to a clickable dim icon")) return
      shell.find(one, "teamsButton").triggerPress(Qt.LeftButton)
      expect(function() { return one.popup.bodyItem !== null }, 5000, "body built on open")
    },
    function() {
      shell.width0 = one.popup.contentWidth
      one.openSettings()
      expect(function() { return Plugin.TeamsService.candidatesWanted }, 5000, "picker list while Settings is open")
    },
    function() {
      if (!check(one.popup.contentWidth === shell.width0, "width stays " + shell.width0 + " in Settings, got " + one.popup.contentWidth)) return
      // Inline path: the shell entry does not update yet; the second save must carry the first.
      one.savePreference("showCount", false)
      one.savePreference("showContext", true)
      if (!check(shell.calls.length === 2, "two inline saves, got " + shell.calls.length)) return
      if (!check(shell.calls[1].settings.showCount === false && shell.calls[1].settings.showContext === true, "second inline save keeps the first: " + JSON.stringify(shell.calls[1].settings))) return
      if (!check(shell.calls[1].settings.accounts.length === 1, "inline save keeps accounts")) return
      // CLI path: both saves run, one after another (each stub call sleeps 0.2 s).
      shell.inline = false
      two.savePreference("unreadFirst", true)
      two.savePreference("showClosed", false)
      if (!check(two.saving, "second CLI save queued while the first runs")) return
      expect(function() { return !two.saving }, 18000, "the CLI save queue drains")
    },
    function() {
      logView.path = Quickshell.env("FOAMY_CLI_LOG")
      logView.reload()
      var lines = logView.text().trim().split("\n")
      if (!check(lines.length === 2, "two CLI saves, got " + JSON.stringify(lines))) return
      if (!check(lines[0] === "bar set foamy.teams unreadFirst true --json" && lines[1] === "bar set foamy.teams showClosed false --json", "CLI order: " + JSON.stringify(lines))) return
      if (!check(two.prefs.error === "", "queue drained without error")) return
      // Dropdowns stay bound after a pick (kit 0.2.0 no longer assigns value).
      var pick = shell.find(one.popup.bodyItem, "defaultAccount")
      if (!check(pick.compact, "middle-click account uses the settings row form")) return
      shell.inline = true
      pick.changed("work")
      if (!check(pick.value === "work", "middle-click dropdown follows the saved value, got " + pick.value)) return
      one.popup.bodyItem.editAccount(shell.accounts[0])
      expect(function() { return shell.find(one.popup.bodyItem, "appIdPicker").visible }, 5000, "the account editor opens")
    },
    function() {
      var picker = shell.find(one.popup.bodyItem, "appIdPicker")
      picker.changed("teams-other")
      if (!check(picker.value === "teams-other", "picker shows the chosen window, got " + picker.value)) return
      one.popup.bodyItem.editAccount(shell.accounts[0])   // reopen the editor: draft resets
      if (!check(picker.value === "teams-work", "picker follows the draft after reopening, got " + picker.value)) return
      shell.find(one.popup.bodyItem, "teamsSettings").leaveEditor()
      var mode = shell.find(one.popup.bodyItem, "closedMode")
      if (!check(mode && mode.visible && mode.compact && mode.value === "mute", "closed mode defaults to Dim")) return
      mode.changed("hide")
      if (!check(mode.value === "hide" && one.preference("hideWhenClosed"), "Hide saves the existing preference")) return
      if (!check(one.visible, "open settings stay reachable in Hide mode")) return
      one.closeSettings(); one.close()
      expect(function() { return !one.visible }, 5000, "Hide removes the closed widget")
    },
    function() {
      // A running but unfocused window must restore the icon in either mode.
      Plugin.TeamsService.windows = [{ appId: "teams-work", title: "(3) Chat | Microsoft Teams", activated: false, toplevel: null }]
      expect(function() { return one.visible && !shell.find(one, "teamsButton").dimmed && one.summary.totalUnread === 3 }, 5000, "unfocused running account restores the normal unread icon")
    },
    function() {
      Plugin.TeamsService.windows = []
      expect(function() { return !one.visible && shell.find(one, "teamsButton").dimmed && one.summary.totalUnread === 0 }, 5000, "closing the last window clears unread and hides")
    },
    function() {
      one.openSettings()
      expect(function() { return one.visible && one.editingSettings }, 5000, "hidden widget remains reachable through settings")
    },
    function() {
      var mode = shell.find(one.popup.bodyItem, "closedMode")
      mode.changed("mute")
      if (!check(mode.value === "mute" && !one.preference("hideWhenClosed"), "Dim selection stays bound to saved preference")) return
      one.closeSettings(); one.close()
      expect(function() { return !one.opened && one.visible && shell.find(one, "teamsButton").dimmed }, 5000, "Dim keeps closed widget visible")
    },
    function() {
      // Invalid stored configuration must not hide the only repair path.
      two.settings = { accounts: [null], hideWhenClosed: true }
      if (!check(two.visible && two.configurationError !== "", "invalid configuration remains reachable")) return
      two.settings = { accounts: [], hideWhenClosed: true }
      if (!check(two.visible, "initial setup remains reachable")) return
      two.settings = { accounts: shell.accounts }
      // A running account is focused through its toplevel; nothing launches.
      Plugin.TeamsService.windows = [{ appId: "teams-work", title: "Chat | Microsoft Teams", activated: false, toplevel: fakeWindow }]
      one.open()
      expect(function() { return one.opened && one.accounts[0].running }, 5000, "the popup opens on a running account")
    },
    function() {
      one.openAccount(one.accounts[0])
      if (!check(fakeWindow.activations === 1 && !one.opened && one.launchingId === "" && one.launchError === "", "focus activates the window and closes the popup: " + fakeWindow.activations + " " + one.opened + " " + one.launchingId)) return
      Plugin.TeamsService.windows = []
      // A launcher that cannot start the client reports it (exit 127), never success.
      two.settings = { accounts: [Object.assign({}, shell.accounts[0], { command: ["foamy-teams-no-such-client"] })] }
      two.openAccount(two.accounts[0])
      if (!check(two.launchingId === "work", "launch starts, got " + two.launchingId)) return
      // Up to 9 s: the exit-127 error, well before the 15 s no-window timeout.
      expect(function() { return two.launchingId === "" }, 9000, "failed launch ends before the no-window timeout")
    },
    function() {
      if (!check(two.launchError === two.tr("Could not launch the account. Check its browser or launch arguments.") && two.opened, "failed launch shows its error: " + JSON.stringify([two.launchError, two.opened]))) return
      two.close()
      // A title that keeps changing faster than the settle window must still
      // publish while it changes, not only after it stops.
      Plugin.TeamsService.matched = [fakeWindow]
      churn.start()
      expect(function() { return !churn.running }, 10000, "the title churn ends")
    },
    function() {
      if (!check(shell.publishedDuringChurn > 0, "settled updates publish during constant title changes, got " + shell.publishedDuringChurn)) return
      Plugin.TeamsService.matched = []
      // One invalid stored account (a hand edit) makes the list read as empty;
      // the editor must stay blocked so no save can replace the stored list.
      shell.inline = true
      shell.calls = []
      one.settings = { accounts: [shell.accounts[0], Object.assign({}, shell.accounts[0], { id: "home", name: "Home", appId: "teams-home", url: "http://teams.example" })] }
      one.open()
      one.openSettings()
      expect(function() { return one.editingSettings && shell.find(one.popup.bodyItem, "addAccount") !== null }, 5000, "Settings opens on an invalid account list")
    },
    function() {
      var page = shell.find(one.popup.bodyItem, "teamsSettings")
      var add = shell.find(one.popup.bodyItem, "addAccount")
      if (!check(one.definitions.length === 0 && !add.enabled, "Add is blocked while a stored account is invalid")) return
      var hint = one.tr("Fix or remove the invalid account in shell.json to edit the account list.")
      if (!check(page.error.indexOf(hint) >= 0 && page.error.indexOf(one.tr("Enter an HTTPS Teams URL.")) >= 0, "the page names the problem and the fix: " + page.error)) return
      // A direct call (keyboard, a stale button) is refused as well.
      page.edit(null)
      if (!check(!page.editing, "the account editor stays closed")) return
      // Other settings still save, and carry the stored accounts over verbatim.
      one.savePreference("showCount", true)
      if (!check(shell.calls.length === 1 && shell.calls[0].settings.accounts.length === 2 && shell.calls[0].settings.accounts[1].url === "http://teams.example", "the stored accounts survive another save: " + JSON.stringify(shell.calls))) return
      // Fixing shell.json unblocks the editor.
      one.settings = { accounts: shell.accounts }
      expect(function() { return add.enabled && page.error === "" }, 5000, "a fixed account list unblocks Add", function() { return add.enabled + " " + JSON.stringify(page.error) })
    },
    function() {
      one.closeSettings(); one.close()
      // Launch state is once per shell: a launch from one bar shows on the
      // other, and no bar starts a second client while it runs.
      var work = Object.assign({}, shell.accounts[0], { command: ["foamy-teams-fake-client", "work"] })
      var home = Object.assign({}, shell.accounts[0], { id: "home", name: "Home", appId: "teams-home", command: ["foamy-teams-fake-client", "home"] })
      for (var p of [one, two]) p.settings = { accounts: [work, home] }
      Plugin.TeamsService.windows = []
      two.openAccount(two.accounts[0])
      expect(function() { return shell.clientLog().length === 1 }, 9000, "the fake client starts", function() { return JSON.stringify(shell.clientLog()) })
    },
    function() {
      if (!check(one.launchingId === "work" && two.launchingId === "work", "both bars show the launch: " + JSON.stringify([one.launchingId, two.launchingId]))) return
      one.openAccount(one.accounts[0])
      one.openAccount(one.accounts[1])
      two.openAccount(two.accounts[1])
      // (two saved showClosed false earlier, so its popup hides closed rows.)
      one.open()
      expect(function() { return one.popup.bodyItem !== null && shell.find(one.popup.bodyItem, "account:home") !== null }, 5000, "the other bar's popup lists the accounts")
    },
    function() {
      var other = shell.find(one.popup.bodyItem, "account:home"), busy = shell.find(one.popup.bodyItem, "account:work")
      if (!check(busy.launching && other.blocked === true && !other.enabled, "another closed account shows as unavailable while one launches: " + JSON.stringify([busy.launching, other.blocked, other.enabled]))) return
      // A refused launch would have started its client well within this time.
      wait.after(1000, function() {
        if (!check(shell.clientLog().length === 1, "no second client while a launch runs: " + JSON.stringify(shell.clientLog()))) return
        // The window appears: the launch ends on every bar.
        Plugin.TeamsService.windows = [{ appId: "teams-work", title: "Chat | Microsoft Teams", activated: false, toplevel: null }]
        expect(function() { return one.launchingId === "" && two.launchingId === "" && !other.blocked && one.launchError === "" }, 5000, "the launch ends when its window appears")
      })
    },
    function() {
      one.close()
      // Unread totals above 2^31 must not wrap (the count would hide while
      // the icon stays in the unread state).
      Plugin.TeamsService.windows = [
        { appId: "teams-work", title: "(2147483647) Chat | Microsoft Teams", activated: false, toplevel: null },
        { appId: "teams-home", title: "(1) Chat | Microsoft Teams", activated: false, toplevel: null }
      ]
      var content = shell.find(one, "teamsBarContent")
      expect(function() { return content.unread === 2147483648 && shell.find(one, "unreadCount").visible }, 5000, "the bar shows an unread total above 2^31", function() { return content.unread })
    },
    function() {
      Plugin.TeamsService.windows = []
      // An account name that starts with an emoji (a surrogate pair) shows
      // the whole character as its initial, never half of it.
      one.settings = { accounts: [Object.assign({}, shell.accounts[0], { name: "\u{1F600} Fun" })] }
      one.open()
      one.openSettings()
      expect(function() { return one.editingSettings && shell.find(one.popup.bodyItem, "accountInitial") !== null }, 5000, "Settings lists the account")
    },
    function() {
      var initial = shell.find(one.popup.bodyItem, "accountInitial").text
      if (!check(initial === "\u{1F600}", "the initial is the whole emoji: " + JSON.stringify(initial))) return
      one.closeSettings(); one.close()
      console.log("FOAMY DONE")
      Qt.quit()
    }
  ]
  function clientLog() {
    clientView.reload()
    var text = clientView.text().trim()
    return text ? text.split("\n") : []
  }
  FileView { id: clientView; path: Quickshell.env("FOAMY_CLIENT_LOG"); blockLoading: true; printErrors: false }
  property real width0: 0
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
    # The launch tests' client: records its arguments, never a real Teams.
    (stub / "foamy-teams-fake-client").write_text('#!/bin/sh\necho "$*" >> "$FOAMY_CLIENT_LOG"\n')
    (stub / "foamy-teams-fake-client").chmod(0o755)
    r.env["FOAMY_CLIENT_LOG"] = str(r.base / "client.log")
    r.run(timeout=60)
    # Nothing may reach a real omarchy-* host command (the harness stubs log them).
    host = r.host_commands()
    ok = r.ok and not host
    if host:
        print("  host commands:", host)
    for line in r.log.splitlines():
        if ("WARN" in line or "rror" in line) and "wl_display" not in line and "window masks" not in line:
            print("  log:", line.strip())
    if not ok:
        print(r.log)
    print(f"foamy-teams runtime: {'pass' if ok else 'FAIL'}")
    r.cleanup()
    return ok


sys.exit(0 if run() else 1)
