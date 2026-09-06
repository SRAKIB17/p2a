import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function sanitizeFilename(name) {
    const sanitized = name.replace(/[<>:"/\\|?*]/g, '_').trim().replace(/\.+$/, '');
    return sanitized || 'untitled';
}

function extractVideoItems(data) {
    const items = [];
    function traverse(node) {
        if (node && typeof node === 'object') {
            if (Array.isArray(node)) {
                node.forEach(traverse);
            } else {
                if (node.slug && (node.type === 'video' || (!node.contents || node.contents.length === 0))) {
                    items.push({
                        id: node.id,
                        title: node.title || node.slug,
                        slug: node.slug,
                        order: node.order
                    });
                }
                for (const key of Object.keys(node)) {
                    traverse(node[key]);
                }
            }
        }
    }
    traverse(data);
    return items;
}

async function fetchContentDetails(slug, headers) {
    const url = `https://p2a.academy/api/content/${slug}`;
    try {
        const res = await fetch(url, { headers });
        if (!res.ok) {
            console.log(`\n  [ERROR] HTTP ${res.status}: ${res.statusText}`);
            if (res.status === 401) {
                console.log(`  [TIP] 401 Unauthorized! headers.json ফাইলে নতুন Token বা Cookie আপডেট করুন।`);
            }
            return null;
        }
        const json = await res.json();
        return json.data || null;
    } catch (err) {
        console.log(`\n  [ERROR] এপিআই কল ব্যর্থ: ${err.message}`);
        return null;
    }
}

function findFfmpeg() {
    const candidates = [
        path.join(__dirname, 'ffmpeg.exe'),
        path.join(__dirname, '.venv', 'Scripts', 'ffmpeg.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Microsoft', 'WinGet', 'Packages', 'yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe', 'ffmpeg-N-125875-g5d4d3bdc61-win64-gpl', 'bin', 'ffmpeg.exe')
    ];
    for (const c of candidates) {
        if (fs.existsSync(c)) {
            return path.dirname(c);
        }
    }
    return null;
}

function runYtDlp(videoUrl, outputTemplate) {
    return new Promise((resolve) => {
        const venvYtDlp = path.join(__dirname, '.venv', 'Scripts', 'yt-dlp.exe');
        const cmd = fs.existsSync(venvYtDlp) ? venvYtDlp : 'yt-dlp';

        const args = [
            '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '--merge-output-format', 'mp4',
            '--no-warnings',
            '--js-runtimes', 'node',
            '-o', outputTemplate
        ];

        const ffmpegDir = findFfmpeg();
        if (ffmpegDir) {
            args.push('--ffmpeg-location', ffmpegDir);
        }

        args.push(videoUrl);

        const proc = spawn(cmd, args, { stdio: 'inherit' });
        proc.on('close', (code) => {
            resolve(code === 0);
        });
        proc.on('error', (err) => {
            console.log(`  [ERROR] yt-dlp চালানো যায়নি: ${err.message}`);
            resolve(false);
        });
    });
}

async function main() {
    let jsonFile = process.argv[2] || 'video_data.json';
    if (!fs.existsSync(jsonFile) && fs.existsSync('data.json')) {
        jsonFile = 'data.json';
    }

    const outputDir = path.resolve(__dirname, 'downloaded_videos');
    const headersFile = path.resolve(__dirname, 'headers.json');

    console.log('='.repeat(65));
    console.log('       P2A Academy Video Auto Downloader (Node.js)');
    console.log('='.repeat(65));

    if (!fs.existsSync(jsonFile)) {
        console.log(`[!] '${jsonFile}' ফাইল পাওয়া যায়নি!`);
        return;
    }

    const data = JSON.parse(fs.readFileSync(jsonFile, 'utf-8'));
    const items = extractVideoItems(data);

    console.log(`\n[+] মোট ${items.length} টি ভিডিও কনটেন্ট পাওয়া গেছে।\n`);

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    let headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://p2a.academy/',
        'Accept': '*/*',
        'Accept-Language': 'bn,en-US;q=0.9,en;q=0.8'
    };

    if (fs.existsSync(headersFile)) {
        try {
            const customHeaders = JSON.parse(fs.readFileSync(headersFile, 'utf-8'));
            headers = { ...headers, ...customHeaders };
            console.log(`[✓] '${headersFile}' থেকে Headers এবং Auth টোকেন লোড করা হয়েছে।`);
        } catch (e) {
            console.log(`[!] headers.json পড়তে সমস্যা: ${e.message}`);
        }
    }

    let successCount = 0;
    let skipCount = 0;
    let failCount = 0;

    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const idx = i + 1;
        const cleanTitle = sanitizeFilename(item.title || item.slug);
        const expectedFilename = `${String(idx).padStart(2, '0')}_${cleanTitle}.mp4`;
        const expectedPath = path.join(outputDir, expectedFilename);
        const outputTemplate = path.join(outputDir, `${String(idx).padStart(2, '0')}_${cleanTitle}.%(ext)s`);

        console.log(`[${idx}/${items.length}] প্রক্রিয়াকরণ হচ্ছে: ${item.title}`);
        console.log(`  Slug: ${item.slug}`);

        if (fs.existsSync(expectedPath) && fs.statSync(expectedPath).size > 1024 * 1024) {
            console.log(`  [✓] ফাইলটি ইতিমধ্যে ডাউনলোড করা আছে (Skipped): ${expectedFilename}`);
            skipCount++;
            console.log('-'.repeat(55));
            continue;
        }

        console.log('  -> এপিআই থেকে ভিডিও লিংক আনা হচ্ছে...');
        const details = await fetchContentDetails(item.slug, headers);
        if (!details || !details.video) {
            console.log(`  [✗] কোনো ভিডিও তথ্য পাওয়া যায়নি!`);
            failCount++;
            console.log('-'.repeat(55));
            continue;
        }

        const videoUrl = details.video.link || details.video.embedded;
        console.log(`  -> Video Source: ${details.video.source || 'unknown'}`);
        console.log(`  -> Video URL: ${videoUrl}`);

        if (!videoUrl) {
            console.log('  [✗] কোনো ভিডিও URL পাওয়া যায়নি!');
            failCount++;
            console.log('-'.repeat(55));
            continue;
        }

        console.log(`  -> ডাউনলোড শুরু হচ্ছে: ${expectedFilename}`);
        const success = await runYtDlp(videoUrl, outputTemplate);

        if (success) {
            console.log(`  [✓] সফলভাবে ডাউনলোড সম্পন্ন হয়েছে!`);
            successCount++;
        } else {
            console.log(`  [✗] ডাউনলোড ব্যর্থ হয়েছে!`);
            failCount++;
        }

        console.log('-'.repeat(55));
    }

    console.log('\n' + '='.repeat(65));
    console.log(`সমাপ্ত! মোট: ${items.length} | সফল: ${successCount} টি | স্কিপড: ${skipCount} টি | ব্যর্থ: ${failCount} টি`);
    console.log(`ভিডিও ফোল্ডার: ${outputDir}`);
    console.log('='.repeat(65));
}

main();
