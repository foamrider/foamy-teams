import QtQuick
import qs.Commons
import qs.Ui
import "kit"

// The bar button's content: the Teams glyph and, when enabled, the unread
// count in the bar's urgent colour.
Row {
  id: root

  property int unread: 0
  property bool showCount: true
  property string glyphFont: Style.font.family
  property color foreground: "white"
  property color urgent: "red"

  spacing: Style.space(1)

  OpticalGlyph {
    width: Style.bar.iconCanvas
    height: Style.bar.iconCanvas
    text: "󰊻"
    fontFamily: root.glyphFont
    fontSize: Style.font.body
    color: root.foreground
  }
  Text {
    visible: root.showCount && root.unread > 0
    anchors.verticalCenter: parent.verticalCenter
    text: FoamyI18n.number(root.unread, 0)
    textFormat: Text.PlainText
    color: root.urgent
    font.family: root.glyphFont
    font.pixelSize: Style.font.body
  }
}
