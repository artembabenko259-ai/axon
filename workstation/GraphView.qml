import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: graphView
    color: "#09090b" // Dark background matching Obsidian Graph View
    clip: true

    property var nodes: [
        { id: "main", label: "AXON Core", type: "agent", x: 450, y: 300 },
        { id: "gmail", label: "Gmail Linker", type: "agent", x: 250, y: 150 },
        { id: "telegram", label: "Telegram Bot", type: "agent", x: 650, y: 150 },
        { id: "todo", label: "TODO.md", type: "file", x: 150, y: 350 },
        { id: "readme", label: "README.md", type: "file", x: 750, y: 350 },
        { id: "git", label: "Git AutoCommit", type: "action", x: 300, y: 450 },
        { id: "log", label: "session_log.json", type: "file", x: 600, y: 450 }
    ]

    property var links: [
        { from: "main", to: "gmail" },
        { from: "main", to: "telegram" },
        { from: "main", to: "todo" },
        { from: "main", to: "readme" },
        { from: "main", to: "git" },
        { from: "main", to: "log" },
        { from: "gmail", to: "todo" },
        { from: "telegram", to: "log" }
    ]

    property string selectedNodeLabel: "None"
    property string selectedNodeType: "None"

    // Zoom and pan container
    Flickable {
        id: flickable
        anchors.fill: parent
        contentWidth: board.width
        contentHeight: board.height
        boundsBehavior: Flickable.StopAtBounds

        // Initialize viewport scroll in center
        Component.onCompleted: {
            flickable.contentX = (board.width - flickable.width) / 2
            flickable.contentY = (board.height - flickable.height) / 2
        }

        Item {
            id: board
            width: 2000
            height: 2000
            scale: zoomSlider.value

            Behavior on scale { NumberAnimation { duration: 150 } }

            // Custom connection line renderer
            Canvas {
                id: linkCanvas
                anchors.fill: parent
                z: 0

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    
                    // Draw grid background (subtle)
                    ctx.strokeStyle = "#141419"
                    ctx.lineWidth = 1
                    var gridSize = 40
                    for (var x = 0; x < width; x += gridSize) {
                        ctx.beginPath()
                        ctx.moveTo(x, 0)
                        ctx.lineTo(x, height)
                        ctx.stroke()
                    }
                    for (var y = 0; y < height; y += gridSize) {
                        ctx.beginPath()
                        ctx.moveTo(0, y)
                        ctx.lineTo(width, y)
                        ctx.stroke()
                    }

                    // Draw connections
                    ctx.strokeStyle = "#272733"
                    ctx.lineWidth = 1.5
                    
                    for (var i = 0; i < graphView.links.length; i++) {
                        var link = graphView.links[i]
                        var fromNode = findNode(link.from)
                        var toNode = findNode(link.to)

                        if (fromNode && toNode) {
                            ctx.beginPath()
                            // Coordinates centered on nodes
                            ctx.moveTo(fromNode.x + fromNode.width / 2, fromNode.y + fromNode.height / 2)
                            ctx.lineTo(toNode.x + toNode.width / 2, toNode.y + toNode.height / 2)
                            ctx.stroke()
                        }
                    }
                }
            }

            // Generate nodes from JS array
            Repeater {
                model: graphView.nodes
                delegate: GraphNode {
                    label: modelData.label
                    type: modelData.type
                    x: modelData.x
                    y: modelData.y
                    z: 10
                    isSelected: graphView.selectedNodeLabel === modelData.label

                    onMoved: {
                        modelData.x = x
                        modelData.y = y
                        linkCanvas.requestPaint()
                    }

                    onClicked: {
                        graphView.selectedNodeLabel = modelData.label
                        graphView.selectedNodeType = modelData.type
                    }
                }
            }
        }
    }

    // Helper functions to resolve node coordinates
    function findNode(id) {
        for (var i = 0; i < board.children.length; i++) {
            var child = board.children[i]
            // We search children that are instances of GraphNode (Repeater items)
            if (child.label !== undefined && graphView.nodes[i] !== undefined && graphView.nodes[i].id === id) {
                return child
            }
        }
        // Fallback search by index
        for (var idx = 0; idx < graphView.nodes.length; idx++) {
            if (graphView.nodes[idx].id === id) {
                var repeaterItem = board.children[idx + 1] // +1 due to Canvas being the first child
                if (repeaterItem && repeaterItem.label !== undefined) return repeaterItem
            }
        }
        return null
    }

    // Floating Zoom Controls (Obsidian Style)
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 25
        width: 220
        height: 45
        color: "#0f0f13"
        border.color: "#1d1d22"
        border.width: 1
        radius: 8
        z: 100

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 15
            anchors.rightMargin: 15
            spacing: 10

            Text {
                text: "🔍"
                font.pixelSize: 14
            }

            Slider {
                id: zoomSlider
                Layout.fillWidth: true
                from: 0.3
                to: 1.8
                value: 1.0
            }
        }
    }

    // Side Info Panel for Selected Node
    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 20
        width: 280
        color: "#0b0b0e"
        border.color: "#1c1c22"
        border.width: 1
        radius: 8
        z: 100
        visible: graphView.selectedNodeLabel !== "None"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 15

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Node inspector"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 14
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "×"
                    onClicked: graphView.selectedNodeLabel = "None"
                    contentItem: Text { text: "×"; color: "#8a8a98"; font.pixelSize: 18 }
                    background: null
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#1c1c22"
            }

            Text {
                text: graphView.selectedNodeLabel
                color: "#ffffff"
                font.pixelSize: 18
                font.bold: true
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Text {
                text: "Type: " + graphView.selectedNodeType.toUpperCase()
                color: "#8a8a98"
                font.pixelSize: 11
            }

            Text {
                text: "Connected to other nodes in the workspace graph. Drag nodes to reshape, double click to view related notes, logs, or agent task logs."
                color: "#5e5e6e"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Item { Layout.fillHeight: true } // Spacer

            Button {
                Layout.fillWidth: true
                text: "Open Related File"
                contentItem: Text {
                    text: "Open File Context"
                    color: "#ffffff"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
                background: Rectangle {
                    color: "#272733"
                    radius: 4
                }
            }
        }
    }
}
