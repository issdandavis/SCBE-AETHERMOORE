import pytest
from src.polly_pads_runtime import PollyPadsRuntime

# --- Constants ---
# Define the 6 "Sacred Tongue" test conversations from your AWS report
# These messages are designed to be stable inputs that should result in zero deviation.
TEST_CONVERSATIONS = [
    ("KO-SCOUT: Scan area for anomalies", "KO-SCOUT"),
    ("AV-VISION: Verify target identity", "AV-VISION"),
    ("RU-READER: Extract mission parameters from document", "RU-READER"),
    ("CA-CLICKER: Navigate to new configuration dashboard", "CA-CLICKER"),
    ("UM-TYPER: Enter security credentials", "UM-TYPER"),
    ("DR-JUDGE: Validate previous mission results", "DR-JUDGE"),
]


class TestPollyHamiltonianStability:
    """
    Validates the Hamiltonian stability of Polly's Sacred Tongue routing protocol.
    A successful test asserts that all test conversations result in zero Hamiltonian deviation.
    """
    def setup_method(self):
        # Initialize the runtime environment for each test
        self.runtime = PollyPadsRuntime()

    @pytest.mark.parametrize("message, agent_id", TEST_CONVERSATIONS)
    def test_zero_hamiltonian_deviation(self, message: str, agent_id: str):
        """
        Tests that each sacred tongue message results in a stable Hamiltonian state.
        Asserts that deviation is below the system's defined threshold (1e-6).
        """
        # Run the routing protocol
        result = self.runtime.route_conversation(message, agent_id)

        # Assertions based on the AWS validation report
        assert result["decision"] == "ALLOW", f"Decision should be ALLOW for {agent_id}"
        assert result["hamiltonian_deviation"] < 1e-6, f"Deviation must be near zero for {agent_id}"

# To run: `pytest tests/polly_live_test.py`
