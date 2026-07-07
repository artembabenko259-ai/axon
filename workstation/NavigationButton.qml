import QtQuick
import QtQuick.Controls

Item {
    id: root
    width: 50
    height: 50
    Layout.alignment: Qt.AlignHCenter

    property string iconText: ""
    property bool active: false
    signal clicked()

    Rectangle {
        anchors.fill: parent
        color: root.active ? "#1c1c24" : (mouseArea.containsMouse ? "#121217" : "transparent")
        radius: 8
        border.color: root.active ? "#2d2d3d" : "transparent"
        border.width: 1

        Behavior on color { ColorAnimation { duration: 150 } }

        Text {
            anchors.centerIn: parent
            text: root.iconText
            font.pixelSize: 20
            opacity: root.active ? 1.0 : (mouseArea.containsMouse ? 0.8 : 0.4)
            Behavior on opacity { NumberAnimation { duration: 150 } }
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
