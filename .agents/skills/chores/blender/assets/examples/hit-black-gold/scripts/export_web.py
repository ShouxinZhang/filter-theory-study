"""将黑金徽章烘焙为两种材质的网格，单独导出网页 GLB。"""
import bpy,argparse,sys,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--user-confirmed',action='store_true');p.add_argument('--output',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);assert a.user_confirmed
root=bpy.data.objects['HIT emblem | assembly'];objects=list(root.children)
bpy.ops.object.select_all(action='DESELECT')
# 适度降低曲线采样，保留所有轮廓和倒角，控制下载体积。
for ob in objects:
    if ob.type=='CURVE':ob.data.resolution_u=6;ob.data.bevel_resolution=2
    ob.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.convert(target='MESH')
meshes=list(bpy.context.selected_objects);groups={}
for ob in meshes:groups.setdefault(ob.data.materials[0].name,[]).append(ob)
merged=[]
for material,group in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for ob in group:ob.select_set(True)
    bpy.context.view_layer.objects.active=group[0];bpy.ops.object.join();ob=bpy.context.object;ob.name=material
    # 保留世界变换后解除父级，避免导出相机/灯光。
    matrix=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=matrix;merged.append(ob)
bpy.ops.object.select_all(action='DESELECT')
for ob in merged:ob.select_set(True)
a.output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(a.output),export_format='GLB',use_selection=True,export_cameras=False,export_lights=False,export_apply=True,export_yup=True)
summary={'meshes':len(merged),'vertices':sum(len(o.data.vertices) for o in merged),'polygons':sum(len(o.data.polygons) for o in merged),'bytes':a.output.stat().st_size,'materials':[o.data.materials[0].name for o in merged]}
a.output.with_suffix('.json').write_text(json.dumps(summary,indent=2));print(summary)
