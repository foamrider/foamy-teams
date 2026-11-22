"""Load the real Panel.qml twice (two monitors) in an isolated offscreen shell
on Omarchy 4.5 and run named scenarios through it: IPC through `qs ipc`, the
lazy popup body, the Settings page and its account editor, saves (inline and a
failed `omarchy bar set` with Retry), a failed paste in the editor (shown in
Norwegian), the closed modes, the status heading, clicks and keys, launches
(failed, refused, timed out), the window tracker, the bar count, the account
order at equal counts, plain-text rendering of page-controlled text and
preview/Preview.qml's editor state, walked as the kit's render harness does.

  python3 tests/runtime.py

Runs on the installed /usr/share/omarchy/shell, or the tree in FOAMY_HOST_45.

Uses foamy-kit's preview harness (FOAMY_KIT, default ~/GitHub/Personal/foamy-kit):
temp HOME/XDG dirs, no Wayland/Hyprland variables, no host scripts run. The
`omarchy` CLI is a stub that logs its arguments and fails one call when a
scenario asks for it; the Teams client is a stub that logs its arguments; a
paste reads the kit's wl-paste stand-in (hostenv.clipboard_fakes).
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

SHELL = r"""import QtQuick
import QtTest
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
  property string scenario: ""
  property var calls: []
  property bool inline: true
  function fail(message) { console.log("FOAMY FAIL " + (scenario ? scenario + ": " : "") + message); Qt.quit() }
  function check(condition, message) { if (!condition) fail(message); return condition }

  FloatingWindow {
    id: window
    implicitWidth: 1920; implicitHeight: 1080
    ScreenSim { id: sim }
    Plugin.Panel { id: one; x: 1400; y: 4; width: 30; height: 26 }
    Plugin.Panel { id: two; x: 1440; y: 4; width: 30; height: 26 }
  }
  Component { id: barPanel; Plugin.Panel { } }
  // Two handlers on one target on purpose: run() requires Quickshell's
  // conflict warning for them, so a reworded warning fails the run instead
  // of hiding a second foamy.teams handler.
  IpcHandler { target: "foamy-teams-probe"; function ping(): void {} }
  IpcHandler { target: "foamy-teams-probe"; function ping(): void {} }

  // preview/Preview.qml's own bar, so its open popup never takes one of the panels' places.
  MockBar { id: previewBar }
  property var preview: null

  MockBar {
    id: bar
    shell: QtObject {
      function updateEntryInline(id, settings) {
        shell.calls = shell.calls.concat([{ id: id, settings: JSON.parse(JSON.stringify(settings)) }])
        return shell.inline
      }
    }
  }

  readonly property var work: ({ id: "work", name: "Work", appId: "teams-work", enabled: true, browser: "omarchy-launch-webapp", profile: "", url: "https://teams.microsoft.com", command: [] })
  readonly property var home: ({ id: "home", name: "Home", appId: "teams-home", enabled: true, browser: "omarchy-launch-webapp", profile: "", url: "https://teams.microsoft.com", command: [] })
  readonly property var accounts: [work]
  function account(base, changes) { return Object.assign({}, base, changes || {}) }
  // Windows of the "equal counts" accounts tie0..tie7: one unread each, two
  // for the account at index `higher`; activating one records its account in
  // `picked`.
  property string picked: ""
  function tieToplevel(id) { return { activate: function() { shell.picked = id } } }
  function tieWindows(higher) {
    var windows = []
    for (var i = 0; i < 8; i++)
      windows.push(teamsWindow("teams-tie" + i, "(" + (i === higher ? 2 : 1) + ") Chat | Microsoft Teams", tieToplevel("tie" + i)))
    return windows
  }
  function teamsWindow(appId, title, toplevel) { return { appId: appId, title: title, activated: false, toplevel: toplevel || null } }

  Component.onCompleted: {
    for (var p of [one, two]) { p.bar = bar; p.moduleName = "foamy.teams"; p.settings = { accounts: shell.accounts, showCount: true } }
    shell.next()
  }

  FoamyWait { id: wait }
  // Keys as a user types them, to the window that has the keys.
  TestEvent { id: ev }

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

  // Every scenario starts here, so none depends on what an earlier one left.
  // The mock host never writes a save back to the panel, so saved values stay
  // pending in the queue: showing the panel what was saved settles them
  // before the scenario's own settings replace everything. Window lists are
  // assigned after every settings change, because a new account list makes
  // the leader read the real (empty, offscreen) window list again.
  function reset(name, settings) {
    scenario = name
    calls = []
    inline = true
    bar.position = "top"
    Plugin.TeamsService.matched = []
    Plugin.TeamsService.launchError = ""
    Plugin.TeamsService.launchTimeout.interval = 15000
    if (!check(Plugin.TeamsService.launchingId === "" && !one.saving && !two.saving, "the scenario before left a launch or a save running")) return false
    for (var p of [one, two]) {
      p.closeSettings()
      p.close()
      p.settings = Object.assign({}, p.prefs.storedSettings, p.prefs.pending)
      p.settings = JSON.parse(JSON.stringify(settings))
    }
    Plugin.TeamsService.windows = []
    for (var w of [fakeWindow, fakeHome]) { w.activations = 0; w.activated = false; w.title = "(1) Chat | Microsoft Teams" }
    published = 0
    publishedDuringChurn = -1
    clientBase = clientLog().length
    cliBase = cliLog().length
    return true
  }
  // Play the host: show the panel the entry its last save wrote.
  function reflect(panel) { panel.settings = shell.calls[shell.calls.length - 1].settings }
  function page() { return find(one.popup.bodyItem, "teamsSettings") }
  function savedIds() { return shell.calls[shell.calls.length - 1].settings.accounts.map(function(a) { return a.id }) }

  // `qs ipc call foamy.teams <fn>` against this shell, as a user or a key
  // binding would call it.
  property int ipcExit: -1
  property var ipcBar: null
  Process { id: ipc; onExited: function(code) { shell.ipcExit = code } }
  function ipcCall(fn) {
    shell.ipcExit = -1
    ipc.command = ["qs", "ipc", "-i", Quickshell.instanceId, "call", "foamy.teams", fn]
    ipc.running = true
  }
  function ipcStep(fn, condition, message) {
    return function() {
      ipcCall(fn)
      wait.waitFor(function() { return shell.ipcExit !== -1 && (shell.ipcExit !== 0 || condition()) }, 10000, function(ok) {
        if (check(ok && shell.ipcExit === 0, message + ": exit " + shell.ipcExit + ", opened " + [one.opened, two.opened] + ", on Settings " + [one.editingSettings, two.editingSettings])) next()
      })
    }
  }

  readonly property var steps: [
    // --- start: the first open; must run first ---------------------------
    function() {
      if (!reset("start", { accounts: shell.accounts, showCount: true })) return
      if (!check(JSON.stringify(Plugin.TeamsService.trackedAppIds) === '["teams-work"]', "tracker follows configured ids: " + JSON.stringify(Plugin.TeamsService.trackedAppIds))) return
      if (!check(one.popup && one.popup.bodyItem === null, "body not built before first open")) return
      if (!check(Plugin.TeamsService.candidatesWanted === false, "no picker list while closed")) return
      if (!check(one.visible && shell.find(one, "teamsButton").dimmed, "closed accounts default to a clickable dim icon")) return
      shell.find(one, "teamsButton").triggerPress(Qt.LeftButton)
      expect(function() { return one.popup.bodyItem !== null && one.opened }, 5000, "a left click opens the popup and builds its body")
    },

    // --- ipc: one leader answers the documented functions ----------------
    function() {
      if (!reset("ipc", { accounts: shell.accounts })) return
      next()
    },
    ipcStep("open", function() { return one.opened !== two.opened }, "open opens exactly one bar's popup"),
    function() {
      shell.ipcBar = one.opened ? one : two
      if (!check(!shell.ipcBar.editingSettings, "open shows the account list, not Settings")) return
      next()
    },
    ipcStep("settings", function() { return shell.ipcBar.opened && shell.ipcBar.editingSettings && one.opened !== two.opened }, "settings turns the same popup to Settings"),
    ipcStep("close", function() { return !one.opened && !two.opened }, "close closes the popup"),
    ipcStep("settings", function() { return one.opened !== two.opened && (one.opened ? one : two).editingSettings }, "settings opens one closed popup on Settings"),
    ipcStep("toggle", function() { return !one.opened && !two.opened }, "toggle closes the open popup"),

    // --- settings page: dropdowns and the window picker -------------------
    function() {
      if (!reset("settings page", { accounts: shell.accounts, showCount: true })) return
      one.open()
      one.openSettings()
      expect(function() { return Plugin.TeamsService.candidatesWanted && one.editingSettings && shell.find(one.popup.bodyItem, "defaultAccount") !== null }, 5000, "picker list while Settings is open")
    },
    function() {
      // Dropdowns stay bound after a pick (kit 0.2.0 no longer assigns value).
      var pick = shell.find(one.popup.bodyItem, "defaultAccount")
      if (!check(pick.compact, "middle-click account uses the settings row form")) return
      pick.changed("work")
      if (!check(pick.value === "work", "middle-click dropdown follows the saved value, got " + pick.value)) return
      if (!check(shell.calls.length === 1 && shell.calls[0].settings.defaultAccount === "work", "the pick saves the middle-click account: " + JSON.stringify(shell.calls))) return
      one.popup.bodyItem.editAccount(shell.work)
      expect(function() { return shell.find(one.popup.bodyItem, "appIdPicker").visible }, 5000, "the account editor opens")
    },
    function() {
      var picker = shell.find(one.popup.bodyItem, "appIdPicker")
      picker.changed("teams-other")
      if (!check(picker.value === "teams-other", "picker shows the chosen window, got " + picker.value)) return
      one.popup.bodyItem.editAccount(shell.work)   // reopen the editor: draft resets
      if (!check(picker.value === "teams-work", "picker follows the draft after reopening, got " + picker.value)) return
      page().leaveEditor()
      next()
    },

    // --- saves: two quick inline saves while the entry is stale -----------
    function() {
      if (!reset("saves", { accounts: shell.accounts, showCount: true })) return
      // The shell entry does not update yet; the second save must carry the first.
      one.savePreference("showCount", false)
      one.savePreference("showContext", true)
      if (!check(shell.calls.length === 2, "two inline saves, got " + shell.calls.length)) return
      if (!check(shell.calls[1].settings.showCount === false && shell.calls[1].settings.showContext === true, "second inline save keeps the first: " + JSON.stringify(shell.calls[1].settings))) return
      if (!check(shell.calls[1].settings.accounts.length === 1, "inline save keeps accounts")) return
      next()
    },

    // --- failed save: the CLI fails once, Settings offers Retry -----------
    function() {
      if (!reset("failed save", { accounts: shell.accounts, showCount: true })) return
      one.open()
      one.openSettings()
      expect(function() { return one.editingSettings && shell.page() !== null }, 5000, "Settings opens")
    },
    function() {
      shell.inline = false
      // The stub fails the next CLI call, then removes the marker.
      cliFail.setText("1\n")
      one.savePreference("showCount", false)
      if (!check(one.saving, "the save runs through the CLI")) return
      expect(function() { return !one.saving }, 18000, "the failed CLI save ends")
    },
    function() {
      var page = shell.page()
      if (!check(page.error === one.tr("Couldn't save the setting.") && page.retryable === true, "Settings shows the failed save with Retry: " + JSON.stringify([page.error, page.retryable]))) return
      if (!check(one.preference("showCount") === true, "the stored value shows again after the failure")) return
      page.retry()
      expect(function() { return !one.saving && page.error === "" }, 18000, "Retry saves", function() { return JSON.stringify([one.saving, page.error]) })
    },
    function() {
      if (!check(one.preference("showCount") === false, "the retried value shows")) return
      var lines = shell.cliLog().slice(shell.cliBase)
      if (!check(lines.length === 2, "the save ran twice through the CLI: " + JSON.stringify(lines))) return
      shell.inline = true
      next()
    },

    // --- closed mode: Dim and Hide ----------------------------------------
    function() {
      if (!reset("closed mode", { accounts: shell.accounts, showCount: true })) return
      one.open()
      one.openSettings()
      expect(function() { return one.editingSettings && shell.find(one.popup.bodyItem, "closedMode") !== null }, 5000, "Settings opens")
    },
    function() {
      var mode = shell.find(one.popup.bodyItem, "closedMode")
      if (!check(mode.visible && mode.value === "mute", "closed mode defaults to Dim")) return
      mode.changed("hide")
      if (!check(mode.value === "hide" && one.preference("hideWhenClosed"), "Hide saves the existing preference")) return
      shell.reflect(one)
      if (!check(one.visible, "open settings stay reachable in Hide mode")) return
      one.closeSettings(); one.close()
      expect(function() { return !one.visible }, 5000, "Hide removes the closed widget")
    },
    function() {
      // A running but unfocused window must restore the icon in either mode.
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", "(3) Chat | Microsoft Teams")]
      var button = shell.find(one, "teamsButton"), count = shell.find(one, "unreadCount")
      expect(function() { return one.visible && !button.dimmed && button.active && count.visible && count.text === "3" }, 5000, "unfocused running account restores the normal unread icon",
             function() { return JSON.stringify([one.visible, button.dimmed, button.active, count.visible, count.text]) })
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
      shell.reflect(one)
      one.closeSettings(); one.close()
      expect(function() { return !one.opened && one.visible && shell.find(one, "teamsButton").dimmed }, 5000, "Dim keeps closed widget visible")
    },
    function() {
      // Invalid stored configuration must not hide the only repair path.
      two.settings = { accounts: [null], hideWhenClosed: true }
      if (!check(two.visible && two.configurationError !== "", "invalid configuration remains reachable")) return
      two.settings = { accounts: [], hideWhenClosed: true }
      if (!check(two.visible, "initial setup remains reachable")) return
      next()
    },

    // --- status: the heading, the tooltip and the empty states ------------
    function() {
      if (!reset("status", { accounts: [] })) return
      one.open()
      expect(function() { return one.opened && one.popup.bodyItem !== null }, 5000, "the popup opens")
    },
    function() {
      var off = shell.account(shell.work, { enabled: false })
      var rows = [
        [{ accounts: [] }, [], "No accounts configured"],
        [{ accounts: [off] }, [], "All accounts are disabled"],
        [{ accounts: [shell.work] }, [], "Teams is not running"],
        [{ accounts: [shell.work] }, [shell.teamsWindow("teams-work", "(3) Chat | Microsoft Teams")], "3 unread messages"],
        [{ accounts: [shell.work] }, [shell.teamsWindow("teams-work", "(1) Chat | Microsoft Teams")], "1 unread message"],
        [{ accounts: [shell.work] }, [shell.teamsWindow("teams-work", "Chat | Microsoft Teams")], "All read"],
        [{ accounts: [shell.work] }, [shell.teamsWindow("teams-work", "Sign in | Microsoft Teams")], "Microsoft Teams"],
        [{ accounts: [shell.work, shell.home] }, [shell.teamsWindow("teams-work", "Chat | Microsoft Teams")], "All read"]
      ]
      for (var row of rows) {
        one.settings = row[0]
        Plugin.TeamsService.windows = row[1]
        if (!check(one.heading === row[2], "heading for " + JSON.stringify([row[0].accounts.map(function(a) { return a.id + (a.enabled ? "" : " off") }), row[1].map(function(w) { return w.title })]) + ": " + one.heading)) return
      }
      var tooltip = shell.find(one, "teamsButton").tooltipText
      if (!check(tooltip === "Microsoft Teams · All read", "the bar tooltip carries the heading: " + tooltip)) return
      var body = one.popup.bodyItem
      one.settings = { accounts: [] }
      Plugin.TeamsService.windows = []
      if (!check(shell.findText(body, "Add your Teams accounts in Settings") !== null, "no accounts: the popup points at Settings")) return
      one.settings = { accounts: [off] }
      Plugin.TeamsService.windows = []
      if (!check(shell.findText(body, "Enable an account in Settings") !== null, "all disabled: the popup says how to enable one")) return
      one.settings = { accounts: [shell.work], showClosed: false }
      Plugin.TeamsService.windows = []
      if (!check(shell.findText(body, "No visible accounts\nShow closed accounts in Settings") !== null, "closed rows hidden: the popup says why it is empty")) return
      next()
    },

    // --- focus, clicks and keys -------------------------------------------
    function() {
      if (!reset("focus, clicks and keys", { accounts: [shell.work, shell.home], defaultAccount: "home" })) return
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", "Chat | Microsoft Teams", fakeWindow), shell.teamsWindow("teams-home", "Chat | Microsoft Teams", fakeHome)]
      one.open()
      expect(function() { return one.opened && one.accounts[0].running && shell.find(one.popup.bodyItem, "account:work") !== null }, 5000, "the popup opens on a running account")
    },
    function() {
      // A click on a running account's row focuses its window; nothing launches.
      shell.find(one.popup.bodyItem, "account:work").clicked()
      if (!check(fakeWindow.activations === 1 && fakeHome.activations === 0 && !one.opened && one.launchingId === "" && one.launchError === "", "a row click activates the window and closes the popup: " + JSON.stringify([fakeWindow.activations, fakeHome.activations, one.opened, one.launchingId]))) return
      shell.find(one, "teamsButton").triggerPress(Qt.MiddleButton)
      if (!check(fakeHome.activations === 1 && fakeWindow.activations === 1 && !one.opened, "middle-click focuses the default account and opens no popup: " + JSON.stringify([fakeWindow.activations, fakeHome.activations, one.opened]))) return
      shell.find(one, "teamsButton").triggerPress(Qt.RightButton)
      expect(function() { return one.opened && one.editingSettings }, 5000, "right-click opens Settings")
    },
    function() {
      one.closeSettings(); one.close()
      one.open()
      expect(function() { return one.opened && one.popup.bodyItem !== null }, 5000, "the popup opens again")
    },
    function() {
      var view = one.popup.bodyItem
      view.moveRequested(0, 1)
      view.moveRequested(0, 1)
      view.activateRequested()
      if (!check(fakeHome.activations === 2 && fakeWindow.activations === 1 && !one.opened, "the keys move to the second account and focus it: " + JSON.stringify([fakeWindow.activations, fakeHome.activations, one.opened]))) return
      one.open()
      expect(function() { return one.opened }, 5000, "the popup opens for the shortcut keys")
    },
    function() {
      var view = one.popup.bodyItem
      view.textKey("s", Qt.ControlModifier)
      if (!check(!one.editingSettings, "Ctrl+S is not the Settings shortcut")) return
      view.textKey("s", Qt.NoModifier)
      if (!check(one.editingSettings, "S opens Settings")) return
      one.closeSettings()
      view.closeRequested()
      if (!check(!one.opened, "Escape on the account list closes the popup")) return
      next()
    },

    // --- launch: failure, refused launches, the window ends it ------------
    function() {
      // A launcher that cannot start the client reports it (exit 127), never success.
      if (!reset("launch", { accounts: [shell.account(shell.work, { command: ["foamy-teams-no-such-client"] })] })) return
      two.openAccount(two.accounts[0])
      if (!check(two.launchingId === "work", "launch starts, got " + two.launchingId)) return
      // Up to 9 s: the exit-127 error, well before the 15 s no-window timeout.
      expect(function() { return two.launchingId === "" }, 9000, "failed launch ends before the no-window timeout")
    },
    function() {
      if (!check(two.launchError === two.tr("Could not launch the account. Check its browser or launch arguments.") && two.opened && !one.opened, "failed launch opens its own bar's popup with the error: " + JSON.stringify([two.launchError, two.opened, one.opened]))) return
      two.close()
      // Launch state is once per shell: a launch from one bar shows on the
      // other, and no bar starts a second client while it runs.
      var work = shell.account(shell.work, { command: ["foamy-teams-fake-client", "work"] })
      var home = shell.account(shell.home, { command: ["foamy-teams-fake-client", "home"] })
      for (var p of [one, two]) p.settings = { accounts: [work, home] }
      Plugin.TeamsService.windows = []
      two.openAccount(two.accounts[0])
      if (!check(two.launchError === "", "the next launch clears the error")) return
      expect(function() { return shell.clientRuns().length === 1 }, 9000, "the fake client starts", function() { return JSON.stringify(shell.clientRuns()) })
    },
    function() {
      if (!check(one.launchingId === "work" && two.launchingId === "work", "both bars show the launch: " + JSON.stringify([one.launchingId, two.launchingId]))) return
      one.openAccount(one.accounts[0])
      one.openAccount(one.accounts[1])
      two.openAccount(two.accounts[1])
      shell.find(one, "teamsButton").triggerPress(Qt.MiddleButton)
      one.open()
      expect(function() { return one.popup.bodyItem !== null && shell.find(one.popup.bodyItem, "account:home") !== null }, 5000, "the other bar's popup lists the accounts")
    },
    function() {
      var other = shell.find(one.popup.bodyItem, "account:home"), busy = shell.find(one.popup.bodyItem, "account:work")
      if (!check(busy.launching && busy.actionText === one.tr("Launching…") && other.blocked === true && !other.enabled, "another closed account shows as unavailable while one launches: " + JSON.stringify([busy.launching, busy.actionText, other.blocked, other.enabled]))) return
      // The window appears: the launch ends on every bar.
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", "Chat | Microsoft Teams")]
      expect(function() { return one.launchingId === "" && two.launchingId === "" && !other.blocked && one.launchError === "" }, 5000, "the launch ends when its window appears")
    },
    function() {
      // An allowed launch now starts. A refused attempt that had started a
      // client would have logged its line before this one.
      one.openAccount(one.accounts[1])
      expect(function() { return shell.clientRuns().length >= 2 }, 9000, "the next launch starts its client", function() { return JSON.stringify(shell.clientRuns()) })
    },
    function() {
      if (!check(JSON.stringify(shell.clientRuns()) === '["work","home"]', "no client started while a launch ran: " + JSON.stringify(shell.clientRuns()))) return
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", "Chat | Microsoft Teams"), shell.teamsWindow("teams-home", "Chat | Microsoft Teams")]
      expect(function() { return one.launchingId === "" && two.launchingId === "" }, 5000, "the second launch ends when its window appears")
    },

    // --- launch timeout: no window ever appears ---------------------------
    function() {
      if (!reset("launch timeout", { accounts: [shell.account(shell.work, { command: ["foamy-teams-fake-client", "work"] })] })) return
      Plugin.TeamsService.launchTimeout.interval = 200
      two.openAccount(two.accounts[0])
      if (!check(two.launchingId === "work", "launch starts, got " + two.launchingId)) return
      expect(function() { return two.launchingId === "" && two.opened && !Plugin.TeamsService.launcher.running }, 9000, "a launch without a window ends",
             function() { return JSON.stringify([two.launchingId, two.opened, Plugin.TeamsService.launcher.running, two.launchError]) })
    },
    function() {
      if (!check(two.launchError === two.tr("No matching window appeared. Check the account application ID or sign in to Teams.") && !one.opened, "the timed-out launch shows its error on its own bar: " + JSON.stringify([two.launchError, one.opened]))) return
      Plugin.TeamsService.launchTimeout.interval = 15000
      two.openAccount(two.accounts[0])
      if (!check(two.launchingId === "work" && two.launchError === "", "the launch can start again: " + JSON.stringify([two.launchingId, two.launchError]))) return
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", "Chat | Microsoft Teams")]
      expect(function() { return one.launchingId === "" && two.launchingId === "" && two.launchError === "" && JSON.stringify(shell.clientRuns()) === '["work","work"]' }, 5000, "the second launch ends when its window appears",
             function() { return JSON.stringify([one.launchingId, two.launchingId, two.launchError, shell.clientRuns()]) })
    },

    // --- tracker: a title that keeps changing -----------------------------
    function() {
      if (!reset("tracker", { accounts: shell.accounts })) return
      // A title that keeps changing faster than the settle window must still
      // publish while it changes, not only after it stops, and not on every change.
      Plugin.TeamsService.matched = [fakeWindow]
      shell.churnStarted = Date.now()
      churn.start()
      expect(function() { return !churn.running }, 10000, "the title churn ends")
    },
    function() {
      // A settle timer may fire up to 5 % early (coarse timers); 0.8 leaves
      // margin while one publish per change (30) still fails.
      var bound = Math.floor(shell.churnElapsed / (Plugin.TeamsService.settleMs * 0.8)) + 1
      if (!check(shell.publishedDuringChurn > 0 && shell.publishedDuringChurn <= bound, "settled updates publish during constant title changes, at most " + bound + " in " + shell.churnElapsed + " ms, got " + shell.publishedDuringChurn)) return
      Plugin.TeamsService.matched = []
      next()
    },

    // --- invalid stored list: editing stays blocked -----------------------
    function() {
      // One invalid stored account (a hand edit) makes the list read as empty;
      // the editor must stay blocked so no save can replace the stored list.
      if (!reset("invalid stored list", { accounts: [shell.work, shell.account(shell.home, { url: "http://teams.example" })] })) return
      one.open()
      one.openSettings()
      expect(function() { return one.editingSettings && shell.find(one.popup.bodyItem, "addAccount") !== null }, 5000, "Settings opens on an invalid account list")
    },
    function() {
      var page = shell.page()
      var add = shell.find(one.popup.bodyItem, "addAccount")
      if (!check(one.definitions.length === 0 && !add.enabled, "Add is blocked while a stored account is invalid")) return
      var hint = one.tr("Fix or remove the invalid account in shell.json to edit the account list.")
      if (!check(page.error.indexOf(hint) >= 0 && page.error.indexOf(one.tr("Enter an HTTPS Teams URL.")) >= 0, "the page names the problem and the fix: " + page.error)) return
      // The setup hint would point at the wrong fix.
      if (!check(shell.findText(one.popup.bodyItem, one.tr("Open Teams in a separate browser profile, then select its window here.")) === null, "no setup hint while the stored list is invalid")) return
      // A direct call (keyboard, a stale button) is refused as well.
      page.edit(null)
      if (!check(!page.editing, "the account editor stays closed")) return
      // Other settings still save, and carry the stored accounts over verbatim.
      one.savePreference("showCount", false)
      if (!check(shell.calls.length === 1 && shell.calls[0].settings.accounts.length === 2 && shell.calls[0].settings.accounts[1].url === "http://teams.example", "the stored accounts survive another save: " + JSON.stringify(shell.calls))) return
      // Fixing shell.json unblocks the editor.
      one.settings = { accounts: shell.accounts }
      expect(function() { return add.enabled && page.error === "" }, 5000, "a fixed account list unblocks Add", function() { return add.enabled + " " + JSON.stringify(page.error) })
    },
    function() {
      // A hand-edited "accounts": null reads as no list, like a missing key:
      // the list is empty and editable, and no error is shown.
      var page = shell.page(), add = shell.find(one.popup.bodyItem, "addAccount")
      one.settings = { accounts: null }
      expect(function() { return one.definitions.length === 0 && add.enabled && page.error === "" }, 5000, "a null account list shows no error", function() { return add.enabled + " " + JSON.stringify(page.error) })
    },

    // --- account editor: add, edit, move and remove through the view ------
    function() {
      if (!reset("account editor", { accounts: shell.accounts })) return
      one.open()
      one.openSettings()
      expect(function() { return one.editingSettings && shell.find(one.popup.bodyItem, "addAccount") !== null }, 5000, "Settings opens")
    },
    function() {
      var page = shell.page()
      shell.find(one.popup.bodyItem, "addAccount").clicked()
      if (!check(page.editing && page.adding, "Add opens the editor on a new account")) return
      page.change("name", "Home")
      page.change("appId", "teams-home")
      page.saveAccount()
      if (!check(shell.calls.length === 1, "Save writes the list once: " + JSON.stringify(shell.calls) + " " + page.error)) return
      var saved = shell.calls[0].settings.accounts, added = saved[1]
      if (!check(saved.length === 2 && saved[0].id === "work" && added && added.name === "Home" && added.appId === "teams-home" && added.enabled === true && added.browser === "omarchy-launch-webapp" && added.profile === "" && added.url === "https://teams.microsoft.com" && JSON.stringify(added.command) === "[]" && /^account-\d+$/.test(added.id), "the new account is saved after the others with the defaults: " + JSON.stringify(saved))) return
      if (!check(!page.editing && page.error === "", "the editor closes after the save")) return
      shell.reflect(one)
      // An invalid draft is refused with its message, and nothing is written.
      page.edit(one.definitions[0])
      page.change("url", "http://x")
      page.saveAccount()
      if (!check(page.error === one.tr("Enter an HTTPS Teams URL.") && page.editing && shell.calls.length === 1, "an http URL is refused: " + JSON.stringify([page.error, page.editing, shell.calls.length]))) return
      page.change("url", "https://teams.microsoft.com")
      page.commandDraft = "not json"
      page.saveAccount()
      if (!check(page.error === one.tr("Enter a JSON array of command arguments, or [].") && shell.calls.length === 1, "launch arguments that are not JSON are refused: " + page.error)) return
      page.leaveEditor()
      // Edit keeps the ids and their order.
      page.edit(one.definitions[0])
      page.change("name", "Work 2")
      page.saveAccount()
      if (!check(shell.calls.length === 2 && JSON.stringify(shell.savedIds()) === JSON.stringify(["work", added.id]) && shell.calls[1].settings.accounts[0].name === "Work 2" && !page.editing, "Edit saves the changed account in place: " + JSON.stringify(shell.calls[shell.calls.length - 1]))) return
      shell.reflect(one)
      // Another monitor renamed the account being edited while the editor
      // was open: saving the changed draft would overwrite that rename.
      page.edit(one.definitions[0])
      page.change("name", "Work 3")
      var elsewhere = JSON.parse(JSON.stringify(one.settings))
      elsewhere.accounts[0].name = "Work elsewhere"
      one.settings = elsewhere
      page.saveAccount()
      if (!check(page.error === one.tr("Settings changed elsewhere. Reopen the account editor.") && shell.calls.length === 2, "a save over a list changed elsewhere is refused: " + JSON.stringify([page.error, shell.calls.length]))) return
      page.leaveEditor()
      // Move and remove.
      page.move(0, 1)
      if (!check(shell.calls.length === 3 && JSON.stringify(shell.savedIds()) === JSON.stringify([added.id, "work"]), "Move down writes the other order: " + JSON.stringify(shell.savedIds()))) return
      shell.reflect(one)
      page.edit(one.definitions[1])
      page.remove("work")
      if (!check(shell.calls.length === 4 && JSON.stringify(shell.savedIds()) === JSON.stringify([added.id]) && !page.editing, "Remove writes the list without the account and closes the editor: " + JSON.stringify([shell.savedIds(), page.editing]))) return
      next()
    },

    // --- paste errors: a failed paste says why, in the page's language ----
    function() {
      if (!reset("paste errors", { accounts: shell.accounts })) return
      language.setText("no\n")
      one.open()
      one.openSettings()
      expect(function() { return Kit.FoamyI18n.language === "no" && one.editingSettings && shell.page() !== null }, 5000, "Settings opens in Norwegian")
    },
    function() {
      shell.page().edit(one.definitions[0])
      expect(function() { var name = shell.editorFields(shell.page())[0]; return name && name.text === "Work" && name.inputActiveFocus }, 5000, "the editor opens with the keys in the name field")
    },
    function() {
      // Ctrl+V with a clipboard text over the kit's 16 KiB limit (the kit's
      // wl-paste stand-in): the paste fails and the page says why.
      clipboardMode.setText("large")
      ev.keyClick(Qt.Key_V, Qt.ControlModifier, -1)
      var name = shell.editorFields(shell.page())[0]
      expect(function() { return shell.page().error === Kit.FoamyI18n.t("Clipboard text is too large or contains invalid characters.") }, 10000, "a paste over the limit shows why on the page",
             function() { return JSON.stringify([shell.page().error, name.pasteError, name.text]) })
    },
    function() {
      clipboardMode.setText("normal")
      var page = shell.page(), fields = shell.editorFields(page)
      if (!check(fields.length === 6 && fields[0].text === "Work" && page.draft.name === "Work", "the failed paste leaves the name as it was: " + JSON.stringify([fields.length, fields[0].text, page.draft.name]))) return
      // The next edit clears the message, as it clears the field's paste error.
      ev.keyClickChar("x", Qt.NoModifier, -1)
      if (!check(page.draft.name.length === 5 && page.error === "", "typing clears the paste error: " + JSON.stringify([page.draft.name, page.error]))) return
      // Each field's paste error, set as the kit sets it after a failed
      // paste, shows on the page in Norwegian.
      var messages = ["Clipboard paste timed out. Copy the text again.", "Clipboard text is too large or contains invalid characters.", "Could not paste clipboard text. Copy plain text and try again."]
      for (var i = 0; i < fields.length; i++) {
        for (var english of messages) {
          var shown = Kit.FoamyI18n.t(english)
          fields[i].pasteError = english
          if (!check(shown !== english && page.error === shown, "text field " + i + ": the paste error shows in Norwegian, got " + JSON.stringify(page.error) + " for " + JSON.stringify(english))) return
          fields[i].pasteError = ""
        }
      }
      // A paste error goes with the editor: the account list shows none.
      fields[2].pasteError = messages[0]
      page.leaveEditor()
      if (!check(page.error === "", "the closed editor leaves no paste error: " + JSON.stringify(page.error))) return
      language.setText("en\n")
      expect(function() { return Kit.FoamyI18n.language === "en" }, 5000, "the run goes on in English")
    },

    // --- bar count --------------------------------------------------------
    function() {
      if (!reset("bar count", { accounts: [shell.work, shell.home], showCount: true })) return
      // Unread totals above 2^31 must not wrap (the count would hide while
      // the icon stays in the unread state).
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", "(2147483647) Chat | Microsoft Teams"), shell.teamsWindow("teams-home", "(1) Chat | Microsoft Teams")]
      var content = shell.find(one, "teamsBarContent")
      expect(function() { return content.unread === 2147483648 && shell.find(one, "unreadCount").visible }, 5000, "the bar shows an unread total above 2^31", function() { return content.unread })
    },
    function() {
      var count = shell.find(one, "unreadCount"), other = shell.find(two, "unreadCount")
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", "Chat | Microsoft Teams")]
      if (!check(!count.visible, "no count at a total of 0")) return
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", "(4) Chat | Microsoft Teams")]
      if (!check(count.visible && other.visible, "the count shows on both bars")) return
      two.savePreference("showCount", false)
      if (!check(!other.visible && count.visible, "turning the count off hides it on that bar only")) return
      bar.position = "left"
      if (!check(!count.visible, "a vertical bar shows no count")) return
      bar.position = "top"
      if (!check(count.visible, "the count shows again on a horizontal bar")) return
      next()
    },

    // --- equal counts: the configured order breaks ties --------------------
    function() {
      // The QML engine's sort is not stable, so this runs in the real engine:
      // equal counts must keep the configured order in the popup, and
      // middle-click must open the first of the equal accounts.
      var accounts = []
      for (var i = 0; i < 8; i++) accounts.push(shell.account(shell.work, { id: "tie" + i, name: "Tie " + i, appId: "teams-tie" + i }))
      if (!reset("equal counts", { accounts: accounts, unreadFirst: true })) return
      shell.picked = ""
      Plugin.TeamsService.windows = shell.tieWindows(-1)
      var order = one.displayed.map(function(a) { return a.id }).join(",")
      if (!check(order === "tie0,tie1,tie2,tie3,tie4,tie5,tie6,tie7", "equal counts keep the configured order: " + order)) return
      shell.find(one, "teamsButton").triggerPress(Qt.MiddleButton)
      if (!check(shell.picked === "tie0", "middle-click at equal counts opens the first account: " + shell.picked)) return
      Plugin.TeamsService.windows = shell.tieWindows(6)
      order = one.displayed.map(function(a) { return a.id }).join(",")
      if (!check(order === "tie6,tie0,tie1,tie2,tie3,tie4,tie5,tie7", "a higher count moves up, the rest keep their order: " + order)) return
      next()
    },

    // --- rendering: whole characters and plain text -----------------------
    function() {
      // An account name that starts with an emoji (a surrogate pair) shows
      // the whole character as its initial, never half of it.
      if (!reset("rendering", { accounts: [shell.account(shell.work, { name: "\u{1F600} Fun" })] })) return
      one.open()
      one.openSettings()
      expect(function() { return one.editingSettings && shell.find(one.popup.bodyItem, "accountInitial") !== null }, 5000, "Settings lists the account")
    },
    function() {
      var initial = shell.find(one.popup.bodyItem, "accountInitial").text
      if (!check(initial === "\u{1F600}", "the initial is the whole emoji: " + JSON.stringify(initial))) return
      one.closeSettings()
      // A web page sets the window title, and the user the account name:
      // neither may render as markup.
      one.settings = { accounts: [shell.account(shell.work, { name: "<i>Work</i>" }), shell.home], showContext: true }
      Plugin.TeamsService.windows = [shell.teamsWindow("teams-work", '(2) <b>Bold</b> <img src="x"> | Microsoft Teams')]
      expect(function() { return !one.editingSettings && shell.findText(one.popup.bodyItem, '<b>Bold</b> <img src="x">') !== null }, 5000, "the popup shows the window context")
    },
    function() {
      var body = one.popup.bodyItem
      var context = shell.findText(body, '<b>Bold</b> <img src="x">'), name = shell.findText(body, "<i>Work</i>")
      if (!check(context.textFormat === Text.PlainText && name && name.textFormat === Text.PlainText, "page-controlled text is plain text: " + JSON.stringify([context.textFormat, name && name.textFormat]))) return
      if (!check(shell.findText(body, one.tr("Not running")) !== null, "a closed account says it is not running")) return
      next()
    },

    // --- preview: the states the kit's render harness walks ----------------
    function() {
      if (!reset("preview", { accounts: shell.accounts })) return
      // As preview/render.py loads it: a bar and an anchor, then every state
      // in the order of previewStates.
      var component = Qt.createComponent(Qt.resolvedUrl("plugin/preview/Preview.qml"))
      shell.preview = component.createObject(sim.content, { bar: previewBar, anchorItem: sim.anchor })
      if (!check(shell.preview !== null, "the preview loads: " + component.errorString())) return
      expect(function() { return shell.preview.popup.bodyItem !== null }, 5000, "the preview's popup builds its body")
    },
    function() {
      var states = shell.preview.previewStates
      for (var i = 0; i < states.indexOf("editor"); i++) shell.preview.previewState = states[i]
      shell.preview.previewState = "editor"
      var page = shell.find(shell.preview.popup.bodyItem, "teamsSettings")
      expect(function() { return page.visible && page.editing && !page.adding && page.draft.id === "work" }, 5000, "the preview's editor state shows the account editor, not the settings list",
             function() { return JSON.stringify([page.visible, page.editing, page.accountsLocked, page.title]) })
    },
    function() {
      shell.preview.destroy()
      shell.preview = null
      next()
    },

    // --- createObject settings --------------------------------------------
    function() {
      if (!reset("createObject settings", { accounts: shell.accounts })) return
      // The bar hands settings over through createObject, where each list
      // is a QML sequence wrapper (not an Array). The account list must
      // still read as valid, and a save must carry it over.
      var three = barPanel.createObject(window.contentItem, { x: 1480, y: 4, width: 30, height: 26, bar: bar, moduleName: "foamy.teams", settings: { accounts: shell.accounts, showCount: true } })
      if (!check(!Array.isArray(three.settings.accounts), "createObject hands the account list over as a sequence wrapper")) return
      if (!check(three.definitions.length === 1 && three.accountsProblem === "", "a wrapped account list reads as valid: " + JSON.stringify([three.definitions, three.accountsProblem]))) return
      three.savePreference("showContext", true)
      if (!check(shell.calls.length === 1 && shell.calls[0].settings.accounts.length === 1 && shell.calls[0].settings.accounts[0].id === "work", "a save carries the wrapped accounts over: " + JSON.stringify(shell.calls))) return
      three.destroy()
      console.log("FOAMY DONE")
      Qt.quit()
    }
  ]
  function clientLog() {
    clientView.reload()
    var text = clientView.text().trim()
    return text ? text.split("\n") : []
  }
  // The client runs of the current scenario.
  property int clientBase: 0
  function clientRuns() { return clientLog().slice(clientBase) }
  FileView { id: clientView; path: Quickshell.env("FOAMY_CLIENT_LOG"); blockLoading: true; printErrors: false }
  property int published: 0
  property int publishedDuringChurn: -1
  property double churnStarted: 0
  property double churnElapsed: 0
  QtObject {
    id: fakeWindow
    property string appId: "teams-work"
    property string title: "(1) Chat | Microsoft Teams"
    property bool activated: false
    property int activations: 0
    function activate() { activations++ }
  }
  QtObject {
    id: fakeHome
    property string appId: "teams-home"
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
      if (n >= 30) { shell.churnElapsed = Date.now() - shell.churnStarted; shell.publishedDuringChurn = shell.published; stop() }
    }
  }
  function find(item, name) {
    if (!item) return null
    if (item.objectName === name) return item
    var kids = item.children || []
    for (var i = 0; i < kids.length; i++) { var hit = find(kids[i], name); if (hit) return hit }
    return null
  }
  // The account editor's text fields (kit SafeTextFields) in page order:
  // name, application ID, browser, profile, URL, launch arguments.
  function editorFields(page) {
    var found = []
    function walk(item) {
      if (!item) return
      if (item.pasteError !== undefined && item.editorItem !== undefined) { found.push(item); return }
      var kids = item.children || []
      for (var i = 0; i < kids.length; i++) walk(kids[i])
    }
    walk(page)
    return found
  }
  // The first visible item whose text is exactly `text`.
  function findText(item, text) {
    if (!item || !item.visible) return null
    if (item.text === text) return item
    var kids = item.children || []
    for (var i = 0; i < kids.length; i++) { var hit = findText(kids[i], text); if (hit) return hit }
    return null
  }
  function cliLog() {
    cliView.reload()
    var text = cliView.text().trim()
    return text ? text.split("\n") : []
  }
  // The `omarchy` calls of the current scenario.
  property int cliBase: 0
  FileView { id: cliView; path: Quickshell.env("FOAMY_CLI_LOG"); blockLoading: true; printErrors: false }
  FileView { id: cliFail; path: Quickshell.env("FOAMY_CLI_FAIL"); blockWrites: true; printErrors: false }
  // What the next paste reads (the kit's wl-paste stand-in), and Omarchy's language.
  FileView { id: clipboardMode; path: Quickshell.env("TEST_CLIPBOARD_STATE"); blockWrites: true; printErrors: false }
  FileView { id: language; path: Quickshell.env("OMARCHY_LANGUAGE_FILE"); blockWrites: true; printErrors: false }
}
"""

# The `omarchy` stub: logs its arguments and succeeds, unless a scenario
# wrote the marker file: then this one call fails (a failed `omarchy bar
# set`) and the marker is removed, so a retry succeeds.
OMARCHY_STUB = """#!/bin/sh
echo "$*" >> "$FOAMY_CLI_LOG"
if [ -f "$FOAMY_CLI_FAIL" ]; then
  rm -f "$FOAMY_CLI_FAIL"
  exit 1
