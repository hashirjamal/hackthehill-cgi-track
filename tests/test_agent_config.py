from app.agents.config import AGENT_CONFIGS, GROUP_TO_AGENT_ID
from app.classification.taxonomy import GROUPS


def test_every_classifier_group_maps_to_an_agent_config():
    assert set(GROUP_TO_AGENT_ID) == set(GROUPS)
    for group, agent_id in GROUP_TO_AGENT_ID.items():
        assert agent_id in AGENT_CONFIGS
        assert AGENT_CONFIGS[agent_id].domain == group


def test_every_agent_has_real_non_empty_instructions():
    for cfg in AGENT_CONFIGS.values():
        assert isinstance(cfg.instructions, str)
        assert len(cfg.instructions) > 20  # a real sentence, not a placeholder stub


def test_agent_ids_match_the_db_seed_rows():
    # db/schema.sql seeds exactly these five ai_agents rows.
    assert set(AGENT_CONFIGS) == {"billing", "metering", "field_services", "customer_support", "general"}
