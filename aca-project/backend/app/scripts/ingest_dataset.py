from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import delete

from app.db.base import Base
from app.db.models import DatasetImage, DatasetSplit
from app.db.session import AsyncSessionLocal


IMG_EXTS = {'.png', '.jpg', '.jpeg', '.bmp'}


def iter_images(root: Path):
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            yield p


def parse_entry(root: Path, path: Path):
    # Expected: root/item/split/defect_type/(files)
    rel = path.relative_to(root)
    parts = rel.parts
    if len(parts) < 4:
        return None
    item, split, defect_type = parts[0], parts[1], parts[2]
    if split not in {'train', 'test', 'ground_truth'}:
        return None
    is_mask = split == 'ground_truth'
    return item, split, defect_type, is_mask


async def ingest(root: Path, clear: bool = False) -> dict:
    async with AsyncSessionLocal() as session:
        # Ensure tables exist (create_all)
        async with session.bind.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        if clear:
            await session.execute(delete(DatasetImage))
            await session.commit()

        count = 0
        for path in iter_images(root):
            parsed = parse_entry(root, path)
            if not parsed:
                continue
            item, split, defect_type, is_mask = parsed
            di = DatasetImage(
                item=item,
                split=DatasetSplit(split),
                defect_type=defect_type,
                file_path=str(path),
                is_mask=is_mask,
            )
            session.add(di)
            count += 1

            if count % 1000 == 0:
                await session.commit()
        await session.commit()

    return {'inserted': count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, help='dataset root (e.g., C:\\python_project\\image\\trainimage)')
    parser.add_argument('--clear', action='store_true', help='clear dataset_images table before insert')
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f'root not found: {root}')

    import asyncio

    result = asyncio.run(ingest(root=root, clear=args.clear))
    print(result)


if __name__ == '__main__':
    main()
