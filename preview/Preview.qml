import QtQuick
import qs.Commons as Commons
import "../kit"
import ".." as Teams

// Preview states for the foamy-kit preview harness (mock data, no processes).
Item {
  id: preview
  required property QtObject bar
  required property Item anchorItem
  property var previewStates: ["accounts", "context", "empty", "launching", "settings", "invalid", "editor", "bar"]
  property string previewState: "accounts"
  readonly property var popup: previewPopup

  readonly property var definitions: [
    {
      id: "work",
      name: "Contoso",
      appId: "teams-contoso",
      enabled: true,
      browser: "omarchy-launch-webapp",
      profile: "Work",
      url: "https://teams.microsoft.com",
      command: []
    },
    {
      id: "client",
      name: "Fabrikam (guest)",
      appId: "teams-fabrikam",
      enabled: true,
      browser: "omarchy-launch-webapp",
      profile: "Guest",
      url: "https://teams.microsoft.com",
      command: []
    },
    {
      id: "home",
      name: "Personal",
      appId: "teams-personal",
      enabled: true,
      browser: "omarchy-launch-webapp",
      profile: "Home",
      url: "https://teams.live.com",
      command: []
    }
  ]
  readonly property var accounts: [
    {
      id: "work",
      name: "Contoso",
      definition: definitions[0],
      running: true,
      active: true,
      unread: 3,
      context: "Design sync | Product",
      toplevel: null
    },
    {
      id: "client",
      name: "Fabrikam (guest)",
      definition: definitions[1],
      running: true,
      active: false,
      unread: 0,
      context: "Ada Lovelace",
      toplevel: null
    },
    {
      id: "home",
      name: "Personal",
      definition: definitions[2],
      running: false,
      active: false,
      unread: null,
      context: "",
      toplevel: null
    }
  ]
  // One account launching: the other closed account is unavailable meanwhile.
  readonly property var launchingAccounts: [accounts[0], Object.assign({}, accounts[1], {
      running: false,
      active: false,
      unread: null,
      context: ""
    }), accounts[2]]
  readonly property bool empty: previewState === "empty"
  // A hand-edited shell.json with one invalid account: the list reads empty and editing is blocked.
  readonly property bool invalid: previewState === "invalid"

  onPreviewStateChanged: if (previewState === "editor" && popup.bodyItem)
    popup.bodyItem.editAccount(definitions[0])

  FoamyPopup {
    id: previewPopup
    anchorItem: preview.anchorItem
    bar: preview.bar
    open: true
    body: Component {
      Item {
        implicitHeight: preview.previewState === "bar" ? barStrip.height : view.implicitHeight
        function editAccount(a) {
          view.editAccount(a)
        }
        Teams.TeamsView {
          id: view
          visible: preview.previewState !== "bar"
          width: parent.width
          height: parent.height
          accounts: preview.empty ? [] : preview.previewState === "launching" ? preview.launchingAccounts : preview.accounts
          launchingId: preview.previewState === "launching" ? "home" : ""
          summary: preview.empty ? {
            totalUnread: 0,
            runningCount: 0,
            unknownCount: 0,
            accountCount: 0
          } : {
            totalUnread: 3,
            runningCount: 2,
            unknownCount: 1,
            accountCount: 3
          }
          heading: preview.empty ? FoamyI18n.t("No accounts configured") : FoamyI18n.tn("%1 unread messages", 3)
          configured: !preview.empty
          showContext: preview.previewState === "context"
          editingSettings: preview.previewState === "settings" || preview.previewState === "editor" || preview.invalid
          settings: ({
              accounts: preview.invalid ? [] : preview.definitions,
              showCount: true,
              showContext: false
            })
          accountsLocked: preview.invalid
          settingsError: preview.invalid ? FoamyI18n.t("Enter an HTTPS Teams URL.") + " " + FoamyI18n.t("Fix or remove the invalid account in shell.json to edit the account list.") : ""
          candidates: [
            {
              appId: "teams-contoso",
              title: "(3) Design sync | Product | Microsoft Teams"
            },
            {
              appId: "teams-fabrikam",
              title: "Ada Lovelace | Microsoft Teams"
            }
          ]
        }
        // Bar widget states: no unread, unread with count, count hidden.
        Rectangle {
          id: barStrip
          visible: preview.previewState === "bar"
          width: parent.width
          height: 64
          color: Commons.Color.bar.background
          Row {
            anchors.centerIn: parent
            spacing: 48
            Repeater {
              model: [
                {
                  unread: 0,
                  show: true
                },
                {
                  unread: 3,
                  show: true
                },
                {
                  unread: 12,
                  show: true
                },
                {
                  unread: 3,
                  show: false
                }
              ]
              Teams.TeamsBarContent {
                required property var modelData
                unread: modelData.unread
                showCount: modelData.show
                foreground: Commons.Color.bar.text
                urgent: Commons.Color.urgent
              }
            }
          }
        }
      }
    }
  }
}
