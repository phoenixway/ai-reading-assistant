package com.agent008

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

object WebPageLoader {
    private val urlPattern = Regex("https?://[^\\s]+")
    suspend fun fromShared(text: String): Result<Pair<String, String>> = withContext(Dispatchers.IO) {
        runCatching {
            val url = urlPattern.find(text)?.value ?: error("У поширеному тексті не знайдено URL")
            val connection = URL(url).openConnection() as HttpURLConnection
            connection.connectTimeout = 12_000; connection.readTimeout = 20_000
            connection.useCaches = false
            connection.setRequestProperty("Cache-Control", "no-cache")
            connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Android) LocalPageAI/1.0")
            val html = connection.inputStream.bufferedReader().use { it.readText() }
            val main = extractMainContent(html)
            val clean = main.replace(Regex("(?is)<(script|style|noscript|svg|header|nav|footer|aside|form|template).*?</\\1>"), " ")
                .replace(Regex("(?i)<br\\s*/?>|</?(p|div|li|h[1-6]|section|article)[^>]*>"), "\n")
                .replace(Regex("(?s)<[^>]+>"), " ")
                .replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", "\"")
                .replace("&#39;", "'").replace(Regex("[ \\t]+"), " ")
                .replace(Regex("\\n{3,}"), "\n\n").trim().take(18_000)
            require(clean.length > 120) { "На сторінці не знайдено достатньо тексту" }
            url to clean
        }
    }

    private fun extractMainContent(html: String): String {
        val candidates = listOf("article", "main", "[role=main]")
        candidates.forEach { selector ->
            val pattern = when (selector) {
                "[role=main]" -> Regex("(?is)<([a-z0-9]+)[^>]*role=[\"']main[\"'][^>]*>(.*?)</\\1>")
                else -> Regex("(?is)<$selector[^>]*>(.*?)</$selector>")
            }
            pattern.find(html)?.groupValues?.getOrNull(if (selector == "[role=main]") 2 else 1)?.takeIf { it.length > 300 }?.let { return it }
        }
        return Regex("(?is)<body[^>]*>(.*?)</body>").find(html)?.groupValues?.getOrNull(1) ?: html
    }
}
