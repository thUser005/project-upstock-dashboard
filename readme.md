🚀 Upstox GTT Engine – REST API

### A production-ready Flask-based REST API for placing, cancelling, and tracking Upstox GTT (Good Till Triggered) orders with:

### ✅ Auto strategy (Entry / Target / SL)

### 🔁 Manual override support

### 📊 Daily trade limits
 
### 🗂 MongoDB logging (requests, responses, errors)

### 🔐 Secure token loading (keys.json or .env)

### 📦 Features
 
### Auto GTT Strategy

### Entry = OPEN + OPEN × 0.04

### Target = ENTRY + ENTRY × 0.01

### Stop Loss = ENTRY - ENTRY × 0.01

### BUY / SELL supported

### Intraday (I) / Delivery (D)

### Daily trade limit enforced

### Force override available

### MongoDB-based audit trail

### ⚙️ Environment Setup
1️⃣ .env Variables
ACCESS_TOKEN=your_upstox_access_token
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net
MONGO_DB=upstox_gtt

### 2️⃣ Optional keys.json
{
  "access_token": "your_upstox_access_token"
}

### 
keys.json takes priority over .env

### ▶️ Run Server
python app.py

### 
Server starts at:

### http://localhost:5000

### 🩺 Health Check
GET /api/health

### URL

### http://localhost:5000/api/health

### 
Response

### {
  "status": "ok",
  "service": "Upstox GTT Engine",
  "today_trade_count": 1
}

### 📌 Place GTT Order
POST /api/gtt/place
GET /api/gtt/place

### URL

### http://localhost:5000/api/gtt/place

### ✅ Minimum Required Fields
Field	Type	Description
instrument	string	`NSE_EQ
symbol_key	string	NSE_EQ:IDEA
qty	int	Quantity
transaction_type	string	BUY or SELL
🔁 Auto Strategy (Recommended)

### Request

### {
  "instrument": "NSE_EQ|INE669E01016",
  "symbol_key": "NSE_EQ:IDEA",
  "qty": 10,
  "transaction_type": "BUY"
}

### 
Auto Calculation

### Entry  = Open + 4%
Target = Entry + 1%
SL     = Entry - 1%

### ✏️ Manual Override Example
{
  "instrument": "NSE_EQ|INE669E01016",
  "symbol_key": "NSE_EQ:IDEA",
  "qty": 10,
  "transaction_type": "BUY",

###   "entry_mode": "manual",
  "entry_value": 270,
  "target_type": "manual",
  "target_value": 273,
  "sl_type": "manual",
  "sl_value": 267
}

### ⚠️ Force Trade (Ignore Daily Limit)
{
  "instrument": "NSE_EQ|INE669E01016",
  "symbol_key": "NSE_EQ:IDEA",
  "qty": 10,
  "transaction_type": "BUY",
  "force": true
}

### ✅ Success Response
{
  "success": true,
  "gtt_id": "123456789",
  "status": "ACTIVE",
  "trade_count": 2,
  "request_id": "uuid"
}

### ❌ Cancel GTT Order
POST /api/gtt/cancel
GET /api/gtt/cancel

### URL

### http://localhost:5000/api/gtt/cancel

### 
Request

### {
  "gtt_id": "123456789"
}

### 
Response

### {
  "success": true,
  "gtt_id": "123456789",
  "status": "CANCELLED",
  "request_id": "uuid"
}

### 📋 List GTT Orders
GET /api/gtt/orders

### URL

### http://localhost:5000/api/gtt/orders

### 🔍 Filter by Status
http://localhost:5000/api/gtt/orders?status=ACTIVE
http://localhost:5000/api/gtt/orders?status=CANCELLED

### 📦 Response
{
  "success": true,
  "count": 1,
  "orders": [
    {
      "gtt_id": "123456789",
      "status": "ACTIVE",
      "placed_at": "2026-01-01T10:30:00",
      "cancelled_at": null,
      "request_id": "uuid"
    }
  ]
}

### 🗂 MongoDB Collections
Collection	Purpose
gtt_requests	Incoming API payloads
gtt_responses	Successful responses
gtt_errors	Errors + stack trace
trade_counters	Daily trade limit
🔒 Safety & Validation

### BUY → SL < ENTRY < TARGET

### SELL → TARGET < ENTRY < SL

### Invalid price structure ❌ rejected

### Market open price fallback → LTP

### 🧠 Recommended Usage

### Use auto mode for consistency

### Use force=true only for testing

### Monitor /api/health daily

### Run behind NGINX / Railway / Render in production

### 🧑‍💻 Author Notes

### Designed for intraday breakout GTT automation

### Fully compatible with Upstox V3 APIs

### Safe for concurrent API calls