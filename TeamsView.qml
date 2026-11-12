import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "kit"

// The popup body: header, account rows on one keyboard/pointer cursor, and
// the settings page. Data comes in through properties so the preview can feed
// mock states; the Panel owns window tracking, launching and saving.
PanelKeyCatcher {
  id: root

  property var accounts: []
  property var summary: ({ totalUnread: 0, runningCount: 0, unknownCount: 0, accountCount: 0 })
  property string heading: ""
  property bool configured: false
  property bool showContext: false
  property string error: ""
  property string launchingId: ""
  property bool editingSettings: false
  property var settings: ({})
  property var candidates: []
  property bool saving: false
  property string settingsError: ""
  property bool accountsLocked: false
  property bool retryable: false

  signal activate(var account)
  signal settingsRequested()
  signal settingsBack()
  signal closeRequestedByView()
  signal switchPanelRequested(int direction)
  signal saveRequested(string key, var value)
  signal retryRequested()

  readonly property int settingsStop: accounts.length
  readonly property string subtitle: summary.accountCount === 0
    ? FoamyI18n.t(configured ? "Enable an account in Settings" : "Add your Teams accounts in Settings") : ""

  function panelOpened() {
    cursor.reset()
    list.contentY = 0
    if (editingSettings) settingsPane.focusBack()
    else root.forceActiveFocus()
  }
  function settingsOpened() { settingsPane.resetScroll(); settingsPane.focusBack() }
  function settingsClosed() { list.contentY = 0; root.forceActiveFocus() }
  function saved(key) { settingsPane.saved(key) }
  function editAccount(account) { settingsPane.edit(account) }
  function activateCursor() {
    if (cursor.index >= 0 && cursor.index < accounts.length) root.activate(accounts[cursor.index])
    else if (cursor.index === settingsStop) root.settingsRequested()
  }
  // Keep the keyboard cursor's row in view.
  function reveal(index) {
    var row = accountRepeater.itemAt(index)
    if (!row) { if (index === settingsStop) list.contentY = 0; return }
    var y = row.mapToItem(list.contentItem, 0, 0).y
    if (y < list.contentY) list.contentY = Math.max(0, y - FoamyStyle.gap)
    else if (y + row.height > list.contentY + list.height)
      list.contentY = Math.min(list.contentHeight - list.height, y + row.height - list.height + FoamyStyle.gap)
  }

  implicitWidth: FoamyStyle.popupWidth
  implicitHeight: editingSettings ? settingsPane.implicitHeight : content.implicitHeight
  blocked: editingSettings

  FoamyCursor { id: cursor; count: root.accounts.length + 1 }

  onMoveRequested: function(dx, dy) { cursor.move(dy !== 0 ? dy : dx); root.reveal(cursor.index) }
  onActivateRequested: root.activateCursor()
  onCloseRequested: root.closeRequestedByView()
  onTabRequested: function(direction) { root.switchPanelRequested(direction) }
  onTextKey: function(text, modifiers) { if (cursor.plain(modifiers) && (text === "s" || text === "S")) root.settingsRequested() }

  component Label: Text {
    textFormat: Text.PlainText
    horizontalAlignment: Text.AlignLeft
    font.family: FoamyStyle.fontFamily
    font.pixelSize: FoamyStyle.font.body
    color: FoamyPalette.text
    wrapMode: Text.WordWrap
  }

  Flickable {
    id: list
    visible: !root.editingSettings
    anchors.fill: parent
    contentWidth: width
    contentHeight: content.implicitHeight
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    flickableDirection: Flickable.VerticalFlick
    Controls.ScrollBar.vertical: Controls.ScrollBar { policy: Controls.ScrollBar.AsNeeded }

    // A wheel notch scrolls about three rows, however the mouse splits it.
    FoamyWheelScroll { target: list }

    Column {
      id: content
      width: list.width
      bottomPadding: FoamyStyle.padding

      // Title-only band (list panel): no hero content.
      FoamyHeroBand {
        width: parent.width
        iconGlyph: "\u{f02bb}"   // nf-md-microsoft_teams, as the bar widget
        title: "Microsoft Teams"
        meta: root.heading
        settingsHasCursor: cursor.at(root.settingsStop)
        onSettingsClicked: root.settingsRequested()
        onSettingsHovered: function(hovered) { if (hovered) cursor.hover(root.settingsStop) }
      }

      Item { width: 1; height: FoamyStyle.gap }

      Column {
        x: FoamyStyle.padding
        width: parent.width - FoamyStyle.padding * 2
        spacing: FoamyStyle.gap
        bottomPadding: visible ? FoamyStyle.gap : 0
        visible: root.subtitle !== "" || root.error !== "" || (root.accounts.length === 0 && root.summary.accountCount > 0)
        Label {
          visible: root.error !== ""
          width: parent.width
          text: root.error
          color: Commons.Color.urgent
          font.pixelSize: FoamyStyle.font.bodySmall
          Accessible.role: Accessible.AlertMessage
          Accessible.name: text
        }
        Label {
          visible: root.subtitle !== ""
          width: parent.width
          text: root.subtitle
          color: FoamyPalette.mutedText
          font.pixelSize: FoamyStyle.font.bodySmall
        }
        Label {
          visible: root.accounts.length === 0 && root.summary.accountCount > 0
          width: parent.width
          text: FoamyI18n.t("No visible accounts") + "\n" + FoamyI18n.t("Show closed accounts in Settings")
          color: FoamyPalette.mutedText
          font.pixelSize: FoamyStyle.font.bodySmall
        }
      }

      Repeater {
        id: accountRepeater
        model: root.accounts
        FoamyCursorSurface {
          id: row
          required property var modelData
          required property int index
          readonly property bool launching: root.launchingId === modelData.id
          // Another account is launching: this closed one can't start until it ends.
          readonly property bool blocked: root.launchingId !== "" && !launching && !modelData.running
          readonly property bool hasUnread: modelData.running && modelData.unread > 0
          readonly property bool active: hasCursor
          readonly property string statusText: !modelData.running || modelData.unread === null ? ""
            : modelData.unread > 0 ? FoamyI18n.tn("%1 unread", modelData.unread) : FoamyI18n.t("No unread")
          readonly property string actionText: launching ? FoamyI18n.t("Launching…")
            : modelData.running ? FoamyI18n.t("Focus") : FoamyI18n.t("Launch")
          objectName: "account:" + modelData.id
          enabled: !blocked
          opacity: blocked ? FoamyStyle.disabledOpacity : 1
          x: FoamyStyle.gapLarge
          width: content.width - FoamyStyle.gapLarge * 2
          height: root.showContext ? Style.space(60) : Style.space(46)
          foreground: FoamyPalette.text
          hasCursor: cursor.at(index)
          onHovered: cursor.hover(index)
          onClicked: root.activate(modelData)
          Accessible.role: Accessible.Button
          Accessible.name: modelData.name + (statusText ? ", " + statusText : "") + ", " + actionText
          Accessible.onPressAction: root.activate(modelData)

          RowLayout {
            anchors.fill: parent
            anchors.leftMargin: FoamyStyle.rowPadding
            anchors.rightMargin: FoamyStyle.rowPadding
            spacing: FoamyStyle.rowPadding

            // Running marker: theme green when the account has a window.
            Rectangle {
              Layout.preferredWidth: Style.space(3)
              Layout.preferredHeight: Style.space(26)
              radius: FoamyStyle.pillRadius(width)
              color: row.modelData.running ? FoamyPalette.onSurface(FoamyPalette.success) : FoamyPalette.divider
            }
            ColumnLayout {
              Layout.fillWidth: true
              spacing: FoamyStyle.gapTiny
              // The unread count sits with the name it belongs to; nothing when
              // all is read (the header says so) or the count is unknown.
              Row {
                id: nameLine
                Layout.fillWidth: true
                spacing: FoamyStyle.gap
                Label {
                  anchors.verticalCenter: parent.verticalCenter
                  width: Math.min(implicitWidth, nameLine.width - (badge.visible ? badge.width + nameLine.spacing : 0))
                  text: row.modelData.name
                  elide: Text.ElideRight
                  wrapMode: Text.NoWrap
                  font.pixelSize: FoamyStyle.font.subtitle
                  // A closed account reads as available, not current.
                  color: row.modelData.running ? FoamyPalette.text : FoamyPalette.secondaryText
                }
                Rectangle {
                  id: badge
                  visible: row.hasUnread
                  anchors.verticalCenter: parent.verticalCenter
                  height: count.implicitHeight + FoamyStyle.gapTiny * 2
                  width: Math.max(height, count.implicitWidth + FoamyStyle.gap * 2)
                  radius: FoamyStyle.pillRadius(height)
                  color: Qt.alpha(Commons.Color.urgent, 0.18)
                  Label {
                    id: count
                    anchors.centerIn: parent
                    text: row.modelData.unread > 99 ? FoamyI18n.number(99, 0) + "+" : FoamyI18n.number(row.modelData.unread || 0, 0)
                    wrapMode: Text.NoWrap
                    color: Commons.Color.urgent
                    font.pixelSize: FoamyStyle.font.caption
                    font.weight: Font.DemiBold
                  }
                }
              }
              Label {
                visible: root.showContext
                Layout.fillWidth: true
                text: row.modelData.running ? (row.modelData.context || "Microsoft Teams") : FoamyI18n.t("Not running")
                color: FoamyPalette.secondaryText
                font.pixelSize: FoamyStyle.font.caption
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
              }
            }
            // The whole row is the button; its verb shows under the cursor (and
            // while launching), the icon says which one it is at rest.
            Label {
              Layout.alignment: Qt.AlignVCenter
              text: row.actionText
              wrapMode: Text.NoWrap
              color: FoamyPalette.secondaryText
              font.pixelSize: FoamyStyle.font.bodySmall
              opacity: row.active || row.launching ? 1 : 0
              Behavior on opacity { NumberAnimation { duration: FoamyMotion.hover } }
            }
            FoamyIcon {
              id: actionIcon
              Layout.preferredWidth: FoamyStyle.iconSize - Style.space(3)
              Layout.preferredHeight: Layout.preferredWidth
              Layout.alignment: Qt.AlignVCenter
              name: row.launching ? "refresh-cw" : row.modelData.running ? "app-window" : "play"
              color: row.active ? FoamyPalette.text : FoamyPalette.secondaryText
              RotationAnimation on rotation {
                running: row.launching && row.visible && !FoamyMotion.reduceMotion
                from: 0
                to: 360
                duration: FoamyMotion.spin
                loops: Animation.Infinite
                onStopped: actionIcon.rotation = 0
              }
            }
          }
        }
      }
    }
  }

  SettingsPane {
    id: settingsPane
    visible: root.editingSettings
    width: parent.width
    height: parent.height
    settings: root.settings
    candidates: root.candidates
    saving: root.saving
    panelError: root.settingsError
    accountsLocked: root.accountsLocked
    retryable: root.retryable
    onSave: function(key, value) { root.saveRequested(key, value) }
    onBackToPanel: root.settingsBack()
    onRetry: root.retryRequested()
  }
}
