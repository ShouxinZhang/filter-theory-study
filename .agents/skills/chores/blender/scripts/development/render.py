"""由 Blender 内置 Python 渲染单帧；参数仅作用于本次进程。"""
import argparse
from pathlib import Path
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import add_confirmation, require_confirmation, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene')
    parser.add_argument('--camera')
    parser.add_argument('--frame', type=int)
    parser.add_argument('--width', type=int, default=256)
    parser.add_argument('--height', type=int, default=256)
    parser.add_argument('--samples', type=int, default=8)
    parser.add_argument('--engine', choices=['CYCLES', 'BLENDER_EEVEE'])
    parser.add_argument('--output', type=Path, required=True, help='新建 PNG 文件')
    add_confirmation(parser)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    require_confirmation(parser, args)
    if min(args.width, args.height, args.samples) < 1:
        parser.error('尺寸与采样数必须为正')
    scene = bpy.data.scenes.get(args.scene) if args.scene else bpy.context.scene
    if scene is None:
        parser.error('场景不存在')
    if args.camera:
        camera = scene.objects.get(args.camera)
        if camera is None or camera.type != 'CAMERA':
            parser.error('所选相机不存在于场景中')
        scene.camera = camera
    if scene.camera is None:
        parser.error('场景缺少相机')
    output = args.output.expanduser().resolve()
    report = output.with_suffix('.render.json')
    if output.suffix.lower() != '.png' or output.exists() or report.exists():
        parser.error('输出必须是尚不存在的 PNG，报告路径也须可用')
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.engine:
        scene.render.engine = args.engine
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = args.samples
        scene.cycles.device = 'CPU'
    if args.frame is not None:
        scene.frame_set(args.frame)
    scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    if not output.is_file():
        raise RuntimeError('渲染返回后未找到目标 PNG')
    write_json(report, {'source': bpy.data.filepath, 'scene': scene.name,
                        'engine': scene.render.engine, 'frame': scene.frame_current,
                        'resolution': [args.width, args.height], 'output': str(output),
                        'samples': scene.cycles.samples if scene.render.engine == 'CYCLES' else None,
                        'source_saved': False})


if __name__ == '__main__':
    main()
