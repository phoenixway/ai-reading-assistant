package com.agent008

import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.animateScrollBy
import androidx.compose.foundation.interaction.collectIsDraggedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.zIndex
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import java.util.UUID

private enum class Screen { CHAT, CHATS, SETTINGS, PROMPTS }

@Composable
fun LocalPageAiApp(sharedText: String?, consumeShared: () -> Unit) {
    val context = LocalContext.current
    val store = remember { LocalStore(context) }
    val scope = rememberCoroutineScope()
    val workManager = remember { WorkManager.getInstance(context) }
    var screen by remember { mutableStateOf(Screen.CHAT) }
    var config by remember { mutableStateOf(store.config()) }
    var actualContextTokens by remember { mutableStateOf<Int?>(if (config.provider == Provider.OLLAMA) config.contextTokens else null) }
    var contextProbeVersion by remember { mutableIntStateOf(0) }
    var chats by remember {
        mutableStateOf(store.chats().map { it.deduplicateSources().withoutWelcomeMessages() }.ifEmpty {
            listOf(ChatSession(System.currentTimeMillis(), "Попередній чат", messages = store.messages().filterNot { it.isWelcomeMessage() }))
        })
    }
    var currentChatId by remember { mutableStateOf(store.currentChatId()?.takeIf { id -> chats.any { it.id == id } } ?: chats.first().id) }
    var loading by remember { mutableStateOf(false) }
    var generationWorkId by remember { mutableStateOf<UUID?>(null) }
    var generationWorkChatId by remember { mutableStateOf<Long?>(null) }
    val expandedMessages = remember { mutableStateMapOf<String, Boolean>() }
    val currentChat = chats.first { it.id == currentChatId }
    val generationUpdates by GenerationUpdates.updates.collectAsState()
    val currentGeneration = generationUpdates[currentChatId]?.takeIf { update ->
        currentChat.messages.lastOrNull()?.let { it.fromUser && !it.isSource && it.text.hashCode() == update.requestHash } == true
    }
    val visibleMessages = currentGeneration?.let { update ->
        currentChat.messages + ChatMessage(
            text = update.text,
            fromUser = false,
            includeInApi = false,
            displayText = "stream:${update.requestHash}",
        )
    } ?: currentChat.messages
    val generationActive = loading || generationUpdates.values.any { !it.completed }
    val generationRunning = generationWorkId != null || generationUpdates.values.any { !it.completed }

    LaunchedEffect(chats) { store.saveChats(chats) }
    LaunchedEffect(currentChatId) { store.saveCurrentChatId(currentChatId) }
    LaunchedEffect(config, contextProbeVersion) {
        actualContextTokens = if (config.provider == Provider.OLLAMA) config.contextTokens else null
        LocalAiClient.actualContextTokens(config).onSuccess { detected -> actualContextTokens = detected }
    }
    LaunchedEffect(actualContextTokens) {
        val actual = actualContextTokens ?: return@LaunchedEffect
        chats = chats.map { chat -> chat.copy(messages = LocalAiClient.autoDisableOldSources(chat.messages, actual)) }
    }
    LaunchedEffect(generationUpdates) {
        val completedChatIds = generationUpdates.filterValues { it.completed }.keys
        if (completedChatIds.isNotEmpty()) {
            chats = store.chats().map { it.deduplicateSources().withoutWelcomeMessages() }
            completedChatIds.forEach(GenerationUpdates::clear)
        }
    }
    fun updateChat(chat: ChatSession) { chats = chats.map { if (it.id == chat.id) chat.copy(updatedAt = System.currentTimeMillis()) else it }; store.saveChats(chats) }
    fun transformChat(chatId: Long, transform: (ChatSession) -> ChatSession) {
        chats = chats.map { chat -> if (chat.id == chatId) transform(chat).copy(updatedAt = System.currentTimeMillis()) else chat }; store.saveChats(chats)
    }
    fun addChat(chat: ChatSession) { chats = (chats + chat).sortedByDescending { it.updatedAt }; currentChatId = chat.id }
    fun enqueueGeneration(chatId: Long, requestText: String) {
        val requestHash = requestText.hashCode()
        GenerationUpdates.begin(chatId, requestHash)
        val work = OneTimeWorkRequestBuilder<GenerationWorker>()
            .setInputData(Data.Builder().putLong(GenerationWorker.CHAT_ID, chatId).putInt(GenerationWorker.REQUEST_HASH, requestHash).build())
            .build()
        generationWorkId = work.id
        generationWorkChatId = chatId
        loading = true
        workManager.enqueueUniqueWork("generation-$chatId", ExistingWorkPolicy.REPLACE, work)
    }
    fun stopGeneration() {
        val chatId = generationWorkChatId
            ?: generationUpdates.entries.firstOrNull { !it.value.completed }?.key
            ?: return
        val partial = generationUpdates[chatId]
        GenerationUpdates.cancel(chatId, partial?.requestHash)
        workManager.cancelUniqueWork("generation-$chatId")
        if (partial != null && partial.text.isNotBlank()) {
            store.completeGeneration(chatId, partial.requestHash, partial.text)
        }
        store.clearGenerationDraft(chatId)
        chats = store.chats().map { it.deduplicateSources().withoutWelcomeMessages() }
        generationWorkId = null
        generationWorkChatId = null
        loading = false
    }

    LaunchedEffect(generationWorkId) {
        val workId = generationWorkId ?: return@LaunchedEffect
        workManager.getWorkInfoByIdFlow(workId).collect { info ->
            if (generationWorkId != workId) return@collect
            loading = info?.state?.isFinished != true
            if (info?.state?.isFinished == true) {
                chats = store.chats().map { it.deduplicateSources() }
                generationWorkChatId?.let(GenerationUpdates::clear)
                generationWorkChatId = null
                generationWorkId = null
            }
        }
    }

    LaunchedEffect(sharedText) {
        val shared = sharedText ?: return@LaunchedEffect
        val sharedChat = newChat("Нова сторінка")
        addChat(sharedChat)
        loading = true
        WebPageLoader.fromShared(shared).onSuccess { (url, content) ->
            updateChat(sharedChat.copy(messages = emptyList()).withSource(url, content, actualContextTokens).copy(title = url.removePrefix("https://").removePrefix("http://")))
        }.onFailure { updateChat(sharedChat.copy(messages = sharedChat.messages + ChatMessage("Не вдалося завантажити сторінку. Перевірте URL та з’єднання з інтернетом.", false, includeInApi = false))) }
        loading = false; consumeShared()
    }
    when (screen) {
        Screen.CHAT -> ChatScreen(currentChat.id, visibleMessages, generationActive, generationRunning, currentChat.sourceUrl, LocalAiClient.contextUsage(currentChat.messages, actualContextTokens ?: 0), "${config.provider.title} · ${config.model.ifBlank { "модель не вибрана" }}", expandedMessages, onSettings = { screen = Screen.SETTINGS }, onPrompts = { screen = Screen.PROMPTS }, onChats = { screen = Screen.CHATS }, onNewChat = { addChat(newChat()) }, onStopGeneration = ::stopGeneration, onToggleSource = { url, enabled -> transformChat(currentChat.id) { chat -> chat.copy(messages = chat.messages.map { if (it.isSource && it.displayText == url) it.copy(sourceEnabled = enabled) else it }) } }, onSend = { text ->
            val chatId = currentChat.id
            val pending = currentChat.copy(messages = currentChat.messages + ChatMessage(text, true)); updateChat(pending)
            enqueueGeneration(chatId, text)
        }, onRegenerate = { messageIndex ->
            val message = currentChat.messages.getOrNull(messageIndex) ?: return@ChatScreen
            if (!message.fromUser || message.isSource || generationActive) return@ChatScreen
            val pending = currentChat.copy(messages = currentChat.messages.take(messageIndex + 1))
            updateChat(pending)
            enqueueGeneration(currentChat.id, message.text)
        }, onAddUrl = { url ->
            val chatId = currentChat.id
            loading = true; scope.launch { WebPageLoader.fromShared(url).onSuccess { (loadedUrl, content) -> transformChat(chatId) { chat -> chat.withSource(loadedUrl, content, actualContextTokens) }
            }.onFailure { transformChat(chatId) { chat -> chat.copy(messages = chat.messages + ChatMessage("Не вдалося додати URL. Перевірте адресу та з’єднання з інтернетом.", false, includeInApi = false)) } }; loading = false }
        }, prompts = store.prompts(), onSavePrompt = { title, body ->
            store.savePrompts(store.prompts() + SavedPrompt(System.currentTimeMillis(), title, body)); Toast.makeText(context, "Промпт збережено", Toast.LENGTH_SHORT).show()
        })
        Screen.CHATS -> ChatsScreen(chats, store, currentChatId, onBack = { screen = Screen.CHAT }, onSelect = { currentChatId = it; screen = Screen.CHAT }, onCreate = { addChat(it) }, onUpdate = ::updateChat, onDelete = { id -> if (chats.size > 1) { chats = chats.filterNot { it.id == id }; if (currentChatId == id) currentChatId = chats.first().id } })
        Screen.SETTINGS -> SettingsScreen(config, store::portFor, store::modelFor, onBack = { screen = Screen.CHAT }, onSave = { config = it; store.saveConfig(it); contextProbeVersion++; screen = Screen.CHAT })
        Screen.PROMPTS -> PromptsScreen(store, onBack = { screen = Screen.CHAT })
    }
}

