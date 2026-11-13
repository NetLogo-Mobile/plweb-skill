"""Generate a sequenced music .plsav and optional MIDI using the bundled library."""
import argparse,json
from pathlib import Path
from offline_physicslab import load_local_modules

def build(score,output,title='Music experiment',midi=None):
    load_local_modules()
    from physicslab.music import from_json,AUTHOR_GITHUB
    from physicslab.circuit import load_circuit_experiment_by_file_path
    output=Path(output)
    if output.exists() or midi and Path(midi).exists():raise FileExistsError('Choose new output paths')
    piece=from_json(score);experiment=piece.release(title);output.parent.mkdir(parents=True,exist_ok=True);experiment.save_to(output)
    load_circuit_experiment_by_file_path(output)
    if midi:piece.write_midi(midi)
    return {'archive':str(output.resolve()),'midi':str(Path(midi).resolve()) if midi else None,'slots':len(piece.slots()),'generated':True,'published':False,'author':'Arendelle','authorGithub':AUTHOR_GITHUB,'attribution':'本实验使用 Arendelle 的 physicslab 内置建模库生成：https://github.com/SekaiArendelle'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--score',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--midi',type=Path);p.add_argument('--title',default='Music experiment');a=p.parse_args()
    print(json.dumps(build(json.loads(a.score.read_text(encoding='utf-8-sig')),a.output,a.title,a.midi),ensure_ascii=False))
