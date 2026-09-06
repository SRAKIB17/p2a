import json
import os
import re
import sys
import shutil
import urllib.request
import urllib.error

# Windows কনসোলে UTF-8 এনকোডিং নিশ্চিত করা
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# yt-dlp ইমপোর্ট করার চেষ্টা
try:
    import yt_dlp
except ImportError:
    print("[!] 'yt-dlp' প্যাকেজটি ইনস্টল করা নেই!")
    print("অনুগ্রহ করে নিচের কমান্ডটি চালিয়ে yt-dlp ইনস্টল করুন:")
    print("  pip install yt-dlp")
    sys.exit(1)


def sanitize_filename(name: str) -> str:
    """Windows এবং অন্যান্য OS এর জন্য ইনভ্যালিড ক্যারেক্টার রিমুভ করে নিরাপদ ফাইলের নাম তৈরি করে।"""
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip().strip('.')
    return sanitized if sanitized else "untitled"


def find_ffmpeg() -> str | None:
    """FFmpeg এর লোকেশন শনাক্ত করে।"""
    # 1. System PATH or Project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffmpeg = os.path.join(script_dir, "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg

    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path

    # 2. Virtual environment Scripts
    venv_ffmpeg = os.path.join(script_dir, ".venv", "Scripts", "ffmpeg.exe")
    if os.path.exists(venv_ffmpeg):
        return venv_ffmpeg

    # 3. WinGet Packages directory
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_base = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
        if os.path.exists(winget_base):
            for root, _, files in os.walk(winget_base):
                if "ffmpeg.exe" in files:
                    return os.path.join(root, "ffmpeg.exe")

    return None


def extract_video_items(data):
    """JSON থেকে রিকার্সিভভাবে সব contents থেকে slug এবং title সংগ্রহ করে।"""
    items = []

    def traverse(node):
        if isinstance(node, dict):
            # If node has slug and type is video (or simply has slug inside contents list)
            if "slug" in node and node.get("slug"):
                node_type = node.get("type")
                has_subcontents = bool(node.get("contents"))
                
                # Check if it is a video leaf item
                if node_type == "video" or (not has_subcontents and node.get("order") is not None):
                    items.append({
                        "id": node.get("id"),
                        "title": node.get("title") or node.get("slug"),
                        "slug": node.get("slug"),
                        "order": node.get("order", len(items) + 1),
                        "type": node_type or "video"
                    })

            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    traverse(value)
        elif isinstance(node, list):
            for item in node:
                traverse(item)

    traverse(data)
    return items


def fetch_content_details(slug: str, headers: dict) -> dict | None:
    """P2A API থেকে নির্দিষ্ট slug এর কনটেন্ট ও ভিডিও লিংক নিয়ে আসে।"""
    url = f"https://p2a.academy/api/content/{slug}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data.get("data", {})
    except urllib.error.HTTPError as e:
        print(f"\n  [ERROR] HTTP {e.code}: {e.reason}")
        if e.code == 401:
            print("  [TIP] 401 Unauthorized! আপনার headers.json ফাইলে নতুন Token বা Cookie দিন।")
        return None
    except Exception as e:
        print(f"\n  [ERROR] এপিআই থেকে ডাটা আনা যায়নি: {e}")
        return None


def download_video_ytdlp(video_url: str, output_template: str, ffmpeg_path: str | None = None) -> bool:
    """yt-dlp দিয়ে ভিডিও ডাউনলোড করে।"""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': True,
        'noprogress': False,
        'js_runtimes': {'node': {}} if shutil.which("node") else {}
    }

    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            retcode = ydl.download([video_url])
            return retcode == 0
    except Exception as e:
        print(f"\n  [ERROR] ভিডিও ডাউনলোড ব্যর্থ: {e}")
        return False


