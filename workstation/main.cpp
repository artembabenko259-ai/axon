#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QFile>
#include "llmclient.h"

int main(int argc, char *argv[])
{
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
    QCoreApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
#endif

    QGuiApplication app(argc, argv);
    app.setOrganizationName("AXON");
    app.setOrganizationDomain("axon-agent.ai");
    app.setApplicationName("AXON Workstation");

    QQmlApplicationEngine engine;

    // Instantiate LLM client and inject into QML context
    LlmClient llm;
    engine.rootContext()->setContextProperty("llm", &llm);

    const QUrl url(QStringLiteral("qrc:/main.qml"));
    
    // In case resources are loaded from local file path during dev:
    const QUrl localUrl = QUrl::fromLocalFile(app.applicationDirPath() + "/main.qml");

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated,
                     &app, [url, localUrl](QObject *obj, const QUrl &objUrl) {
        if (!obj && (objUrl == url || objUrl == localUrl))
            QCoreApplication::exit(-1);
    }, Qt::QueuedConnection);

    // Try loading compiled QRC first, fallback to local file
    engine.load(localUrl.isValid() && QFile::exists(localUrl.toLocalFile()) ? localUrl : QUrl(QStringLiteral("qrc:/main.qml")));

    return app.exec();
}
