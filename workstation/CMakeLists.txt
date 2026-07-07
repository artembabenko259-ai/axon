cmake_minimum_required(VERSION 3.16)

project(axon-workstation VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt6 components
find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick Network)

qt_standard_project_setup()

# Define source files
set(SOURCES
    main.cpp
    llmclient.h
    llmclient.cpp
)

# Define QML and resource files
set(QML_FILES
    main.qml
    NavigationButton.qml
)

qt_add_executable(axon-workstation
    ${SOURCES}
)

# Embed QML resources in the executable
qt_add_qml_module(axon-workstation
    URI Workstation
    VERSION 1.0
    QML_FILES ${QML_FILES}
)

target_link_libraries(axon-workstation PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    Qt6::Quick
    Qt6::Network
)

# Custom installation rules
install(TARGETS axon-workstation
    BUNDLE DESTINATION .
    RUNTIME DESTINATION .
)
