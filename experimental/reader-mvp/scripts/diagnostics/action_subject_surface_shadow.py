from app.config import settings
from app.llama import LlamaClient
from app.reader import ACTION_COVERAGE_SYSTEM


OLD = (
    "- Use the explicit character name instead of a pronoun "
    "when the referent is unambiguous in the supplied paragraph."
)

NEW = (
    "- Preserve the grammatical subject expression used by the source. "
    "If the source action uses a pronoun such as he, she, they, or it, "
    "keep that pronoun. Never replace a subject pronoun with a character "
    "name in this pass. Subject coreference is not part of action extraction."
)

if OLD not in ACTION_COVERAGE_SYSTEM:
    raise SystemExit("subject rule anchor not found")

SYSTEM = ACTION_COVERAGE_SYSTEM.replace(
    OLD,
    NEW,
    1,
)


CASES = [
    (
        "ambiguous-he",
        """[P02] Marek and Pavel stood beside the gate. He nodded once. Neither man spoke.

[P03] A bell rang. Pavel entered the ticket booth while Marek remained beside the gate.

[P04] Marek opened the ledger and marked the time. He stayed beside the gate with the ledger open.""",
    ),
    (
        "pronoun-transfer-p2",
        """[P02] Maeve set a brass compass on a crate beside Ivo, a man in a dark coat. He snatched it, wrapped it in a scarf, and tossed it across the room to Lian, a woman waiting by the window. She caught the compass and slid it into her satchel.""",
    ),
    (
        "pronoun-transfer-p3",
        """[P03] A moment later Lian pulled the compass out, passed it to Oren, a man standing beside the west passage, and zipped the satchel shut. He clipped the compass to his belt and stepped into the west passage.""",
    ),
    (
        "interrupted-dax",
        """[P03] Dax started, “I thought the east room—” but Lora interrupted, “Not tonight.” He set the crate beside the furnace.""",
    ),
    (
        "shared-object",
        """[P03] Without stopping, Elena crossed the catwalk and returned the canister to Tomas. Tomas tucked it beneath his coat.""",
    ),
]


llama = LlamaClient()

for name, fragment in CASES:
    output, elapsed = llama.chat(
        [
            {
                "role": "system",
                "content": SYSTEM,
            },
            {
                "role": "user",
                "content": (
                    "Extract explicit material actions "
                    "from ONLY these paragraphs.\n\n"
                    + fragment
                ),
            },
        ],
        temperature=settings.extraction_temperature,
        seed=settings.extraction_seed,
        cache_prompt=False,
    )

    print()
    print("=" * 88)
    print(name, f"{elapsed:.2f}s")
    print("=" * 88)
    print(output)
