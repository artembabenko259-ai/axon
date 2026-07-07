import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: graphView
    color: "#09090b" // Slate-950 off-black
    clip: true

    property string selectedNodeLabel: "None"
    property string selectedNodeType: "None"

    // Flickable Viewport Board
    Flickable {
        id: flickable
        anchors.fill: parent
        contentWidth: board.width
        contentHeight: board.height
        boundsBehavior: Flickable.StopAtBounds

        Component.onCompleted: {
            flickable.contentX = (board.width - flickable.width) / 2
            flickable.contentY = (board.height - flickable.height) / 2
        }

        Item {
            id: board
            width: 2000
            height: 2000
            scale: zoomSlider.value

            Behavior on scale { NumberAnimation { duration: 100 } }

            // Static Dot Grid Background (Drawn once, does not redraw on drag!)
            Canvas {
                id: gridCanvas
                anchors.fill: parent
                z: 0
                Component.onCompleted: requestPaint()

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    
                    // Subtle Dot Grid (Obsidian / Linear style)
                    ctx.fillStyle = "#1b1b22"
                    var dotSpacing = 24
                    for (var x = 0; x < width; x += dotSpacing) {
                        for (var y = 0; y < height; y += dotSpacing) {
                            ctx.beginPath()
                            ctx.arc(x, y, 0.75, 0, 2 * Math.PI)
                            ctx.fill()
                        }
                    }
                }
            }

            // Connection Lines (GPU accelerated via direct property bindings)
            ConnectionLine { fromNode: mainNode; toNode: gmailNode }
            ConnectionLine { fromNode: mainNode; toNode: telegramNode }
            ConnectionLine { fromNode: mainNode; toNode: todoNode }
            ConnectionLine { fromNode: mainNode; toNode: readmeNode }
            ConnectionLine { fromNode: mainNode; toNode: commitNode }
            ConnectionLine { fromNode: mainNode; toNode: sessionNode }
            ConnectionLine { fromNode: gmailNode; toNode: todoNode }
            ConnectionLine { fromNode: telegramNode; toNode: sessionNode }

            // Draggable Nodes (Static declarations with GPU-bound coordinates)
            GraphNode {
                id: mainNode
                label: "AXON CORE"
                type: "agent"
                x: 950; y: 950
                isSelected: graphView.selectedNodeLabel === label
                onClicked: { graphView.selectedNodeLabel = label; graphView.selectedNodeType = type }
            }

            GraphNode {
                id: gmailNode
                label: "GMAIL BOT"
                type: "agent"
                x: 750; y: 800
                isSelected: graphView.selectedNodeLabel === label
                onClicked: { graphView.selectedNodeLabel = label; graphView.selectedNodeType = type }
            }

            GraphNode {
                id: telegramNode
                label: "TELEGRAM CHAT"
                type: "agent"
                x: 1150; y: 800
                isSelected: graphView.selectedNodeLabel === label
                onClicked: { graphView.selectedNodeLabel = label; graphView.selectedNodeType = type }
            }

            GraphNode {
                id: todoNode
                label: "workspace/todo.md"
                type: "file"
                x: 650; y: 1000
                isSelected: graphView.selectedNodeLabel === label
                onClicked: { graphView.selectedNodeLabel = label; graphView.selectedNodeType = type }
            }

            GraphNode {
                id: readmeNode
                label: "workspace/readme.md"
                type: "file"
                x: 1250; y: 1000
                isSelected: graphView.selectedNodeLabel === label
                onClicked: { graphView.selectedNodeLabel = label; graphView.selectedNodeType = type }
            }

            GraphNode {
                id: commitNode
                label: "git:commit-helper"
                type: "action"
                x: 800; y: 1150
                isSelected: graphView.selectedNodeLabel === label
                onClicked: { graphView.selectedNodeLabel = label; graphView.selectedNodeType = type }
            }

            GraphNode {
                id: sessionNode
                label: "logs/session.json"
                type: "file"
                x: 1100; y: 1150
                isSelected: graphView.selectedNodeLabel === label
                onClicked: { graphView.selectedNodeLabel = label; graphView.selectedNodeType = type }
            }
        }
    }

    // Minimalistic floating zoom controls
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 30
        width: 180
        height: 36
        color: "#0a0a0d"
        border.color: "#18181b"
        border.width: 1
        radius: 6
        z: 100

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 8

            Text {
                text: "ZOOM"
                color: "#52525b"
                font.family: "Inter"
                font.pixelSize: 9
                font.bold: true
                font.letterSpacing: 1.0
            }

            Slider {
                id: zoomSlider
                Layout.fillWidth: true
                from: 0.4
                to: 1.5
                value: 1.0

                background: Rectangle {
                    implicitWidth: 100
                    implicitHeight: 2
                    width: parent.availableWidth
                    height: implicitHeight
                    radius: 1
                    color: "#18181b"

                    Rectangle {
                        width: zoomSlider.visualPosition * parent.width
                        height: parent.height
                        color: "#27272a"
                        radius: 1
                    }
                }

                handle: Rectangle {
                    x: zoomSlider.leftPadding + zoomSlider.visualPosition * (zoomSlider.availableWidth - width)
                    y: zoomSlider.topPadding + zoomSlider.availableHeight / 2 - height / 2
                    implicitWidth: 10
                    implicitHeight: 10
                    radius: 5
                    color: zoomSlider.pressed ? "#ffffff" : "#d4d4d8"
                    border.color: "#18181b"
                    border.width: 1
                }
            }
        }
    }

    // Side Info Panel (Obsidian-Style, ultra-minimal)
    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 30
        width: 260
        color: "#09090b"
        border.color: "#18181b"
        border.width: 1
        radius: 6
        z: 100
        visible: graphView.selectedNodeLabel !== "None"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "INSPECTOR"
                    color: "#71717a"
                    font.family: "Inter"
                    font.pixelSize: 9
                    font.bold: true
                    font.letterSpacing: 1.0
                }
                Item { Layout.fillWidth: true }
                MouseArea {
                    width: 16
                    height: 16
                    cursorShape: Qt.PointingHandCursor
                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: "#52525b"
                        font.pixelSize: 16
                    }
                    onClicked: graphView.selectedNodeLabel = "None"
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#18181b"
            }

            Text {
                text: graphView.selectedNodeLabel
                color: "#ffffff"
                font.family: "Inter"
                font.pixelSize: 14
                font.bold: true
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Text {
                text: "TYPE: " + graphView.selectedNodeType.toUpperCase()
                color: {
                    if (graphView.selectedNodeType === "agent") return "#818cf8"
                    if (graphView.selectedNodeType === "file") return "#34d399"
                    return "#fb7185"
                }
                font.family: "Inter"
                font.pixelSize: 9
                font.bold: true
                font.letterSpacing: 0.5
            }

            Text {
                text: "Click and drag graph nodes to rearrange coordinates. Double-click files to open their local markdown/code context inside the workstation editor workspace."
                color: "#52525b"
                font.family: "Inter"
                font.pixelSize: 11
                lineHeight: 1.3
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Item { Layout.fillHeight: true } // Spacer

            Rectangle {
                Layout.fillWidth: true
                height: 32
                color: "#18181b"
                radius: 4
                border.color: "#27272a"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "OPEN FILE CONTEXT"
                    color: "#d4d4d8"
                    font.family: "Inter"
                    font.pixelSize: 9
                    font.bold: true
                    font.letterSpacing: 0.5
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onEntered: parent.color = "#27272a"
                    onExited: parent.color = "#18181b"
                }
            }
        }
    }
}
