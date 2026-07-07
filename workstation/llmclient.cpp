#include "llmclient.h"
#include <QNetworkRequest>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QUrl>
#include <QDebug>
#include <QDir>
#include <QFile>

LlmClient::LlmClient(QObject *parent)
    : QObject(parent)
    , m_manager(new QNetworkAccessManager(this))
    , m_currentReply(nullptr)
    , m_provider("gemini")
    , m_model("gemini-2.5-flash")
{
    loadConfig();
}

LlmClient::~LlmClient()
{
    cancelRequest();
}

void LlmClient::setProvider(const QString &provider)
{
    if (m_provider != provider) {
        m_provider = provider;
        emit providerChanged();
    }
}

void LlmClient::setModel(const QString &model)
{
    if (m_model != model) {
        m_model = model;
        emit modelChanged();
    }
}

void LlmClient::setApiKey(const QString &apiKey)
{
    if (m_apiKey != apiKey) {
        m_apiKey = apiKey;
        emit apiKeyChanged();
    }
}

void LlmClient::sendPrompt(const QString &prompt)
{
    cancelRequest();
    m_buffer.clear();

    if (m_apiKey.isEmpty()) {
        emit errorOccurred("API Key is missing. Set it in config.");
        return;
    }

    QUrl url;
    QNetworkRequest request;
    QByteArray requestData;

    if (m_provider == "gemini") {
        QString modelName = m_model;
        if (modelName.contains("/")) {
            modelName = modelName.split("/").last();
        }
        // Gemini streamGenerateContent REST API
        url = QUrl(QString("https://generativelanguage.googleapis.com/v1beta/models/%1:streamGenerateContent?key=%2")
                       .arg(modelName)
                       .arg(m_apiKey));
        
        request.setUrl(url);
        request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

        QJsonObject root;
        QJsonObject part;
        part["text"] = prompt;
        QJsonArray parts;
        parts.append(part);
        QJsonObject content;
        content["parts"] = parts;
        QJsonArray contents;
        contents.append(content);
        root["contents"] = contents;

        requestData = QJsonDocument(root).toJson();
    }
    else if (m_provider == "openrouter") {
        url = QUrl("https://openrouter.ai/api/v1/chat/completions");
        request.setUrl(url);
        request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
        request.setRawHeader("Authorization", QString("Bearer %1").arg(m_apiKey).toUtf8());

        QJsonObject root;
        root["model"] = m_model;
        root["stream"] = true;

        QJsonObject message;
        message["role"] = "user";
        message["content"] = prompt;
        QJsonArray messages;
        messages.append(message);
        root["messages"] = messages;

        requestData = QJsonDocument(root).toJson();
    }
    else {
        emit errorOccurred("Unsupported provider: " + m_provider);
        return;
    }

    m_currentReply = m_manager->post(request, requestData);
    connect(m_currentReply, &QNetworkReply::readyRead, this, &LlmClient::onReadyRead);
    connect(m_currentReply, &QNetworkReply::finished, this, &LlmClient::onFinished);
    
    // Qt6 signal compatibility
    connect(m_currentReply, &QNetworkReply::errorOccurred, this, &LlmClient::onError);

    emit streamStarted();
}

void LlmClient::cancelRequest()
{
    if (m_currentReply) {
        m_currentReply->abort();
        m_currentReply->disconnect();
        m_currentReply->deleteLater();
        m_currentReply = nullptr;
        emit streamFinished();
    }
}

void LlmClient::onReadyRead()
{
    if (!m_currentReply) return;

    m_buffer.append(m_currentReply->readAll());
    
    // Process SSE stream line by line
    int newlineIndex;
    while ((newlineIndex = m_buffer.indexOf('\n')) != -1) {
        QString line = m_buffer.left(newlineIndex).trimmed();
        m_buffer.remove(0, newlineIndex + 1);

        if (line.isEmpty()) continue;

        if (m_provider == "gemini") {
            processGeminiChunk(line);
        } else if (m_provider == "openrouter") {
            processOpenRouterChunk(line);
        }
    }
}

