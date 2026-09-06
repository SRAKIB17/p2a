# P2A Academy PDF Downloader

এই প্রজেক্টটি দিয়ে আপনি `p2a.academy` এর কোর্স/কনটেন্ট JSON ফাইল থেকে স্বয়ংক্রিয়ভাবে সমস্ত PDF ডাউনলোড করতে পারবেন।

---

## 🚀 কীভাবে ব্যবহার করবেন

### ১. JSON ডেটা রাখা
আপনার দেওয়া JSON রেসপন্সটি [data.json](file:///f:/project/p2a/pdf/data.json) ফাইলে সেভ করা আছে। নতুন কোনো JSON আসলে তা `data.json` ফাইলে রিপ্লেস করুন।

### ২. অথেনটিকেশন / টোকেন যুক্ত করা (গুরুত্বপূর্ণ)
যেহেতু `p2a.academy` এর PDF প্রক্সি এপিআই (`https://p2a.academy/api/pdf-proxy?content={slug}`) অথেনটিকেশন ছাড়া **`401 Unauthorized`** দেয়, তাই ব্রাউজারের টোকেন প্রয়োজন:

1. আপনার ব্রাউজারে `p2a.academy` তে লগইন করুন।
2. কীবোর্ডে `F12` চেপে **Developer Tools** খুলুন এবং **Network** ট্যাবে যান।
3. যেকোনো PDF পেজ রিফ্রেশ করুন বা অপেন করুন।
4. Network ট্যাবে `pdf-proxy` বা যেকোনো রিকোয়েস্টে ক্লিক করে **Request Headers** থেকে:
   - `Authorization: Bearer eyJ...` (অথবা `Cookie: ...`) কপি করুন।
5. [headers.json.example](file:///f:/project/p2a/pdf/headers.json.example) ফাইলটিকে রিনেম করে `headers.json` বানিয়ে আপনার টোকেন পেস্ট করে দিন:
   ```json
   {
     "Authorization": "Bearer আপনার_টোকেন_এখানে",
     "Cookie": "আপনার_কুকিজ_এখানে"
   }
   ```

---

### ৩. স্ক্রিপ্ট রান করুন

#### Python দিয়ে:
```bash
python downloader.py
```
*(অন্য ফাইলের নাম দিতে চাইলে: `python downloader.py my_data.json`)*

#### অথবা Node.js দিয়ে:
```bash
node downloader.js
```

---

## 📁 ডাউনলোড ফোল্ডার
ডাউনলোড হওয়া সমস্ত ফাইল সুন্দরভাবে সিরিয়াল নম্বর ও টাইটেলসহ [downloaded_pdfs/](file:///f:/project/p2a/pdf/downloaded_pdfs) ফোল্ডারে সেভ হবে।
