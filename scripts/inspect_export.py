#!/usr/bin/env python3
"""唯讀檢查 Figma 插件匯出包；只解析資料，不執行 JSX 或連線下載。"""

import argparse
import base64
import binascii
from collections import Counter
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

MAX_SVG_BYTES = 256 * 1024 * 1024
MAX_METADATA_BYTES = 8 * 1024 * 1024
KEY = re.compile(r"f\d+_TID_\d+_\d+")
URL = re.compile(r"url\(\s*['\"]?#([^)'\"\s]+)['\"]?\s*\)")
XLINK = "{http://www.w3.org/1999/xlink}href"


def read_limited(path, limit):
    if path.stat().st_size > limit:
        raise ValueError(f"檔案超過大小限制：{path.name}")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"檔案超過大小限制：{path.name}")
    return data


def metadata(path):
    source = read_limited(path, MAX_METADATA_BYTES).decode("utf-8-sig")
    match = re.search(r"\bvar\s+BAKED_FIGMA_META\s*=\s*", source)
    if not match:
        raise ValueError("找不到 BAKED_FIGMA_META JSON；不會執行 JSX 取資料")
    records, _ = json.JSONDecoder().raw_decode(source, match.end())
    if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
        raise ValueError("BAKED_FIGMA_META 必須是 JSON 物件陣列")
    if any(r.get("segments") is not None and
           (not isinstance(r["segments"], list) or
            any(not isinstance(s, dict) for s in r["segments"])) for r in records):
        raise ValueError("metadata segments 必須是 JSON 物件陣列")
    return records


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def properties(element, inherited):
    result = dict(inherited)
    for name in ("font-family", "font-weight", "fill"):
        if name in element.attrib:
            result[name] = element.attrib[name]
    # 行內 style 的優先序高於 presentation attributes。
    for item in element.get("style", "").split(";"):
        if ":" in item:
            name, value = item.split(":", 1)
            if name.strip() in ("font-family", "font-weight", "fill", "filter"):
                result[name.strip()] = value.strip()
    return result


def image_status(element, directory):
    href = element.get("href", element.get(XLINK, ""))
    if not href:
        return "missing_href"
    if href.startswith("data:"):
        header, separator, payload = href.partition(",")
        if not separator or not header.startswith("data:image/") or not payload:
            return "invalid_embedded"
        if ";base64" in header:
            try:
                decoded = base64.b64decode(re.sub(r"\s+", "", payload), validate=True)
                if not decoded:
                    return "invalid_embedded"
            except (binascii.Error, ValueError):
                return "invalid_embedded"
        return "embedded_unverified_pixels"
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or href.startswith("/"):
        return "external_not_checked"
    if not parsed.path:
        return "fragment_not_checked"
    target = (directory / unquote(parsed.path)).resolve()
    # 不沿著相對路徑或符號連結探查匯出資料夾外的檔案。
    try:
        target.relative_to(directory.resolve())
    except ValueError:
        return "outside_export_not_checked"
    return "linked_file_exists" if target.is_file() else "linked_file_missing"