private fun newChat(title: String = "Новий чат") = ChatSession(System.currentTimeMillis(), title, messages = emptyList())

private fun ChatMessage.isWelcomeMessage() = !fromUser && !includeInApi &&
    (text.startsWith("Вітаю! Додайте URL") || text == "Вітаю! Новий чат готовий.")

private fun ChatSession.withoutWelcomeMessages() = copy(messages = messages.filterNot { it.isWelcomeMessage() })

private fun ChatSession.withSource(url: String, content: String, contextTokens: Int?): ChatSession {
    val updated = messages.filterNot { it.isSource && it.displayText == url } + ChatMessage("Джерело: $url\n\n$content", true, true, displayText = url)
    return copy(sourceUrl = url, messages = contextTokens?.let { LocalAiClient.autoDisableOldSources(updated, it) } ?: updated)
}

private fun ChatSession.deduplicateSources(): ChatSession {
    val seenUrls = mutableSetOf<String>()
    val result = messages.asReversed().filter { message ->
        !message.isSource || seenUrls.add(message.displayText ?: message.text)
    }.asReversed()
    return copy(messages = result)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable private fun ChatsScreen(chats: List<ChatSession>, store: LocalStore, selectedId: Long, onBack: () -> Unit, onSelect: (Long) -> Unit, onCreate: (ChatSession) -> Unit, onUpdate: (ChatSession) -> Unit, onDelete: (Long) -> Unit) {
    var folders by remember { mutableStateOf(store.chatFolders()) }; var editor by remember { mutableStateOf<ChatSession?>(null) }; var folderDialog by remember { mutableStateOf(false) }
    Scaffold(topBar = { TopAppBar(title = { Text("Чати") }, navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "Назад") } }, actions = { IconButton(onClick = { folderDialog = true }) { Icon(Icons.Default.CreateNewFolder, "Нова папка") } }) }, floatingActionButton = { FloatingActionButton(onClick = { editor = ChatSession(0, "", folders.firstOrNull() ?: "Загальні", emptyList()) }) { Icon(Icons.Default.Add, "Новий чат") } }) { pad ->
        LazyColumn(Modifier.padding(pad).fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            folders.forEach { folder ->
                item { Text(folder, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp)) }
                items(chats.filter { it.folder == folder }, key = { it.id }) { chat -> Card(Modifier.fillMaxWidth().clickable { onSelect(chat.id) }, colors = CardDefaults.cardColors(containerColor = if (chat.id == selectedId) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceVariant)) {
                    ListItem(headlineContent = { Text(chat.title, maxLines = 1) }, supportingContent = { Text(chat.sourceUrl ?: chat.messages.lastOrNull()?.text.orEmpty(), maxLines = 1) }, trailingContent = { Row { IconButton(onClick = { editor = chat }) { Icon(Icons.Default.Edit, "Редагувати") }; IconButton(onClick = { onDelete(chat.id) }) { Icon(Icons.Default.DeleteOutline, "Видалити") } } })
                } }
            }
        }
    }
    editor?.let { chat -> ChatEditor(chat, folders, onDismiss = { editor = null }, onSave = { changed -> if (changed.id == 0L) onCreate(changed.copy(id = System.currentTimeMillis())) else onUpdate(changed); editor = null }) }
    if (folderDialog) TextInputDialog("Нова папка для чатів", "Наприклад: Дослідження", onDismiss = { folderDialog = false }) { name -> folders = (folders + name.trim()).filter { it.isNotBlank() }.distinct().sorted(); store.saveChatFolders(folders.toSet()); folderDialog = false }
}

