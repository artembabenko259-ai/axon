import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects // For smooth shadows/blur in Qt6

ApplicationWindow {
    id: window
    width: 1200
    height: 800
    visible: true
    title: "AXON Workstation"
    color: "#0e0e11" // Sleek off-black background

    // UI State & Configuration
    property string activeTab: "chat"
    property string streamText: ""
    property bool isStreaming: false
    property string currentStatus: "Ready"

    // Config is loaded automatically from local AXON config.json by LlmClient constructor

    Connections {
        target: llm
        function onStreamStarted() {
            isStreaming = true
            streamText = ""
            currentStatus = "Thinking..."
        }
        function onTokenReceived(token) {
            streamText += token
        }
        function onStreamFinished() {
            isStreaming = false
            currentStatus = "Ready"
        }
        function onErrorOccurred(error) {
            isStreaming = false
            streamText += "\n\n[Error]: " + error
            currentStatus = "Error"
        }
    }

    // Modern Side Navigation Bar (Obsidian-style, ultra-minimal)
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar Navigation
        Rectangle {
            width: 70
            Layout.fillHeight: true
            color: "#0a0a0c"
            border.color: "#1d1d22"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 20
                anchors.bottomMargin: 20
                spacing: 25

                // Top Icon / Logo
                Text {
                    text: "▲"
                    font.pixelSize: 22
                    color: "#6366f1" // Indigo accent
                    Layout.alignment: Qt.AlignHCenter
                }

                Item { Layout.fillHeight: true } // Spacer

                // Chat Tab Button
                NavigationButton {
                    iconText: "💬"
                    active: window.activeTab === "chat"
                    onClicked: window.activeTab = "chat"
                }

                // Notes / Editor Tab
                NavigationButton {
                    iconText: "📝"
                    active: window.activeTab === "notes"
                    onClicked: window.activeTab = "notes"
                }

                // Subagent Graph Tab
                NavigationButton {
                    iconText: "🕸️"
                    active: window.activeTab === "graph"
                    onClicked: window.activeTab = "graph"
                }

                Item { Layout.fillHeight: true } // Spacer

                // Status Indicator
                Rectangle {
                    width: 10
                    height: 10
                    radius: 5
                    color: window.isStreaming ? "#fbbf24" : "#10b981" // Amber when thinking, Green when ready
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Main Workstation Content Area
        StackLayout {
            id: mainStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.activeTab === "chat" ? 0 : (window.activeTab === "notes" ? 1 : 2)

            // Tab 0: Minimal Chat
            Rectangle {
                color: "transparent"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 40
                    spacing: 20

                    // Top Bar / Model Selector
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 15

                        Text {
                            text: "AXON CHAT"
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                            color: "#ffffff"
                        }

                        Rectangle {
                            width: 1
                            height: 15
                            color: "#2a2a32"
                        }

                        Text {
                            text: llm.model
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            color: "#8a8a98"
                        }

                        Item { Layout.fillWidth: true }
                    }

                    // Divider
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: "#1d1d22"
                    }

                    // Chat Stream / Conversation Panel
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true

                        TextArea {
                            id: chatOutput
                            text: window.streamText
                            font.family: "Consolas"
                            font.pixelSize: 14
                            color: "#e4e4e7"
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextEdit.Wrap
                            placeholderText: "Axon responses will stream here..."
                            placeholderTextColor: "#4a4a58"
                            background: null
                        }
                    }

                    // Input Field Container (Sleek minimalist bar)
                    Rectangle {
                        Layout.fillWidth: true
                        height: 60
                        color: "#121216"
                        radius: 8
                        border.color: inputField.activeFocus ? "#6366f1" : "#1d1d22"
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 15
                            anchors.rightMargin: 15
                            spacing: 10

                            TextField {
                                id: inputField
                                Layout.fillWidth: true
                                placeholderText: "Ask AXON anything..."
                                placeholderTextColor: "#6b7280"
                                color: "#ffffff"
                                font.family: "Segoe UI"
                                font.pixelSize: 14
                                background: null
                                onAccepted: {
                                    if (text.trim() !== "") {
                                        llm.sendPrompt(text);
                                        text = "";
                                    }
                                }
                            }

                            // Send Button
                            Button {
                                text: "Send"
                                font.bold: true
                                font.pixelSize: 12
                                contentItem: Text {
                                    text: "Send"
                                    color: "#ffffff"
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    implicitWidth: 60
                                    implicitHeight: 32
                                    color: parent.hovered ? "#4f46e5" : "#6366f1"
                                    radius: 4
                                }
                                onClicked: {
                                    if (inputField.text.trim() !== "") {
                                        llm.sendPrompt(inputField.text);
                                        inputField.text = "";
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Tab 1: Obsidian-style Notes (Minimal Markdown editor layout)
            Rectangle {
                color: "transparent"
                Text {
                    anchors.centerIn: parent
                    text: "Obsidian Editor Integration"
                    color: "#8a8a98"
                }
            }

            // Tab 2: Subagent Graph Visualization
            Rectangle {
                color: "transparent"
                Text {
                    anchors.centerIn: parent
                    text: "Interactive Subagent Graph View"
                    color: "#8a8a98"
                }
            }
        }
    }
}
