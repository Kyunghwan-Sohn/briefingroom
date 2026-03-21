import re
import zlib
import zipfile
from pathlib import Path

import olefile
import pdfplumber

from .config import PDF_DIR, TXT_DIR


def download_file(url, filename, session):
    path = PDF_DIR / filename
    if path.exists():
        print(f"    [스킵] {filename}")
        return path
    try:
        r = session.get(url, timeout=30, stream=True)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "html" in ct:
            print("    [스킵] HTML 응답")
            return None

        cd = r.headers.get("Content-Disposition", "")
        cd_name = ""
        m = re.search(r"filename[^=]*=([^;\n]+)", cd, re.I)
        if m:
            cd_name = m.group(1).strip().lower()
            stem = Path(filename).stem
            if cd_name.endswith(".pdf"):
                filename = stem + ".pdf"
            elif re.search(r"\.hwp", cd_name):
                filename = stem + (".hwpx" if cd_name.endswith(".hwpx") else ".hwp")
            path = PDF_DIR / filename

        if path.exists():
            print(f"    [스킵] {filename}")
            return path

        with open(path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"    저장: {filename} ({path.stat().st_size//1024}KB)")
        return path
    except Exception as e:
        print(f"    다운로드 오류: {e}")
        return None


def clean_hwp_text(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(path):
    try:
        texts = []
        with pdfplumber.open(path) as pdf:
            for pg in pdf.pages:
                t = pg.extract_text()
                if t:
                    texts.append(t)
        text = "\n".join(texts)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except Exception as e:
        print(f"    PDF 추출 오류: {e}")
        return ""


def extract_hwp(path):
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        if magic[:4] in (b"<!DO", b"<htm", b"<HTM", b"<HTM") or magic[:1] == b"<":
            print("    [스킵] HTML 응답")
            return ""
        if magic[:2] == b"PK":
            with zipfile.ZipFile(path) as z:
                files = z.namelist()
                if "Preview/PrvText.txt" in files:
                    text = z.read("Preview/PrvText.txt").decode("utf-8", errors="ignore")
                    return clean_hwp_text(text)
                sections = sorted(f for f in files if re.match(r"Contents/section\d+\.xml", f))
                parts = []
                for sec in sections:
                    xml = z.read(sec).decode("utf-8", errors="ignore")
                    parts.extend(re.findall(r"<hp:t[^>]*>([^<]+)</hp:t>", xml))
                return clean_hwp_text(" ".join(parts))
        ole = olefile.OleFileIO(str(path))
        if ole.exists("PrvText"):
            raw = ole.openstream("PrvText").read()
            text = raw.decode("utf-16-le", errors="ignore")
            ole.close()
            return clean_hwp_text(text)
        texts = []
        for i in range(10):
            sec = f"BodyText/Section{i}"
            if not ole.exists(sec):
                break
            raw = ole.openstream(sec).read()
            try:
                raw = zlib.decompress(raw, -15)
            except Exception:
                pass
            texts.append(raw.decode("utf-16-le", errors="ignore"))
        ole.close()
        return clean_hwp_text("\n".join(texts))
    except Exception as e:
        print(f"    HWP 추출 오류: {e}")
        return ""


def save_text(item, text):
    src = re.sub(r"[^\w가-힣]", "", item["source"])[:4]
    safe = re.sub(r"[^\w가-힣]", "_", item["title"])[:30]
    fname = f"{item['date']}_{src}_{safe}.txt"
    path = TXT_DIR / fname
    content = (
        f"[출처] {item['source']}\n[제목] {item['title']}\n"
        f"[날짜] {item['date']}\n[URL]  {item['url']}\n"
        f"{'─'*60}\n{text}\n"
    )
    path.write_text(content, encoding="utf-8")
    item["text_path"] = str(path)
    print(f"    텍스트 저장: {fname} ({len(text)}자)")
    return path
