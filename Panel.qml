import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "kit"
import "Model.js" as Model
import "Preferences.js" as Preferences

Panel {
  id: root
  ipcTarget: "foamy.teams"
  manageIpc: false

  readonly property bool vertical: bar ? bar.vertical : false
  readonly property alias popup: popup
  readonly property alias prefs: prefs
  // Normalize Qt-backed settings lists before validating them as JSON arrays.
  readonly property var shellSettings: JSON.parse(JSON.stringify(root.settings || {}))
  // Saved values (including ones the shell has not reflected yet).
  readonly property var preferences: prefs.effectiveSettings
  readonly property var definitions: preference("accounts")
  readonly property string configurationError: Preferences.configurationError(preferences)
  readonly property bool editingSettings: settingsState.editing
  property string launchError: ""
  property string launchingId: ""
  readonly property bool saving: prefs.busy

  function preference(key) { return prefs.value(key) }
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
  onOpenedChanged: if (opened) Qt.callLater(function() { if (popup.bodyItem) popup.bodyItem.panelOpened() })

  // Settings page state: lands on Settings even when the popup was closed,
  // resets only when the popup closes.
  FoamySettingsState {
    id: settingsState
    panel: root
    onShown: Qt.callLater(function() { if (popup.bodyItem) popup.bodyItem.settingsOpened() })
    onHidden: Qt.callLater(function() { if (popup.bodyItem) popup.bodyItem.settingsClosed() })
  }
  function openSettings() { settingsState.show() }
  function closeSettings() { settingsState.hide() }

  // Saves run in order and never merge over a stale entry; the accounts
  // array is a FoamyPrefs `array` field validated by Preferences.accountError.
  FoamyPrefsQueue {
    id: prefs
    bar: root.bar
    moduleName: root.moduleName
    fields: Preferences.fields
    settings: root.shellSettings
    onSaved: function(key) { if (popup.bodyItem) popup.bodyItem.saved(key) }
  }
  function savePreference(key, value) { return prefs.save(key, value) }

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
        settingsError: prefs.error ? root.tr(prefs.error) : (root.configurationError ? root.tr(root.configurationError) : "")
        retryable: prefs.canRetry
        onActivate: function(account) { root.openAccount(account) }
        onSettingsRequested: root.openSettings()
        onSettingsBack: root.closeSettings()
        onCloseRequestedByView: root.close()
        onSwitchPanelRequested: function(direction) { root.switchPanel(direction) }
        onSaveRequested: function(key, value) { root.savePreference(key, value) }
        onRetryRequested: prefs.retry()
      }
    }
  }
}
