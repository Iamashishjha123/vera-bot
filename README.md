# 🚀 Merchant Growth AI Assistant

A FastAPI-based **AI decision engine** that helps local businesses improve growth by analyzing performance, customer behavior, and market signals, then generating **actionable, high-conversion messages**.

---

## 💡 What it does

- Identifies key business problems (low CTR, drop in calls, poor reviews)
- Recommends **specific actions** (offers, campaigns, engagement)
- Generates **ready-to-send messages** with clear CTAs
- Handles **customer communication** (recall, winback, reminders)

---

## 🧠 Key Highlights

- 📊 **Data-driven decisions** using merchant performance, signals, and triggers  
- 🏷️ **Category-aware strategies** (dentists, salons, gyms, etc.)  
- ⚡ **Prioritizes high-impact actions** using urgency-based trigger sorting  
- 🚫 **Prevents spam** using suppression logic  
- 💬 **Conversation-ready** with YES/NO interaction flow  

---

## 🏗️ Architecture


Context (merchant + trigger + customer)
↓
FastAPI backend
↓
Decision engine (compose)
↓
Structured output (message + CTA + rationale)


---

## 🔌 Core APIs

| Endpoint | Description |
|--------|------------|
| `GET /v1/healthz` | Health check |
| `GET /v1/metadata` | Bot metadata |
| `POST /v1/context` | Ingest merchant/category/customer/trigger data |
| `POST /v1/tick` | Generate actions (main logic) |
| `POST /v1/reply` | Handle user responses |

---

## 🌐 Live Demo

**API Base URL:**  

https://YOUR-RENDER-URL.onrender.com


**Swagger Docs:**  

https://YOUR-RENDER-URL.onrender.com/docs


---

## 🧪 Example Output

> Calls dropped 50% in the last 7 days.  
> Current: 1000 views → 5 calls (CTR 2%).  
> Issue: no active offer.  
>
> Quick fix: launch “Dental Cleaning @ ₹299” + one post.  
> Reply YES — I’ll set it up.

---

## ⚙️ Tech Stack

- Python  
- FastAPI  
- Render (deployment)

---

## 🚀 Run Locally

```bash
git clone <your-repo-url>
cd vera-bot

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python -m uvicorn server:app --reload --port 8080
