package com.agent008

import android.content.Context
import android.os.SystemClock
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive

class GenerationWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val chatId = inputData.getLong(CHAT_ID, -1L)
        val requestHash = inputData.getInt(REQUEST_HASH, Int.MIN_VALUE)
        if (chatId == -1L || requestHash == Int.MIN_VALUE) return Result.failure()

        val store = LocalStore(applicationContext)
        val chat = store.chats().firstOrNull { it.id == chatId } ?: return Result.success()
        if (chat.messages.lastOrNull()?.let { !it.fromUser || it.isSource || it.text.hashCode() != requestHash } != false) return Result.success()

        val config = store.config()
        var latestText = store.generationDraft(chatId, requestHash).orEmpty()
        var lastUiUpdate = 0L
        var lastCheckpoint = 0L
        GenerationUpdates.publish(chatId, requestHash, latestText)
        val workerContext = currentCoroutineContext()
        val response = LocalAiClient.askStreaming(config, chat.messages) { partial ->
            if (isStopped) throw CancellationException("Generation stopped")
            workerContext.ensureActive()
            latestText = partial
            val now = SystemClock.elapsedRealtime()
            if (now - lastUiUpdate >= UI_UPDATE_INTERVAL_MS) {
                GenerationUpdates.publish(chatId, requestHash, partial)
                lastUiUpdate = now
            }
            if (now - lastCheckpoint >= CHECKPOINT_INTERVAL_MS) {
                store.saveGenerationDraft(chatId, requestHash, partial)
                lastCheckpoint = now
            }
        }.getOrElse { failure ->
            if (isStopped) throw CancellationException("Generation stopped", failure)
            workerContext.ensureActive()
            val detail = failure.message.orEmpty().replace(Regex("\\s+"), " ").take(500)
            "Не вдалося отримати відповідь від ${config.provider.title}.${if (detail.isBlank()) " Перевірте сервер і модель." else " $detail"}"
        }
        if (isStopped) return Result.success()
        workerContext.ensureActive()
        GenerationUpdates.publish(chatId, requestHash, response)
        store.completeGeneration(chatId, requestHash, response)
        store.clearGenerationDraft(chatId)
        GenerationUpdates.publish(chatId, requestHash, response, completed = true)
        return Result.success()
    }

    companion object {
        const val CHAT_ID = "chat_id"
        const val REQUEST_HASH = "request_hash"
        private const val UI_UPDATE_INTERVAL_MS = 80L
        private const val CHECKPOINT_INTERVAL_MS = 1_000L
    }
}
