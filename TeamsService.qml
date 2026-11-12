pragma Singleton
import QtQuick
import Quickshell.Io
import Quickshell.Wayland
import "Model.js" as Model

// One window tracker per shell (4.5 draws a bar per monitor; a plugin
// singleton is shared by all of them). Only toplevels whose application ID
// belongs to a configured account are read: their titles and focus state are
// watched, everything else is ignored, so a terminal running `watch` or a
// media player's changing title never touches the account model.
//
//   trackedAppIds     lower-case IDs of the enabled accounts (set by the leader)
//   windows           [{appId, title, activated, toplevel}] for tracked windows
//   candidatesWanted  a Settings page is open: also list every window's ID
//   candidates        [{appId, title}] of all windows, only while wanted
//   launchingId       the account being launched, "" when none (every bar
//                     shows it; one launch at a time per shell)
//   launchError       English message of the last failed launch, "" when none
QtObject {
  id: root

  property var trackedAppIds: []
  property bool candidatesWanted: false
  property var windows: []
  property var candidates: []
  property string launchingId: ""
  property string launchError: ""
  // The launching account's lower-case application ID, and the bar that
  // asked: a failed launch opens that bar's popup to show the error.
  property string launchingAppId: ""
  property QtObject launchOwner: null
  signal launchFailed(QtObject owner)

  // Tracked toplevel objects, and the published snapshot's comparable form.
  property var matched: []
  property string publishedSignature: ""
  // Title/focus changes inside this window are coalesced into one update.
  readonly property int settleMs: 250

  function toplevelList() {
    return ToplevelManager.toplevels ? ToplevelManager.toplevels.values : []
  }

  function snapshot(list) {
    return list.map(function(w) {
      return { appId: String(w.appId || ""), title: String(w.title || ""), activated: w.activated === true, toplevel: w }
    })
  }

  // The set of tracked windows changed (opened, closed, re-identified or the
  // configuration changed): publish now, identity included.
  function rematch() {
    var ids = root.trackedAppIds
    var next = ids.length ? toplevelList().filter(function(w) { return Model.tracked(ids, w.appId) }) : []
    matched = next
    settle.stop()
    var published = snapshot(next)
    publishedSignature = Model.signature(published)
    windows = published
    if (candidatesWanted) refreshCandidates()
  }

  // A tracked window's title or focus changed: publish after a short settle,
  // and only if the visible result differs. The window starts at the first
  // change and is not extended by later ones, so a title that keeps changing
  // still publishes every settleMs instead of never.
  function scheduleUpdate() { if (!settle.running) settle.start() }

  function publishSettled() {
    var published = snapshot(matched)
    var signature = Model.signature(published)
    if (signature === publishedSignature) return
    publishedSignature = signature
    windows = published
  }

  function refreshCandidates() {
    candidates = candidatesWanted ? toplevelList().map(function(w) { return { appId: String(w.appId || ""), title: String(w.title || "") } }) : []
  }

  // Starts `command` for account `id` unless a launch is already running on
  // any bar. It ends when a window with `appId` appears, the launcher fails
  // (sh exits 127 when the client is missing) or after 15 s.
  function launch(id, appId, command, owner) {
    if (launchingId !== "" || launcher.running) return false
    launchingId = id
    launchingAppId = String(appId).toLowerCase()
    launchOwner = owner
    launcher.command = command
    launcher.running = true
    launchTimeout.restart()
    return true
  }
  function endLaunch(error) {
    var owner = launchOwner
    launchingId = ""
    launchingAppId = ""
    launchOwner = null
    launchTimeout.stop()
    if (error) {
      launchError = error
      launchFailed(owner)
    }
  }

  onWindowsChanged: if (launchingAppId !== "" && windows.some(function(w) { return w.appId.toLowerCase() === root.launchingAppId })) endLaunch("")
  onTrackedAppIdsChanged: rematch()
  onCandidatesWantedChanged: refreshCandidates()
  Component.onCompleted: rematch()

  property Timer settle: Timer {
    interval: root.settleMs
    onTriggered: root.publishSettled()
  }

  property Process launcher: Process {
    onExited: function(code) { if (code !== 0) root.endLaunch("Could not launch the account. Check its browser or launch arguments.") }
  }

  property Timer launchTimeout: Timer {
    interval: 15000
    onTriggered: root.endLaunch("No matching window appeared. Check the account application ID or sign in to Teams.")
  }

  property Connections listWatcher: Connections {
    target: ToplevelManager.toplevels
    function onValuesChanged() { root.rematch() }
  }

  // Every window: only its application ID (rarely changes after mapping) and,
  // while Settings is open, its title for the window picker.
  property Instantiator identityWatchers: Instantiator {
    model: ToplevelManager.toplevels
    delegate: QtObject {
      id: watcher
      required property var modelData
      property Connections identity: Connections {
        target: watcher.modelData
        function onAppIdChanged() { root.rematch() }
      }
      property Connections pickerTitle: Connections {
        target: watcher.modelData
        enabled: root.candidatesWanted
        function onTitleChanged() { root.refreshCandidates() }
      }
    }
  }

  // Tracked windows only: title (unread count, context) and focus.
  property Instantiator trackedWatchers: Instantiator {
    model: root.matched
    delegate: Connections {
      required property var modelData
      target: modelData
      function onTitleChanged() { root.scheduleUpdate() }
      function onActivatedChanged() { root.scheduleUpdate() }
    }
  }
}
