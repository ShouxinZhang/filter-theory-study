"""独立黑金校徽案例；从随附矢量重建工程和两张预览。"""
import sys,argparse
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
from svg_paths import read_emblem
from emblem_geometry import create_emblem
p=argparse.ArgumentParser();p.add_argument('--user-confirmed',action='store_true');p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--resolution',type=int,default=1000);p.add_argument('--samples',type=int,default=96)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);assert a.user_confirmed;a.output_dir.mkdir(parents=True,exist_ok=False)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.name='HIT | independent metal emblem';scene.render.engine='CYCLES';scene.cycles.samples=a.samples;scene.cycles.use_denoising=True
scene.render.resolution_x=a.resolution;scene.render.resolution_y=a.resolution;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'

def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=m.diffuse_color;b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;return m
silver=material('Gold | warm polished relief',(.83,.48,.12),1,.24)
dark=material('Black | satin recessed field',(.004,.0045,.005),.05,.40)
dark.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.14
paths=read_emblem(Path(__file__).parents[1]/'source/emblem.svg');parts=create_emblem(paths,silver,dark)
root=bpy.data.objects.new('HIT emblem | assembly',None);scene.collection.objects.link(root)
for part in parts:part.parent=root
# 独立徽章置于浅灰摄影台；衬底承接断开的窗格与字符。
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.135));stage=bpy.context.object;stage.name='Stage | cool matte';stage.data.materials.append(material('Stage | pale grey',(.62,.69,.75),0,.6))
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.82,.82,.82,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.32

def light(name,loc,power,size,sy,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='RECTANGLE';data.size=size;data.size_y=sy;data.color=color
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
light('Softbox | left',(-3,4,6),1000,4,5,(1,.97,.92))
light('Strip | right',(4,1,4),800,1,5,(1,.94,.85))
light('Strip | front',(-1,-4,5),500,5,1,(1,1,1))
camdata=bpy.data.cameras.new('Camera | product');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=(2.5,-4,11)
f=(-cam.location).normalized();r=f.cross(Vector((0,1,0))).normalized();u=r.cross(f);cam.rotation_euler=Matrix((r,u,-f)).transposed().to_euler();camdata.type='ORTHO';camdata.ortho_scale=6.15;scene.camera=cam
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA'
notes=bpy.data.texts.new('SOURCE AND DESIGN');notes.write('HIT 中文校徽；矢量源：https://zh.wikipedia.org/wiki/File:Harbin_Institute_of_Technology_logo.svg\n原页面注明提取自哈工大百年标识手册。校徽权利归校方。\n本次创意：暖金分层浮雕、黑色缎面衬底、摄影布光。非校方官方文创，非制造用闭合单体。\n275 个矢量路径保持可编辑。')
# 第二个相机可用于正面核对校徽细节。
frontdata=camdata.copy();front=bpy.data.objects.new('Camera | front detail',frontdata);scene.collection.objects.link(front);front.location=(0,0,12);front.rotation_euler=(0,0,0);frontdata.ortho_scale=5.65
scene.render.filepath='//preview.png';bpy.ops.wm.save_as_mainfile(filepath=str(a.output_dir/'scene.blend'));bpy.ops.render.render(write_still=True)

scene.camera=front;scene.render.filepath=str(a.output_dir/'front.png');bpy.ops.render.render(write_still=True)