@Composable private fun ChatEditor(initial: ChatSession, folders: List<String>, onDismiss: () -> Unit, onSave: (ChatSession) -> Unit) {
    var title by remember { mutableStateOf(initial.title) }; var folder by remember { mutableStateOf(initial.folder) }; var expanded by remember { mutableStateOf(false) }
    AlertDialog(onDismissRequest = onDismiss, title = { Text(if (initial.id == 0L) "Новий чат" else "Редагувати чат") }, text = { Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        OutlinedTextField(title, { title = it }, label = { Text("Назва") }, singleLine = true)
        Box { OutlinedButton(onClick = { expanded = true }) { Text("Папка: $folder") }; DropdownMenu(expanded, { expanded = false }) { folders.forEach { option -> DropdownMenuItem(text = { Text(option) }, onClick = { folder = option; expanded = false }) } } }
    } }, confirmButton = { TextButton(enabled = title.isNotBlank(), onClick = { onSave(initial.copy(title = title, folder = folder)) }) { Text("Зберегти") } }, dismissButton = { TextButton(onClick = onDismiss) { Text("Скасувати") } })
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable private fun ChatScreen(chatId: Long, messages: List<ChatMessage>, loading: Boolean, generationRunning: Boolean, sourceUrl: String?, contextUsage: ContextUsage, serverLabel: String, expandedMessages: MutableMap<String, Boolean>, onSettings: () -> Unit, onPrompts: () -> Unit, onChats: () -> Unit, onNewChat: () -> Unit, onStopGeneration: () -> Unit, onToggleSource: (String, Boolean) -> Unit, onSend: (String) -> Unit, onRegenerate: (Int) -> Unit, onAddUrl: (String) -> Unit, prompts: List<SavedPrompt>, onSavePrompt: (String, String) -> Unit) {
    var input by remember { mutableStateOf("") }; var urlDialog by remember { mutableStateOf(false) }; var choosePrompt by remember { mutableStateOf(false) }; var saveDialog by remember { mutableStateOf(false) }; var sourcesDialog by remember { mutableStateOf(false) }; var topMenuExpanded by remember { mutableStateOf(false) }; var messageToSave by remember { mutableStateOf<String?>(null) }
    val context = LocalContext.current
    val messagesState = rememberLazyListState()
    val scrollScope = rememberCoroutineScope()
    var followStreaming by remember { mutableStateOf(true) }
    val isUserDragging by messagesState.interactionSource.collectIsDraggedAsState()
    var scrollToSentMessageIndex by remember { mutableStateOf(-1) }
    val lastMessageIndex = messages.lastIndex
    val showScrollToLast by remember(messagesState, lastMessageIndex) {
        derivedStateOf {
            val layout = messagesState.layoutInfo
            val lastMessage = layout.visibleItemsInfo.firstOrNull { it.index == lastMessageIndex }
            lastMessageIndex >= 0 && layout.visibleItemsInfo.isNotEmpty() &&
                (lastMessage == null || lastMessage.offset + lastMessage.size > layout.viewportEndOffset)
        }
    }
    val focusManager = LocalFocusManager.current
    val keyboardController = LocalSoftwareKeyboardController.current
    val submitMessage = {
        scrollToSentMessageIndex = messages.size
        onSend(input)
        input = ""
        focusManager.clearFocus()
        keyboardController?.hide()
        Unit
    }
    LaunchedEffect(messages.size, scrollToSentMessageIndex) {
        if (scrollToSentMessageIndex in messages.indices) {
            messagesState.animateScrollToItem(scrollToSentMessageIndex)
            scrollToSentMessageIndex = -1
        }
    }
    val scrollToLastMessageEnd = {
        followStreaming = true
        scrollScope.launch {
            if (lastMessageIndex >= 0) {
                messagesState.animateScrollToItem(lastMessageIndex)
                val layout = messagesState.layoutInfo
                val lastMessage = layout.visibleItemsInfo.firstOrNull { it.index == lastMessageIndex }
                val hiddenBottom = lastMessage?.let { it.offset + it.size - layout.viewportEndOffset } ?: 0
                if (hiddenBottom > 0) messagesState.animateScrollBy(hiddenBottom.toFloat())
            }
        }
        Unit
    }
    val streamingMessage = messages.lastOrNull()?.takeIf { it.displayText?.startsWith("stream:") == true }
    LaunchedEffect(streamingMessage?.displayText) {
        if (streamingMessage != null) followStreaming = true
    }
    LaunchedEffect(isUserDragging) {
        if (isUserDragging) followStreaming = false
    }
    LaunchedEffect(streamingMessage?.text, followStreaming) {
        if (streamingMessage != null && followStreaming) {
            withFrameNanos { }
            scrollToLastMessageEnd()
        }
    }
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("agent008", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, maxLines = 1)
                        Text(serverLabel, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
                    }
                },
                actions = {
                    IconButton(enabled = !loading, onClick = onNewChat, modifier = Modifier.size(40.dp)) { Icon(Icons.Default.AddComment, "Новий чат", modifier = Modifier.size(22.dp)) }
                    IconButton(enabled = !loading, onClick = onChats, modifier = Modifier.size(40.dp)) { Icon(Icons.Default.Forum, "Список чатів", modifier = Modifier.size(22.dp)) }
                    Box {
                        IconButton(onClick = { topMenuExpanded = true }, modifier = Modifier.size(40.dp)) { Icon(Icons.Default.MoreVert, "Меню", modifier = Modifier.size(22.dp)) }
                        DropdownMenu(expanded = topMenuExpanded, onDismissRequest = { topMenuExpanded = false }) {
                            DropdownMenuItem(text = { Text("Prompts") }, leadingIcon = { Icon(Icons.Default.Bookmarks, null) }, onClick = { topMenuExpanded = false; onPrompts() })
                            DropdownMenuItem(text = { Text("Налаштування") }, leadingIcon = { Icon(Icons.Default.Settings, null) }, onClick = { topMenuExpanded = false; onSettings() })
                        }
                    }
                    Spacer(Modifier.width(8.dp))
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        },
        bottomBar = {
            Surface(color = MaterialTheme.colorScheme.background) {
                Surface(
                    modifier = Modifier.fillMaxWidth().padding(start = 12.dp, end = 12.dp, top = 6.dp, bottom = 22.dp),
                    shape = RoundedCornerShape(24.dp),
                    color = MaterialTheme.colorScheme.surface,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.75f)),
                    tonalElevation = 2.dp,
                    shadowElevation = 2.dp,
                ) {
                    Column(Modifier.padding(horizontal = 8.dp, vertical = 6.dp)) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            IconButton(enabled = !loading, onClick = { urlDialog = true }, modifier = Modifier.size(36.dp)) { Icon(Icons.Default.AddLink, "Додати URL", modifier = Modifier.size(20.dp)) }
                            IconButton(onClick = { choosePrompt = true }, modifier = Modifier.size(36.dp)) { Icon(Icons.Default.Bookmark, "Вибрати збережений промпт", modifier = Modifier.size(20.dp)) }
                            if (input.isNotBlank()) IconButton(onClick = { saveDialog = true }, modifier = Modifier.size(36.dp)) { Icon(Icons.Default.BookmarkAdd, "Зберегти як промпт", modifier = Modifier.size(20.dp)) }
                            if (contextUsage.totalSources > 0) ContextIndicator(contextUsage, onSourcesClick = { sourcesDialog = true })
                            Spacer(Modifier.weight(1f))
                            if (generationRunning) {
                                FilledIconButton(onClick = onStopGeneration, modifier = Modifier.size(40.dp)) {
                                    Icon(Icons.Default.StopCircle, "Зупинити генерацію", modifier = Modifier.size(21.dp))
                                }
                            } else {
                                FilledIconButton(enabled = input.isNotBlank() && !loading, onClick = submitMessage, modifier = Modifier.size(40.dp)) {
                                    Icon(Icons.AutoMirrored.Filled.Send, "Надіслати", modifier = Modifier.size(20.dp))
                                }
                            }
                        }
                        TextField(
                            value = input,
                            onValueChange = { input = it },
                            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp, max = 116.dp),
                            placeholder = { Text(if (sourceUrl == null) "Напишіть повідомлення…" else "Запитайте про сторінку…", color = MaterialTheme.colorScheme.onSurfaceVariant) },
                            textStyle = MaterialTheme.typography.bodyMedium,
                            shape = RoundedCornerShape(18.dp),
                            minLines = 1,
                            maxLines = 4,
                            colors = TextFieldDefaults.colors(
                                focusedContainerColor = Color.Transparent,
                                unfocusedContainerColor = Color.Transparent,
                                disabledContainerColor = Color.Transparent,
                                focusedIndicatorColor = Color.Transparent,
                                unfocusedIndicatorColor = Color.Transparent,
                                disabledIndicatorColor = Color.Transparent,
                            )
                        )
                    }
                }
            }
        }
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            LazyColumn(Modifier.fillMaxSize().padding(horizontal = 14.dp), state = messagesState, verticalArrangement = Arrangement.spacedBy(24.dp), contentPadding = PaddingValues(vertical = 14.dp)) {
                itemsIndexed(
                    items = messages,
                    key = { index, message -> messageUiKey(chatId, index, message) },
                ) { index, message ->
                    val messageKey = messageUiKey(chatId, index, message)
                    val defaultExpanded = !message.fromUser && !message.isSource && index == messages.lastIndex
                    MessageBubble(
                        message = message,
                        stateKey = messageKey,
                        initiallyExpanded = expandedMessages[messageKey] ?: defaultExpanded,
                        onExpandedChange = { expandedMessages[messageKey] = it },
                        onCopy = { text ->
                    val clipboard = context.getSystemService(android.content.ClipboardManager::class.java)
                    clipboard?.setPrimaryClip(android.content.ClipData.newPlainText("Повідомлення", text))
                    Toast.makeText(context, "Скопійовано", Toast.LENGTH_SHORT).show()
                        },
                        onSaveAsPrompt = { messageToSave = it },
                        onRegenerate = {
                            expandedMessages.remove(messageUiKey(chatId, index + 1, ChatMessage("", false)))
                            onRegenerate(index)
                        },
                    )
                }
            }
            if (messages.isEmpty() && !loading) Column(Modifier.align(Alignment.Center).padding(horizontal = 36.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Default.AutoAwesome, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(28.dp))
                Text("Вітаю", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text(
                    "Додайте URL або поширте сторінку з браузера — я використаю її вміст як контекст.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
            }
            if (loading && streamingMessage == null) {
                Surface(shape = RoundedCornerShape(50), color = MaterialTheme.colorScheme.surfaceContainerHigh, tonalElevation = 6.dp, shadowElevation = 3.dp, modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp)) {
                    Box(Modifier.size(48.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(modifier = Modifier.size(38.dp), strokeWidth = 2.5.dp, color = MaterialTheme.colorScheme.primary, trackColor = MaterialTheme.colorScheme.primaryContainer)
                        Icon(Icons.Default.AutoAwesome, "Генерація відповіді", tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
                    }
                }
            } else {
                AnimatedVisibility(showScrollToLast, modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp)) {
                    FilledTonalIconButton(onClick = scrollToLastMessageEnd) {
                        Icon(Icons.Default.KeyboardArrowDown, "До кінця останнього повідомлення")
                    }
                }
            }
        }
    }
    if (urlDialog) TextInputDialog("Додати URL", "https://…", allowClipboardPaste = true, onDismiss = { urlDialog = false }) { onAddUrl(it); urlDialog = false }
    if (saveDialog) TextInputDialog("Назва промпту", "Наприклад: Короткий виклад", onDismiss = { saveDialog = false }) { onSavePrompt(it, input); saveDialog = false }
    messageToSave?.let { message -> TextInputDialog("Назва промпту", "Наприклад: Короткий виклад", onDismiss = { messageToSave = null }) { onSavePrompt(it, message); messageToSave = null } }
    if (choosePrompt) AlertDialog(onDismissRequest = { choosePrompt = false }, title = { Text("Збережені промпти") }, text = { LazyColumn { items(prompts) { prompt -> ListItem(headlineContent = { Text(prompt.title) }, supportingContent = { Text(prompt.folder) }, modifier = Modifier.clickable { input = prompt.body; choosePrompt = false }) } } }, confirmButton = { TextButton(onClick = { choosePrompt = false }) { Text("Закрити") } })
    if (sourcesDialog) SourceSelectionDialog(messages.filter { it.isSource }, contextUsage, onToggleSource, onDismiss = { sourcesDialog = false })
}

