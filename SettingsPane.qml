import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import qs.Ui
import qs.Commons
import "Preferences.js" as Preferences
import "Model.js" as Model

Column {
  id: root
  required property var settings
  required property var windows
  required property string language
  property bool saving: false
  property string error: ""
  property string localError: ""
  property bool editing: false
  property var draft: ({})
  property string accountsBaseline: ""
  property bool adding: false
  property string commandDraft: "[]"
  readonly property var definitions: Preferences.value(settings,"accounts")
  readonly property color secondary: Qt.tint(Color.popups.background,Qt.alpha(Color.popups.text,0.7))
  signal save(string key,var value)
  signal back()
  function tr(label) { return Preferences.text(label,language) }
  function focusBack() { backButton.forceActiveFocus() }
  function edit(account) {
    adding=!account
    accountsBaseline=JSON.stringify(definitions)
    draft=account ? JSON.parse(JSON.stringify(account)) : {id:"account-"+Date.now(),name:"",appId:"",enabled:true,browser:"omarchy-launch-webapp",profile:"",url:"https://teams.microsoft.com",command:[]}
    commandDraft=JSON.stringify(draft.command)
    localError=""; editing=true
    Qt.callLater(function() { nameField.forceActiveFocus() })
  }
  function change(key,value) { var next=Object.assign({},draft); next[key]=value; draft=next }
  function saveAccount() {
    if (accountsBaseline!==JSON.stringify(definitions)) { localError=tr("Settings changed elsewhere. Reopen the account editor."); return }
    var updated=Object.assign({},draft)
    try { updated.command=JSON.parse(commandDraft) } catch(e) { localError=tr("Enter a JSON array of command arguments, or []."); return }
    var next=definitions.slice()
    if (adding) next.push(updated)
    else next=next.map(function(a) { return a.id===updated.id ? updated : a })
    var message=Preferences.accountError(next)
    if (message) { localError=tr(message); return }
    localError=""; root.save("accounts",next)
  }
  function saved(key) { if (key==="accounts") { editing=false; localError=""; focusBack() } }
  function remove(id) { root.save("accounts",definitions.filter(function(a) { return a.id!==id })) }
  function move(index,delta) {
    var next=definitions.slice(), item=next.splice(index,1)[0]
    next.splice(index+delta,0,item); root.save("accounts",next)
  }
  padding: Style.space(20)
  spacing: Style.space(12)
  component Label: Text {
    textFormat: Text.PlainText; color: Color.popups.text; font.family: "sans-serif"; font.pixelSize: Style.space(13); wrapMode: Text.WordWrap
  }
  component Field: Controls.TextField {
    color: Color.popups.text; font.family: "sans-serif"; font.pixelSize: Style.space(13); selectByMouse: true
    implicitHeight: Style.space(36)
    background: Rectangle { color: Qt.alpha(Color.popups.text,0.035); radius: Style.space(7); border.width: 1; border.color: parent.activeFocus ? Color.accent : Qt.alpha(Color.popups.text,0.2) }
  }
  RowLayout {
    width: parent.width-root.padding*2
    TeamsAction { id: backButton; iconName: "arrow-left"; tooltipText: root.tr("Back"); foreground: root.secondary; enabled: !root.saving; onClicked: { if(root.editing) {root.editing=false;root.localError=""} else root.back() } }
    Label { text: root.tr(root.editing ? (root.adding ? "New account" : "Edit account") : "Settings"); Layout.fillWidth: true }
    Label { visible: root.saving; text: root.tr("Saving…"); color: root.secondary; font.pixelSize: Style.space(11) }
  }
  Label { visible: root.localError!=="" || root.error!==""; width: parent.width-root.padding*2; text: root.localError || root.error; color: Color.urgent; Accessible.role: Accessible.AlertMessage }
  Column {
    visible: !root.editing
    width: parent.width-root.padding*2
    spacing: Style.space(10)
    enabled: !root.saving
    RowLayout {
      width: parent.width
      Label { text: root.tr("Accounts"); Layout.fillWidth: true }
      TeamsAction { label: root.tr("Add account"); iconName: "plus"; foreground: Color.accent; enabled: root.definitions.length<32; onClicked: root.edit(null) }
    }
    Repeater {
      model: root.definitions
      Item {
        id: accountRow
        required property var modelData
        required property int index
        width: parent.width
        implicitHeight: Style.space(64)
        RowLayout {
          anchors.fill: parent
          spacing: Style.space(10)
          Rectangle {
            Layout.preferredWidth: Style.space(34); Layout.preferredHeight: Style.space(34)
            radius: Style.space(9)
            color: Qt.alpha(Color.popups.text,0.06)
            Label { anchors.centerIn: parent; text: accountRow.modelData.name.slice(0,1).toUpperCase(); color: root.secondary; font.pixelSize: Style.space(14) }
          }
          ColumnLayout {
            Layout.fillWidth: true
            spacing: Style.space(2)
            Label { text: accountRow.modelData.name; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap; font.pixelSize: Style.space(14) }
            Label { text: root.tr(accountRow.modelData.enabled ? "Enabled" : "Disabled"); color: root.secondary; font.pixelSize: Style.space(11) }
          }
          RowLayout {
            spacing: Style.space(2)
            TeamsAction { iconName: "chevron-up"; tooltipText: root.tr("Move up"); foreground: root.secondary; enabled: accountRow.index>0; onClicked: root.move(accountRow.index,-1) }
            TeamsAction { iconName: "chevron-down"; tooltipText: root.tr("Move down"); foreground: root.secondary; enabled: accountRow.index<root.definitions.length-1; onClicked: root.move(accountRow.index,1) }
            TeamsAction { iconName: "pencil"; tooltipText: root.tr("Edit")+" · "+accountRow.modelData.name; foreground: root.secondary; onClicked: root.edit(accountRow.modelData) }
          }
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Qt.alpha(Color.popups.text,0.1) }
      }
    }
    TeamsDropdown {
      width: parent.width; fontFamily: "sans-serif"; label: root.tr("Language"); value: Preferences.value(root.settings,"language")
      options: [{value:"system",label:root.tr("System")},{value:"en",label:"English"},{value:"nb",label:"Norsk bokmål"}]
      onChanged: function(value) { root.save("language",value) }
    }
    Repeater {
      model: [{key:"showCount",label:"Show unread count in the bar"},{key:"hideWhenClosed",label:"Hide when all accounts are closed"},{key:"showContext",label:"Show window context"},{key:"showClosed",label:"Show closed accounts"},{key:"unreadFirst",label:"Put unread accounts first"}]
      Toggle {
        required property var modelData
        width: parent.width; implicitHeight: Style.space(36); color: "transparent"; borderSpec: activeFocus ? Border.flat(Color.accent,1) : Border.none(); radius: Style.space(7)
        fontFamily: "sans-serif"; titleSize: Style.space(12); label: root.tr(modelData.label); checked: Preferences.value(root.settings,modelData.key)
        onClicked: root.save(modelData.key,!checked)
      }
    }
    TeamsDropdown {
      width: parent.width; fontFamily: "sans-serif"; label: root.tr("Middle-click account"); value: root.definitions.some(function(a) {return a.enabled && a.id===Preferences.value(root.settings,"defaultAccount")}) ? Preferences.value(root.settings,"defaultAccount") : ""
      options: [{value:"",label:root.tr("Most relevant account")}].concat(root.definitions.filter(function(a) {return a.enabled}).map(function(a) {return {value:a.id,label:a.name}}))
      onChanged: function(value) { root.save("defaultAccount",value) }
    }
  }
  Column {
    visible: root.editing
    width: parent.width-root.padding*2
    spacing: Style.space(8)
    enabled: !root.saving
    Label { width: parent.width; text: root.tr("Open Teams in a separate browser profile, then select its window here."); color: root.secondary; font.pixelSize: Style.space(12) }
    Label { text: root.tr("Name") }
    Field { id: nameField; width: parent.width; text: root.draft.name || ""; Accessible.name: root.tr("Name"); onTextEdited: root.change("name",text) }
    TeamsDropdown {
      width: parent.width; fontFamily: "sans-serif"; label: root.tr("Open Teams window"); value: root.draft.appId || ""
      options: [{value:"",label:root.tr("Manual application ID")}].concat(Model.candidates(root.windows))
      onChanged: function(value) { root.change("appId",value) }
    }
    Label { text: root.tr("Application ID") }
    Field { width: parent.width; text: root.draft.appId || ""; Accessible.name: root.tr("Application ID"); onTextEdited: root.change("appId",text) }
    Label { visible: !!root.draft.appId && !root.windows.some(function(w) { return w.appId.toLowerCase()===root.draft.appId.toLowerCase() }); text: root.tr("No matching window yet"); color: root.secondary; font.pixelSize: Style.space(11) }
    Toggle { width: parent.width; implicitHeight: Style.space(36); color: "transparent"; borderSpec: activeFocus ? Border.flat(Color.accent,1) : Border.none(); radius: Style.space(7); label: root.tr("Enabled"); fontFamily: "sans-serif"; titleSize: Style.space(13); checked: root.draft.enabled===true; onClicked: root.change("enabled",!checked) }
    Label { text: root.tr("Browser executable") }
    Field { width: parent.width; text: root.draft.browser || ""; Accessible.name: root.tr("Browser executable"); onTextEdited: root.change("browser",text) }
    Label { text: root.tr("Browser profile") }
    Field { width: parent.width; text: root.draft.profile || ""; Accessible.name: root.tr("Browser profile"); onTextEdited: root.change("profile",text) }
    Label { text: root.tr("Teams URL") }
    Field { width: parent.width; text: root.draft.url || ""; Accessible.name: root.tr("Teams URL"); onTextEdited: root.change("url",text) }
    Label { text: root.tr("Advanced launch arguments (JSON array)"); width: parent.width }
    Field { id: commandField; width: parent.width; text: root.commandDraft; onTextEdited: root.commandDraft=text; Accessible.name: root.tr("Advanced launch arguments (JSON array)") }
    Label { width: parent.width; text: root.tr("Leave advanced arguments as [] to use the browser settings."); color: root.secondary; font.pixelSize: Style.space(12) }
    RowLayout {
      width: parent.width
      TeamsAction { visible: !root.adding; label: root.tr("Remove"); iconName: "trash"; foreground: root.secondary; onClicked: root.remove(root.draft.id) }
      TeamsAction { label: root.tr("Cancel"); iconName: ""; foreground: root.secondary; onClicked: {root.editing=false;root.localError=""} }
      Item { Layout.fillWidth: true }
      TeamsAction { label: root.tr("Save"); iconName: "check"; foreground: Color.accent; onClicked: root.saveAccount() }
    }
  }
}
