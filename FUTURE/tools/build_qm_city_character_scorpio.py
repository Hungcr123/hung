from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "character_animation" / "characters" / "character_bo_cap"
OUTPUT = ROOT / "FUTURE" / "web"
MOTION_CELL = (256, 256)
BASIC_CELL = (384, 256)
BURN_CELL = (256, 320)
ULTIMATE_CELL = (640, 640)
ULTIMATE_BURN_CELL = (256, 320)
ULTIMATE_FIXED_SCALE = 0.62
# Updated 2026-08-16: add transparent headroom for frame 5 without changing its scale or foot offset.
ULTIMATE_DESTINATION_GROUND = (320, 483)
# Frames 3-5 intentionally fly; anchor their ground circle instead of pulling the character back down.
ULTIMATE_SOURCE_GROUND_ANCHORS = (
    (525, 729),
    (535, 719),
    (535, 722),
    (535, 718),
    (535, 704),
    (540, 668),
)


def visible_alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").point(lambda alpha: 255 if alpha >= 12 else 0).getbbox()


# Added 2026-08-16: normalize one transparent source without moving its foot anchor.
def fitted_cell(path: Path, cell_size: tuple[int, int], max_size: tuple[int, int], flip: bool = False) -> Image.Image:
    source = Image.open(path).convert("RGBA")
    try:
        if flip:
            source = ImageOps.mirror(source)
        bbox = visible_alpha_bbox(source)
        cell = Image.new("RGBA", cell_size, (0, 0, 0, 0))
        if not bbox:
            return cell
        visual = source.crop(bbox)
        scale = min(max_size[0] / visual.width, max_size[1] / visual.height)
        visual = visual.resize(
            (max(1, round(visual.width * scale)), max(1, round(visual.height * scale))),
            Image.Resampling.LANCZOS,
        )
        cell.alpha_composite(visual, ((cell_size[0] - visual.width) // 2, cell_size[1] - visual.height))
        return cell
    finally:
        source.close()


# Added 2026-08-16: pack a bottom-aligned row for CSS step animation.
def build_row(paths: list[Path], output_name: str, cell_size: tuple[int, int], max_size: tuple[int, int]) -> Path:
    atlas = Image.new("RGBA", (cell_size[0] * len(paths), cell_size[1]), (0, 0, 0, 0))
    for index, path in enumerate(paths):
        atlas.alpha_composite(fitted_cell(path, cell_size, max_size), (index * cell_size[0], 0))
    output_path = OUTPUT / output_name
    atlas.save(output_path, optimize=True)
    return output_path


# Added 2026-08-16: keep Nộ ground origin fixed while its character intentionally rises in frames 3-5.
def build_ground_anchored_row(
    paths: list[Path],
    source_anchors: tuple[tuple[int, int], ...],
    output_name: str,
    cell_size: tuple[int, int],
    destination_anchor: tuple[int, int],
    scale: float,
) -> Path:
    if len(paths) != len(source_anchors):
        raise ValueError("Every anchored frame requires one ground coordinate")
    atlas = Image.new("RGBA", (cell_size[0] * len(paths), cell_size[1]), (0, 0, 0, 0))
    for index, (path, source_anchor) in enumerate(zip(paths, source_anchors)):
        with Image.open(path).convert("RGBA") as source:
            visual = source.resize(
                (round(source.width * scale), round(source.height * scale)),
                Image.Resampling.LANCZOS,
            )
        target_x = round(destination_anchor[0] - source_anchor[0] * scale)
        target_y = round(destination_anchor[1] - source_anchor[1] * scale)
        cell = Image.new("RGBA", cell_size, (0, 0, 0, 0))
        cell.alpha_composite(visual, (target_x, target_y))
        atlas.alpha_composite(cell, (index * cell_size[0], 0))
    output_path = OUTPUT / output_name
    atlas.save(output_path, optimize=True)
    return output_path


# Added 2026-08-16: crop square UI art while retaining transparent ornamental edges.
def build_square_asset(path: Path, output_name: str, size: int = 256) -> Path:
    source = Image.open(path).convert("RGBA")
    try:
        bbox = visible_alpha_bbox(source)
        visual = source.crop(bbox) if bbox else source
        visual.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(visual, ((size - visual.width) // 2, (size - visual.height) // 2))
        output_path = OUTPUT / output_name
        canvas.save(output_path, optimize=True)
        return output_path
    finally:
        source.close()


# Updated 2026-08-16: build Scorpio motion, Basic casts, homing effects, Nộ, avatar, and buttons.
def main() -> int:
    written = []
    written.append(build_row(
        [SOURCE / "đứng" / name for name in ("trước.png", "ngang.png", "sau.png")],
        "character_scorpio_stand_atlas.png",
        MOTION_CELL,
        (238, 248),
    ))
    motion_groups = (
        ("chạy trước", "down", 6),
        ("chạy ngang", "side", 5),
        ("chạy sau", "up", 6),
    )
    for directory, direction, count in motion_groups:
        paths = sorted((SOURCE / directory).glob("*.png"), key=lambda path: path.name.lower())
        if len(paths) != count:
            raise RuntimeError(f"Expected {count} Scorpio {direction} frames, found {len(paths)}")
        written.append(build_row(paths, f"character_scorpio_run_{direction}_atlas.png", MOTION_CELL, (248, 248)))

    # Added 2026-08-17: Training Field and Battle PvP use the weapon-ready
    # Scorpio locomotion while QM-City keeps the original peaceful atlas.
    written.append(build_row(
        [SOURCE / "đứng có vũ khí" / name for name in ("trước.png", "ngang.png", "sau.png")],
        "character_scorpio_weapon_stand_atlas.png",
        MOTION_CELL,
        (248, 248),
    ))
    weapon_motion_groups = (
        ("chạy trước có vũ khí", "down", 6),
        ("chạy ngang có vũ khí", "side", 6),
        ("chạy sau có vũ khí", "up", 8),
    )
    for directory, direction, count in weapon_motion_groups:
        paths = sorted((SOURCE / directory).glob("*.png"), key=lambda path: path.name.lower())
        if len(paths) != count:
            raise RuntimeError(f"Expected {count} weapon Scorpio {direction} frames, found {len(paths)}")
        written.append(build_row(paths, f"character_scorpio_weapon_run_{direction}_atlas.png", MOTION_CELL, (248, 248)))

    for skill_index, frame_count in ((1, 8), (2, 6), (3, 7)):
        paths = [SOURCE / f"basic skill {skill_index}" / f"{index}.png" for index in range(1, frame_count + 1)]
        written.append(build_row(paths, f"character_scorpio_basic_{skill_index}_atlas.png", BASIC_CELL, (376, 248)))

    for frame_index in (1, 2):
        written.append(build_square_asset(
            SOURCE / "tên bám mục tiêu" / f"{frame_index}.png",
            f"character_scorpio_homing_arrow_{frame_index}.png",
            256,
        ))
    burn_paths = [SOURCE / "burn basis" / f"{index}.png" for index in range(1, 8)]
    written.append(build_row(burn_paths, "character_scorpio_basic_burn_atlas.png", BURN_CELL, (248, 312)))
    ultimate_paths = [SOURCE / "skill nộ" / f"{index}.png" for index in range(1, 7)]
    written.append(build_ground_anchored_row(
        ultimate_paths,
        ULTIMATE_SOURCE_GROUND_ANCHORS,
        "character_scorpio_ultimate_atlas.png",
        ULTIMATE_CELL,
        ULTIMATE_DESTINATION_GROUND,
        ULTIMATE_FIXED_SCALE,
    ))
    ultimate_burn_one_paths = [SOURCE / "burn nộ 1" / f"{index}.png" for index in range(1, 9)]
    written.append(build_row(
        ultimate_burn_one_paths,
        "character_scorpio_ultimate_burn_1_atlas.png",
        ULTIMATE_BURN_CELL,
        (248, 312),
    ))
    ultimate_burn_two_paths = [SOURCE / "burn nộ 2" / f"{index}.png" for index in range(1, 9)]
    written.append(build_row(
        ultimate_burn_two_paths,
        "character_scorpio_ultimate_burn_2_atlas.png",
        ULTIMATE_BURN_CELL,
        (248, 312),
    ))
    written.append(build_square_asset(SOURCE / "avata.png", "character_scorpio_avatar.png", 256))
    for index in range(1, 11):
        written.append(build_square_asset(SOURCE / "nút skill" / f"{index}.png", f"character_scorpio_basic_skill_{index}.png", 256))
    written.append(build_square_asset(SOURCE / "nút skill" / "19.png", "character_scorpio_ultimate_skill_button.png", 256))

    for path in written:
        with Image.open(path) as image:
            print(f"wrote {path} ({image.width}x{image.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
