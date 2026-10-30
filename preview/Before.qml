import QtQuick
import qs.Commons
import qs.Commons as Commons
import ".." as Dev

// The dev-branch UI for the --trio "Before" column (rendered from origin/dev).
Item {
  id: preview
  required property QtObject bar
  required property Item anchorItem
  property var previewStates: ["accounts", "context", "empty", "settings"]
  property string previewState: "accounts"
  readonly property Item popup: popup

  readonly property var definitions: [
    { id: "work", name: "Contoso", appId: "teams-contoso", enabled: true, browser: "omarchy-launch-webapp", profile: "Work", url: "https://teams.microsoft.com", command: [] },
    { id: "client", name: "Fabrikam (guest)", appId: "teams-fabrikam", enabled: true, browser: "omarchy-launch-webapp", profile: "Guest", url: "https://teams.microsoft.com", command: [] },
    { id: "home", name: "Personal", appId: "teams-personal", enabled: true, browser: "omarchy-launch-webapp", profile: "Home", url: "https://teams.live.com", command: [] }
  ]
  readonly property var accounts: [
    { id: "work", name: "Contoso", definition: definitions[0], running: true, active: true, unread: 3, context: "Design sync | Product", toplevel: null },
    { id: "client", name: "Fabrikam (guest)", definition: definitions[1], running: true, active: false, unread: 0, context: "Ada Lovelace", toplevel: null },
    { id: "home", name: "Personal", definition: definitions[2], running: false, active: false, unread: null, context: "", toplevel: null }
  ]
  readonly property bool empty: previewState === "empty"
  readonly property bool settingsState: previewState === "settings"

  Dev.TeamsPopup {
    id: popup
    anchorItem: preview.anchorItem; bar: preview.bar; open: true; padding: 0
    contentWidth: popup.fittedContentWidth(Style.space(preview.settingsState ? 440 : 420))
    contentHeight: popup.fittedContentHeight(preview.settingsState ? pane.implicitHeight : view.implicitHeight, Style.space(preview.settingsState ? 680 : 560))
    Dev.TeamsView {
      id: view
      visible: !preview.settingsState
      width: parent.width
      accounts: preview.empty ? [] : preview.accounts
      summary: preview.empty ? { totalUnread: 0, runningCount: 0, unknownCount: 0, accountCount: 0 } : { totalUnread: 3, runningCount: 2, unknownCount: 1, accountCount: 3 }
      language: "en"
      configured: !preview.empty
      showContext: preview.previewState === "context"
    }
    Dev.SettingsPane {
      id: pane
      visible: preview.settingsState
      width: parent.width
      settings: ({ accounts: preview.definitions, showCount: true, showContext: true })
      windows: []
      language: "en"
    }
  }
}
