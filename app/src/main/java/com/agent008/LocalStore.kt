package com.agent008

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

class LocalStore(context: Context) {
    private val prefs = context.getSharedPreferences("local_page_ai", Context.MODE_PRIVATE)

    fun config(): ServerConfig {
        val provider = Provider.valueOf(prefs.getString("provider", Provider.OLLAMA.name)!!)
        return ServerConfig(prefs.getString("host", "192.168.1.10")!!, portFor(provider), provider, modelFor(provider), prefs.getInt("context_tokens", 8192))
    }

    fun portFor(provider: Provider): String = prefs.getString("port_${provider.name}", null)
        ?: prefs.getString("port", defaultPort(provider))!!

    fun modelFor(provider: Provider): String {
        prefs.getString("model_${provider.name}", null)?.let { return it }
        val savedProvider = prefs.getString("provider", Provider.OLLAMA.name)
        return if (savedProvider == provider.name) prefs.getString("model", "").orEmpty() else ""
    }

    private fun defaultPort(provider: Provider) = if (provider == Provider.OLLAMA) "11434" else "8080"

    fun saveConfig(value: ServerConfig) = prefs.edit()
        .putString("host", value.host).putString("port", value.port)
        .putString("port_${value.provider.name}", value.port)
        .putString("provider", value.provider.name).putString("model", value.model)
        .putString("model_${value.provider.name}", value.model)
        .putInt("context_tokens", value.contextTokens).apply()

    fun prompts(): List<SavedPrompt> = runCatching {
        val array = JSONArray(prefs.getString("prompts", "[]"))
        (0 until array.length()).map { i -> array.getJSONObject(i).let {
            SavedPrompt(it.getLong("id"), it.getString("title"), it.getString("body"), it.optString("folder", "Загальні"))
        } }
    }.getOrDefault(emptyList())
    fun savePrompts(items: List<SavedPrompt>) {
        val arr = JSONArray(); items.forEach { arr.put(JSONObject().apply {
            put("id", it.id); put("title", it.title); put("body", it.body); put("folder", it.folder)
        }) }; prefs.edit().putString("prompts", arr.toString()).apply()
    }
    fun folders(): List<String> = prefs.getStringSet("folders", setOf("Загальні"))!!.sorted()
    fun saveFolders(items: Set<String>) = prefs.edit().putStringSet("folders", items).apply()

    fun messages(): List<ChatMessage> = runCatching {
        val array = JSONArray(prefs.getString("messages", "[]"))
        (0 until array.length()).map { i -> array.getJSONObject(i).let {
            ChatMessage(it.getString("text"), it.getBoolean("fromUser"), it.optBoolean("isSource"), it.optBoolean("includeInApi", true), it.optString("displayText").ifBlank { null }, it.optBoolean("sourceEnabled", true))
        } }
    }.getOrDefault(emptyList())

    fun saveMessages(items: List<ChatMessage>) {
        val array = JSONArray()
        items.takeLast(40).forEach { message -> array.put(JSONObject().apply {
            put("text", message.text); put("fromUser", message.fromUser)
            put("isSource", message.isSource); put("includeInApi", message.includeInApi); put("displayText", message.displayText); put("sourceEnabled", message.sourceEnabled)
        }) }
        prefs.edit().putString("messages", array.toString()).apply()
    }

    fun chats(): List<ChatSession> = runCatching {
        val array = JSONArray(prefs.getString("chats", "[]"))
        (0 until array.length()).map { i -> array.getJSONObject(i).toChatSession() }.sortedByDescending { it.updatedAt }
    }.getOrDefault(emptyList())

    fun saveChats(items: List<ChatSession>) {
        val array = JSONArray(); items.forEach { chat -> array.put(chat.toJson()) }
        prefs.edit().putString("chats", array.toString()).apply()
    }

    fun completeGeneration(chatId: Long, requestHash: Int, response: String) {
        synchronized(chatLock) {
            val saved = chats()
            val updated = saved.map { chat ->
                if (chat.id != chatId || chat.messages.lastOrNull()?.let { !it.fromUser || it.isSource || it.text.hashCode() != requestHash } != false) chat
                else chat.copy(messages = chat.messages + ChatMessage(response, false), updatedAt = System.currentTimeMillis())
            }
            saveChats(updated)
        }
    }

    fun generationDraft(chatId: Long, requestHash: Int): String? =
        prefs.getString("generation_draft_$chatId", null)
            ?.takeIf { prefs.getInt("generation_hash_$chatId", Int.MIN_VALUE) == requestHash }

    fun saveGenerationDraft(chatId: Long, requestHash: Int, text: String) {
        prefs.edit()
            .putInt("generation_hash_$chatId", requestHash)
            .putString("generation_draft_$chatId", text)
            .apply()
    }

    fun clearGenerationDraft(chatId: Long) {
        prefs.edit().remove("generation_hash_$chatId").remove("generation_draft_$chatId").apply()
    }

    fun chatFolders(): List<String> = prefs.getStringSet("chat_folders", setOf("Загальні"))!!.sorted()
    fun saveChatFolders(items: Set<String>) = prefs.edit().putStringSet("chat_folders", items).apply()
    fun currentChatId(): Long? = prefs.getLong("current_chat", -1).takeIf { it != -1L }
    fun saveCurrentChatId(id: Long) = prefs.edit().putLong("current_chat", id).apply()

    private fun ChatSession.toJson() = JSONObject().apply {
        put("id", id); put("title", title); put("folder", folder); put("sourceUrl", sourceUrl); put("updatedAt", updatedAt)
        put("messages", JSONArray().apply { messages.forEach { message -> put(JSONObject().apply {
            put("text", message.text); put("fromUser", message.fromUser); put("isSource", message.isSource)
            put("includeInApi", message.includeInApi); put("displayText", message.displayText); put("sourceEnabled", message.sourceEnabled)
        }) } })
    }

    private fun JSONObject.toChatSession(): ChatSession {
        val items = getJSONArray("messages").let { array -> (0 until array.length()).map { i -> array.getJSONObject(i).let {
            ChatMessage(it.getString("text"), it.getBoolean("fromUser"), it.optBoolean("isSource"), it.optBoolean("includeInApi", true), it.optString("displayText").ifBlank { null }, it.optBoolean("sourceEnabled", true))
        } } }
        return ChatSession(getLong("id"), getString("title"), optString("folder", "Загальні"), items, optString("sourceUrl").ifBlank { null }, optLong("updatedAt", 0))
    }

    private companion object { val chatLock = Any() }
}