@Composable private fun ContextIndicator(usage: ContextUsage, onSourcesClick: () -> Unit) {
    val contextKnown = usage.contextLimitTokens > 0
    val color = if (contextKnown && usage.withinLimit) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
    val container = if (contextKnown && usage.withinLimit) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer
    Surface(
        color = container,
        shape = RoundedCornerShape(50),
        modifier = Modifier.height(32.dp).clickable(onClick = onSourcesClick)
    ) {
        Row(Modifier.padding(horizontal = 9.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(18.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(progress = if (contextKnown) usage.fraction else 0f, modifier = Modifier.size(17.dp), color = color, strokeWidth = 2.dp)
                Icon(Icons.Default.Language, null, tint = color, modifier = Modifier.size(10.dp))
            }
            Spacer(Modifier.width(6.dp))
            Text("${if (contextKnown) formatTokenCount(usage.usedTokens) else "…"} · ${usage.includedSources}/${usage.totalSources}", style = MaterialTheme.typography.labelSmall, color = color)
        }
    }
}

private fun formatTokenCount(tokens: Int): String = if (tokens >= 1_000) {
    val tenths = tokens / 100
    "${tenths / 10}.${tenths % 10}k"
} else tokens.toString()

private fun formatContextTokens(tokens: Int): String = "%,d".format(tokens).replace(',', ' ')

private fun messageUiKey(chatId: Long, index: Int, message: ChatMessage): String =
    "$chatId:$index:${message.fromUser}:${message.isSource}"

@Composable private fun SourceSelectionDialog(sources: List<ChatMessage>, usage: ContextUsage, onToggle: (String, Boolean) -> Unit, onDismiss: () -> Unit) {
    val contextKnown = usage.contextLimitTokens > 0
    val statusColor = if (contextKnown && usage.withinLimit) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Джерела цього чату") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(if (contextKnown) "Prompt: ${usage.usedTokens} / ${usage.availableTokens} токенів" else "Визначення контексту сервера…", color = statusColor, style = MaterialTheme.typography.labelLarge)
                LinearProgressIndicator(progress = if (contextKnown) usage.fraction else 0f, modifier = Modifier.fillMaxWidth(), color = statusColor)
                if (contextKnown) Text("n_ctx ${formatContextTokens(usage.contextLimitTokens)} − відповідь ${formatContextTokens(usage.outputReserveTokens)} − запас ${formatContextTokens(usage.safetyMarginTokens)}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (contextKnown && !usage.withinLimit) Text("Ліміт перевищено. Вимкніть одне або кілька джерел.", color = statusColor, style = MaterialTheme.typography.bodySmall)
                Text("Увімкнено ${usage.includedSources} з ${usage.totalSources}", style = MaterialTheme.typography.bodySmall)
                HorizontalDivider()
                LazyColumn(Modifier.heightIn(max = 320.dp)) {
                    items(sources, key = { it.displayText ?: it.text.hashCode().toString() }) { source ->
                        val url = source.displayText ?: return@items
                        Row(Modifier.fillMaxWidth().clickable { onToggle(url, !source.sourceEnabled) }.padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(checked = source.sourceEnabled, onCheckedChange = { onToggle(url, it) })
                            Spacer(Modifier.width(8.dp))
                            Text(url, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Готово") } }
    )
}

@Composable private fun MessageBubble(message: ChatMessage, stateKey: String, initiallyExpanded: Boolean = false, onExpandedChange: (Boolean) -> Unit = {}, onCopy: (String) -> Unit = {}, onSaveAsPrompt: (String) -> Unit = {}, onRegenerate: () -> Unit = {}) = Box(Modifier.fillMaxWidth(), contentAlignment = if (message.fromUser) Alignment.CenterEnd else Alignment.CenterStart) {
    if (message.displayText?.startsWith("stream:") == true && message.text.isBlank()) {
        Row(Modifier.padding(start = 8.dp, top = 6.dp, bottom = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.AutoAwesome, "Генерація відповіді", tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(9.dp))
            CircularProgressIndicator(modifier = Modifier.size(17.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.primary, trackColor = MaterialTheme.colorScheme.primaryContainer)
        }
        return@Box
    }
    val collapsedHeight = LocalConfiguration.current.screenHeightDp.dp * 0.5f
    val collapsedContentHeight = collapsedHeight - 8.dp
    val collapsedContentHeightPx = (collapsedContentHeight.value * androidx.compose.ui.platform.LocalDensity.current.density).toInt()
    var reachesCollapsedLimit by remember(message.displayText ?: message.text, collapsedContentHeightPx) { mutableStateOf(false) }
    var expanded by rememberSaveable(stateKey) { mutableStateOf(initiallyExpanded) }
    fun setExpanded(value: Boolean) {
        expanded = value
        onExpandedChange(value)
    }
    val canCollapse = !message.isSource && reachesCollapsedLimit
    val bubbleColor = when {
        message.isSource && message.sourceEnabled -> MaterialTheme.colorScheme.surface
        message.isSource -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.72f)
        message.fromUser -> MaterialTheme.colorScheme.secondaryContainer
        else -> MaterialTheme.colorScheme.surface
    }
    val bubbleShape = when {
        message.isSource -> RoundedCornerShape(14.dp)
        message.fromUser -> RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomStart = 20.dp, bottomEnd = 6.dp)
        else -> RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomStart = 6.dp, bottomEnd = 20.dp)
    }
    val bubbleBorder = when {
        message.isSource -> BorderStroke(1.dp, if (message.sourceEnabled) MaterialTheme.colorScheme.primary.copy(alpha = 0.28f) else MaterialTheme.colorScheme.outlineVariant)
        !message.fromUser -> BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.72f))
        else -> null
    }
    Column(horizontalAlignment = if (message.fromUser) Alignment.End else Alignment.Start, modifier = Modifier.fillMaxWidth()) {
    Box(modifier = Modifier.fillMaxWidth(if (message.isSource) 1f else if (message.fromUser) 0.86f else 0.94f)) {
    Surface(
        color = bubbleColor,
        shape = bubbleShape,
        border = bubbleBorder,
        tonalElevation = if (message.fromUser && !message.isSource) 0.dp else 1.dp,
        shadowElevation = if (!message.fromUser && !message.isSource) 1.dp else 0.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        if (message.isSource) {
            Row(Modifier.padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.Top) {
                Icon(Icons.Default.Add, null, tint = if (message.sourceEnabled) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 1.dp).size(17.dp))
                Spacer(Modifier.width(7.dp))
                Text(message.displayText ?: "URL не вказано", style = MaterialTheme.typography.bodySmall, color = if (message.sourceEnabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.68f), modifier = Modifier.weight(1f))
            }
        } else {
            Column {
                Box(
                    Modifier
                        .then(if (!expanded && canCollapse) Modifier.height(collapsedContentHeight).clipToBounds() else Modifier)
                        .onSizeChanged { if (it.height > collapsedContentHeightPx) reachesCollapsedLimit = true }
                ) {
                    Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
                        if (message.fromUser) Text(message.text, style = MaterialTheme.typography.bodyMedium)
                        else MarkdownText(message.text)
                        if (expanded && canCollapse) Spacer(Modifier.height(60.dp))
                    }
                }
            }
        }
    }
        if (canCollapse) {
            Row(
                Modifier
                    .align(Alignment.BottomCenter)
                    .zIndex(2f)
                    .fillMaxWidth()
                    .clip(bubbleShape)
                    .then(
                        if (!expanded) Modifier.background(
                            Brush.verticalGradient(listOf(Color.Transparent, bubbleColor.copy(alpha = 0.94f), bubbleColor))
                        ) else Modifier
                    )
                    .clickable { setExpanded(!expanded) }
                    .padding(top = 16.dp, bottom = 24.dp),
                horizontalArrangement = Arrangement.Center,
            ) {
                Icon(
                    if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    if (expanded) "Згорнути повідомлення" else "Розгорнути повідомлення",
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(20.dp),
                )
            }
        }
    }
    if (message.fromUser && !message.isSource) Row(Modifier.padding(top = 2.dp, end = 2.dp)) {
        val actionTint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.68f)
        IconButton(onClick = { onCopy(message.text) }, modifier = Modifier.size(30.dp)) { Icon(Icons.Default.ContentCopy, "Копіювати", tint = actionTint, modifier = Modifier.size(16.dp)) }
        IconButton(onClick = { onSaveAsPrompt(message.text) }, modifier = Modifier.size(30.dp)) { Icon(Icons.Default.BookmarkAdd, "Додати до prompts", tint = actionTint, modifier = Modifier.size(16.dp)) }
        IconButton(onClick = onRegenerate, modifier = Modifier.size(30.dp)) { Icon(Icons.Default.Refresh, "Перегенерувати відповідь", tint = actionTint, modifier = Modifier.size(16.dp)) }
    }
    }
}

