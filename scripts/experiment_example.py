"""Create a local circuit archive. This script never logs in or publishes."""
from pathlib import Path
import argparse
import json

def build(destination: Path, title: str = "Logic connection"):
    from offline_physicslab import load_local_modules
    local = load_local_modules()
    circuit, coordinates = local['circuit'], local['coordinate_system']
    if destination.exists():
        raise FileExistsError("Choose a new output filename; existing experiments are not overwritten.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with circuit.crt_circuit_experiment(title) as experiment:
        source = circuit.LogicInput(coordinates.Position(-0.12, 0, 0.05))
        indicator = circuit.LogicOutput(coordinates.Position(0.12, 0, 0.05))
        experiment.crt_elements(source, indicator)
        experiment.crt_a_wire(source.o, indicator.i)
        experiment.save_to(destination)
    json.loads(destination.read_text(encoding="utf-8-sig"))
    loaded = circuit.load_circuit_experiment_by_file_path(destination)
    return {"archive": str(destination.resolve()), "title": loaded.name,
            "generated": True, "simulation_verified": False, "published": False}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default="Logic connection")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.title), ensure_ascii=False))