def inspect(svg_path, jsx_path=None):
    svg_path = Path(svg_path)
    data = read_limited(svg_path, MAX_SVG_BYTES).decode("utf-8-sig")
    # 不接受 DTD／自訂實體；ElementTree 也不會被用來解析外部資料。
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", data, re.I):
        raise ValueError("不接受含 DOCTYPE 或 ENTITY 的 SVG")
    root = ET.fromstring(data)
    if local_name(root.tag) != "svg":
        raise ValueError("根元素不是 svg")

    report = {
        "schema_version": 1,
        "mode": "read_only",
        "source_name": svg_path.name,
        "summary": {},
        "svg_fonts": [],
        "metadata_fonts": [],
        "font_manifest": [],
        "findings": [],
        "not_verified": [
            "字型是否已安裝，以及 Illustrator 實際套用的字型與字重",
            "圖片像素、色彩描述檔與實際外觀",
            "Illustrator 的可編輯性、工作區域尺寸及原生漸層／陰影",
            "AI 是否成功存檔並重新開啟",
        ],
    }

    def finding(code, level, count, message):
        if count:
            report["findings"].append({"code": code, "level": level,
                                       "count": count, "message": message})

    records = []
    if jsx_path:
        try:
            records = metadata(Path(jsx_path))
        except (ValueError, UnicodeError, OSError):
            finding("metadata_unreadable", "warning", 1,
                    "伴隨 JSX 的 JSON metadata 無法安全解析；不執行腳本，請檢查格式")
    else:
        finding("metadata_not_supplied", "info", 1,
                "未指定伴隨 JSX；不能檢查原始字體 metadata 對應")
    key_counts = Counter(r.get("k") for r in records if isinstance(r.get("k"), str))
    by_key = {r["k"]: r for r in records if isinstance(r.get("k"), str)
              and key_counts[r["k"]] == 1}
    finding("duplicate_metadata_keys", "error",
            sum(c > 1 for c in key_counts.values()), "metadata 有重複 ID，不應自動套用修復")
    expected = set()
    for record in records:
        for segment in [record] + (record.get("segments") or []):
            if isinstance(segment, dict) and isinstance(segment.get("ff"), str):
                expected.add((segment["ff"], str(segment.get("fs", ""))))
    report["metadata_fonts"] = [{"family": family, "style": style}
                                for family, style in sorted(expected)]
    manifest = svg_path.parent / "fonts.txt"
    if manifest.is_file():
        try:
            report["font_manifest"] = [line[2:].strip() for line in
                read_limited(manifest, MAX_METADATA_BYTES).decode("utf-8-sig").splitlines()
                if line.startswith("- ")]
        except (ValueError, UnicodeError, OSError):
            finding("manifest_unreadable", "warning", 1, "fonts.txt 無法讀取")

    ids = Counter(e.get("id") for e in root.iter() if e.get("id"))
    definitions = {e.get("id"): local_name(e.tag) for e in root.iter() if e.get("id")}
    gradients = {key for key, tag in definitions.items()
                 if tag in ("linearGradient", "radialGradient")}
    fonts, images = Counter(), Counter()
    frames, texts, blank, filtered, gradient_texts, unmapped, placeholders = (0,) * 7
    filtered_groups, used_keys = set(), set()
    refs, css_count, hidden_texts = set(), 0, 0
    # 使用顯式堆疊，避免深層 SVG 群組造成 Python 遞迴溢位。
    stack = [(root, {}, None, (), False)]
    while stack:
        element, inherited, parent_key, ancestor_filters, parent_hidden = stack.pop()
        tag = local_name(element.tag)
        props = properties(element, inherited)
        element_id = element.get("id", "")
        match = KEY.search(element_id)
        key = match.group(0) if match else parent_key
        filters = ancestor_filters
        own_filter = element.get("filter", "")
        style = dict(item.split(":", 1) for item in element.get("style", "").split(";")
                     if ":" in item)
        style = {k.strip(): v.strip() for k, v in style.items()}
        own_filter = style.get("filter", own_filter)
        if own_filter and own_filter != "none":
            filters += (element_id or f"anonymous-{id(element)}",)
        hidden = parent_hidden or style.get("display", element.get("display")) == "none"
        hidden = hidden or style.get("opacity", element.get("opacity")) in ("0", "0.0")
        if tag == "style":
            css_count += 1
        if tag == "g" and element_id.startswith("FRAME__"):
            frames += 1
        for value in element.attrib.values():
            refs.update(URL.findall(value))
        if tag == "image":
            images[image_status(element, svg_path.parent)] += 1
        if tag in ("text", "tspan") and props.get("font-family"):
            fonts[props["font-family"]] += 1
        if tag == "text":
            texts += 1
            content = "".join(element.itertext())
            if not content.strip():
                blank += 1
            if hidden or props.get("fill") == "none":
                hidden_texts += 1
            if filters:
                filtered += 1
                filtered_groups.update(filters)
            paint_refs = set(URL.findall(props.get("fill", "")))
            for descendant in element.iter():
                child_props = properties(descendant, props)
                paint_refs.update(URL.findall(child_props.get("fill", "")))
            if paint_refs & gradients:
                gradient_texts += 1
            if content.strip() and records:
                if key in by_key:
                    used_keys.add(key)
                    if (props.get("font-family", "").strip("'\"").lower() == "arial"
                            and isinstance(by_key[key].get("ff"), str)
                            and by_key[key]["ff"].lower() != "arial"):
                        placeholders += 1
                else:
                    unmapped += 1
        for child in reversed(list(element)):
            stack.append((child, props, key, filters, hidden))

    report["svg_fonts"] = sorted(fonts)
    report["summary"] = {
        "svg_text_elements": texts,
        "blank_text_elements": blank,
        "image_elements": sum(images.values()),
        "image_states": dict(sorted(images.items())),
        "frame_markers": frames,
        "gradient_definitions": len(gradients),
        "text_elements_with_filters": filtered,
        "filter_owners_affecting_text": len(filtered_groups),
        "text_elements_with_gradient_fill": gradient_texts,
        "metadata_records": len(records),
        "mapped_metadata_keys": len(used_keys),
    }
    finding("duplicate_svg_ids", "error", sum(c > 1 for c in ids.values()),
            "SVG ID 重複，URL 或 metadata 對應可能不可靠")
    finding("missing_url_targets", "error", len(refs - definitions.keys()),
            "SVG 的內部 URL 引用缺少目標定義")
    finding("linked_images_missing", "error", images["linked_file_missing"],
            "圖片相對連結不存在；先保留資料夾結構並修復連結")
    finding("invalid_embedded_images", "error", images["invalid_embedded"] + images["missing_href"],
            "圖片缺少 href 或嵌入資料格式不正確")
    unchecked = sum(images[k] for k in ("external_not_checked", "outside_export_not_checked",
                                        "fragment_not_checked"))
    finding("image_references_unchecked", "warning", unchecked,
            "外部或資料夾外的圖片引用未檢查；不連線、不探查外部路徑")
    finding("text_filter_risk", "warning", filtered,
            "文字受 SVG filter 影響；需在 Illustrator 測試，不能直接判定缺字或移除陰影")
    finding("text_gradient_risk", "warning", gradient_texts,
            "文字使用漸層；需驗證 Illustrator 實際填色，不自動改成近似顏色")
    finding("placeholder_font_suspected", "warning", placeholders,
            "SVG 為 Arial，但對應 metadata 宣告其他字體；可能是插件占位字體")
    finding("unmapped_text_metadata", "warning", unmapped,
            "非空白文字無唯一 metadata ID 對應；不要用猜測的字體覆寫")
    finding("explicitly_hidden_text", "warning", hidden_texts,
            "文字或祖先有 display:none、零透明度或文字 fill:none；需確認是否刻意隱藏")
    finding("css_styles_not_resolved", "warning", css_count,
            "含樣式表；此工具不計算 CSS 選擇器，字體與效果統計可能不完整")
    finding("no_frame_markers", "info", int(frames == 0),
            "未找到 FRAME__ 群組標記；不代表沒有版面，需另行辨識工作區域")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="匯出資料夾或指定 SVG")
    parser.add_argument("--svg", help="資料夾中有多個 SVG 時指定檔名")
    parser.add_argument("--jsx", type=Path, help="明確指定伴隨 JSX；只解析 JSON")
    parser.add_argument("--output", type=Path, help="另存 JSON；拒絕覆蓋既有檔案")
    args = parser.parse_args(argv)
    try:
        if args.source.is_dir():
            candidates = sorted(args.source.glob("*.svg"))
            svg = args.source / args.svg if args.svg else None
            if svg is None:
                if len(candidates) != 1:
                    raise ValueError("資料夾的 SVG 數量不是一個，請使用 --svg 明確指定")
                svg = candidates[0]
        else:
            if args.svg:
                raise ValueError("指定單一 SVG 時不使用 --svg")
            svg = args.source
        jsx = args.jsx
        companion = svg.parent / "01-create-artboards-and-merge-text.jsx"
        if jsx is None and companion.is_file():
            jsx = companion
        report = inspect(svg, jsx)
        output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            # 使用排他建立，不能誤覆蓋原始 SVG、JSX 或既有報告。
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(output)
        print(output, end="")
        return 2 if any(f["level"] == "error" for f in report["findings"]) else 0
    except (OSError, ValueError, ET.ParseError) as error:
        print(f"檢查失敗：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
