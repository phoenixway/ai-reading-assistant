package com.agent008

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily

private val AgentLightColorScheme = lightColorScheme(
    primary = Color(0xFF5064D9),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE7EBFF),
    onPrimaryContainer = Color(0xFF17245F),
    secondaryContainer = Color(0xFFE9EDFF),
    onSecondaryContainer = Color(0xFF202951),
    tertiaryContainer = Color(0xFFE0F3EF),
    onTertiaryContainer = Color(0xFF123C36),
    surface = Color(0xFFFFFFFF),
    surfaceVariant = Color(0xFFF0F2F7),
    background = Color(0xFFF8F9FC),
    onSurface = Color(0xFF1B1C22),
    onSurfaceVariant = Color(0xFF676A75),
    outline = Color(0xFF777A85),
    outlineVariant = Color(0xFFDDE0E8),
)

private val AgentDarkColorScheme = darkColorScheme(
    primary = Color(0xFFB9C3FF),
    onPrimary = Color(0xFF1B2B72),
    primaryContainer = Color(0xFF33458F),
    onPrimaryContainer = Color(0xFFE0E5FF),
    secondaryContainer = Color(0xFF343B59),
    onSecondaryContainer = Color(0xFFE0E5FF),
    tertiaryContainer = Color(0xFF214E48),
    onTertiaryContainer = Color(0xFFBCECE3),
    surface = Color(0xFF191A1F),
    surfaceVariant = Color(0xFF25262D),
    background = Color(0xFF111216),
    onSurface = Color(0xFFE5E1E9),
    onSurfaceVariant = Color(0xFFC5C5D0),
    outline = Color(0xFF90919C),
    outlineVariant = Color(0xFF3B3D46),
)

private val AgentTypography = Typography().run {
    copy(
        displayLarge = displayLarge.copy(fontFamily = FontFamily.SansSerif),
        headlineLarge = headlineLarge.copy(fontFamily = FontFamily.SansSerif),
        titleLarge = titleLarge.copy(fontFamily = FontFamily.SansSerif),
        titleMedium = titleMedium.copy(fontFamily = FontFamily.SansSerif),
        bodyLarge = bodyLarge.copy(fontFamily = FontFamily.SansSerif),
        bodyMedium = bodyMedium.copy(fontFamily = FontFamily.SansSerif),
        bodySmall = bodySmall.copy(fontFamily = FontFamily.SansSerif),
        labelLarge = labelLarge.copy(fontFamily = FontFamily.SansSerif),
        labelMedium = labelMedium.copy(fontFamily = FontFamily.SansSerif)
    )
}

@Composable
fun AgentTheme(content: @Composable () -> Unit) = MaterialTheme(
    colorScheme = if (isSystemInDarkTheme()) AgentDarkColorScheme else AgentLightColorScheme,
    typography = AgentTypography,
    content = content,
)
