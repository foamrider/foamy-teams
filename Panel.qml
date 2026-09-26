import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui
import "Model.js" as Model
import "Preferences.js" as Preferences

Panel {
  id: root
  moduleName: "foamy.teams"
  ipcTarget: "foamy.teams"
  manageIpc: false
  readonly property bool vertical: bar ? bar.vertical : false
  readonly property string language: Preferences.language(preference("language"),Qt.locale().name)
  // Normalize Qt-backed settings lists before validating them as JSON arrays.
  readonly property var preferences: JSON.parse(JSON.stringify(root.settings || {}))
  readonly property var definitions: preference("accounts")
  readonly property string configurationError: Preferences.configurationError(preferences)
  property bool editingSettings: false
  property string settingsError: ""
  property string launchError: ""
  property string launchingId: ""
  property string savingKey: ""
  property int generation: 0
  function preference(key) { return Preferences.value(preferences,key) }
  function tr(label,values) { return Preferences.text(label,language,values) }
  readonly property var windows: {
    var revision=generation
    var values=ToplevelManager.toplevels ? ToplevelManager.toplevels.values : []
    return values.map(function(w) { return {appId:String(w.appId || ""),title:String(w.title || ""),activated:w.activated===true,toplevel:w} })
  }
  readonly property var accounts: Model.accountsForWindows(definitions,windows)
  readonly property var summary: Model.summary(accounts)
  readonly property var displayed: Model.displayedAccounts(accounts,preference("showClosed"),preference("unreadFirst"))
  // Keep setup and invalid configuration reachable even when auto-hide is enabled.
  visible: !preference("hideWhenClosed") || summary.runningCount>0 || summary.accountCount===0 || opened || configurationError!==""
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  Connections { target: ToplevelManager.toplevels; function onValuesChanged() { root.generation++ } }
  onAccountsChanged: {
    if (launchingId && accounts.some(function(a) { return a.id===root.launchingId && a.running })) {
      launchingId=""; launchTimeout.stop()
    }
  }
  function openSettings() {
    editingSettings=true; open(); scroll.contentY=0
    Qt.callLater(function() { settingsPane.focusBack() })
  }
  function closeSettings() { editingSettings=false; scroll.contentY=0; Qt.callLater(function() { view.forceActiveFocus() }) }
  function savePreference(key,value) {
    if (preferencesSave.running) return
    if (!Preferences.valid(key,value)) { settingsError=tr(key==="accounts" ? Preferences.accountError(value) : "Invalid setting."); return }
    settingsError=""; savingKey=key
    // The shell writer merges only this setting into the latest on-disk config.
    preferencesSave.command=["omarchy-shell","shell","setBarWidget",moduleName,key," "+JSON.stringify(value),"{}"]
    preferencesSave.running=true
  }
  Process {
    id: preferencesSave
    stdout: StdioCollector { id: saveOutput; waitForEnd: true }
    onExited: function(code) {
      if (code!==0 || saveOutput.text.trim()!=="ok") root.settingsError=root.tr("Could not save settings. Try again.")
      else settingsPane.saved(root.savingKey)
    }
  }
  function openAccount(account) {
    if (!account) return
    launchError=""
    if (account.running && account.toplevel) { close(); account.toplevel.activate(); return }
    if (launchingId || launcher.running) return
    launchingId=account.id
    launcher.command=["python3",decodeURIComponent(String(Qt.resolvedUrl("launch.py")).replace(/^file:\/\//,"")),JSON.stringify(Model.launchArguments(account.definition))]
    launcher.running=true
    launchTimeout.restart()
  }
  Process {
    id: launcher
    onExited: function(code) {
      if (code!==0) { root.launchingId=""; launchTimeout.stop(); root.launchError=root.tr("Could not launch the account. Check its browser or launch arguments."); root.open() }
    }
  }
  Timer {
    id: launchTimeout
    interval: 15000
    onTriggered: { root.launchingId=""; root.launchError=root.tr("No matching window appeared. Check the account application ID or sign in to Teams."); root.open() }
  }
  IpcHandler {
    target: "foamy.teams"
    function open(): void { root.open() }
    function close(): void { root.close() }
    function toggle(): void { root.toggle() }
    function settings(): void { root.openSettings() }
  }
  onOpenedChanged: if (opened) {
    view.cursorIndex=-1
    Qt.callLater(function() { if (root.editingSettings) settingsPane.focusBack(); else view.forceActiveFocus() })
  }
  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""; labelVisible: false; hasVisualContent: true
    active: root.summary.totalUnread>0
    activeColor: Color.accent
    fixedWidth: root.vertical ? -1 : Math.max(Style.bar.iconSlot,barContent.implicitWidth+Style.bar.iconSlot-Style.bar.iconCanvas)
    tooltipText: "Microsoft Teams · "+view.heading
    onPressed: function(code) {
      if (code===Qt.MiddleButton) root.openAccount(Model.primaryAccount(root.accounts,root.preference("defaultAccount")))
      else if (code===Qt.RightButton) root.openSettings()
      else root.toggle()
    }
    Row {
      id: barContent
      anchors.centerIn: parent
      spacing: Style.space(1)
      OpticalGlyph { width: Style.bar.iconCanvas; height: Style.bar.iconCanvas; text: "󰊻"; fontFamily: button.fontFamily; fontSize: Style.font.body; color: button.foreground }
      Text { visible: !root.vertical && root.preference("showCount") && root.summary.totalUnread>0; text: String(root.summary.totalUnread); color: root.bar ? root.bar.urgent : Color.urgent; font.family: button.fontFamily; font.pixelSize: Style.font.body; anchors.verticalCenter: parent.verticalCenter }
    }
  }
  TeamsPopup {
    id: popup
    anchorItem: button; owner: root; bar: root.bar; open: root.opened
    padding: 0
    contentWidth: fittedContentWidth(Style.space(root.editingSettings ? 440 : 420))
    contentHeight: fittedContentHeight(root.editingSettings ? settingsPane.implicitHeight : view.implicitHeight,Style.space(root.editingSettings ? 680 : 560))
    focusTarget: root.editingSettings ? settingsPane : view
    Controls.ScrollView {
      id: scroll
      anchors.fill: parent
      clip: true
      property alias contentY: flick.contentY
      Flickable {
        id: flick
        contentWidth: width
        contentHeight: root.editingSettings ? settingsPane.implicitHeight : view.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        Keys.onEscapePressed: { if (root.editingSettings && settingsPane.editing) settingsPane.editing=false; else if (root.editingSettings) root.closeSettings(); else root.close() }
        TeamsView {
          id: view
          visible: !root.editingSettings
          width: parent.width
          accounts: root.displayed; summary: root.summary; language: root.language; configured: root.definitions.length>0
          showContext: root.preference("showContext")
          error: root.launchError
          launchingId: root.launchingId
          onActivate: function(account) { root.openAccount(account) }
          onSettingsRequested: root.openSettings()
        }
        SettingsPane {
          id: settingsPane
          visible: root.editingSettings
          width: parent.width
          settings: root.preferences; windows: root.windows; language: root.language; saving: preferencesSave.running
          error: root.settingsError || (root.configurationError ? root.tr(root.configurationError) : "")
          onSave: function(key,value) { root.savePreference(key,value) }
          onBack: root.closeSettings()
        }
      }
      Controls.ScrollBar.vertical.policy: flick.contentHeight>height ? Controls.ScrollBar.AsNeeded : Controls.ScrollBar.AlwaysOff
      Connections {
        target: scroll.Window.window
        function onActiveFocusItemChanged() {
          var item=scroll.Window.window ? scroll.Window.window.activeFocusItem : null
          if (!item || !root.opened) return
          var ancestor=item
          while (ancestor && ancestor!==flick.contentItem) ancestor=ancestor.parent
          if (!ancestor) return
          var point=item.mapToItem(flick.contentItem,0,0)
          if (point.y<flick.contentY) flick.contentY=Math.max(0,point.y-Style.space(8))
          else if (point.y+item.height>flick.contentY+flick.height) flick.contentY=Math.max(0,Math.min(flick.contentHeight-flick.height,point.y+item.height-flick.height+Style.space(8)))
        }
      }
    }
  }
}
