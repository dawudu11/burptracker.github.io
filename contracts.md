# Burp Tracker App - Backend Integration Contracts

## Current Mock Data (to be replaced)

**mock.js handles:**
- Local storage of daily burp sessions
- Daily total time calculation
- Session history tracking
- Midnight reset logic
- Time formatting utilities

## API Contracts

### 1. Daily Burp Data Model
```
BurpSession {
  id: string (UUID)
  duration: number (milliseconds)
  timestamp: datetime
  user_id: string (for future multi-user support)
}

DailyStats {
  date: string (YYYY-MM-DD)
  total_time: number (milliseconds)
  session_count: number
  longest_session: number (milliseconds)
  sessions: BurpSession[]
}
```

### 2. Backend Endpoints

**GET /api/burp/today**
- Returns today's burp statistics
- Response: DailyStats object

**POST /api/burp/session**
- Records a new burp session
- Body: { duration: number }
- Response: Updated DailyStats object

**GET /api/burp/history/{days}**
- Returns historical data for past N days
- Response: DailyStats[]

## Backend Implementation Plan

1. **MongoDB Models:**
   - BurpSession collection with date indexing
   - Automatic date-based querying and aggregation

2. **Business Logic:**
   - Daily stats calculation via MongoDB aggregation
   - Timezone-aware midnight reset handling
   - Session validation (minimum duration > 100ms)

3. **API Features:**
   - Date-based data grouping
   - Automatic daily rollover at midnight
   - Real-time stats computation

## Frontend Integration Changes

**Replace in BurpRecorder.jsx:**
- `burpTracker.addBurpSession()` → `POST /api/burp/session`
- Remove mock.js dependency

**Replace in DailyStats.jsx:**
- `burpTracker.getTodayData()` → `GET /api/burp/today`
- Remove localStorage dependency

**Replace in App.js:**
- `burpTracker.checkMidnightReset()` → Periodic API polling
- Add error handling and loading states
- Replace all mock data calls with API calls

## Data Migration
- No migration needed (starts fresh with API)
- localStorage data remains for offline fallback if needed