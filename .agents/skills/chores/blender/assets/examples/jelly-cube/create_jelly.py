"""实验果冻案例，须先询问用户。通过 Blender 后台运行，输出到新目录。"""
import bpy
import math
from pathlib import Path
from mathutils import Vector

import argparse
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--user-confirmed', action='store_true')
parser.add_argument('--resolution-percent', type=int, default=100)
parser.add_argument('--samples', type=int, default=64)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
if not args.user_confirmed:
    parser.error('本案例由 agent 实验编写；请先询问用户，得到同意后再传入 --user-confirmed')
if not 1 <= args.resolution_percent <= 100 or args.samples < 1:
    parser.error('resolution-percent 应在 1–100 之间，samples 应为正')
ROOT = args.output_dir.expanduser().resolve()
ROOT.mkdir(parents=True, exist_ok=False)
for folder in ('renders', 'blend'):
    (ROOT / folder).mkdir(exist_ok=True)

def rgba(value):
    value = value.lstrip('#')
    rgb = [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


def setup(scene, scale, target, resolution):
    scene.render.engine='CYCLES'
    scene.cycles.samples=args.samples
    scene.cycles.use_denoising=True
    scene.cycles.max_bounces=12
    scene.cycles.transmission_bounces=8
    scene.cycles.transparent_max_bounces=12
    scene.render.resolution_x, scene.render.resolution_y=resolution
    scene.render.resolution_percentage=args.resolution_percent
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='Standard'
    scene.view_settings.look='None'
    scene.view_settings.exposure=-.15
    world=bpy.data.worlds.new(scene.name+' / indigo world'); world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=rgba('302650')
    world.node_tree.nodes['Background'].inputs[1].default_value=.9
    scene.world=world
    data=bpy.data.cameras.new(scene.name+' / orthographic camera')
    camera=bpy.data.objects.new('Camera',data); scene.collection.objects.link(camera)
    camera.location=Vector(target)+Vector((12,-12,11.8))
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO'; data.ortho_scale=scale; data.lens=50; scene.camera=camera
    for name,loc,power,color,area in [
        ('Large softbox',(-10,-18,30),4500,'FFE9F5',20),
        ('Rose rim',(20,15,25),2000,'FFD3E7',15),
    ]:
        ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.color=rgba(color)[:3]; ld.shape='DISK'; ld.size=area
        lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc
        lo.rotation_euler=(Vector(target)-lo.location).to_track_quat('-Z','Y').to_euler()
    tree=bpy.data.node_groups.new(scene.name+' / soft bloom','CompositorNodeTree')
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    scene.compositing_node_group=tree
    src=tree.nodes.new('CompositorNodeRLayers'); src.scene=scene
    glare=tree.nodes.new('CompositorNodeGlare')
    glare.inputs['Type'].default_value='Fog Glow'
    glare.inputs['Quality'].default_value='High'
    glare.inputs['Highlights Threshold'].default_value=.8
    glare.inputs['Strength'].default_value=.18
    output=tree.nodes.new('NodeGroupOutput')
    tree.links.new(src.outputs['Image'],glare.inputs['Image']); tree.links.new(glare.outputs['Image'],output.inputs['Image'])
    # Save a useful camera framing when the project is opened interactively.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.color_type='MATERIAL'

def principled(name, color, emission=0, transmission=0, rough=.3):
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=rgba(color)
    mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=rgba(color)
    p.inputs['Emission Color'].default_value=rgba(color)
    p.inputs['Emission Strength'].default_value=emission
    p.inputs['Transmission Weight'].default_value=transmission
    p.inputs['Roughness'].default_value=rough
    p.inputs['IOR'].default_value=1.12
    return mat

def glass(name, color, haze=.13):
    mat=principled(name,color,.22,.90,.35)
    n,l=mat.node_tree.nodes,mat.node_tree.links
    p=n.get('Principled BSDF'); out=n.get('Material Output')
    p.inputs['Coat Weight'].default_value=.05
    trans=n.new('ShaderNodeBsdfTransparent')
    trans.inputs[0].default_value=rgba('FFF1F6')
    mix=n.new('ShaderNodeMixShader'); mix.inputs[0].default_value=.07
    l.new(p.outputs[0],mix.inputs[1]); l.new(trans.outputs[0],mix.inputs[2]); l.new(mix.outputs[0],out.inputs['Surface'])
    absorption=n.new('ShaderNodeVolumeAbsorption')
    absorption.inputs['Color'].default_value=rgba(color)
    absorption.inputs['Density'].default_value=haze
    l.new(absorption.outputs[0],out.inputs['Volume'])
    return mat

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for old in list(bpy.data.scenes)[1:]: bpy.data.scenes.remove(old)
s=bpy.context.scene; s.name='01 • Jelly core — close-up'
shell=glass('01 / Rose jelly body · refraction + soft haze','FFCCE4',.08)
# A filled gelatin body has one boundary instead of a hollow glass-box rim.
n,l=shell.node_tree.nodes,shell.node_tree.links
tex=n.new('ShaderNodeTexCoord'); sep=n.new('ShaderNodeSeparateXYZ'); ramp=n.new('ShaderNodeValToRGB')
l.new(tex.outputs['Generated'],sep.inputs[0]); l.new(sep.outputs['Z'],ramp.inputs[0])
for i,(pos,col) in enumerate([(0,'FFBD96'),(.28,'FFAD95'),(.55,'F4A5C8'),(1,'F5B7D7')]):
    e=ramp.color_ramp.elements[i] if i<2 else ramp.color_ramp.elements.new(pos)
    e.position=pos; e.color=rgba(col)
ramp.color_ramp.interpolation='EASE'
l.new(ramp.outputs[0],n.get('Principled BSDF').inputs['Base Color'])
l.new(ramp.outputs[0],n.get('Principled BSDF').inputs['Emission Color'])
strength=n.new('ShaderNodeMapRange')
strength.inputs['From Min'].default_value=.05
strength.inputs['From Max'].default_value=.48
strength.inputs['To Min'].default_value=.62
strength.inputs['To Max'].default_value=.22
l.new(sep.outputs['Z'],strength.inputs['Value'])
l.new(strength.outputs[0],n.get('Principled BSDF').inputs['Emission Strength'])
shell_top=principled('01b / Soft pink gelatin cap','F4AED5',.60,.10,.38)
core=principled('02 / Dense rose jelly core','DF6EA6',.40,.12,.42)
core_top=principled('03 / Core top · petal pink','F4A8D5',.42,.08,.4)
warm=principled('04 / Apricot light inside base','FFC090',1.1,.25,.48)
layer=glass('05 / Translucent rose stacked base','EA89A7',.22)
layer_core=principled('06 / Lower layer rose insert','C95F83',.28,.28,.33)

def box(name, location, dimensions, mat, bevel=.018, top=None, thickness=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    obj=bpy.context.object; obj.name=name; obj.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(mat)
    if top:
        obj.data.materials.append(top)
        for poly in obj.data.polygons: poly.material_index=1 if poly.normal.z>.5 else 0
    b=obj.modifiers.new('Soft jelly edges','BEVEL'); b.width=bevel; b.segments=4
    if thickness:
        solid=obj.modifiers.new('Physical shell thickness','SOLIDIFY'); solid.thickness=thickness; solid.offset=-1
    obj.modifiers.new('Face normals','WEIGHTED_NORMAL')
    return obj

def jelly(name, center, size, stacked=False):
    x,y,z=center
    outer=box(name+' / outer jelly body',(x,y,z),(size,)*3,shell,size*.012,top=shell_top)
    box(name+' / suspended cubic core',(x,y,z+size*.07),(size*.74,)*3,core,size*.032,top=core_top)
    if stacked:
        box(name+' / lower translucent layer',(x,y,z-size*.75),(size*.985,size*.985,size*.46),layer,size*.013)
        box(name+' / lower rose insert',(x,y,z-size*.78),(size*.79,size*.79,size*.29),layer_core,size*.017)
    return outer

jelly('Hero',(0,0,0),2.5)
setup(s,5.6,(0,0,0),(1000,1000))
s.render.filepath=str(ROOT/'renders'/'03-jelly-core.png')
bpy.ops.render.render(write_still=True)

import os
if not os.environ.get('JELLY_PREVIEW_ONLY'):
    a=bpy.data.scenes.new('02 • Jelly with translucent stacked layers')
    bpy.context.window.scene=a
    jelly('Layer study',(-2.05,-2.05,.25),1.85,True)
    for i in range(3):
        for j in range(3):
            jelly(f'3x3 / {i+1}.{j+1}',(.5+(i-1)*1.06,.5+(j-1)*1.06,.25),.89,True)
    setup(a,10.5,(-.6,-.6,.02),(1500,1000))
    a.render.filepath=str(ROOT/'renders'/'04-jelly-stacked.png')
    bpy.ops.render.render(write_still=True)
    bpy.context.window.scene=s
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blend'/'pink-jelly-v2.blend'))
print('JELLY COMPLETE',ROOT)