@Composable private fun TextInputDialog(title: String, hint: String, allowClipboardPaste: Boolean = false, onDismiss: () -> Unit, onConfirm: (String) -> Unit) {
    val context = LocalContext.current
    var value by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            OutlinedTextField(
                value = value,
                onValueChange = { value = it },
                placeholder = { Text(hint) },
                trailingIcon = if (allowClipboardPaste) {
                    {
                        IconButton(onClick = {
                            val clipboard = context.getSystemService(android.content.ClipboardManager::class.java)
                            value = clipboard?.primaryClip?.getItemAt(0)?.coerceToText(context)?.toString().orEmpty()
                        }) { Icon(Icons.Default.ContentPaste, "Вставити з буфера") }
                    }
                } else null,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        },
        confirmButton = { TextButton(enabled = value.isNotBlank(), onClick = { onConfirm(value) }) { Text("Додати") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Скасувати") } }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable private fun SettingsScreen(initial: ServerConfig, portForProvider: (Provider) -> String, modelForProvider: (Provider) -> String, onBack: () -> Unit, onSave: (ServerConfig) -> Unit) {
    var host by remember { mutableStateOf(initial.host) }; var port by remember { mutableStateOf(initial.port) }
    var model by remember { mutableStateOf(initial.model) }; var provider by remember { mutableStateOf(initial.provider) }; var expanded by remember { mutableStateOf(false) }
    var contextTokens by remember { mutableStateOf(initial.contextTokens.toString()) }
    var editedPorts by remember { mutableStateOf(mapOf(initial.provider to initial.port)) }
    var editedModels by remember { mutableStateOf(mapOf(initial.provider to initial.model)) }
    var modelMenuExpanded by remember { mutableStateOf(false) }; var availableModels by remember { mutableStateOf(emptyList<String>()) }
    var loadingModels by remember { mutableStateOf(false) }; var modelsError by remember { mutableStateOf<String?>(null) }
    var detectedContextTokens by remember { mutableStateOf<Int?>(null) }
    var contextProbeError by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val reloadModels = {
        loadingModels = true; modelsError = null; contextProbeError = null
        scope.launch {
            val desired = contextTokens.toIntOrNull()?.coerceAtLeast(2_048) ?: 8_192
            val probeConfig = ServerConfig(host.trim(), port.trim(), provider, model.trim(), desired)
            LocalAiClient.models(probeConfig).onSuccess { loaded ->
                availableModels = loaded
                if (model.isBlank() && loaded.isNotEmpty()) {
                    model = loaded.first()
                    editedModels = editedModels + (provider to model)
                }
            }.onFailure { modelsError = it.message ?: "Не вдалося отримати список моделей" }
            LocalAiClient.actualContextTokens(probeConfig)
                .onSuccess { detectedContextTokens = it }
                .onFailure {
                    detectedContextTokens = null
                    contextProbeError = it.message ?: "Не вдалося визначити контекст сервера"
                }
            loadingModels = false
        }
        Unit
    }
    LaunchedEffect(provider) { reloadModels() }
    val configuredContext = contextTokens.toIntOrNull()
    val shownServerContext = if (provider == Provider.OLLAMA) configuredContext else detectedContextTokens
    val contextMatches = configuredContext != null && configuredContext == shownServerContext
    Scaffold(topBar = { TopAppBar(title = { Text("Налаштування з’єднання") }, navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "Назад") } }) }, bottomBar = { Surface(tonalElevation = 3.dp) { Button(onClick = { onSave(ServerConfig(host.trim(), port.trim(), provider, model.trim(), contextTokens.toIntOrNull()?.coerceAtLeast(2048) ?: 8192)) }, modifier = Modifier.fillMaxWidth().padding(16.dp)) { Text("Зберегти") } } }) { pad ->
        Column(Modifier.padding(pad).verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Локальний сервер", style = MaterialTheme.typography.titleMedium); Text("Телефон і сервер мають бути в одній Wi‑Fi мережі.", style = MaterialTheme.typography.bodySmall)
            OutlinedTextField(host, { host = it }, label = { Text("Хост / IP-адреса") }, placeholder = { Text("192.168.1.10") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            ExposedDropdownMenuBox(expanded, { expanded = !expanded }) { OutlinedTextField(provider.title, {}, readOnly = true, label = { Text("Провайдер") }, trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) }, modifier = Modifier.menuAnchor().fillMaxWidth())
                ExposedDropdownMenu(expanded, { expanded = false }) { Provider.entries.forEach { option -> DropdownMenuItem(text = { Text(option.title) }, onClick = {
                    editedPorts = editedPorts + (provider to port)
                    editedModels = editedModels + (provider to model)
                    provider = option
                    port = editedPorts[option] ?: portForProvider(option)
                    model = editedModels[option] ?: modelForProvider(option)
                    expanded = false
                    availableModels = emptyList()
                    modelsError = null
                    detectedContextTokens = null
                    contextProbeError = null
                }) } }
            }
            OutlinedTextField(port, { port = it.filter(Char::isDigit); editedPorts = editedPorts + (provider to it.filter(Char::isDigit)) }, label = { Text("Порт ${provider.title}") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Row(verticalAlignment = Alignment.CenterVertically) {
                ExposedDropdownMenuBox(modelMenuExpanded, { modelMenuExpanded = !modelMenuExpanded }, Modifier.weight(1f)) {
                    OutlinedTextField(model, { model = it; editedModels = editedModels + (provider to it) }, label = { Text("Модель") }, placeholder = { Text("Оберіть зі списку або введіть назву") }, trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(modelMenuExpanded) }, modifier = Modifier.menuAnchor().fillMaxWidth(), singleLine = true)
                    ExposedDropdownMenu(modelMenuExpanded, { modelMenuExpanded = false }) {
                        if (availableModels.isEmpty()) DropdownMenuItem(text = { Text("Список порожній — натисніть оновити") }, enabled = false, onClick = {})
                        else availableModels.forEach { item -> DropdownMenuItem(text = { Text(item) }, onClick = { model = item; editedModels = editedModels + (provider to item); modelMenuExpanded = false }) }
                    }
                }
                IconButton(onClick = reloadModels, enabled = !loadingModels) {
                    if (loadingModels) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp) else Icon(Icons.Default.Refresh, "Оновити список моделей")
                }
            }
            Text("Моделі ${provider.title}: ${if (availableModels.isEmpty()) "ще не завантажено" else "${availableModels.size} доступно"}", style = MaterialTheme.typography.labelMedium)
            modelsError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            OutlinedTextField(
                contextTokens,
                { contextTokens = it.filter(Char::isDigit) },
                label = { Text("Бажаний контекст (токени)") },
                supportingText = { Text(if (provider == Provider.OLLAMA) "Передається серверу як num_ctx." else "Для llama.cpp це бажане значення; фактичний n_ctx читається з /props.") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Surface(shape = RoundedCornerShape(14.dp), color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f)) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Row(Modifier.fillMaxWidth()) {
                        Text("Configured context", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
                        Text(configuredContext?.let(::formatContextTokens) ?: "—", style = MaterialTheme.typography.labelLarge)
                    }
                    Row(Modifier.fillMaxWidth()) {
                        Text("Server context", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
                        Text(
                            shownServerContext?.let(::formatContextTokens) ?: "невідомо",
                            style = MaterialTheme.typography.labelLarge,
                            color = if (shownServerContext == null || !contextMatches) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                        )
                        if (shownServerContext != null) Text(if (contextMatches) "  ✓" else "  ⚠", color = if (contextMatches) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error)
                    }
                    if (provider == Provider.LLAMA_CPP && shownServerContext != null && !contextMatches) {
                        Text("Бюджет джерел рахуватиметься від ${formatContextTokens(shownServerContext)}. Змініть запуск llama-server: --ctx-size ${configuredContext ?: shownServerContext}.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                    }
                    Text(
                        "Резерв відповіді: ${shownServerContext?.let { formatContextTokens(LocalAiClient.outputReserveTokens(it)) } ?: "—"} · запас безпеки: 256",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            contextProbeError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            HorizontalDivider(); Text(if (provider == Provider.OLLAMA) "Ollama API: /api/chat" else "llama.cpp OpenAI-сумісний API: /v1/chat/completions", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable private fun PromptsScreen(store: LocalStore, onBack: () -> Unit) {
    var prompts by remember { mutableStateOf(store.prompts()) }; var folders by remember { mutableStateOf(store.folders()) }
    var editor by remember { mutableStateOf<SavedPrompt?>(null) }; var folderDialog by remember { mutableStateOf(false) }
    Scaffold(topBar = { TopAppBar(title = { Text("Prompts") }, navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "Назад") } }, actions = { IconButton(onClick = { folderDialog = true }) { Icon(Icons.Default.CreateNewFolder, "Нова папка") } }) }, floatingActionButton = { FloatingActionButton(onClick = { editor = SavedPrompt(0, "", "", folders.firstOrNull() ?: "Загальні") }) { Icon(Icons.Default.Add, "Новий промпт") } }) { pad ->
        LazyColumn(Modifier.padding(pad).fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            folders.forEach { folder ->
                item { Text(folder, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold) }
                items(prompts.filter { it.folder == folder }, key = { it.id }) { prompt -> Card(Modifier.fillMaxWidth().clickable { editor = prompt }) { ListItem(headlineContent = { Text(prompt.title) }, supportingContent = { Text(prompt.body, maxLines = 2) }, trailingContent = { IconButton(onClick = { prompts = prompts.filterNot { it.id == prompt.id }; store.savePrompts(prompts) }) { Icon(Icons.Default.DeleteOutline, "Видалити") } }) } }
            }
            if (prompts.isEmpty()) item { Text("Створіть перший шаблон запиту або збережіть текст із чату.") }
        }
    }
    editor?.let { PromptEditor(it, folders, onDismiss = { editor = null }, onSave = { saved -> prompts = if (saved.id == 0L) prompts + saved.copy(id = System.currentTimeMillis()) else prompts.map { if (it.id == saved.id) saved else it }; store.savePrompts(prompts); editor = null }) }
    if (folderDialog) TextInputDialog("Нова папка", "Наприклад: Робота", onDismiss = { folderDialog = false }) { name -> folders = (folders + name.trim()).distinct().sorted(); store.saveFolders(folders.toSet()); folderDialog = false }
}

@Composable private fun PromptEditor(initial: SavedPrompt, folders: List<String>, onDismiss: () -> Unit, onSave: (SavedPrompt) -> Unit) {
    var title by remember { mutableStateOf(initial.title) }; var body by remember { mutableStateOf(initial.body) }; var folder by remember { mutableStateOf(initial.folder) }; var expanded by remember { mutableStateOf(false) }
    AlertDialog(onDismissRequest = onDismiss, title = { Text(if (initial.id == 0L) "Новий промпт" else "Редагувати промпт") }, text = { Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        OutlinedTextField(title, { title = it }, label = { Text("Назва") }, singleLine = true); OutlinedTextField(body, { body = it }, label = { Text("Текст промпту") }, minLines = 4)
        Box { OutlinedButton(onClick = { expanded = true }) { Text("Папка: $folder") }; DropdownMenu(expanded, { expanded = false }) { folders.forEach { option -> DropdownMenuItem(text = { Text(option) }, onClick = { folder = option; expanded = false }) } } }
    } }, confirmButton = { TextButton(enabled = title.isNotBlank() && body.isNotBlank(), onClick = { onSave(initial.copy(title = title, body = body, folder = folder)) }) { Text("Зберегти") } }, dismissButton = { TextButton(onClick = onDismiss) { Text("Скасувати") } })
}
