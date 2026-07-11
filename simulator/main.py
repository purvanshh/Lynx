from pathlib import Path

from simulator.scheduler import load_scenario


def main() -> None:
    scenario_path = Path(__file__).parent / "scenarios" / "happy_path.json"
    scenario = load_scenario(scenario_path)
    print(f"Loaded scenario: {scenario['scenario_id']}")


if __name__ == "__main__":
    main()
