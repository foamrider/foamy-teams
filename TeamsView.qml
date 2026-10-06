import QtQuick
import QtQuick.Layouts
import qs.Commons
import "Preferences.js" as Preferences

Column {
  id: root
  property real cornerRadius: Style.cornerRadius * 2
  required property var accounts
  required property var summary
  required property string language
  property bool configured: false
  property bool showContext: true
  property string error: ""
  property string launchingId: ""
  property int cursorIndex: -1
  signal activate(var account)
  signal settingsRequested()
  function tr(label, values) { return Preferences.text(label, language, values) }
  function move(direction) {
    if (!accounts.length) { settingsButton.forceActiveFocus(); return }
    cursorIndex = cursorIndex < 0 ? (direction > 0 ? 0 : accounts.length-1) : (cursorIndex+direction+accounts.length)%accounts.length
    accountRepeater.itemAt(cursorIndex).forceActiveFocus()
  }
  readonly property color foreground: Color.popups.text
  readonly property color secondary: Qt.tint(Color.popups.background, Qt.alpha(foreground, 0.7))
  readonly property bool lightTheme: Color.popups.background.r + Color.popups.background.g + Color.popups.background.b > 1.5
  readonly property color runningColor: lightTheme ? "#3b6b30" : "#a6e3a1"
  readonly property string heading: summary.accountCount === 0 ? tr(configured ? "All accounts are disabled" : "No accounts configured")
    : summary.totalUnread > 0 ? tr(summary.totalUnread === 1 ? "%1 unread message" : "%1 unread messages", [summary.totalUnread])
    : summary.runningCount === 0 ? tr("Teams is not running")
    : summary.unknownCount > summary.accountCount - summary.runningCount ? "Microsoft Teams" : tr("All read")
  readonly property string subtitle: summary.accountCount === 0 ? tr(configured ? "Enable an account in Settings" : "Add your Teams accounts in Settings") : ""
  Keys.onPressed: function(event) {
    if ([Qt.Key_Down,Qt.Key_J,Qt.Key_Up,Qt.Key_K].indexOf(event.key)>=0) { move(event.key===Qt.Key_Down || event.key===Qt.Key_J ? 1 : -1); event.accepted=true }
    else if (event.key===Qt.Key_S) { settingsRequested(); event.accepted=true }
  }
  component Label: Text {
    textFormat: Text.PlainText
    font.family: "sans-serif"
    font.pixelSize: Style.space(13)
    color: root.foreground
    wrapMode: Text.WordWrap
  }
  Item {
    width: parent.width
    height: header.implicitHeight + Style.space(40)

    // Use the same static, theme-derived header wash as clock and weather.
    Canvas {
      id: headerBackground
      anchors.fill: parent
      onWidthChanged: requestPaint()
      onHeightChanged: requestPaint()
      onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        var radius = Math.min(width / 2, height, root.cornerRadius)
        ctx.beginPath()
        ctx.moveTo(radius, 0); ctx.lineTo(width - radius, 0)
        ctx.quadraticCurveTo(width, 0, width, radius)
        ctx.lineTo(width, height); ctx.lineTo(0, height); ctx.lineTo(0, radius)
        ctx.quadraticCurveTo(0, 0, radius, 0); ctx.closePath(); ctx.clip()
        var gradient = ctx.createLinearGradient(0, 0, width * 0.5, height)
        gradient.addColorStop(0, Qt.tint(Color.popups.background, Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.08)))
        gradient.addColorStop(1, Color.popups.background)
        ctx.fillStyle = gradient; ctx.fillRect(0, 0, width, height)
        var glow = ctx.createRadialGradient(width * 0.9, 0, 0, width * 0.9, 0, width * 0.85)
        glow.addColorStop(0, Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.17))
        glow.addColorStop(1, "transparent")
        ctx.fillStyle = glow; ctx.fillRect(0, 0, width, height)
      }
      Connections {
        target: root
        function onCornerRadiusChanged() { headerBackground.requestPaint() }
      }
      Connections {
        target: Color
        function onAccentChanged() { headerBackground.requestPaint() }
        function onShellValuesChanged() { headerBackground.requestPaint() }
        function onBackgroundChanged() { headerBackground.requestPaint() }
      }
    }
    Column {
      id: header
      anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
      anchors.margins: Style.space(20)
      spacing: Style.space(8)
      RowLayout {
        width: parent.width
        Text { text: "󰊻"; color: root.foreground; font.family: Style.font.family; font.pixelSize: Style.space(17) }
        Label { text: "Microsoft Teams"; Layout.fillWidth: true; font.pixelSize: Style.space(13) }
        TeamsAction { id: settingsButton; iconName: "settings"; foreground: root.secondary; tooltipText: root.tr("Settings"); onClicked: root.settingsRequested() }
      }
      Item { width: 1; height: Style.space(4) }
      Label {
        width: parent.width
        textFormat: root.summary.totalUnread > 0 ? Text.StyledText : Text.PlainText
        text: root.summary.totalUnread > 0
          ? root.heading.replace(String(root.summary.totalUnread), '<font color="' + Color.urgent + '">' + root.summary.totalUnread + '</font>')
          : root.heading
        font.pixelSize: Style.space(21)
      }
      Label { visible: root.subtitle!==""; width: parent.width; text: root.subtitle; font.pixelSize: Style.space(12); color: root.secondary }
    }
  }
  Column {
    width: parent.width
    padding: Style.space(20)
    topPadding: Style.space(4)
    bottomPadding: Style.space(8)
    Label { visible: root.error!==""; width: parent.width-parent.padding*2; text: root.error; color: Color.urgent; Accessible.role: Accessible.AlertMessage }
    Repeater {
      id: accountRepeater
      model: root.accounts
      Rectangle {
        id: row
        required property var modelData
        required property int index
        width: parent.width-parent.padding*2
        height: Style.space(root.showContext ? 76 : 58)
        color: "transparent"
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: modelData.name+", "+status.text+", "+action.text
        Accessible.onPressAction: root.activate(modelData)
        Keys.onReturnPressed: root.activate(modelData)
        Keys.onEnterPressed: root.activate(modelData)
        Keys.onSpacePressed: root.activate(modelData)
        onActiveFocusChanged: if (activeFocus) root.cursorIndex=index
        Rectangle {
          anchors.fill: parent
          anchors.topMargin: Style.space(4); anchors.bottomMargin: Style.space(4)
          radius: Style.cornerRadius * 2
          color: hover.containsMouse || row.activeFocus ? Qt.alpha(root.foreground,0.05) : "transparent"
          border.width: row.activeFocus ? 1 : 0
          border.color: Color.accent
        }
        RowLayout {
          anchors.fill: parent
          anchors.leftMargin: Style.space(12); anchors.rightMargin: Style.space(12)
          spacing: Style.space(12)
          Rectangle { Layout.preferredWidth: Style.space(2); Layout.preferredHeight: Style.space(34); radius: 1; color: row.modelData.running ? root.runningColor : Qt.alpha(root.foreground,0.3) }
          ColumnLayout {
            Layout.fillWidth: true
            spacing: Style.space(3)
            Label { Layout.fillWidth: true; text: row.modelData.name; elide: Text.ElideRight; wrapMode: Text.NoWrap; font.pixelSize: Style.space(15) }
            Label { visible: root.showContext && row.modelData.running; Layout.fillWidth: true; text: row.modelData.running ? (row.modelData.context || "Microsoft Teams") : root.tr("Not running"); color: root.secondary; font.pixelSize: Style.space(12); elide: Text.ElideRight; wrapMode: Text.NoWrap }
          }
          ColumnLayout {
            spacing: Style.space(3)
            Rectangle {
              readonly property bool hasUnread: row.modelData.unread > 0
              visible: row.modelData.running && row.modelData.unread !== null
              Layout.alignment: Qt.AlignRight
              implicitWidth: status.implicitWidth
              implicitHeight: status.implicitHeight
              radius: Style.cornerRadius * 2
              color: hasUnread ? Qt.alpha(Color.urgent, 0.16) : "transparent"
              Label {
                id: status
                text: row.modelData.unread === null ? "" : row.modelData.unread > 0
                  ? root.tr(row.modelData.unread === 1 ? "1 unread" : "%1 unread", [row.modelData.unread]) : root.tr("No unread")
                color: parent.hasUnread ? Color.urgent : root.secondary
                font.pixelSize: Style.space(12)
                font.weight: parent.hasUnread ? Font.DemiBold : Font.Normal
                leftPadding: parent.hasUnread ? Style.space(8) : 0
                rightPadding: leftPadding
                topPadding: parent.hasUnread ? Style.space(3) : 0
                bottomPadding: topPadding
              }
            }
            Label { id: action; Layout.alignment: Qt.AlignRight; text: (root.launchingId===row.modelData.id ? root.tr("Launching…") : root.tr(row.modelData.running ? "Focus" : "Launch")) + "  ↗"; color: root.secondary; font.pixelSize: Style.space(12) }
          }
        }
        Rectangle { visible: row.index<root.accounts.length-1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Qt.alpha(root.foreground,0.1) }
        MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.activate(row.modelData) }
      }
    }
    Label { visible: root.accounts.length===0 && root.summary.accountCount>0; width: parent.width-parent.padding*2; padding: Style.space(12); text: root.tr("No visible accounts")+"\n"+root.tr("Show closed accounts in Settings"); color: root.secondary }
  }
}
