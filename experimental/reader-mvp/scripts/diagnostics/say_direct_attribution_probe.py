from app.reader import (
    _say_content_bounds,
    _source_supports_speaker,
)


CASES = [
    (
        "mara-post-pronoun",
        (
            'Mara had told Levin twice that the eastern stair was sealed. '
            'On the third evening she found him testing the brass handle anyway. '
            '“My father welded it shut before he died,” she said. '
            'Levin stepped back, embarrassed, and apologized.'
        ),
        "Mara",
        "My father welded it shut before he died",
    ),
    (
        "nadia-post-pronoun",
        (
            'Nadia placed a silver key on the kitchen table. '
            '“This opens the archive room, not the cellar,” she told Olek. '
            'Olek thanked her but left the key where it was.'
        ),
        "Nadia",
        "This opens the archive room, not the cellar",
    ),
    (
        "olek-before-name",
        (
            'At dusk Olek met Petro beside the courtyard gate. '
            'He handed Petro the silver key and said, '
            '“Give this only to Nadia.” '
            'Petro nodded, hid the key inside his boot, '
            'and stayed by the gate while Olek walked away.'
        ),
        "Olek",
        "Give this only to Nadia.",
    ),
    (
        "dax-started",
        (
            'Dax started, “I thought the east room—” '
            'but Lora interrupted, “Not tonight.” '
            'He set the crate beside the furnace.'
        ),
        "Dax",
        "I thought the east room—",
    ),
    (
        "lora-interrupted",
        (
            'Dax started, “I thought the east room—” '
            'but Lora interrupted, “Not tonight.” '
            'He set the crate beside the furnace.'
        ),
        "Lora",
        "Not tonight",
    ),
]


for name, source, speaker, content in CASES:
    bounds = _say_content_bounds(
        source,
        content,
    )

    print()
    print("=" * 88)
    print(name)
    print("speaker:", speaker)
    print("content:", repr(content))
    print("bounds:", bounds)

    if bounds is None:
        print("supported: False")
        continue

    start, end = bounds

    before = source[
        max(0, start - 220):
        start
    ]

    after = source[
        end:
        end + 120
    ]

    matched = source[start:end]

    print("matched:", repr(matched))
    print("before :", repr(before))
    print("after  :", repr(after))
    print(
        "supported:",
        _source_supports_speaker(
            source,
            speaker,
            bounds,
        ),
    )
