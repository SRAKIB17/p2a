import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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
        const venvYtDlp = path.join(__dirname, 'video', '.venv', 'Scripts', 'yt-dlp.exe');
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
const url = "https://www.youtube.com/watch?v=mWXfYAnuEi0";
const output = "output.mp4";
runYtDlp(url, output);