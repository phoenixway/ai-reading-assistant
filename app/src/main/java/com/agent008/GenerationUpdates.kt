package com.agent008

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

data class GenerationUpdate(
    val requestHash: Int,
    val text: String,
    val completed: Boolean = false,
)

object GenerationUpdates {
    private val _updates = MutableStateFlow<Map<Long, GenerationUpdate>>(emptyMap())
    private val activeRequests = mutableMapOf<Long, Int>()
    val updates: StateFlow<Map<Long, GenerationUpdate>> = _updates

    @Synchronized
    fun begin(chatId: Long, requestHash: Int, text: String = "") {
        activeRequests[chatId] = requestHash
        _updates.value = _updates.value + (chatId to GenerationUpdate(requestHash, text))
    }

    @Synchronized
    fun publish(chatId: Long, requestHash: Int, text: String, completed: Boolean = false) {
        if (activeRequests[chatId] != requestHash) return
        _updates.value = _updates.value + (chatId to GenerationUpdate(requestHash, text, completed))
    }

    @Synchronized
    fun cancel(chatId: Long, requestHash: Int?) {
        if (requestHash == null || activeRequests[chatId] == requestHash) activeRequests.remove(chatId)
        _updates.value = _updates.value - chatId
    }

    @Synchronized
    fun clear(chatId: Long) {
        activeRequests.remove(chatId)
        _updates.value = _updates.value - chatId
    }
}
