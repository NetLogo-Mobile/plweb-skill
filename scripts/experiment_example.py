"""Create a local circuit archive. This script never logs in or publishes."""
from pathlib import Path
import argparse
import json

def build(destination: Path, title: str = "Logic connection", kind: str = "circuit"):
    from offline_physicslab import load_local_modules
    local = load_local_modules()
    circuit, coordinates = local['circuit'], local['coordinate_system']
    if destination.exists():
        raise FileExistsError("Choose a new output filename; existing experiments are not overwritten.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if kind == 'circuit':
        experiment = circuit.crt_circuit_experiment(title)
        source = circuit.LogicInput(coordinates.Position(-0.12, 0, 0.05))
        indicator = circuit.LogicOutput(coordinates.Position(0.12, 0, 0.05))
        experiment.crt_elements(source, indicator)
        experiment.crt_a_wire(source.o, indicator.i)
        loader = circuit.load_circuit_experiment_by_file_path
    elif kind == 'celestial':
        module = local['celestial']
        experiment = module.crt_celestial_experiment(title)
        experiment.crt_elements(module.Sun(coordinates.Position(0, 0, 0)), module.Earth(coordinates.Position(1, 0, 0)))
        loader = module.load_celestial_experiment_by_file_path
    elif kind == 'electromagnetism':
        module = local['electromagnetism']
        experiment = module.crt_electromagnetism_experiment(title)
        experiment.crt_elements(module.PositiveCharge(coordinates.Position(-0.1, 0, 0)), module.NegativeCharge(coordinates.Position(0.1, 0, 0)))
        loader = module.load_electromagnetism_experiment_by_file_path
    else:
        raise ValueError('Unknown experiment kind')
    experiment.save_to(destination)
    json.loads(destination.read_text(encoding="utf-8-sig"))
    loaded = loader(destination)
    return {"archive": str(destination.resolve()), "title": loaded.name,
            "generated": True, "simulation_verified": False, "published": False, "author": "Arendelle", "authorGithub": "https://github.com/SekaiArendelle", "attribution": "本实验使用 Arendelle 的 physicslab 内置建模库生成：https://github.com/SekaiArendelle"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default="Logic connection")
    parser.add_argument("--type", choices=['circuit','celestial','electromagnetism'], default='circuit')
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.title, args.type), ensure_ascii=False))
