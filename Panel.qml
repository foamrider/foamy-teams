import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "kit"
import "kit/FoamyPrefs.js" as Prefs
import "Model.js" as Model
import "Preferences.js" as Preferences

Panel {
  id: root
  ipcTarget: "foamy.teams"
  manageIpc: false

  readonly property bool vertical: bar ? bar.vertical : false
  // Saved values that have not reached `settings` yet, so a second save
  // never merges over a stale entry (see savePreference).
  property var savedOverlay: ({})
  // Normalize Qt-backed settings lists before validating them as JSON arrays.
  readonly property var shellSettings: JSON.parse(JSON.stringify(root.settings || {}))
  readonly property var preferences: Preferences.withOverlay(shellSettings, savedOverlay)
  readonly property var definitions: preference("accounts")
  readonly property string configurationError: Preferences.configurationError(preferences)
  property bool editingSettings: false
  property string settingsError: ""
  property string launchError: ""
  property string launchingId: ""
  property var saveQueue: []
  property var savingItem: null
  property var lastFailedSave: null
  readonly property bool saving: savingItem !== null || saveQueue.length > 0
  readonly property alias popup: popup

  function preference(key) { return Preferences.value(preferences, key) }
  function tr(label, values) { return FoamyI18n.t(label, values) }

  readonly property var trackedAppIds: Model.trackedAppIds(definitions)
  readonly property var accounts: Model.accountsForWindows(definitions, TeamsService.windows)
  readonly property var summary: Model.summary(accounts)
  readonly property var displayed: Model.displayedAccounts(accounts, preference("showClosed"), preference("unreadFirst"))
  readonly property string heading: summary.accountCount === 0 ? tr(definitions.length > 0 ? "All accounts are disabled" : "No accounts configured")
    : summary.totalUnread > 0 ? FoamyI18n.tn("%1 unread messages", summary.totalUnread)
    : summary.runningCount === 0 ? tr("Teams is not running")
    : summary.unknownCount > summary.accountCount - summary.runningCount ? "Microsoft Teams" : tr("All read")

  // Keep setup and invalid configuration reachable even when auto-hide is enabled.
  visible: !preference("hideWhenClosed") || summary.runningCount > 0 || summary.accountCount === 0 || opened || configurationError !== ""
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  // Once per shell: the leader feeds the shared window tracker and owns IPC.
  FoamyMember { id: member; scope: "teams"; demanding: root.opened && root.editingSettings }
  Binding { target: TeamsService; property: "trackedAppIds"; value: root.trackedAppIds; when: member.isLeader }
  Binding { target: TeamsService; property: "candidatesWanted"; value: member.demanded; when: member.isLeader }

  onAccountsChanged: {
    if (launchingId && accounts.some(function(a) { return a.id === root.launchingId && a.running })) {
      launchingId = ""; launchTimeout.stop()
    }
  }
  onShellSettingsChanged: savedOverlay = Preferences.settledOverlay(shellSettings, savedOverlay)
  onOpenedChanged: {
    if (opened) Qt.callLater(function() { if (popup.bodyItem) popup.bodyItem.panelOpened() })
    else if (!saving) savedOverlay = ({})
  }

  function openSettings() {
    editingSettings = true
    open()
    Qt.callLater(function() { if (popup.bodyItem) popup.bodyItem.settingsOpened() })
  }
  function closeSettings() {
    editingSettings = false
    Qt.callLater(function() { if (popup.bodyItem) popup.bodyItem.settingsClosed() })
  }

  // Saves run one at a time; a change made while another is in flight waits
  // in the queue (newest value per key) instead of being dropped.
  function savePreference(key, value) {
    if (!Preferences.valid(key, value)) {
      settingsError = tr(key === "accounts" ? Preferences.accountError(value) : "Invalid setting.")
      return
    }
    settingsError = ""
    lastFailedSave = null
    saveQueue = Preferences.enqueue(saveQueue, key, value)
    flushSaves()
  }

  function retrySave() {
    if (lastFailedSave) savePreference(lastFailedSave.key, lastFailedSave.value)
  }

  function flushSaves() {
    while (savingItem === null && saveQueue.length > 0) {
      var item = saveQueue[0]
      saveQueue = saveQueue.slice(1)
      var result = savePlan(item.key, item.value)
      if (!result.ok) { failSave(item, result.error); continue }
      if (!result.changed) { saved(item.key); continue }
      var overlay = Object.assign({}, savedOverlay)
      overlay[item.key] = item.value
      savedOverlay = overlay
      if (result.command.length === 0) { saved(item.key); continue }
      savingItem = item
      saveProcess.command = result.command
      saveProcess.running = true
    }
  }

  // FoamyPrefs.save for the scalar settings; the accounts array (validated by
  // Preferences.accountError) takes the same inline-then-CLI path.
  function savePlan(key, value) {
    if (key !== "accounts") return Prefs.save(root.bar, root.moduleName, Preferences.fields, root.preferences, key, value)
    var result = { ok: false, changed: false, inline: false, command: [], error: "" }
    if (!root.moduleName) { result.error = "Settings can't be saved: this widget has no bar entry."; return result }
    result.ok = true
    if (JSON.stringify(root.preferences.accounts) === JSON.stringify(value)) return result
    result.changed = true
    if (Prefs.canSaveInline(root.bar)) {
      try {
        if (root.bar.shell.updateEntryInline(String(root.moduleName), Prefs.merged(root.preferences, key, value)) === true) {
          result.inline = true
          return result
        }
      } catch (error) {
        console.warn("foamy.teams: inline save failed, using omarchy bar set:", error)
      }
    }
    result.command = Prefs.saveCommand(root.moduleName, key, value)
    return result
  }

  function saved(key) {
    if (popup.bodyItem) popup.bodyItem.saved(key)
  }

  function failSave(item, message) {
    var overlay = Object.assign({}, savedOverlay)
    delete overlay[item.key]
    savedOverlay = overlay
    lastFailedSave = item
    settingsError = tr(message || "Could not save settings. Try again.")
  }

  Process {
    id: saveProcess
    onExited: function(code) {
      var item = root.savingItem
      root.savingItem = null
      if (code !== 0) root.failSave(item, "Could not save settings. Try again.")
      else root.saved(item.key)
      Qt.callLater(root.flushSaves)
    }
  }

  function openAccount(account) {
    if (!account) return
    launchError = ""
    if (account.running && account.toplevel) { close(); account.toplevel.activate(); return }
    if (launchingId || launcher.running) return
    launchingId = account.id
    launcher.command = ["python3", decodeURIComponent(String(Qt.resolvedUrl("launch.py")).replace(/^file:\/\//, "")), JSON.stringify(Model.launchArguments(account.definition))]
    launcher.running = true
    launchTimeout.restart()
  }

  Process {
    id: launcher
    onExited: function(code) {
      if (code !== 0) { root.launchingId = ""; launchTimeout.stop(); root.launchError = root.tr("Could not launch the account. Check its browser or launch arguments."); root.open() }
    }
  }

  Timer {
    id: launchTimeout
    interval: 15000
    onTriggered: { root.launchingId = ""; root.launchError = root.tr("No matching window appeared. Check the account application ID or sign in to Teams."); root.open() }
  }

  FoamyIpc {
    target: "foamy.teams"
    enabled: member.isLeader
    function open(): void { root.open() }
    function close(): void { root.close() }
    function toggle(): void { root.toggle() }
    function settings(): void { root.openSettings() }
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""; labelVisible: false; hasVisualContent: true
    active: root.summary.totalUnread > 0
    activeColor: Commons.Color.accent
    fixedWidth: root.vertical ? -1 : Math.max(Style.bar.iconSlot, barContent.implicitWidth + Style.bar.iconSlot - Style.bar.iconCanvas)
    tooltipText: "Microsoft Teams · " + root.heading
    onPressed: function(code) {
      if (code === Qt.MiddleButton) root.openAccount(Model.primaryAccount(root.accounts, root.preference("defaultAccount")))
      else if (code === Qt.RightButton) root.openSettings()
      else root.toggle()
    }
    TeamsBarContent {
      id: barContent
      anchors.centerIn: parent
      unread: root.summary.totalUnread
      showCount: !root.vertical && root.preference("showCount")
      glyphFont: button.fontFamily
      foreground: button.foreground
      urgent: root.bar ? root.bar.urgent : Commons.Color.urgent
    }
  }

  FoamyPopup {
    id: popup
    anchorItem: button
    bar: root.bar
    owner: root
    open: root.opened
    body: Component {
      TeamsView {
        accounts: root.displayed
        summary: root.summary
        heading: root.heading
        configured: root.definitions.length > 0
        showContext: root.preference("showContext")
        error: root.launchError
        launchingId: root.launchingId
        editingSettings: root.editingSettings
        settings: root.preferences
        candidates: TeamsService.candidates
        saving: root.saving
        settingsError: root.settingsError || (root.configurationError ? root.tr(root.configurationError) : "")
        retryable: root.lastFailedSave !== null
        onActivate: function(account) { root.openAccount(account) }
        onSettingsRequested: root.openSettings()
        onSettingsBack: root.closeSettings()
        onCloseRequestedByView: root.close()
        onSwitchPanelRequested: function(direction) { root.switchPanel(direction) }
        onSaveRequested: function(key, value) { root.savePreference(key, value) }
        onRetryRequested: root.retrySave()
      }
    }
  }
}
