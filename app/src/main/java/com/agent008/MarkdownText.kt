package com.agent008

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mikepenz.markdown.m3.Markdown
import com.mikepenz.markdown.m3.markdownTypography
import com.mikepenz.markdown.model.markdownPadding

@Composable
fun MarkdownText(text: String, modifier: Modifier = Modifier) {
    val body = MaterialTheme.typography.bodyMedium.copy(
        fontSize = 14.sp,
        lineHeight = 20.sp,
    )
    fun heading(size: Int, lineHeight: Int) = body.copy(
        fontSize = size.sp,
        lineHeight = lineHeight.sp,
        fontWeight = FontWeight.SemiBold,
    )

    Markdown(
        content = text,
        modifier = modifier,
        padding = markdownPadding(
            list = 3.dp,
            listItemBottom = 1.dp,
        ),
        typography = markdownTypography(
            h1 = heading(19, 25),
            h2 = heading(17, 23),
            h3 = heading(16, 22),
            h4 = heading(15, 21),
            h5 = heading(14, 20),
            h6 = heading(14, 20),
            text = body,
            paragraph = body,
            ordered = body,
            bullet = body,
            list = body,
            quote = body,
            code = body.copy(fontFamily = FontFamily.Monospace),
        ),
    )
}
