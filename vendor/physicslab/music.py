"""Offline music circuits, adapted from Arendelle's MIT physicsLab.music Piece.

The sequencer follows the original D-water-lamp matrix. This adapter targets
the bundled physicslab 3 model API and uses no network or optional packages.
"""
from dataclasses import dataclass,field
from math import ceil,sqrt
from pathlib import Path
import json,struct
from . import circuit
from .coordinate_system import Position,Rotation

AUTHOR_GITHUB='https://github.com/SekaiArendelle'

@dataclass
class Note:
    pitch:int=60
    duration:float=1
    instrument:int=0
    velocity:float=0.7
    def __post_init__(self):
        if type(self.pitch) is not int or not 0<=self.pitch<=127:raise ValueError('MIDI pitch must be 0..127 (C4=60)')
        if not 0<self.duration<=128:raise ValueError('duration must be >0 and <=128 beats')
        if type(self.instrument) is not int or not 0<=self.instrument<=127:raise ValueError('instrument must be 0..127')
        if not 0<self.velocity<=1:raise ValueError('velocity must be >0 and <=1')

@dataclass
class Chord:
    notes:list[Note]=field(default_factory=list)
    duration:float=1
    def __post_init__(self):
        if not 0<self.duration<=128:raise ValueError('duration must be >0 and <=128 beats')
        if len(self.notes)>16 or any(not isinstance(n,Note) for n in self.notes):raise ValueError('Chord requires at most 16 Note objects')

class Piece:
    """Notes/chords/rests on a beat grid. None represents a one-beat rest."""
    def __init__(self,notes,bpm=100,step_beats=1):
        if not 20<=bpm<=300 or not 0<step_beats<=4:raise ValueError('bpm 20..300; step_beats >0..4')
        self.notes=list(notes);self.bpm=bpm;self.step_beats=step_beats

    def slots(self):
        slots=[]
        for item in self.notes:
            if item is None:
                count=1/self.step_beats
                if abs(count-round(count))>1e-7:raise ValueError('One-beat rest must align to step_beats')
                slots.extend([[]]*round(count));continue
            notes=item.notes if isinstance(item,Chord) else [item]
            duration=item.duration
            count=duration/self.step_beats
            if abs(count-round(count))>1e-7:raise ValueError('All durations must be multiples of step_beats')
            slots.append(notes);slots.extend([[]]*(round(count)-1))
        if not slots or not any(slots):raise ValueError('Music must contain a note')
        if len(slots)>512:raise ValueError('At most 512 sequencer slots; split longer music')
        return slots

    def release(self,title='Music experiment'):
        slots=self.slots();side=max(2,ceil(sqrt(len(slots))));rows=max(2,ceil(len(slots)/side))
        exp=circuit.crt_circuit_experiment(title)
        def element(name,x,y,z=0,**kw):
            obj=getattr(circuit,name)(Position(x*.16,z*.16,y*.16),**kw);exp.crt_elements(obj);return obj
        wire=exp.crt_a_wire
        def lamp(count,x,y,horizontal):
            nodes=[element('DFlipflop',x+(i if horizontal else 0),y+(0 if horizontal else 2*i)) for i in range(count)]
            for node in nodes[1:]:wire(nodes[0].i_low,node.i_low)
            wire(nodes[0].o_low,nodes[1].i_up)
            for i in range(1,count-1):wire(nodes[i].o_up,nodes[i+1].i_up)
            wire(nodes[-1].o_low,nodes[0].i_up)
            return nodes,[nodes[0].o_low]+[n.o_up for n in nodes[1:]],[nodes[0].o_up]+[n.o_low for n in nodes[1:]]
        xs,xout,_=lamp(side,1,1,True);ys,_,yneg=lamp(rows,0,3,False)
        tick=element('NimpGate',1,0);counter=element('Counter',0,1);start=element('LogicInput',0,0)
        wire(start.o,tick.i_up);wire(tick.o,tick.i_low);wire(tick.o,counter.i_up)
        yes=element('YesGate',2,0);wire(xs[0].o_low,yes.i);wire(xout[0],ys[0].i_low)
        no=element('NoGate',1,0,1);edge=element('AndGate',2,0,1);gate=element('OrGate',3,0)
        wire(no.o,edge.i_low);wire(no.i,edge.i_up);wire(start.o,no.i)
        wire(gate.i_low,edge.o);wire(gate.i_up,counter.o_upmid);wire(gate.o,xs[0].i_low)
        for index,notes in enumerate(slots):
            row,col=divmod(index,side)
            groups={}
            for note in notes:groups.setdefault((note.instrument,note.velocity),[]).append(note.pitch)
            for layer,((instrument,volume),pitches) in enumerate(groups.items()):
                ins=element('SimpleInstrument',1+col,4+row*2,layer,rotation=Rotation(0,0,0),pitches=pitches,instrument=instrument,volume=volume,bpm=self.bpm,is_ideal=True)
                wire(yes.o if col==0 else xout[col],ins.i);wire(ins.o,yneg[row])
        stop=element('AndGate',1,3+(rows-1)*2)
        wire(stop.o,counter.i_low);wire(stop.i_up,ys[(len(slots)-1)//side].o_up);wire(stop.i_low,xs[side-1].o_up)
        return exp

    def write_midi(self,path):
        """Write standard type-0 MIDI; durations and chords are retained."""
        events=[];time=0
        for item in self.notes:
            duration=1 if item is None else item.duration
            notes=[] if item is None else item.notes if isinstance(item,Chord) else [item]
            for channel,note in enumerate(notes):
                channel=channel%15
                events.extend([(time,bytes([0xc0|channel,note.instrument])),(time,bytes([0x90|channel,note.pitch,max(1,round(note.velocity*127))])),(time+round(duration*480),bytes([0x80|channel,note.pitch,0]))])
            time+=round(duration*480)
        events.sort(key=lambda e:(e[0],0 if e[1][0]&0xf0==0x80 else 1))
        tempo=round(60000000/self.bpm)
        track=bytearray(b'\0\xff\x51\x03'+tempo.to_bytes(3,'big'));last=0
        for stamp,event in events:track.extend(_vlq(stamp-last)+event);last=stamp
        track.extend(b'\0\xff\x2f\0')
        Path(path).write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,480)+b'MTrk'+struct.pack('>I',len(track))+track)

def _vlq(value):
    out=[value&127];value>>=7
    while value:out.insert(0,(value&127)|128);value>>=7
    return bytes(out)

def from_json(value):
    notes=[]
    for item in value['notes']:
        duration=item.get('duration',1)
        pitches=item.get('pitches',[])
        if not pitches:
            count=duration/value.get('step_beats',1)
            if abs(count-round(count))>1e-7:raise ValueError('Rest duration must align to step_beats')
            # None is one beat in Piece, so explicit empty chord keeps duration.
            notes.append(Chord([],duration))
        else:notes.append(Chord([Note(p,duration,item.get('instrument',0),item.get('velocity',.7)) for p in pitches],duration))
    return Piece(notes,value.get('bpm',100),value.get('step_beats',1))
