#ifndef LLMCLIENT_H
#define LLMCLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>

class LlmClient : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString provider READ provider WRITE setProvider NOTIFY providerChanged)
    Q_PROPERTY(QString model READ model WRITE setModel NOTIFY modelChanged)
    Q_PROPERTY(QString apiKey READ apiKey WRITE setApiKey NOTIFY apiKeyChanged)

public:
    explicit LlmClient(QObject *parent = nullptr);
    ~LlmClient();

    QString provider() const { return m_provider; }
    void setProvider(const QString &provider);

    QString model() const { return m_model; }
    void setModel(const QString &model);

    QString apiKey() const { return m_apiKey; }
    void setApiKey(const QString &apiKey);

    Q_INVOKABLE void sendPrompt(const QString &prompt);
    Q_INVOKABLE void cancelRequest();
    Q_INVOKABLE void loadConfig();

signals:
    void streamStarted();
    void tokenReceived(const QString &token);
    void streamFinished();
    void errorOccurred(const QString &error);

    void providerChanged();
    void modelChanged();
    void apiKeyChanged();

private slots:
    void onReadyRead();
    void onFinished();
    void onError(QNetworkReply::NetworkError code);

private:
    void processGeminiChunk(const QString &chunkData);
    void processOpenRouterChunk(const QString &chunkData);

    QNetworkAccessManager *m_manager;
    QNetworkReply *m_currentReply;
    
    QString m_provider; // "gemini" or "openrouter"
    QString m_model;    // e.g. "gemini-2.5-flash"
    QString m_apiKey;
    
    QString m_buffer;   // Buffer for parsing SSE lines
};

#endif // LLMCLIENT_H