fi
"""


def run():
    r = harness.Run("4.5", SHELL, plugin=plugin, prefix="foamy-teams-runtime-")
    stub = r.base / "bin"
    stub.mkdir()
    log = r.base / "cli.log"
    (stub / "omarchy").write_text(OMARCHY_STUB)
    (stub / "omarchy").chmod(0o755)
    r.env["PATH"] = f"{stub}:{r.env['PATH']}"
    r.env["FOAMY_CLI_LOG"] = str(log)
    r.env["FOAMY_CLI_FAIL"] = str(r.base / "cli-fail")
    # The launch tests' client: records its arguments, never a real Teams.
    (stub / "foamy-teams-fake-client").write_text('#!/bin/sh\necho "$*" >> "$FOAMY_CLIENT_LOG"\n')
    (stub / "foamy-teams-fake-client").chmod(0o755)
    r.env["FOAMY_CLIENT_LOG"] = str(r.base / "client.log")
    # Paste runs kit/clipboard.sh against the kit's wl-paste stand-in, never the real clipboard.
    r.env.update(harness.hostenv.clipboard_fakes(r.base / "clipboard", env=r.env))
    r.run(timeout=60)
    # Nothing may reach a real omarchy-* host command (the harness stubs log them).
    host = r.host_commands()
    # One IPC handler per shell: when every bar enables its handler, Quickshell
    # uses one of them and warns about the others, so `qs ipc` still works and
    # only this warning shows the second leader.
    conflict = "another handler is registered for target "
    ipc_control = conflict + "foamy-teams-probe" in r.log
    ipc_conflict = conflict + "foamy.teams" in r.log
    ok = r.ok and not host and ipc_control and not ipc_conflict
    if host:
        print("  host commands:", host)
    if not ipc_control:
        print("  the IPC conflict warning was not seen; the leader check cannot work")
    if ipc_conflict:
        print("  more than one bar enabled the foamy.teams IPC handler")
    expected = ("wl_display", "window masks", "foamy-teams-probe")
    for line in r.log.splitlines():
        if ("WARN" in line or "rror" in line) and not any(text in line for text in expected):
            print("  log:", line.strip())
    if not ok:
        print(r.log)
    print(f"foamy-teams runtime: {'pass' if ok else 'FAIL'}")
    r.cleanup()
    return ok


sys.exit(0 if run() else 1)
