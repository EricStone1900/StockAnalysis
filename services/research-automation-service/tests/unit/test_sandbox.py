from src.research_automation.domain import ExperimentInput
from src.research_automation.sandbox import FixedScriptSandbox


def test_sandbox_command_is_networkless_read_only_and_resource_limited() -> None:
    input_value = ExperimentInput(
        hypothesis="固定脚本",
        data_version_id="dv-1",
        data_artifact_uri="s3://market-data/dv-1.tar.gz",
        data_artifact_hash="b" * 64,
        script_id="fixed-factor-smoke-v1",
        parameters={},
        random_seed=1,
    )
    command = FixedScriptSandbox().build_command(input_value)
    assert ("--network", "none") in zip(command.argv, command.argv[1:])
    assert "--read-only" in command.argv
    assert ("--user", "65532:65532") in zip(command.argv, command.argv[1:])
    assert ("--cap-drop", "ALL") in zip(command.argv, command.argv[1:])
    assert ("--security-opt", "no-new-privileges") in zip(command.argv, command.argv[1:])
    assert "readonly" in " ".join(command.argv)
