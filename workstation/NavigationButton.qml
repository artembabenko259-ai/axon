import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    width: 44
    height: 44
    Layout.alignment: Qt.AlignHCenter

    property string iconName: "chat" // "chat", "notes", "graph"
    property bool active: false
    signal clicked()

    Rectangle {
        anchors.fill: parent
        color: root.active ? "#18181b" : (mouseArea.containsMouse ? "#0f0f13" : "transparent")
        radius: 6
        border.color: root.active ? "#27272a" : "transparent"
        border.width: 1

        Behavior on color { ColorAnimation { duration: 120 } }

        // High-end vector drawing of icons instead of cheap emojis
        Canvas {
            id: iconCanvas
            anchors.fill: parent
            anchors.margins: 12
            antialiasing: true

            property color strokeColor: root.active ? "#ffffff" : (mouseArea.containsMouse ? "#a1a1aa" : "#52525b")
            onStrokeColorChanged: requestPaint()

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = strokeColor
                ctx.lineWidth = 1.2
                ctx.lineJoin = "round"
                ctx.lineCap = "round"

                var w = width
                var h = height

                if (root.iconName === "chat") {
                    // Modern chat bubble outline
                    ctx.beginPath()
                    ctx.moveTo(2, 2)
                    ctx.lineTo(w - 2, 2)
                    ctx.lineTo(w - 2, h - 6)
                    ctx.lineTo(6, h - 6)
                    ctx.lineTo(2, h - 2)
                    ctx.closePath()
                    ctx.stroke()
                    
                    // Tiny line inside
                    ctx.beginPath()
                    ctx.moveTo(6, 6)
                    ctx.lineTo(w - 6, 6)
                    ctx.stroke()
                } 
                else if (root.iconName === "notes") {
                    // Modern file outline
                    ctx.beginPath()
                    ctx.moveTo(3, 2)
                    ctx.lineTo(w - 6, 2)
                    ctx.lineTo(w - 2, 6)
                    ctx.lineTo(w - 2, h - 2)
                    ctx.lineTo(3, h - 2)
                    ctx.closePath()
                    ctx.stroke()

                    // Dog-ear fold
                    ctx.beginPath()
                    ctx.moveTo(w - 6, 2)
                    ctx.lineTo(w - 6, 6)
                    ctx.lineTo(w - 2, 6)
                    ctx.stroke()
                } 
                else if (root.iconName === "graph") {
                    // Modern node graph skeleton
                    var r = 2.5
                    // Draw lines first
                    ctx.beginPath()
                    ctx.moveTo(4, h - 4)
                    ctx.lineTo(w / 2, 4)
                    ctx.lineTo(w - 4, h - 4)
                    ctx.stroke()

                    // Draw circles
                    ctx.fillStyle = strokeColor
                    
                    // Node 1
                    ctx.beginPath()
                    ctx.arc(w / 2, 4, r, 0, 2 * Math.PI)
                    ctx.fill()
                    // Node 2
                    ctx.beginPath()
                    ctx.arc(4, h - 4, r, 0, 2 * Math.PI)
                    ctx.fill()
                    // Node 3
                    ctx.beginPath()
                    ctx.arc(w - 4, h - 4, r, 0, 2 * Math.PI)
                    ctx.fill()
                }
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.clicked()
            cursorShape: Qt.PointingHandCursor
        }
    }
}
