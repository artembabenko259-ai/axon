import QtQuick

Item {
    id: lineItem

    property Item fromNode: null
    property Item toNode: null

    // Direct property bindings to the centers of target nodes
    readonly property real x1: fromNode ? (fromNode.x + fromNode.width / 2) : 0
    readonly property real y1: fromNode ? (fromNode.y + fromNode.height / 2) : 0
    readonly property real x2: toNode ? (toNode.x + toNode.width / 2) : 0
    readonly property real y2: toNode ? (toNode.y + toNode.height / 2) : 0

    x: x1
    y: y1
    
    // Calculate length dynamically on GPU
    width: Math.max(1, Math.sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1)))
    height: 1
    
    // Rotate relative to starting point
    transformOrigin: Item.Left
    rotation: Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI

    Rectangle {
        anchors.fill: parent
        color: "#181822" // Subdued thin slate line
        opacity: 0.6
    }
}
