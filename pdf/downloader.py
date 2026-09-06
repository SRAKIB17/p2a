import json
import os
import re
import sys
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def sanitize_filename(name: str) -> str:
    """Windows এবং অন্যান্য OS এর জন্য ইনভ্যালিড ক্যারেক্টার রিমুভ করে নিরাপদ ফাইলের নাম তৈরি করে।"""
    # Replace invalid chars: < > : " / \ | ? *
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = sanitized.strip().strip('.')
    return sanitized if sanitized else "untitled"

def extract_pdf_items(data):
    """JSON থেকে রিকার্সিভভাবে সব contents থেকে slug এবং title সংগ্রহ করে।"""
    items = []

    def traverse(node):
        if isinstance(node, dict):
            # If node has slug and type is pdf (or just has slug)
            if "slug" in node and node.get("slug"):
                # Avoid the root object if it's just a category/section
                if node.get("type") == "pdf" or "contents" in node and not node["contents"]:
                    items.append({
                        "id": node.get("id"),
                        "title": node.get("title") or node.get("slug"),
                        "slug": node.get("slug"),
                        "order": node.get("order")
                    })

            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    traverse(value)
        elif isinstance(node, list):
            for item in node:
                traverse(item)

    traverse(data)
    return items

def download_file(url: str, output_path: str, headers: dict) -> bool:
    """URL থেকে ফাইল ডাউনলোড করে নির্দিষ্ট লোকেশনে সেভ করে।"""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            total_size = response.headers.get('content-length')
            total_size = int(total_size) if total_size else None
            
            # Content-type check
            content_type = response.headers.get('content-type', '')
            
            downloaded = 0
            chunk_size = 64 * 1024  # 64 KB
            
            with open(output_path, 'wb') as out_file:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        print(f"\r  Progress: {percent:5.1f}% ({downloaded / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB)", end="")
                    else:
                        print(f"\r  Downloaded: {downloaded / 1024:.1f} KB", end="")
            print()
            return True
    except urllib.error.HTTPError as e:
        print(f"\n  [ERROR] HTTP Error {e.code}: {e.reason}")
        if e.code == 401:
            print("  [TIP] 401 Unauthorized এসেছে। ব্রাউজার থেকে Authorization Token বা Cookie 'headers.json' ফাইলে যুক্ত করুন।")
        return False
    except Exception as e:
        print(f"\n  [ERROR] Failed to download: {e}")
        return False

def main():
    json_file = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    output_dir = "downloaded_pdfs"
    headers_file = "headers.json"

    print("=" * 60)
    print("      P2A Academy PDF Auto Downloader")
    print("=" * 60)

    if not os.path.exists(json_file):
        print(f"[!] '{json_file}' ফাইল পাওয়া যায়নি!")
        print(f"অনুগ্রহ করে '{json_file}' ফাইলে JSON ডাটা রাখুন অথবা কমান্ড লাইনে ফাইলের নাম দিন।")
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
        "Accept": "application/pdf,application/octet-stream,*/*"
    }

    if os.path.exists(headers_file):
        try:
            with open(headers_file, 'r', encoding='utf-8') as hf:
                custom_headers = json.load(hf)
                headers.update(custom_headers)
                print(f"[✓] '{headers_file}' থেকে কাস্টম Headers/Auth লোড করা হয়েছে।")
        except Exception as e:
            print(f"[!] '{headers_file}' পড়তে সমস্যা হয়েছে: {e}")

    # Extract all pdf items
    items = extract_pdf_items(data)
    print(f"\n[+] মোট {len(items)} টি PDF কনটেন্ট পাওয়া গেছে।\n")

    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    fail_count = 0

    for idx, item in enumerate(items, 1):
        slug = item["slug"]
        raw_title = item.get("title") or slug
        clean_title = sanitize_filename(raw_title)
        
        # Format filename with serial number
        filename = f"{idx:02d}_{clean_title}.pdf"
        output_path = os.path.join(output_dir, filename)
        
        pdf_url = f"https://p2a.academy/api/pdf-proxy?content={slug}"

        print(f"[{idx}/{len(items)}] ডাউনলোড হচ্ছে: {raw_title}")
        print(f"  URL: {pdf_url}")
        print(f"  File: {filename}")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            print("  [✓] ফাইলটি ইতিমধ্যে ডাউনলোড করা আছে (Skipped).")
            success_count += 1
            print("-" * 50)
            continue

        success = download_file(pdf_url, output_path, headers)
        if success:
            print(f"  [✓] সফলভাবে সেভ হয়েছে!")
            success_count += 1
        else:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            fail_count += 1

        print("-" * 50)

    print("\n" + "=" * 60)
    print(f"সমাপ্ত! সফল: {success_count} টি | ব্যর্থ: {fail_count} টি")
    print(f"ফাইলগুলো পাওয়া যাবে: {os.path.abspath(output_dir)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
