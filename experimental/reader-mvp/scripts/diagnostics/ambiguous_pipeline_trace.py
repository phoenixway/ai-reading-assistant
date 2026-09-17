import runpy
import sys

from app.llama import LlamaClient


orig_chat = LlamaClient.chat
counter = 0


def traced_chat(
    self,
    messages,
    *args,
    **kwargs,
):
    global counter

    counter += 1

    output, elapsed = orig_chat(
        self,
        messages,
        *args,
        **kwargs,
    )

    system = next(
        (
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
        ),
        "",
    )

    user = next(
        (
            message.get("content", "")
            for message in reversed(messages)
            if message.get("role") == "user"
        ),
        "",
    )

    system_head = (
        system.strip().splitlines()[0]
        if system.strip()
        else "<NO SYSTEM>"
    )

    print()
    print("=" * 88)
    print(
        f"LLM CALL {counter} | "
        f"{elapsed:.2f}s"
    )
    print("SYSTEM:", system_head)
    print("-" * 88)
    print("USER:")
    print(user)
    print("-" * 88)
    print("OUTPUT:")
    print(output)
    print("=" * 88)

    return output, elapsed


LlamaClient.chat = traced_chat

sys.argv = [
    "scripts/benchmark_suite.py",
    "--case",
    "gen-ambiguous-pronoun",
]

runpy.run_path(
    "scripts/benchmark_suite.py",
    run_name="__main__",
)