void LlmClient::onFinished()
{
    if (m_currentReply) {
        // Process residual buffer
        if (!m_buffer.trimmed().isEmpty()) {
            if (m_provider == "gemini") {
                processGeminiChunk(m_buffer.trimmed());
            } else if (m_provider == "openrouter") {
                processOpenRouterChunk(m_buffer.trimmed());
            }
        }
        m_currentReply->deleteLater();
        m_currentReply = nullptr;
        emit streamFinished();
    }
}

void LlmClient::onError(QNetworkReply::NetworkError code)
{
    if (code == QNetworkReply::OperationCanceledError) {
        return; // Ignore manual cancellation
    }
    if (m_currentReply) {
        emit errorOccurred(m_currentReply->errorString());
        cancelRequest();
    }
}

void LlmClient::processGeminiChunk(const QString &chunkData)
{
    QString cleanJson = chunkData;
    if (cleanJson.startsWith("[")) cleanJson = cleanJson.mid(1);
    if (cleanJson.startsWith(",")) cleanJson = cleanJson.mid(1);
    if (cleanJson.endsWith("]")) cleanJson = cleanJson.left(cleanJson.length() - 1);
    cleanJson = cleanJson.trimmed();

    if (cleanJson.isEmpty()) return;

    QJsonParseError parseError;
    QJsonDocument doc = QJsonDocument::fromJson(cleanJson.toUtf8(), &parseError);
    if (parseError.error != QJsonParseError::NoError) {
        return; // Could be incomplete chunk, ignore
    }

    QJsonObject root = doc.object();
    QJsonArray candidates = root["candidates"].toArray();
    if (candidates.isEmpty()) return;

    QJsonObject content = candidates[0].toObject()["content"].toObject();
    QJsonArray parts = content["parts"].toArray();
    if (parts.isEmpty()) return;

    QString text = parts[0].toObject()["text"].toString();
    if (!text.isEmpty()) {
        emit tokenReceived(text);
    }
}

void LlmClient::processOpenRouterChunk(const QString &chunkData)
{
    if (!chunkData.startsWith("data:")) return;
    
    QString dataContent = chunkData.mid(5).trimmed();
    if (dataContent == "[DONE]") {
        emit streamFinished();
        return;
    }

    QJsonParseError parseError;
    QJsonDocument doc = QJsonDocument::fromJson(dataContent.toUtf8(), &parseError);
    if (parseError.error != QJsonParseError::NoError) {
        return;
    }

    QJsonObject root = doc.object();
    QJsonArray choices = root["choices"].toArray();
    if (choices.isEmpty()) return;

    QJsonObject delta = choices[0].toObject()["delta"].toObject();
    QString text = delta["content"].toString();
    if (!text.isEmpty()) {
        emit tokenReceived(text);
    }
}

void LlmClient::loadConfig()
{
    QString configPath = QDir::homePath() + "/AppData/Roaming/AXON/config.json";
    QFile file(configPath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qWarning() << "Could not open config file:" << configPath;
        return;
    }

    QByteArray data = file.readAll();
    file.close();

    QJsonParseError parseError;
    QJsonDocument doc = QJsonDocument::fromJson(data, &parseError);
    if (parseError.error != QJsonParseError::NoError) {
        qWarning() << "Error parsing config file:" << parseError.errorString();
        return;
    }

    QJsonObject root = doc.object();
    
    // Set provider
    QString prov = root["provider"].toString().trimmed();
    if (!prov.isEmpty()) {
        // Map backend provider name to workstation QML compatibility
        if (prov == "antigravity") {
            setProvider("gemini");
        } else {
            setProvider(prov);
        }
    }

    // Set model
    QString mod = root["model"].toString().trimmed();
    if (!mod.isEmpty()) {
        setModel(mod);
    }

    // Set key based on provider
    if (m_provider == "gemini") {
        setApiKey(root["antigravity_api_key"].toString().trimmed());
    } else if (m_provider == "openrouter") {
        setApiKey(root["openrouter_api_key"].toString().trimmed());
    } else if (m_provider == "custom") {
        setApiKey(root["custom_api_key"].toString().trimmed());
    }
}
