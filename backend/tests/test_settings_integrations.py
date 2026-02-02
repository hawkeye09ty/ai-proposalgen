"""
Backend tests for Settings, Integration Status, and Inline Editing features
Tests: Settings CRUD, Integration status endpoints, Proposal PATCH for inline editing
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestIntegrationStatus:
    """Tests for integration status endpoints"""
    
    def test_resend_integration_status(self):
        """Test Resend integration status endpoint returns connected=true"""
        response = requests.get(f"{BASE_URL}/api/integrations/resend/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert data["connected"] == True  # Should be connected with valid API key
    
    def test_brevo_integration_status(self):
        """Test Brevo integration status endpoint"""
        response = requests.get(f"{BASE_URL}/api/integrations/brevo/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        # Brevo should be connected with valid API key
        assert data["connected"] == True
    
    def test_google_integration_status(self):
        """Test Google integration status endpoint returns connected=false (no credentials)"""
        response = requests.get(f"{BASE_URL}/api/integrations/google/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert data["connected"] == False  # No Google credentials configured


class TestSettings:
    """Tests for Settings CRUD operations"""
    
    def test_get_default_settings(self):
        """Test getting default settings"""
        response = requests.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200
        data = response.json()
        
        # Verify default settings structure
        assert "company_name" in data
        assert "default_sender_email" in data
        assert "auto_send_on_approval" in data
        assert "brevo_polling_enabled" in data
        assert "brevo_polling_interval" in data
        assert "google_doc_template_id" in data
        assert "approval_keyword" in data
        assert "notify_on_proposal_open" in data
        assert "notify_on_proposal_click" in data
    
    def test_save_settings(self):
        """Test saving settings and verifying persistence"""
        # Save new settings
        new_settings = {
            "company_name": "TEST_Company",
            "default_sender_email": "test@example.com",
            "auto_send_on_approval": True,
            "brevo_polling_enabled": False,
            "brevo_polling_interval": 10,
            "google_doc_template_id": "test-template-id",
            "approval_keyword": "CONFIRMED",
            "notify_on_proposal_open": False,
            "notify_on_proposal_click": False
        }
        
        save_response = requests.post(f"{BASE_URL}/api/settings", json=new_settings)
        assert save_response.status_code == 200
        assert save_response.json()["status"] == "success"
        
        # Verify settings were persisted
        get_response = requests.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        saved_data = get_response.json()
        
        assert saved_data["company_name"] == "TEST_Company"
        assert saved_data["default_sender_email"] == "test@example.com"
        assert saved_data["auto_send_on_approval"] == True
        assert saved_data["brevo_polling_enabled"] == False
        assert saved_data["brevo_polling_interval"] == 10
        assert saved_data["google_doc_template_id"] == "test-template-id"
        assert saved_data["approval_keyword"] == "CONFIRMED"
        assert saved_data["notify_on_proposal_open"] == False
        assert saved_data["notify_on_proposal_click"] == False
    
    def test_restore_default_settings(self):
        """Restore default settings after test"""
        default_settings = {
            "company_name": "ProposalAI",
            "default_sender_email": "",
            "auto_send_on_approval": False,
            "brevo_polling_enabled": True,
            "brevo_polling_interval": 5,
            "google_doc_template_id": "",
            "approval_keyword": "APPROVED",
            "notify_on_proposal_open": True,
            "notify_on_proposal_click": True
        }
        
        response = requests.post(f"{BASE_URL}/api/settings", json=default_settings)
        assert response.status_code == 200


class TestInlineProposalEditing:
    """Tests for inline proposal editing from dashboard (PATCH endpoint)"""
    
    @pytest.fixture
    def test_proposal(self):
        """Create a test proposal for editing tests"""
        proposal_data = {
            "client_name": "TEST_InlineEdit_Client",
            "project_description": "Test project for inline editing",
            "budget_range": "$10,000 - $20,000",
            "timeline": "2 months",
            "deal_value": 15000
        }
        
        response = requests.post(f"{BASE_URL}/api/proposals", json=proposal_data)
        assert response.status_code == 200
        proposal = response.json()
        yield proposal
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{proposal['id']}")
    
    def test_patch_proposal_client_name(self, test_proposal):
        """Test updating client name via PATCH"""
        proposal_id = test_proposal["id"]
        
        update_data = {"client_name": "TEST_Updated_Client"}
        response = requests.patch(f"{BASE_URL}/api/proposals/{proposal_id}", json=update_data)
        
        assert response.status_code == 200
        updated = response.json()
        assert updated["client_name"] == "TEST_Updated_Client"
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}")
        assert get_response.json()["client_name"] == "TEST_Updated_Client"
    
    def test_patch_proposal_budget_and_timeline(self, test_proposal):
        """Test updating budget and timeline via PATCH"""
        proposal_id = test_proposal["id"]
        
        update_data = {
            "budget_range": "$50,000 - $100,000",
            "timeline": "6 months"
        }
        response = requests.patch(f"{BASE_URL}/api/proposals/{proposal_id}", json=update_data)
        
        assert response.status_code == 200
        updated = response.json()
        assert updated["budget_range"] == "$50,000 - $100,000"
        assert updated["timeline"] == "6 months"
    
    def test_patch_proposal_status(self, test_proposal):
        """Test updating status via PATCH"""
        proposal_id = test_proposal["id"]
        
        # Test all status transitions
        statuses = ["Pending Review", "Sent", "Accepted", "Rejected", "Draft"]
        
        for status in statuses:
            response = requests.patch(f"{BASE_URL}/api/proposals/{proposal_id}", json={"status": status})
            assert response.status_code == 200
            assert response.json()["status"] == status
    
    def test_patch_proposal_deal_value(self, test_proposal):
        """Test updating deal value via PATCH"""
        proposal_id = test_proposal["id"]
        
        update_data = {"deal_value": 75000.50}
        response = requests.patch(f"{BASE_URL}/api/proposals/{proposal_id}", json=update_data)
        
        assert response.status_code == 200
        assert response.json()["deal_value"] == 75000.50
    
    def test_patch_proposal_accepted_sets_accepted_at(self, test_proposal):
        """Test that setting status to Accepted sets accepted_at timestamp"""
        proposal_id = test_proposal["id"]
        
        response = requests.patch(f"{BASE_URL}/api/proposals/{proposal_id}", json={"status": "Accepted"})
        
        assert response.status_code == 200
        updated = response.json()
        assert updated["status"] == "Accepted"
        assert updated["accepted_at"] is not None
    
    def test_patch_nonexistent_proposal(self):
        """Test PATCH on non-existent proposal returns 404"""
        response = requests.patch(
            f"{BASE_URL}/api/proposals/nonexistent-id-12345",
            json={"client_name": "Test"}
        )
        assert response.status_code == 404


class TestDashboardStats:
    """Tests for dashboard stats endpoint"""
    
    def test_stats_endpoint(self):
        """Test stats endpoint returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "draft" in data
        assert "pending_review" in data
        assert "sent" in data
        assert "accepted" in data
        assert "rejected" in data
        
        # All values should be non-negative integers
        assert isinstance(data["total"], int) and data["total"] >= 0
        assert isinstance(data["draft"], int) and data["draft"] >= 0


