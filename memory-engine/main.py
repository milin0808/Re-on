"""Run: python main.py --input data/sample_moments.json --output outputs/memories.json"""
import argparse
import json
from pathlib import Path
from models import ALGORITHM, ANALYSIS_TIMEZONE_NAME, ENGINE_VERSION, parse_moments
from sync import annotate_changes
from pattern_detector import DetectionConfig
from memory_generator import generate_memories

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="RE:ON Memory Engine MVP")
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "sample_moments.json", help="Moment JSON 파일")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "memories.json", help="Memory 출력 JSON 파일")
    parser.add_argument("--artist-min-count", type=int, default=3)
    parser.add_argument("--artist-min-share", type=float, default=0.4)
    parser.add_argument("--max-per-month", type=int, default=3)
    args = parser.parse_args()
    if not (0 <= args.artist_min_share <= 1):
        parser.error("--artist-min-share는 0에서 1 사이여야 합니다.")
    if args.artist_min_count < 1 or args.max_per_month < 1:
        parser.error("최소 횟수와 최대 생성 수는 1 이상이어야 합니다.")

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
        moments = parse_moments(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(1, f"입력 오류: {exc}\n")

    config = DetectionConfig(
        artist_min_count=args.artist_min_count,
        artist_min_share=args.artist_min_share,
        max_memories_per_month=args.max_per_month,
    )
    memories = annotate_changes(generate_memories(moments, config), {})
    result = {"meta": {"input_moments": len(moments), "generated_memories": len(memories),
                       "engine_version": ENGINE_VERSION, "algorithm": ALGORITHM,
                       "analysis_timezone": ANALYSIS_TIMEZONE_NAME}, "memories": memories}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"입력 Moment {len(moments)}개 → Memory {len(memories)}개 생성 완료")
    for m in memories:
        print(f" - [{m['type']}] {m['title']} ({len(m['moment_ids'])}개 Moment)")
    print(f"결과 파일: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
