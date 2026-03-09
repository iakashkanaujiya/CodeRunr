import asyncio

from sqlalchemy import select

from db.session import AsyncSessionLocal
from db.models.language import Language


LANGUAGES = [
    {
        "id": 1,
        "name": "C",
        "version": "GCC 13.3.0",
        "source_file": "main.c",
        "compile_cmd": "gcc -o main %s -lm",
        "run_cmd": "./main",
    },
    {
        "id": 2,
        "name": "C++",
        "version": "GCC 13.3.0",
        "source_file": "main.cpp",
        "compile_cmd": "g++ -o main %s -std=c++17",
        "run_cmd": "./main",
    },
    {
        "id": 3,
        "name": "Python",
        "version": "3.12.3",
        "source_file": "main.py",
        "compile_cmd": "python3 -m py_compile %s",
        "run_cmd": "python3 main.py",
    },
    {
        "id": 4,
        "name": "JavaScript",
        "version": "Node.js 18.19.1",
        "source_file": "main.js",
        "compile_cmd": None,
        "run_cmd": "node main.js",
    },
    {
        "id": 5,
        "name": "TypeScript",
        "version": "5.7.3",
        "source_file": "main.ts",
        "compile_cmd": "tsc %s --outDir .",
        "run_cmd": "node main.js",
    },
    {
        "id": 6,
        "name": "Go",
        "version": "1.22.2",
        "source_file": "main.go",
        "compile_cmd": "go build -o main %s",
        "run_cmd": "./main",
    },
    {
        "id": 7,
        "name": "Rust",
        "version": "1.75.0",
        "source_file": "main.rs",
        "compile_cmd": "rustc -o main %s",
        "run_cmd": "./main",
    },
    {
        "id": 8,
        "name": "Java",
        "version": "OpenJDK 21.0.5",
        "source_file": "Main.java",
        "compile_cmd": "javac %s",
        "run_cmd": "java Main",
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Language.name))
        existing_names = set(existing.scalars().all())

        added = 0
        for lang in LANGUAGES:
            if lang["name"] in existing_names:
                print(f"  ⏭  {lang['name']} (already exists)")
                continue

            db.add(Language(**lang))
            added += 1
            print(f"  ✓  {lang['name']}")

        await db.commit()
        print(f"\nSeeded {added} language(s), skipped {len(LANGUAGES) - added}.")


if __name__ == "__main__":
    print("Seeding languages...\n")
    asyncio.run(seed())