class TestBrevoEndpoints:
    """Tests for Brevo CRM integration endpoints"""
    
    def test_brevo_opportunities_endpoint(self):
        """Test Brevo opportunities endpoint"""
        response = requests.get(f"{BASE_URL}/api/brevo/opportunities")
        # Should return 200 or error if Brevo API has issues
        assert response.status_code in [200, 400, 500]
    
    def test_brevo_pending_deals_endpoint(self):
        """Test Brevo pending deals endpoint"""
        response = requests.get(f"{BASE_URL}/api/brevo/pending-deals")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestEmailSending:
    """Tests for email sending functionality via Resend"""
    
    @pytest.fixture
    def test_proposal_with_content(self):
        """Create a test proposal with content for email tests"""
        proposal_data = {
            "client_name": "TEST_Email_Client",
            "project_description": "Test project for email sending",
            "budget_range": "$5,000 - $10,000",
            "timeline": "1 month"
        }
        
        response = requests.post(f"{BASE_URL}/api/proposals", json=proposal_data)
        assert response.status_code == 200
        proposal = response.json()
        
        # Add content to proposal
        content_update = {"content": "This is a test proposal content for email testing."}
        requests.patch(f"{BASE_URL}/api/proposals/{proposal['id']}", json=content_update)
        
        yield proposal
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proposals/{proposal['id']}")
    
    def test_send_email_missing_recipient(self, test_proposal_with_content):
        """Test send email fails without recipient"""
        response = requests.post(f"{BASE_URL}/api/send-email", json={
            "proposal_id": test_proposal_with_content["id"],
            "recipient_email": ""  # Empty email
        })
        # Should fail validation
        assert response.status_code == 422
    
    def test_send_email_invalid_proposal(self):
        """Test send email fails with invalid proposal ID"""
        response = requests.post(f"{BASE_URL}/api/send-email", json={
            "proposal_id": "nonexistent-proposal-id",
            "recipient_email": "test@example.com"
        })
        assert response.status_code == 404
    
    def test_email_logs_endpoint(self, test_proposal_with_content):
        """Test email logs endpoint"""
        proposal_id = test_proposal_with_content["id"]
        response = requests.get(f"{BASE_URL}/api/email-logs/{proposal_id}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
