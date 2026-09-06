# P2A Academy Video Auto Downloader

এই টুলটি দিয়ে আপনি `p2a.academy` এর যেকোনো কোর্স বা সেকশনের JSON ডেটা থেকে স্বয়ংক্রিয়ভাবে slug সংগ্রহ করে এপিআই কল (`https://p2a.academy/api/content/${slug}`) করার মাধ্যমে আসল ভিডিও লিংক (YouTube, Vimeo, HLS, MP4 ইত্যাদি) বের করে সর্বোচ্চ কোয়ালিটিতে ভিডিও ডাউনলোড করতে পারবেন।

---

## 🚀 কীভাবে ব্যবহার করবেন

### ১. JSON ডেটা রাখা
আপনার সংগ্রহ করা কোর্সের JSON ডেটা [video_data.json](file:///f:/project/p2a/video/video_data.json) ফাইলে সেভ করুন। (অথবা নতুন যেকোনো নামের JSON ফাইল দিতে পারেন)।

JSON-এর ফরম্যাট সাধারণত এরকম হয়:
```json
{
  "id": 16200,
  "title": "Video Class",
  "contents": [
    {
      "id": 211981,
      "title": "Lecture-01: Percentage-1",
      "slug": "bank-math-graduation-lecture-01-percentage-1",
      "type": "video"
    }
  ]
}
```

---

### ২. অথেনটিকেশন / টোকেন যুক্ত করা
[headers.json](file:///f:/project/p2a/video/headers.json) ফাইলে আপনার ব্রাউজার থেকে নেওয়া টোকেন ও হেডারগুলো ইতিমধ্যে কনফিগার করে দেওয়া হয়েছে। 

ভবিষ্যতে যদি টোকেনের মেয়াদ শেষ হয়ে যায় (HTTP 401 আসে):
1. ব্রাউজারে `p2a.academy` তে লগইন করুন।
2. কীবোর্ডে `F12` চেপে **Developer Tools** এর **Network** ট্যাবে যান।
3. যেকোনো ভিডিও পেজে গিয়ে `/api/content/...` রিকোয়েস্ট থেকে **Request Headers** এর মানগুলো [headers.json](file:///f:/project/p2a/video/headers.json) এ আপডেট করুন:
   - `authorization`: `Bearer <YOUR_TOKEN>`
   - `cookie`: `_ga=...; token=...`
   - `x-app-key`: `...`
   - `x-secret-token`: `...`

---

### ৩. স্ক্রিপ্ট চালানো

#### সহজ উপায় (এক ক্লিকে):
সরাসরি **[run.bat](file:///f:/project/p2a/video/run.bat)** ফাইলে ডাবল ক্লিক করুন।

#### অথবা টার্মিনাল/কমান্ড লাইন দিয়ে:
```powershell
# ভার্চুয়াল এনভায়রনমেন্ট দিয়ে রান করুন:
.venv\Scripts\python downloader.py

# অথবা অন্য কোনো নির্দিষ্ট JSON ফাইলের জন্য:
.venv\Scripts\python downloader.py my_custom_data.json
```

---

## 📁 ডাউনলোড ফোল্ডার

- সমস্ত ভিডিও [downloaded_videos/](file:///f:/project/p2a/video/downloaded_videos) ফোল্ডারে সেভ হবে।
- ফাইলের নাম সুন্দরভাবে সিরিয়াল নম্বর ও লেকচার টাইটেলসহ সাজানো থাকবে (যেমন: `01_Lecture-01_ Percentage-1.mp4`)।
- **Smart Resume**: কোনো ভিডিও ইতিমধ্যে ডাউনলোড করা থাকলে তা পুনরায় ডাউনলোড না করে স্বয়ংক্রিয়ভাবে স্কিপ করবে।
