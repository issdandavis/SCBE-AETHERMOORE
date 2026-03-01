"""
Tests for Outreach Central Hub — octopus architecture.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from outreach.hub import OutreachHub, TentacleType, ContactPoint, OutreachCampaign
from outreach.tentacles import (
    Tentacle, Sucker, LeadTemperature, LeadSource,
    MarketingTentacle, ResearchTentacle,
    ColdOutreachTentacle, HotOutreachTentacle,
    FreeWorkTentacle, GrantTentacle,
    PartnershipTentacle, ContentTentacle,
)


# ---------------------------------------------------------------------------
#  Sucker (Contact Point) Tests
# ---------------------------------------------------------------------------

class TestSucker:
    def test_create_sucker(self):
        s = Sucker(name="Test Person", email="test@example.com")
        assert s.name == "Test Person"
        assert s.sucker_id  # Auto-generated
        assert s.temperature == LeadTemperature.COLD

    def test_touch_warms_cold_lead(self):
        s = Sucker(name="Cold Lead")
        assert s.temperature == LeadTemperature.COLD
        s.touch("Initial contact")
        assert s.temperature == LeadTemperature.WARM
        assert s.contact_count == 1
        assert s.last_contact is not None

    def test_touch_increments_count(self):
        s = Sucker(name="Active Lead", temperature=LeadTemperature.HOT)
        s.touch("Call 1")
        s.touch("Call 2")
        assert s.contact_count == 2

    def test_to_dict(self):
        s = Sucker(name="Test", email="t@e.com", tags=["vip"])
        d = s.to_dict()
        assert d["name"] == "Test"
        assert d["email"] == "t@e.com"
        assert "vip" in d["tags"]


# ---------------------------------------------------------------------------
#  Base Tentacle Tests
# ---------------------------------------------------------------------------

class TestTentacle:
    def test_create_tentacle(self):
        t = Tentacle("Test Arm", "A test tentacle", priority=7)
        assert t.name == "Test Arm"
        assert t.active is True

    def test_add_and_find_sucker(self):
        t = Tentacle("Test", "desc")
        s = Sucker(name="Alice", email="alice@test.com")
        t.add_sucker(s)
        found = t.find_sucker("alice")  # Case-insensitive
        assert found is not None
        assert found.name == "Alice"

    def test_find_nonexistent_sucker(self):
        t = Tentacle("Test", "desc")
        assert t.find_sucker("Nobody") is None

    def test_reach_records_action(self):
        t = Tentacle("Test", "desc")
        record = t.reach("Target Co", "email", "Sent intro")
        assert record["action"] == "email"
        assert record["target"] == "Target Co"
        assert record["status"] == "executed"

    def test_reach_touches_known_sucker(self):
        t = Tentacle("Test", "desc")
        s = Sucker(name="Bob")
        t.add_sucker(s)
        t.reach("Bob", "call", "Discussed pricing")
        assert s.contact_count == 1
        assert s.temperature == LeadTemperature.WARM

    def test_retract_and_extend(self):
        t = Tentacle("Test", "desc")
        assert t.active is True
        t.retract()
        assert t.active is False
        t.extend()
        assert t.active is True

    def test_lead_filtering(self):
        t = Tentacle("Test", "desc")
        t.add_sucker(Sucker(name="Cold1"))
        t.add_sucker(Sucker(name="Warm1", temperature=LeadTemperature.WARM))
        t.add_sucker(Sucker(name="Hot1", temperature=LeadTemperature.HOT))
        assert len(t.cold_leads) == 1
        assert len(t.warm_leads) == 1
        assert len(t.hot_leads) == 1

    def test_status_report(self):
        t = Tentacle("Test", "desc", priority=8)
        t.add_sucker(Sucker(name="A"))
        t.reach("A", "ping")
        status = t.status()
        assert status["name"] == "Test"
        assert status["total_contacts"] == 1
        assert status["actions_taken"] == 1
        assert status["priority"] == 8


# ---------------------------------------------------------------------------
#  Specialized Tentacle Tests
# ---------------------------------------------------------------------------

class TestMarketingTentacle:
    def test_has_platforms(self):
        m = MarketingTentacle()
        assert "twitter" in m.platforms
        assert "github" in m.platforms

    def test_post(self):
        m = MarketingTentacle()
        record = m.post("twitter", "Check out SCBE governance!")
        assert record["action"] == "post"

    def test_engage(self):
        m = MarketingTentacle()
        record = m.engage("twitter", "some_user", "like")
        assert "twitter_like" in record["action"]


class TestColdOutreachTentacle:
    def test_draft_email(self):
        c = ColdOutreachTentacle()
        email = c.draft_email("intro", "Jane", "Would love to chat.")
        assert "Jane" in email
        assert "SCBE-AETHERMOORE" in email

    def test_draft_demo_offer(self):
        c = ColdOutreachTentacle()
        email = c.draft_email("demo_offer", "Bob", "Free scan available.")
        assert "Bob" in email
        assert "governance scan" in email


class TestFreeWorkTentacle:
    def test_add_free_job(self):
        f = FreeWorkTentacle()
        job = f.add_free_job("Startup X", "Free governance audit", "Convert to monthly ops")
        assert job["client"] == "Startup X"
        assert job["conversion_path"] == "Convert to monthly ops"

    def test_conversion_rate_empty(self):
        f = FreeWorkTentacle()
        assert f.conversion_rate == 0.0


class TestGrantTentacle:
    def test_add_opportunity(self):
        g = GrantTentacle()
        opp = g.add_opportunity("NSF SBIR", "NSF", "$275K", deadline="Jun 2026")
        assert opp["funder"] == "NSF"
        assert opp["status"] == "identified"


class TestResearchTentacle:
    def test_track_paper(self):
        r = ResearchTentacle()
        paper = r.track_paper("My Paper", "https://arxiv.org/paper")
        assert paper["title"] == "My Paper"
        assert r.arxiv_id == "izdandavis"

    def test_track_conference(self):
        r = ResearchTentacle()
        conf = r.track_conference("AAAI", "Sep 2026")
        assert conf["name"] == "AAAI"


class TestContentTentacle:
    def test_queue_content(self):
        c = ContentTentacle()
        item = c.queue_content("Blog Post Title", "blog", "medium")
        assert item["status"] == "queued"
        assert len(c.pending_content()) == 1


class TestPartnershipTentacle:
    def test_initial_targets(self):
        p = PartnershipTentacle()
        assert len(p.targets) >= 2
        names = [t["name"] for t in p.targets]
        assert "OpenClaw" in names


# ---------------------------------------------------------------------------
#  Hub Tests
# ---------------------------------------------------------------------------

class TestOutreachHub:
    def test_create_hub(self):
        hub = OutreachHub()
        assert len(hub.tentacles) == 8

    def test_all_tentacles_active(self):
        hub = OutreachHub()
        for t in hub.tentacles.values():
            assert t.active is True

    def test_add_and_find_contact(self):
        hub = OutreachHub()
        contact = ContactPoint(name="Test User", emails=["test@test.com"])
        hub.add_contact(contact)
        found = hub.find_contact("test user")
        assert found is not None
        assert found.emails == ["test@test.com"]

    def test_route_contact_to_tentacle(self):
        hub = OutreachHub()
        contact = ContactPoint(name="Lead Person", emails=["lead@co.com"])
        hub.add_contact(contact)
        hub.route_contact(contact, TentacleType.COLD_OUTREACH)
        arm = hub.cold_outreach
        assert arm.sucker_count == 1
        assert "cold_outreach" in contact.tentacles

    def test_arm_access(self):
        hub = OutreachHub()
        assert isinstance(hub.marketing, MarketingTentacle)
        assert isinstance(hub.research, ResearchTentacle)
        assert isinstance(hub.grants, GrantTentacle)
        assert isinstance(hub.content, ContentTentacle)
        assert isinstance(hub.partnership, PartnershipTentacle)
        assert isinstance(hub.arm(TentacleType.FREE_WORK), FreeWorkTentacle)

    def test_create_campaign(self):
        hub = OutreachHub()
        campaign = hub.create_campaign(
            "Launch Campaign",
            "Initial market push",
            [TentacleType.MARKETING, TentacleType.CONTENT],
        )
        assert campaign.status == "planned"
        assert len(hub.campaigns) == 1

    def test_diagnostics(self):
        hub = OutreachHub()
        diag = hub.diagnostics()
        assert diag["brain"] == "active"
        assert diag["tentacles_total"] == 8
        assert diag["tentacles_active"] == 8
        assert "identity" in diag

    def test_seed_initial_data(self):
        hub = OutreachHub()
        counts = hub.seed_initial_data()
        assert counts["contacts"] >= 1
        assert counts["grants"] >= 3
        assert counts["partnerships"] >= 2
        assert counts["content"] >= 3
        # Verify SharonAnn is routed to hot outreach
        assert hub.hot_outreach.sucker_count >= 1

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save
            hub1 = OutreachHub(data_dir=tmpdir)
            hub1.add_contact(ContactPoint(name="Persist Test", emails=["p@t.com"]))
            path = hub1.save()
            assert os.path.exists(path)

            # Load
            hub2 = OutreachHub(data_dir=tmpdir)
            loaded = hub2.load()
            assert loaded is True
            assert len(hub2.contacts) == 1
            found = hub2.find_contact("Persist Test")
            assert found is not None

    def test_identity_info(self):
        hub = OutreachHub()
        assert hub.identity["patent"] == "USPTO #63/961,403"
        assert hub.identity["github"] == "https://github.com/issdandavis/SCBE-AETHERMOORE"

    def test_campaign_to_dict(self):
        campaign = OutreachCampaign(
            name="Test",
            description="A test campaign",
            tentacles=[TentacleType.MARKETING],
        )
        d = campaign.to_dict()
        assert d["name"] == "Test"
        assert "marketing" in d["tentacles"]
