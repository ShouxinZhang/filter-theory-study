"""校徽浮雕与承托层；原始贝塞尔保持可编辑。"""
import bpy


def curve_object(name,contours,material,depth,bevel,z):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='2D';data.fill_mode='BOTH';data.resolution_u=12
    data.extrude=depth/2;data.bevel_depth=bevel;data.bevel_resolution=3
    for contour in contours:
        if len(contour)<3:continue
        s=data.splines.new('BEZIER');s.bezier_points.add(len(contour)-1);s.use_cyclic_u=True
        for pt,item in zip(s.bezier_points,contour):
            pt.co=(*item['co'],0);pt.handle_left_type='FREE';pt.handle_right_type='FREE';pt.handle_left=(*item['left'],0);pt.handle_right=(*item['right'],0)
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location.z=z;data.materials.append(material);return ob


def area(contour):
    p=[x['co'] for x in contour];return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2)


def create_emblem(paths,silver,dark):
    # 建筑和书页衬底使用原矢量的最大外轮廓，避免凭空重画边界。
    parts=[]
    for idx in [270,271]:
        outer=max(paths[idx],key=area)
        parts.append(curve_object(f'Backing | source silhouette {idx}',[outer],dark,.10,.004,-.057))
    bpy.ops.mesh.primitive_cylinder_add(vertices=192,radius=1.88,depth=.11,location=(0,.025,-.059))
    disc=bpy.context.object;disc.name='Backing | charcoal inner field';disc.data.materials.append(dark)
    bevel=disc.modifiers.new('Soft backing edge','BEVEL');bevel.width=.012;bevel.segments=3;disc.modifiers.new('Normals','WEIGHTED_NORMAL');parts.append(disc)
    for i,contours in enumerate(paths):
        depth=.09 if i in [0,1,271] else .065 if i in [2,3,4,5,272,273,274] else .040
        label='Architecture' if 6<=i<=270 else 'Gear' if i<2 else '1920' if i<6 else 'Book' if i==271 else 'Chinese name'
        parts.append(curve_object(f'{label} | vector {i:03}',contours,silver,depth,.0015,depth/2+.003))
    return parts
