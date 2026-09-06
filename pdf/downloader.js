import fs from 'fs';
import path from 'path';
import https from 'https';

function sanitizeFilename(name) {
    const sanitized = name.replace(/[<>:"/\\|?*]/g, '_').trim().replace(/\.+$/, '');
    return sanitized || 'untitled';
}

function extractPdfItems(data) {
    const items = [];
    function traverse(node) {
        if (node && typeof node === 'object') {
            if (Array.isArray(node)) {
                node.forEach(traverse);
            } else {
                if (node.slug && (node.type === 'pdf' || (node.contents && node.contents.length === 0))) {
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

function downloadFile(url, outputPath, headers) {
    return new Promise((resolve) => {
        const parsedUrl = new URL(url);
        const req = https.get(parsedUrl, { headers }, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                // Handle redirect
                return downloadFile(res.headers.location, outputPath, headers).then(resolve);
            }

            if (res.statusCode !== 200) {
                console.log(`\n  [ERROR] HTTP Error ${res.statusCode}: ${res.statusMessage}`);
                if (res.statusCode === 401) {
                    console.log(`  [TIP] 401 Unauthorized! Authorization header বা Cookie সেট করুন।`);
                }
                res.resume();
                return resolve(false);
            }

            const totalSize = parseInt(res.headers['content-length'] || '0', 10);
            let downloaded = 0;
            const fileStream = fs.createWriteStream(outputPath);

            res.on('data', (chunk) => {
                downloaded += chunk.length;
                if (totalSize > 0) {
                    const percent = ((downloaded / totalSize) * 100).toFixed(1);
                    process.stdout.write(`\r  Progress: ${percent}% (${(downloaded / 1048576).toFixed(2)} MB / ${(totalSize / 1048576).toFixed(2)} MB)`);
                } else {
                    process.stdout.write(`\r  Downloaded: ${(downloaded / 1024).toFixed(1)} KB`);
                }
            });

            res.pipe(fileStream);

            fileStream.on('finish', () => {
                fileStream.close();
                console.log();
                resolve(true);
            });

            fileStream.on('error', (err) => {
                fs.unlink(outputPath, () => {});
                console.log(`\n  [ERROR] File write error: ${err.message}`);
                resolve(false);
            });
        });

        req.on('error', (err) => {
            console.log(`\n  [ERROR] Request failed: ${err.message}`);
            resolve(false);
        });
    });
}

async function main() {
    const jsonFile = process.argv[2] || 'data.json';
    const outputDir = path.resolve('downloaded_pdfs');
    const headersFile = path.resolve('headers.json');

    console.log('='.repeat(60));
    console.log('      P2A Academy PDF Downloader (Node.js)');
    console.log('='.repeat(60));

    if (!fs.existsSync(jsonFile)) {
        console.log(`[!] '${jsonFile}' ফাইল পাওয়া যায়নি!`);
        return;
    }

    const data = JSON.parse(fs.readFileSync(jsonFile, 'utf-8'));
    const items = extractPdfItems(data);

    console.log(`\n[+] মোট ${items.length} টি PDF কনটেন্ট পাওয়া গেছে।\n`);

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://p2a.academy/',
        'Accept': 'application/pdf,application/octet-stream,*/*'
    };

    if (fs.existsSync(headersFile)) {
        try {
            const customHeaders = JSON.parse(fs.readFileSync(headersFile, 'utf-8'));
            Object.assign(headers, customHeaders);
            console.log(`[✓] '${headersFile}' থেকে Headers/Auth যুক্ত করা হয়েছে।`);
        } catch (e) {
            console.log(`[!] headers.json পার্স করতে সমস্যা: ${e.message}`);
        }
    }

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const idx = i + 1;
        const cleanTitle = sanitizeFilename(item.title || item.slug);
        const fileName = `${String(idx).padStart(2, '0')}_${cleanTitle}.pdf`;
        const outputPath = path.join(outputDir, fileName);
        const pdfUrl = `https://p2a.academy/api/pdf-proxy?content=${item.slug}`;

        console.log(`[${idx}/${items.length}] ডাউনলোড হচ্ছে: ${item.title}`);
        console.log(`  URL: ${pdfUrl}`);
        console.log(`  File: ${fileName}`);

        if (fs.existsSync(outputPath) && fs.statSync(outputPath).size > 1024) {
            console.log(`  [✓] ফাইলটি ইতিমধ্যে ডাউনলোড করা আছে (Skipped).`);
            successCount++;
            console.log('-'.repeat(50));
            continue;
        }

        const success = await downloadFile(pdfUrl, outputPath, headers);
        if (success) {
            console.log(`  [✓] সফলভাবে সেভ হয়েছে!`);
            successCount++;
        } else {
            if (fs.existsSync(outputPath)) {
                try { fs.unlinkSync(outputPath); } catch (_) {}
            }
            failCount++;
        }
        console.log('-'.repeat(50));
    }

    console.log('\n' + '='.repeat(60));
    console.log(`সমাপ্ত! সফল: ${successCount} টি | ব্যর্থ: ${failCount} টি`);
    console.log(`ফাইলগুলো পাওয়া যাবে: ${outputDir}`);
    console.log('='.repeat(60));
}

main();
