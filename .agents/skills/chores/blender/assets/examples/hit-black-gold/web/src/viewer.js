import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// 网页只读取导出的几何；原始 Blender 工程不参与运行。
export async function createViewer(container, onProgress) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.setClearColor(0x000000, 0);
  const canvas = renderer.domElement;
  canvas.tabIndex = 0;
  canvas.setAttribute('aria-label', '黑金校徽：拖动旋转，滚轮缩放，右键平移');
  container.prepend(canvas);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, .1, 100);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = .08;
  controls.minDistance = 3;
  controls.maxDistance = 22;
  controls.autoRotateSpeed = 1;
  controls.maxTargetRadius = 7;
  controls.listenToKeyEvents(canvas);

  // 本地生成摄影棚环境，不依赖远程 HDR 文件。
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const env = pmrem.fromScene(room, .04);
  scene.environment = env.texture;
  scene.environmentIntensity = .9;
  room.dispose(); pmrem.dispose();
  const key = new THREE.DirectionalLight(0xfff0d0, 2.2);
  key.position.set(-3, 5, 8);scene.add(key);
  const fill = new THREE.DirectionalLight(0xe4eaff, 1);
  fill.position.set(4, 0, 3);scene.add(fill);

  let model, startDistance = 10;
  function resize() {
    const previousFit = startDistance;
    const w = container.clientWidth, h = container.clientHeight;
    renderer.setSize(w, h, false);camera.aspect = w/h;camera.updateProjectionMatrix();
    startDistance = Math.max(9.8, 5.9 / camera.aspect / (2 * Math.tan(THREE.MathUtils.degToRad(17.5))));
    controls.maxDistance = Math.max(22, startDistance * 3);
    if (model) {camera.position.sub(controls.target).multiplyScalar(startDistance/previousFit).add(controls.target);controls.update();}
  }
  const observer = new ResizeObserver(resize);observer.observe(container);resize();
  function view(name) {
    const damping = controls.enableDamping;
    controls.enableDamping = false;controls.update(); // 清掉拖动惯性，再精确复位。
    controls.target.set(0, 0, 0);
    const direction = name === 'front' ? new THREE.Vector3(0,0,1) : name === 'back' ? new THREE.Vector3(0,0,-1) : new THREE.Vector3(.20,.26,1).normalize();
    camera.position.copy(direction.multiplyScalar(startDistance));camera.up.set(0,1,0);controls.update();controls.enableDamping=damping;
  }
  view('angled');
  let running = true, last = performance.now();
  renderer.setAnimationLoop(now => {
    if (!running || document.hidden) return;
    controls.update(Math.min((now-last)/1000, .05));last=now;renderer.render(scene,camera);
  });
  try {
    const gltf = await new GLTFLoader().loadAsync('./assets/hit-black-gold.glb', event => onProgress(event.total ? Math.round(event.loaded/event.total*100) : null));
    model = gltf.scene;model.rotation.x = Math.PI/2;model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model);model.position.sub(box.getCenter(new THREE.Vector3()));
    model.traverse(obj => {if(obj.isMesh){obj.material.side=THREE.DoubleSide;}});
    scene.add(model);view('angled');
  } catch(error) {
    running=false;renderer.setAnimationLoop(null);controls.dispose();observer.disconnect();env.dispose();renderer.dispose();canvas.remove();throw error;
  }
  return {
    view,
    setAutoRotate(value) {controls.autoRotate=value;},
    onManual(callback) {controls.addEventListener('start',callback);},
    dispose() {running=false;renderer.setAnimationLoop(null);controls.dispose();observer.disconnect();env.dispose();renderer.dispose();},
  };
}
