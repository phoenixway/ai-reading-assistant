package com.agent008

enum class Provider(val title: String) { OLLAMA("Ollama"), LLAMA_CPP("llama.cpp") }
data class ServerConfig(
    val host: String = "192.168.1.10",
    val port: String = "11434",
    val provider: Provider = Provider.OLLAMA,
    val model: String = "",
    val contextTokens: Int = 8192
)
data class SavedPrompt(val id: Long, val title: String, val body: String, val folder: String = "Загальні")
data class ChatMessage(
    val text: String,
    val fromUser: Boolean,
    val isSource: Boolean = false,
    val includeInApi: Boolean = true,
    val displayText: String? = null,
    val sourceEnabled: Boolean = true
)
data class ChatSession(
    val id: Long,
    val title: String,
    val folder: String = "Загальні",
    val messages: List<ChatMessage>,
    val sourceUrl: String? = null,
    val updatedAt: Long = System.currentTimeMillis()
)
