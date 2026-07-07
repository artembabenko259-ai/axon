import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: node
    width: 24
    height: 24

    property string label: ""
    property string type: "file" // "agent", "file", "action"
    property bool isHovered: mouseArea.containsMouse
    property bool isSelected: false

    signal moved()
    signal clicked()

    // Premium color palette (Tailwind Slate/Zinc tones)
    readonly property color nodeColor: {
        if (type === "agent") return "#818cf8"  // Soft Indigo
        if (type === "file") return "#34d399"   // Soft Emerald
        return "#fb7185"                        // Soft Rose
    }

    // Tiny tactile dot
    Rectangle {
        id: dot
        width: node.isHovered ? 12 : 8
        height: node.isHovered ? 12 : 8
        radius: width / 2
        anchors.centerIn: parent
        color: node.isHovered ? node.nodeColor : "#18181b"
        border.color: node.isSelected ? "#ffffff" : node.nodeColor
        border.width: node.isSelected ? 2 : 1.5

        Behavior on color { ColorAnimation { duration: 150 } }
        Behavior on border.color { ColorAnimation { duration: 150 } }
        Behavior on width { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }
        Behavior on height { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }

        // Glow ring on hover/selected
        Rectangle {
            anchors.centerIn: parent
            width: parent.width + 12
            height: parent.height + 12
            radius: width / 2
            color: "transparent"
            border.color: node.nodeColor
            border.width: 1
            opacity: node.isHovered || node.isSelected ? 0.3 : 0.0
            Behavior on opacity { NumberAnimation { duration: 150 } }
        }
    }

    // Clean, tiny typography label below the node
    Text {
        id: labelText
        anchors.top: parent.bottom
        anchors.topMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        text: node.label
        color: node.isSelected ? "#ffffff" : (node.isHovered ? "#d4d4d8" : "#71717a")
        font.family: "Inter"
        font.pixelSize: 10
        font.letterSpacing: 0.5
        font.bold: node.type === "agent"
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        width: 120
        opacity: node.isHovered || node.isSelected ? 1.0 : 0.7
        Behavior on color { ColorAnimation { duration: 150 } }
        Behavior on opacity { NumberAnimation { duration: 150 } }
    }

    // Drag and interaction area
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        anchors.margins: -10 // Make it easier to grab the tiny dot
        hoverEnabled: true
        drag.target: node
        drag.axis: Drag.XAndYAxis

        onPositionChanged: {
            if (drag.active) {
                node.moved()
            }
        }

        onClicked: node.clicked()
        cursorShape: drag.active ? Qt.ClosedHandCursor : Qt.PointingHandCursor
    }
}
