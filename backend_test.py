#!/usr/bin/env python3
"""
Backend API Test Suite for Burp Tracker
Tests all backend endpoints and database integration
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import sys

# Get the backend URL from frontend .env file
def get_backend_url():
    """Get backend URL from frontend .env file"""
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        print("❌ Frontend .env file not found")
        return None
    return None

class BurpTrackerAPITest:
    def __init__(self):
        self.base_url = get_backend_url()
        if not self.base_url:
            raise Exception("Could not get backend URL from frontend/.env")
        
        self.api_url = f"{self.base_url}/api"
        self.session = None
        self.test_results = []
        
    async def setup(self):
        """Setup test session"""
        self.session = aiohttp.ClientSession()
        print(f"🔧 Testing backend at: {self.api_url}")
        
    async def cleanup(self):
        """Cleanup test session"""
        if self.session:
            await self.session.close()
            
    def log_test(self, test_name, success, message="", details=None):
        """Log test result"""
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details
        })
        
    async def test_health_check(self):
        """Test GET /api/ endpoint"""
        try:
            async with self.session.get(f"{self.api_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    if "message" in data and "Burp Tracker API" in data["message"]:
                        self.log_test("Health Check", True, "API is responding correctly")
                        return True
                    else:
                        self.log_test("Health Check", False, "Unexpected response format", data)
                        return False
                else:
                    self.log_test("Health Check", False, f"HTTP {response.status}", await response.text())
                    return False
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
            return False
            
    async def test_record_burp_session(self, duration=2500):
        """Test POST /api/burp/session endpoint"""
        try:
            payload = {"duration": duration}
            async with self.session.post(
                f"{self.api_url}/burp/session",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and "data" in data:
                        stats = data["data"]
                        expected_fields = ["date", "total_time", "session_count", "longest_session", "average_session", "sessions"]
                        if all(field in stats for field in expected_fields):
                            self.log_test(
                                f"Record Burp Session ({duration}ms)", 
                                True, 
                                f"Session recorded successfully. Count: {stats['session_count']}, Total: {stats['total_time']}ms"
                            )
                            return data
                        else:
                            self.log_test("Record Burp Session", False, "Missing fields in response", stats)
                            return None
                    else:
                        self.log_test("Record Burp Session", False, "Invalid response format", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("Record Burp Session", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("Record Burp Session", False, f"Request error: {str(e)}")
            return None
            
    async def test_get_today_stats(self):
        """Test GET /api/burp/today endpoint"""
        try:
            async with self.session.get(f"{self.api_url}/burp/today") as response:
                if response.status == 200:
                    data = await response.json()
                    expected_fields = ["date", "total_time", "session_count", "longest_session", "average_session", "sessions"]
                    if all(field in data for field in expected_fields):
                        self.log_test(
                            "Get Today Stats", 
                            True, 
                            f"Today's stats retrieved. Sessions: {data['session_count']}, Total: {data['total_time']}ms"
                        )
                        return data
                    else:
                        self.log_test("Get Today Stats", False, "Missing fields in response", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("Get Today Stats", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("Get Today Stats", False, f"Request error: {str(e)}")
            return None
            
    async def test_invalid_duration(self):
        """Test error handling for invalid duration (< 100ms)"""
        try:
            payload = {"duration": 50}  # Below minimum
            async with self.session.post(
                f"{self.api_url}/burp/session",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    if "too short" in error_data.get("detail", "").lower():
                        self.log_test("Invalid Duration Handling", True, "Correctly rejected duration < 100ms")
                        return True
                    else:
                        self.log_test("Invalid Duration Handling", False, "Wrong error message", error_data)
                        return False
                else:
                    self.log_test("Invalid Duration Handling", False, f"Expected 400, got {response.status}")
                    return False
        except Exception as e:
            self.log_test("Invalid Duration Handling", False, f"Request error: {str(e)}")
            return False
            
    async def test_history_endpoint(self, days=7):
        """Test GET /api/burp/history/{days} endpoint"""
        try:
            async with self.session.get(f"{self.api_url}/burp/history/{days}") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and "data" in data:
                        history = data["data"]
                        if isinstance(history, list) and len(history) <= days:
                            # Check if each day has the expected structure
                            valid_structure = True
                            for day_stats in history:
                                expected_fields = ["date", "total_time", "session_count", "longest_session", "average_session", "sessions"]
                                if not all(field in day_stats for field in expected_fields):
                                    valid_structure = False
                                    break
                            
                            if valid_structure:
                                self.log_test(
                                    f"History Endpoint ({days} days)", 
                                    True, 
                                    f"Retrieved {len(history)} days of history"
                                )
                                return data
                            else:
                                self.log_test("History Endpoint", False, "Invalid day structure in history")
                                return None
                        else:
                            self.log_test("History Endpoint", False, f"Expected list with max {days} items, got {type(history)}")
                            return None
                    else:
                        self.log_test("History Endpoint", False, "Invalid response format", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("History Endpoint", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("History Endpoint", False, f"Request error: {str(e)}")
            return None
            
    async def test_multiple_sessions_totals(self):
        """Test multiple burp sessions and verify totals are calculated correctly"""
        print("\n🧪 Testing multiple sessions and total calculations...")
        
        # Get initial stats
        initial_stats = await self.test_get_today_stats()
        if not initial_stats:
            self.log_test("Multiple Sessions Setup", False, "Could not get initial stats")
            return False
            
        initial_count = initial_stats.get("session_count", 0)
        initial_total = initial_stats.get("total_time", 0)
        
        # Record multiple sessions
        test_durations = [1500, 2000, 3000, 1200]
        expected_additional_total = sum(test_durations)
        
        for duration in test_durations:
            result = await self.test_record_burp_session(duration)
            if not result:
                self.log_test("Multiple Sessions", False, f"Failed to record session with duration {duration}ms")
                return False
                
        # Get final stats and verify
        final_stats = await self.test_get_today_stats()
        if not final_stats:
            self.log_test("Multiple Sessions Verification", False, "Could not get final stats")
            return False
            
        final_count = final_stats.get("session_count", 0)
        final_total = final_stats.get("total_time", 0)
        
        expected_count = initial_count + len(test_durations)
        expected_total = initial_total + expected_additional_total
        
        if final_count == expected_count and final_total == expected_total:
            self.log_test(
                "Multiple Sessions Totals", 
                True, 
                f"Totals calculated correctly. Sessions: {final_count}, Total: {final_total}ms"
            )
            return True
        else:
            self.log_test(
                "Multiple Sessions Totals", 
                False, 
                f"Incorrect totals. Expected: {expected_count} sessions, {expected_total}ms. Got: {final_count} sessions, {final_total}ms"
            )
            return False

    # ========== MULTIPLAYER TESTS ==========
    
    async def test_create_user(self, username="TestPlayer"):
        """Test POST /api/user/create endpoint"""
        try:
            payload = {"username": username}
            async with self.session.post(
                f"{self.api_url}/user/create",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and "user" in data:
                        user = data["user"]
                        expected_fields = ["id", "username", "created_at"]
                        if all(field in user for field in expected_fields):
                            self.log_test(
                                f"Create User ({username})", 
                                True, 
                                f"User created successfully. ID: {user['id']}"
                            )
                            return data
                        else:
                            self.log_test("Create User", False, "Missing fields in user response", user)
                            return None
                    else:
                        self.log_test("Create User", False, "Invalid response format", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("Create User", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("Create User", False, f"Request error: {str(e)}")
            return None

    async def test_create_group(self, group_name="Test Burp Squad", creator_username="TestPlayer"):
        """Test POST /api/group/create endpoint"""
        try:
            payload = {"name": group_name, "creator_username": creator_username}
            async with self.session.post(
                f"{self.api_url}/group/create",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and "group" in data:
                        group = data["group"]
                        expected_fields = ["id", "name", "creator_id", "invite_code", "members", "created_at"]
                        if all(field in group for field in expected_fields):
                            if len(group["invite_code"]) == 6:
                                self.log_test(
                                    f"Create Group ({group_name})", 
                                    True, 
                                    f"Group created successfully. Invite code: {group['invite_code']}"
                                )
                                return data
                            else:
                                self.log_test("Create Group", False, f"Invalid invite code length: {len(group['invite_code'])}")
                                return None
                        else:
                            self.log_test("Create Group", False, "Missing fields in group response", group)
                            return None
                    else:
                        self.log_test("Create Group", False, "Invalid response format", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("Create Group", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("Create Group", False, f"Request error: {str(e)}")
            return None

    async def test_join_group(self, invite_code, username="Player2"):
        """Test POST /api/group/join endpoint"""
        try:
            payload = {"invite_code": invite_code, "username": username}
            async with self.session.post(
                f"{self.api_url}/group/join",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and "group" in data and "user" in data:
                        user = data["user"]
                        group = data["group"]

                        if user["username"] == username and user["id"] in group["members"]:
                            self.log_test(
                                f"Join Group ({username})", 
                                True, 
                                f"User joined group successfully. Group has {len(group['members'])} members"
                            )
                            return data
                        else:
                            self.log_test("Join Group", False, f"User not properly added to group members. User ID: {user['id']}, Members: {group['members']}")
                            return None
                    else:
                        self.log_test("Join Group", False, "Invalid response format", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("Join Group", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("Join Group", False, f"Request error: {str(e)}")
            return None

    async def test_invalid_join_group(self):
        """Test joining group with invalid invite code"""
        try:
            payload = {"invite_code": "INVALID", "username": "TestUser"}
            async with self.session.post(
                f"{self.api_url}/group/join",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    if "invalid" in error_data.get("detail", "").lower():
                        self.log_test("Invalid Join Group", True, "Correctly rejected invalid invite code")
                        return True
                    else:
                        self.log_test("Invalid Join Group", False, "Wrong error message", error_data)
                        return False
                else:
                    self.log_test("Invalid Join Group", False, f"Expected 400, got {response.status}")
                    return False
        except Exception as e:
            self.log_test("Invalid Join Group", False, f"Request error: {str(e)}")
            return False

    async def test_update_group_name(self, group_id, user_id, new_name="Updated Squad Name"):
        """Test PUT /api/group/{group_id}/name endpoint"""
        try:
            payload = {"name": new_name}
            async with self.session.put(
                f"{self.api_url}/group/{group_id}/name?user_id={user_id}",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and "group" in data:
                        group = data["group"]
                        if group["name"] == new_name:
                            self.log_test(
                                "Update Group Name", 
                                True, 
                                f"Group name updated to '{new_name}'"
                            )
                            return data
                        else:
                            self.log_test("Update Group Name", False, f"Name not updated correctly. Got: {group['name']}")
                            return None
                    else:
                        self.log_test("Update Group Name", False, "Invalid response format", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("Update Group Name", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("Update Group Name", False, f"Request error: {str(e)}")
            return None

    async def test_record_group_session(self, group_id, user_id, duration=2500):
        """Test POST /api/group/{group_id}/session endpoint"""
        try:
            payload = {
                "user_id": user_id,
                "duration": duration,
                "detection_method": "manual"
            }
            async with self.session.post(
                f"{self.api_url}/group/{group_id}/session",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and "session" in data and "group_stats" in data:
                        session = data["session"]
                        group_stats = data["group_stats"]
                        expected_session_fields = ["id", "duration", "user_id", "username", "group_id"]
                        expected_stats_fields = ["group", "daily_leaderboard", "members_stats"]
                        
                        if (all(field in session for field in expected_session_fields) and
                            all(field in group_stats for field in expected_stats_fields)):
                            self.log_test(
                                f"Record Group Session ({duration}ms)", 
                                True, 
                                f"Session recorded for {session['username']}. Group has {len(group_stats['members_stats'])} members"
                            )
                            return data
                        else:
                            self.log_test("Record Group Session", False, "Missing fields in response")
                            return None
                    else:
                        self.log_test("Record Group Session", False, "Invalid response format", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("Record Group Session", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("Record Group Session", False, f"Request error: {str(e)}")
            return None

    async def test_get_group_stats(self, group_id):
        """Test GET /api/group/{group_id}/stats endpoint"""
        try:
            async with self.session.get(f"{self.api_url}/group/{group_id}/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and "data" in data:
                        stats = data["data"]
                        expected_fields = ["group", "daily_leaderboard", "members_stats"]
                        if all(field in stats for field in expected_fields):
                            # Check leaderboard structure
                            leaderboard = stats["daily_leaderboard"]
                            if isinstance(leaderboard, list):
                                # Verify leaderboard is sorted by longest_burp (descending)
                                is_sorted = all(
                                    leaderboard[i]["longest_burp"] >= leaderboard[i+1]["longest_burp"]
                                    for i in range(len(leaderboard)-1)
                                )
                                if is_sorted:
                                    self.log_test(
                                        "Get Group Stats", 
                                        True, 
                                        f"Group stats retrieved. {len(leaderboard)} members in leaderboard"
                                    )
                                    return data
                                else:
                                    self.log_test("Get Group Stats", False, "Leaderboard not sorted correctly")
                                    return None
                            else:
                                self.log_test("Get Group Stats", False, "Leaderboard is not a list")
                                return None
                        else:
                            self.log_test("Get Group Stats", False, "Missing fields in stats response", stats)
                            return None
                    else:
                        self.log_test("Get Group Stats", False, "Invalid response format", data)
                        return None
                else:
                    error_text = await response.text()
                    self.log_test("Get Group Stats", False, f"HTTP {response.status}", error_text)
                    return None
        except Exception as e:
            self.log_test("Get Group Stats", False, f"Request error: {str(e)}")
            return None

    async def test_websocket_connection(self, group_id, user_id):
        """Test WebSocket /ws/{group_id}/{user_id} endpoint connectivity"""
        try:
            import websockets
            import asyncio
            
            # Convert HTTP URL to WebSocket URL
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://')
            ws_endpoint = f"{ws_url}/ws/{group_id}/{user_id}"
            
            try:
                # Try to connect with a short timeout
                websocket = await asyncio.wait_for(
                    websockets.connect(ws_endpoint),
                    timeout=5.0
                )
                
                # Send a ping message
                await websocket.send("ping")
                
                # Wait for response with timeout
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                
                await websocket.close()
                
                if "pong" in response:
                    self.log_test("WebSocket Connection", True, "WebSocket connected and responded to ping")
                    return True
                else:
                    self.log_test("WebSocket Connection", False, f"Unexpected response: {response}")
                    return False
                    
            except asyncio.TimeoutError:
                self.log_test("WebSocket Connection", False, "Connection timeout")
                return False
            except Exception as e:
                self.log_test("WebSocket Connection", False, f"WebSocket error: {str(e)}")
                return False
                
        except ImportError:
            self.log_test("WebSocket Connection", True, "WebSocket test skipped (websockets library not available)")
            return True
        except Exception as e:
            self.log_test("WebSocket Connection", False, f"Test setup error: {str(e)}")
            return False

    async def test_multiplayer_workflow(self):
        """Test complete multiplayer workflow"""
        print("\n🎮 Testing complete multiplayer workflow...")
        
        # Step 1: Create users
        user1_result = await self.test_create_user("BurpMaster")
        if not user1_result:
            return False
        user1 = user1_result["user"]
        
        user2_result = await self.test_create_user("BurpChamp")
        if not user2_result:
            return False
        user2 = user2_result["user"]
        
        # Step 2: Create group
        group_result = await self.test_create_group("Elite Burpers", user1["username"])
        if not group_result:
            return False
        group = group_result["group"]
        
        # Step 3: Second user joins group
        join_result = await self.test_join_group(group["invite_code"], user2["username"])
        if not join_result:
            return False
        
        # Step 4: Update group name
        update_result = await self.test_update_group_name(group["id"], user1["id"], "Super Burp Squad")
        if not update_result:
            return False
        
        # Step 5: Record sessions for both users
        session1_result = await self.test_record_group_session(group["id"], user1["id"], 3500)
        if not session1_result:
            return False
            
        session2_result = await self.test_record_group_session(group["id"], user2["id"], 2800)
        if not session2_result:
            return False
            
        session3_result = await self.test_record_group_session(group["id"], user1["id"], 4200)
        if not session3_result:
            return False
        
        # Step 6: Get group stats and verify leaderboard
        stats_result = await self.test_get_group_stats(group["id"])
        if not stats_result:
            return False
            
        stats = stats_result["data"]
        leaderboard = stats["daily_leaderboard"]
        
        # Verify leaderboard ranking (user1 should be first with 4200ms longest burp)
        if len(leaderboard) >= 2:
            if leaderboard[0]["username"] == user1["username"] and leaderboard[0]["longest_burp"] == 4200:
                self.log_test("Multiplayer Workflow", True, "Complete multiplayer workflow successful")
                return True
            else:
                self.log_test("Multiplayer Workflow", False, "Leaderboard ranking incorrect")
                return False
        else:
            self.log_test("Multiplayer Workflow", False, "Insufficient leaderboard data")
            return False
            
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Burp Tracker Backend API Tests (Single-player + Multiplayer)")
        print("=" * 70)
        
        await self.setup()
        
        try:
            # ========== SINGLE-PLAYER TESTS ==========
            print("\n📱 SINGLE-PLAYER API TESTS")
            print("-" * 40)
            
            # Test 1: Health check
            health_ok = await self.test_health_check()
            if not health_ok:
                print("❌ Health check failed - stopping tests")
                return False
                
            # Test 2: Invalid duration handling
            await self.test_invalid_duration()
            
            # Test 3: Record a single burp session
            await self.test_record_burp_session(2500)
            
            # Test 4: Get today's stats
            await self.test_get_today_stats()
            
            # Test 5: Test multiple sessions and totals
            await self.test_multiple_sessions_totals()
            
            # Test 6: History endpoint
            await self.test_history_endpoint(7)
            
            # Test 7: History endpoint with different days
            await self.test_history_endpoint(3)
            
            # ========== MULTIPLAYER TESTS ==========
            print("\n🎮 MULTIPLAYER API TESTS")
            print("-" * 40)
            
            # Test 8: Create users
            user1_result = await self.test_create_user("TestPlayer1")
            user2_result = await self.test_create_user("TestPlayer2")
            
            # Test 9: Test duplicate username handling
            await self.test_create_user("TestPlayer1")  # Should return existing user
            
            # Test 10: Create group
            if user1_result:
                group_result = await self.test_create_group("Test Squad", user1_result["user"]["username"])
            else:
                group_result = None
            
            # Test 11: Join group with valid code
            if group_result and user2_result:
                await self.test_join_group(group_result["group"]["invite_code"], user2_result["user"]["username"])
            
            # Test 12: Join group with invalid code
            await self.test_invalid_join_group()
            
            # Test 13: Update group name
            if group_result and user1_result:
                await self.test_update_group_name(
                    group_result["group"]["id"], 
                    user1_result["user"]["id"], 
                    "Updated Test Squad"
                )
            
            # Test 14: Record group sessions
            if group_result and user1_result and user2_result:
                await self.test_record_group_session(
                    group_result["group"]["id"], 
                    user1_result["user"]["id"], 
                    3500
                )
                await self.test_record_group_session(
                    group_result["group"]["id"], 
                    user2_result["user"]["id"], 
                    2800
                )
            
            # Test 15: Get group stats
            if group_result:
                await self.test_get_group_stats(group_result["group"]["id"])
            
            # Test 16: WebSocket connection
            if group_result and user1_result:
                await self.test_websocket_connection(
                    group_result["group"]["id"], 
                    user1_result["user"]["id"]
                )
            
            # Test 17: Complete multiplayer workflow
            await self.test_multiplayer_workflow()
            
        finally:
            await self.cleanup()
            
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        # Group results by category
        single_player_tests = []
        multiplayer_tests = []
        
        for result in self.test_results:
            if any(keyword in result['test'].lower() for keyword in ['user', 'group', 'multiplayer', 'websocket']):
                multiplayer_tests.append(result)
            else:
                single_player_tests.append(result)
        
        print("📱 Single-player Tests:")
        for result in single_player_tests:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status}: {result['test']}")
        
        print("\n🎮 Multiplayer Tests:")
        for result in multiplayer_tests:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status}: {result['test']}")
            
        print(f"\nOverall Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Backend API (single-player + multiplayer) is working correctly.")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed. Check the details above.")
            return False

async def main():
    """Main test runner"""
    tester = BurpTrackerAPITest()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)