def main():
    json_file = sys.argv[1] if len(sys.argv) > 1 else "video_data.json"
    if not os.path.exists(json_file) and os.path.exists("data.json"):
        json_file = "data.json"

    output_dir = "downloaded_videos"
    headers_file = "headers.json"

    print("=" * 65)
    print("        P2A Academy Video Auto Downloader")
    print("=" * 65)

    if not os.path.exists(json_file):
        print(f"[!] '{json_file}' ফাইলটি পাওয়া যায়নি!")
        print(f"অনুগ্রহ করে '{json_file}' ফাইল রাখুন অথবা কমান্ডের সাথে ফাইলের নাম দিন।")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"[!] JSON পার্স করতে সমস্যা হয়েছে: {e}")
            return

    # Headers setup
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://p2a.academy/",
        "Accept": "*/*",
        "Accept-Language": "bn,en-US;q=0.9,en;q=0.8"
    }

    if os.path.exists(headers_file):
        try:
            with open(headers_file, 'r', encoding='utf-8') as hf:
                custom_headers = json.load(hf)
                headers.update(custom_headers)
                print(f"[✓] '{headers_file}' থেকে Headers এবং Auth টোকেন লোড করা হয়েছে।")
        except Exception as e:
            print(f"[!] '{headers_file}' পড়তে সমস্যা হয়েছে: {e}")
    else:
        print(f"[!] সতর্কতা: '{headers_file}' পাওয়া যায়নি। ডিফল্ট হেডার দিয়ে চেষ্টা করা হচ্ছে...")

    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        print(f"[✓] FFmpeg পাওয়া গেছে: {ffmpeg_path}")
    else:
        print("[!] সতর্কতা: FFmpeg পাওয়া যায়নি। কিছু ভিডিওতে অডিও-ভিডিও মার্জে সমস্যা হতে পারে।")

    # Extract all video items
    items = extract_video_items(data)
    print(f"\n[+] মোট {len(items)} টি ভিডিও কনটেন্ট পাওয়া গেছে।\n")

    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    skip_count = 0
    fail_count = 0

    for idx, item in enumerate(items, 1):
        slug = item["slug"]
        raw_title = item.get("title") or slug
        clean_title = sanitize_filename(raw_title)

        expected_filename = f"{idx:02d}_{clean_title}.mp4"
        expected_path = os.path.join(output_dir, expected_filename)
        output_template = os.path.join(output_dir, f"{idx:02d}_{clean_title}.%(ext)s")

        print(f"[{idx}/{len(items)}] প্রক্রিয়াকরণ হচ্ছে: {raw_title}")
        print(f"  Slug: {slug}")

        # Check if already downloaded
        if os.path.exists(expected_path) and os.path.getsize(expected_path) > 1024 * 1024:
            print(f"  [✓] ফাইলটি ইতিমধ্যে ডাউনলোড করা আছে (Skipped): {expected_filename}")
            skip_count += 1
            print("-" * 55)
            continue

        # Step 1: Fetch content details from P2A API
        print("  -> এপিআই থেকে ভিডিও লিংক আনা হচ্ছে...")
        content_details = fetch_content_details(slug, headers)
        if not content_details:
            print(f"  [✗] {slug} এর জন্য তথ্য পাওয়া যায়নি!")
            fail_count += 1
            print("-" * 55)
            continue

        video_info = content_details.get("video")
        if not video_info or not isinstance(video_info, dict):
            print(f"  [✗] এই আইটেমে কোনো ভিডিও ডাটা পাওয়া যায়নি (Type: {content_details.get('type')})")
            fail_count += 1
            print("-" * 55)
            continue

        video_url = video_info.get("link") or video_info.get("embedded")
        source = video_info.get("source", "unknown")
        print(f"  -> Video Source: {source}")
        print(f"  -> Video URL: {video_url}")

        if not video_url:
            print("  [✗] কোনো সক্রিয় ভিডিও লিংক পাওয়া যায়নি!")
            fail_count += 1
            print("-" * 55)
            continue

        # Step 2: Download with yt-dlp
        print(f"  -> ডাউনলোড শুরু হচ্ছে: {expected_filename}")
        success = download_video_ytdlp(video_url, output_template, ffmpeg_path)

        if success:
            print(f"  [✓] সফলভাবে ডাউনলোড সম্পন্ন হয়েছে!")
            success_count += 1
        else:
            print(f"  [✗] ডাউনলোড ব্যর্থ হয়েছে!")
            fail_count += 1

        print("-" * 55)

    print("\n" + "=" * 65)
    print(f"সমাপ্ত! মোট: {len(items)} | সফল: {success_count} টি | স্কিপড: {skip_count} টি | ব্যর্থ: {fail_count} টি")
    print(f"ভিডিও ফোল্ডার: {os.path.abspath(output_dir)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
