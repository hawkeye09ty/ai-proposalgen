import requests
import sys
import json
from datetime import datetime

class ProposalBuilderAPITester:
    def __init__(self, base_url="https://clauses-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_proposal_id = None
        self.created_clause_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    return success, response_data
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_get_stats_empty(self):
        """Test stats endpoint when no proposals exist"""
        success, response = self.run_test(
            "Get Stats (Empty)",
            "GET",
            "stats",
            200
        )
        if success:
            expected_keys = ['total', 'draft', 'pending_review', 'sent', 'accepted', 'rejected']
            if all(key in response for key in expected_keys):
                print(f"   ✅ All required stats keys present")
                return True
            else:
                print(f"   ❌ Missing required stats keys")
                return False
        return success

    def test_get_clauses(self):
        """Test getting all clauses (should have default clauses)"""
        success, response = self.run_test(
            "Get All Clauses",
            "GET",
            "clauses",
            200
        )
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} clauses")
            if len(response) >= 6:  # Should have default clauses
                print(f"   ✅ Default clauses are seeded")
                return True
            else:
                print(f"   ⚠️  Expected at least 6 default clauses, found {len(response)}")
        return success

    def test_create_custom_clause(self):
        """Test creating a custom clause"""
        clause_data = {
            "title": "Test Custom Clause",
            "content": "This is a test clause for API testing purposes.",
            "category": "Legal",
            "is_custom": True
        }
        
        success, response = self.run_test(
            "Create Custom Clause",
            "POST",
            "clauses",
            200,
            data=clause_data
        )
        
        if success and 'id' in response:
            self.created_clause_id = response['id']
            print(f"   ✅ Created clause with ID: {self.created_clause_id}")
            return True
        return success

    def test_create_proposal(self):
        """Test creating a proposal"""
        proposal_data = {
            "client_name": "Test Client Corp",
            "project_description": "Test project for API validation",
            "budget_range": "$10,000 - $15,000",
            "timeline": "2-3 months",
            "selected_clauses": []
        }
        
        success, response = self.run_test(
            "Create Proposal",
            "POST",
            "proposals",
            200,
            data=proposal_data
        )
        
        if success and 'id' in response:
            self.created_proposal_id = response['id']
            print(f"   ✅ Created proposal with ID: {self.created_proposal_id}")
            return True
        return success

    def test_get_proposals(self):
        """Test getting all proposals"""
        success, response = self.run_test(
            "Get All Proposals",
            "GET",
            "proposals",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} proposals")
            return True
        return success

    def test_get_proposal_by_id(self):
        """Test getting a specific proposal"""
        if not self.created_proposal_id:
            print("❌ No proposal ID available for testing")
            return False
            
        success, response = self.run_test(
            "Get Proposal by ID",
            "GET",
            f"proposals/{self.created_proposal_id}",
            200
        )
        
        if success and response.get('id') == self.created_proposal_id:
            print(f"   ✅ Retrieved correct proposal")
            return True
        return success

    def test_update_proposal_status(self):
        """Test updating proposal status"""
        if not self.created_proposal_id:
            print("❌ No proposal ID available for testing")
            return False
            
        update_data = {"status": "Pending Review"}
        
        success, response = self.run_test(
            "Update Proposal Status",
            "PATCH",
            f"proposals/{self.created_proposal_id}",
            200,
            data=update_data
        )
        
        if success and response.get('status') == 'Pending Review':
            print(f"   ✅ Status updated successfully")
            return True
        return success

    def test_ai_proposal_generation(self):
        """Test AI proposal generation"""
        generate_data = {
            "client_name": "AI Test Client",
            "project_description": "Test AI proposal generation functionality",
            "budget_range": "$20,000 - $30,000",
            "timeline": "3-4 months",
            "selected_clauses": [],
            "additional_requirements": "This is a test for AI integration"
        }
        
        print(f"\n🤖 Testing AI Proposal Generation (this may take a few seconds)...")
        success, response = self.run_test(
            "AI Proposal Generation",
            "POST",
            "generate-proposal",
            200,
            data=generate_data
        )
        
        if success and 'content' in response:
            content_length = len(response['content'])
            print(f"   ✅ Generated proposal content ({content_length} characters)")
            if content_length > 100:  # Reasonable content length
                print(f"   ✅ Content appears substantial")
                return True
            else:
                print(f"   ⚠️  Content seems too short")
        return success

    def test_get_stats_with_data(self):
        """Test stats endpoint after creating proposals"""
        success, response = self.run_test(
            "Get Stats (With Data)",
            "GET",
            "stats",
            200
        )
        
        if success:
            total = response.get('total', 0)
            if total > 0:
                print(f"   ✅ Stats show {total} total proposals")
                return True
            else:
                print(f"   ⚠️  Expected proposals in stats but got {total}")
        return success

    def test_delete_custom_clause(self):
        """Test deleting a custom clause"""
        if not self.created_clause_id:
            print("❌ No clause ID available for testing")
            return False
            
        success, response = self.run_test(
            "Delete Custom Clause",
            "DELETE",
            f"clauses/{self.created_clause_id}",
            200
        )
        
        if success:
            print(f"   ✅ Clause deleted successfully")
            return True
        return success

    def test_proposal_filtering(self):
        """Test proposal filtering by status"""
        success, response = self.run_test(
            "Filter Proposals by Status",
            "GET",
            "proposals",
            200,
            params={"status": "Draft"}
        )
        
        if success and isinstance(response, list):
            print(f"   ✅ Filtered proposals returned {len(response)} items")
            return True
        return success

def main():
    print("🚀 Starting Proposal Builder API Tests")
    print("=" * 50)
    
    tester = ProposalBuilderAPITester()
    
    # Test sequence
    tests = [
        tester.test_root_endpoint,
        tester.test_get_stats_empty,
        tester.test_get_clauses,
        tester.test_create_custom_clause,
        tester.test_create_proposal,
        tester.test_get_proposals,
        tester.test_get_proposal_by_id,
        tester.test_update_proposal_status,
        tester.test_proposal_filtering,
        tester.test_get_stats_with_data,
        tester.test_ai_proposal_generation,
        tester.test_delete_custom_clause
    ]
    
    # Run all tests
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())