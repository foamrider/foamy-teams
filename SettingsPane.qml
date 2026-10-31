import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "kit"
import "kit/FoamyPrefs.js" as Prefs
import "Preferences.js" as Preferences
import "Model.js" as Model

// Teams settings on the foamy settings skeleton: the account list (add,
// reorder, edit), bar and panel options, and the account editor, which
// replaces the list on the same page. Back (or Esc) leaves the editor first.
FoamySettingsPage {
  id: root

  required property var settings
  property var candidates: []
  property string localError: ""
  property bool editing: false
  property var draft: ({})
  property string accountsBaseline: ""
  property bool adding: false
  property string commandDraft: "[]"
  readonly property var definitions: pref("accounts")

  signal save(string key, var value)
  signal backToPanel()

  title: FoamyI18n.t(editing ? (adding ? "New account" : "Edit account") : "Settings")
  // Local validation first, then the panel's save error.
  property string panelError: ""
  error: localError || panelError
  onBack: {
    if (editing) leaveEditor()
    else root.backToPanel()
  }

  function tr(label) { return FoamyI18n.t(label) }
  function pref(key) { return Prefs.value(Preferences.fields, root.settings, key) }
  function leaveEditor() { editing = false; localError = ""; resetScroll(); focusBack() }
  function edit(account) {
    adding = !account
    accountsBaseline = JSON.stringify(definitions)
    draft = account ? JSON.parse(JSON.stringify(account)) : { id: "account-" + Date.now(), name: "", appId: "", enabled: true, browser: "omarchy-launch-webapp", profile: "", url: "https://teams.microsoft.com", command: [] }
    commandDraft = JSON.stringify(draft.command)
    localError = ""
    editing = true
    resetScroll()
    Qt.callLater(function() { nameField.focusInput() })
  }
  function change(key, value) { var next = Object.assign({}, draft); next[key] = value; draft = next }
  function saveAccount() {
    if (accountsBaseline !== JSON.stringify(definitions)) { localError = tr("Settings changed elsewhere. Reopen the account editor."); return }
    var updated = Object.assign({}, draft)
    try { updated.command = JSON.parse(commandDraft) } catch (e) { localError = tr("Enter a JSON array of command arguments, or []."); return }
    var next = definitions.slice()
    if (adding) next.push(updated)
    else next = next.map(function(a) { return a.id === updated.id ? updated : a })
    var message = Preferences.accountError(next)
    if (message) { localError = tr(message); return }
    localError = ""
    root.save("accounts", next)
  }
  function saved(key) { if (key === "accounts" && editing) leaveEditor() }
  function remove(id) { root.save("accounts", definitions.filter(function(a) { return a.id !== id })) }
  function move(index, delta) {
    var next = definitions.slice(), item = next.splice(index, 1)[0]
    next.splice(index + delta, 0, item)
    root.save("accounts", next)
  }

  component Label: Text {
    textFormat: Text.PlainText
    horizontalAlignment: Text.AlignLeft
    color: FoamyPalette.text
    font.family: FoamyStyle.fontFamily
    font.pixelSize: FoamyStyle.font.body
    wrapMode: Text.WordWrap
  }
  // The kit's label-above style (FoamyDropdown, FoamyTextSettingField).
  component FieldLabel: Label {
    width: parent.width
    color: FoamyPalette.secondaryText
    font.family: FoamyStyle.fontFamily
    font.pixelSize: FoamyStyle.font.bodySmall
    font.bold: true
  }

  // --- account list and options -------------------------------------------
  FoamySettingsSection {
    visible: !root.editing
    width: parent.width
    title: root.tr("Accounts")
    enabled: !root.saving

    Repeater {
      model: root.definitions
      Item {
        id: accountRow
        required property var modelData
        required property int index
        width: parent.width
        implicitHeight: FoamyStyle.rowHeight + FoamyStyle.gap
        RowLayout {
          anchors.fill: parent
          spacing: FoamyStyle.rowPadding
          Rectangle {
            Layout.preferredWidth: Style.space(30)
            Layout.preferredHeight: Style.space(30)
            radius: FoamyStyle.radius
            color: FoamyPalette.fieldFill
            Label {
              anchors.centerIn: parent
              text: accountRow.modelData.name.slice(0, 1).toUpperCase()
              color: FoamyPalette.secondaryText
              font.pixelSize: FoamyStyle.font.subtitle
            }
          }
          ColumnLayout {
            Layout.fillWidth: true
            spacing: FoamyStyle.gapTiny
            Label { Layout.fillWidth: true; text: accountRow.modelData.name; elide: Text.ElideRight; wrapMode: Text.NoWrap; font.pixelSize: FoamyStyle.font.subtitle }
            Label { text: root.tr(accountRow.modelData.enabled ? "Enabled" : "Disabled"); color: FoamyPalette.secondaryText; font.pixelSize: FoamyStyle.font.caption }
          }
          FoamyAction { focusable: true; iconName: "chevron-up"; tooltipText: root.tr("Move up"); foreground: FoamyPalette.secondaryText; enabled: accountRow.index > 0; onClicked: root.move(accountRow.index, -1) }
          FoamyAction { focusable: true; iconName: "chevron-down"; tooltipText: root.tr("Move down"); foreground: FoamyPalette.secondaryText; enabled: accountRow.index < root.definitions.length - 1; onClicked: root.move(accountRow.index, 1) }
          FoamyAction { focusable: true; iconName: "pencil"; tooltipText: root.tr("Edit") + " · " + accountRow.modelData.name; foreground: FoamyPalette.secondaryText; onClicked: root.edit(accountRow.modelData) }
        }
      }
    }
    Label {
      visible: root.definitions.length === 0
      width: parent.width
      text: root.tr("Open Teams in a separate browser profile, then select its window here.")
      color: FoamyPalette.mutedText
      font.pixelSize: FoamyStyle.font.bodySmall
    }
    FoamyButton {
      focusable: true
      text: root.tr("Add account")
      iconName: "plus"
      enabled: root.definitions.length < 32
      onClicked: root.edit(null)
    }
  }

  FoamySettingsSection {
    visible: !root.editing
    width: parent.width
    title: root.tr("Bar")
    enabled: !root.saving
    Repeater {
      model: [{ key: "showCount", label: "Show unread count in the bar" }, { key: "hideWhenClosed", label: "Hide when all accounts are closed" }]
      FoamyToggle {
        required property var modelData
        width: parent.width
        label: root.tr(modelData.label)
        checked: root.pref(modelData.key)
        onClicked: root.save(modelData.key, !checked)
      }
    }
    FoamyDropdown {
      objectName: "defaultAccount"
      width: parent.width
      compact: true
      label: root.tr("Middle-click account")
      value: root.definitions.some(function(a) { return a.enabled && a.id === root.pref("defaultAccount") }) ? root.pref("defaultAccount") : ""
      options: [{ value: "", label: root.tr("Most relevant account") }].concat(root.definitions.filter(function(a) { return a.enabled }).map(function(a) { return { value: a.id, label: a.name } }))
      onChanged: function(value) { root.save("defaultAccount", value) }
    }
  }

  FoamySettingsSection {
    visible: !root.editing
    width: parent.width
    title: root.tr("Panel")
    enabled: !root.saving
    FoamyToggle {
      width: parent.width
      label: root.tr("Show window context")
      description: root.tr("Shows the chat or person name from each window title. Anyone watching a shared screen can read it.")
      checked: root.pref("showContext")
      onClicked: root.save("showContext", !checked)
    }
    Repeater {
      model: [{ key: "showClosed", label: "Show closed accounts" }, { key: "unreadFirst", label: "Put unread accounts first" }]
      FoamyToggle {
        required property var modelData
        width: parent.width
        label: root.tr(modelData.label)
        checked: root.pref(modelData.key)
        onClicked: root.save(modelData.key, !checked)
      }
    }
  }

  // --- account editor ---------------------------------------------------------
  FoamySettingsSection {
    visible: root.editing
    width: parent.width
    description: root.tr("Open Teams in a separate browser profile, then select its window here.")
    enabled: !root.saving

    FieldLabel { text: root.tr("Name") }
    SafeTextField { id: nameField; width: parent.width; text: root.draft.name || ""; translate: FoamyI18n.t; Accessible.name: root.tr("Name"); onTextEdited: root.change("name", text) }
    FoamyDropdown {
      objectName: "appIdPicker"
      width: parent.width
      label: root.tr("Open Teams window")
      value: root.draft.appId || ""
      options: [{ value: "", label: root.tr("Manual application ID") }].concat(Model.candidates(root.candidates))
      onChanged: function(value) { root.change("appId", value) }
    }
    FieldLabel { text: root.tr("Application ID") }
    SafeTextField { width: parent.width; text: root.draft.appId || ""; translate: FoamyI18n.t; Accessible.name: root.tr("Application ID"); onTextEdited: root.change("appId", text) }
    Label {
      visible: !!root.draft.appId && !root.candidates.some(function(w) { return w.appId.toLowerCase() === String(root.draft.appId).toLowerCase() })
      width: parent.width
      text: root.tr("No matching window yet")
      color: FoamyPalette.mutedText
      font.pixelSize: FoamyStyle.font.bodySmall
    }
    FoamyToggle { width: parent.width; label: root.tr("Enabled"); checked: root.draft.enabled === true; onClicked: root.change("enabled", !checked) }
    FieldLabel { text: root.tr("Browser executable") }
    SafeTextField { width: parent.width; text: root.draft.browser || ""; translate: FoamyI18n.t; Accessible.name: root.tr("Browser executable"); onTextEdited: root.change("browser", text) }
    FieldLabel { text: root.tr("Browser profile") }
    SafeTextField { width: parent.width; text: root.draft.profile || ""; translate: FoamyI18n.t; Accessible.name: root.tr("Browser profile"); onTextEdited: root.change("profile", text) }
    FieldLabel { text: root.tr("Teams URL") }
    SafeTextField { width: parent.width; text: root.draft.url || ""; translate: FoamyI18n.t; Accessible.name: root.tr("Teams URL"); onTextEdited: root.change("url", text) }
    FieldLabel { text: root.tr("Advanced launch arguments (JSON array)") }
    SafeTextField { width: parent.width; text: root.commandDraft; translate: FoamyI18n.t; Accessible.name: root.tr("Advanced launch arguments (JSON array)"); onTextEdited: root.commandDraft = text }
    Label {
      width: parent.width
      text: root.tr("Leave advanced arguments as [] to use the browser settings.")
      color: FoamyPalette.mutedText
      font.pixelSize: FoamyStyle.font.bodySmall
    }
    RowLayout {
      width: parent.width
      spacing: FoamyStyle.gap
      FoamyAction { visible: !root.adding; focusable: true; destructive: true; label: root.tr("Remove"); iconName: "trash"; foreground: FoamyPalette.secondaryText; onClicked: root.remove(root.draft.id) }
      FoamyAction { focusable: true; label: root.tr("Cancel"); iconName: ""; foreground: FoamyPalette.secondaryText; onClicked: root.leaveEditor() }
      Item { Layout.fillWidth: true }
      FoamyAction { focusable: true; label: root.tr("Save"); iconName: "check"; foreground: Commons.Color.accent; onClicked: root.saveAccount() }
    }
  }
}
