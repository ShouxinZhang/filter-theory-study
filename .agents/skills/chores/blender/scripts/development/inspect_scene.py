"""由 Blender 内置 Python 运行，读取场景摘要。"""
import argparse
from pathlib import Path
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import add_confirmation, require_confirmation, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    add_confirmation(parser)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    require_confirmation(parser, args)
    scenes = []
    for scene in bpy.data.scenes:
        scenes.append({'name': scene.name, 'engine': scene.render.engine,
                       'camera': scene.camera.name if scene.camera else None,
                       'resolution': [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
                       'objects': [{'name': obj.name, 'type': obj.type,
                                    'materials': [slot.material.name if slot.material else None for slot in obj.material_slots]}
                                   for obj in scene.objects]})
    write_json(args.output, {'blender_version': bpy.app.version_string,
                           'source': bpy.data.filepath, 'scenes': scenes})


if __name__ == '__main__':
    main()
