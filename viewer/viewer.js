import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const LAYERS = [
  { id: "foundation", label: "Foundation", patterns: ["foundation"] },
  {
    id: "framing",
    label: "Framing",
    patterns: [
      "sill",
      "post",
      "joist",
      "brace",
      "bay_stud",
      "cripple_stud",
      "stud",
      "girt",
      "plate",
      "false_plate",
      "rafter"
    ]
  },
  { id: "floors", label: "Floors", patterns: ["floor", "plank"] },
  { id: "sheathing", label: "Sheathing", patterns: ["sheathing", "weatherboard"] },
  { id: "roof", label: "Roof", patterns: ["roof"] },
  { id: "windows", label: "Windows", patterns: ["window"] },
  { id: "doors", label: "Doors", patterns: ["door"] },
  { id: "cornice", label: "Cornice", patterns: ["cornice", "crown", "bed_molding", "cavetto"] },
  { id: "other", label: "Other", patterns: [] }
];

const container = document.getElementById("viewer-canvas");
const artifactLabel = document.getElementById("artifact-label");
const commitInfo = document.getElementById("commit-info");
const structureHash = document.getElementById("structure-hash");
const meshHash = document.getElementById("mesh-hash");
const downloadLink = document.getElementById("download-link");
const bomLink = document.getElementById("bom-link");
const errorMessage = document.getElementById("error-message");
const statusMessage = document.getElementById("model-status");
const layerControls = document.getElementById("layer-controls");
const showAllButton = document.getElementById("show-all");

const layerState = new Map(LAYERS.map((layer) => [layer.id, true]));
const layerInputs = new Map();
let modelRoot = null;

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
  statusMessage.hidden = true;
  artifactLabel.textContent = "Unable to load model";
}

function setStatus(message) {
  statusMessage.textContent = message;
  statusMessage.hidden = false;
}

function createRenderer() {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  container.appendChild(renderer.domElement);
  return renderer;
}

function createScene() {
  const scene = new THREE.Scene();
  scene.background = null;

  const ambient = new THREE.HemisphereLight(0xffffff, 0x65746d, 2.1);
  scene.add(ambient);

  const key = new THREE.DirectionalLight(0xffffff, 2.3);
  key.position.set(6, 8, 10);
  key.castShadow = true;
  scene.add(key);

  const fill = new THREE.DirectionalLight(0xddeee8, 1.1);
  fill.position.set(-8, 4, -6);
  scene.add(fill);

  return scene;
}

function fitCameraToObject(camera, controls, object) {
  const box = new THREE.Box3().setFromObject(object);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z);
  
  if (camera.isPerspectiveCamera) {
    const distance = maxDim / (2 * Math.tan((Math.PI * camera.fov) / 360));
    camera.position.set(center.x + distance, center.y + distance * 0.72, center.z + distance);
    camera.near = Math.max(distance / 100, 0.01);
    camera.far = distance * 100;
  } else {
    // Orthographic camera
    const aspect = camera.right / camera.top;
    const frustumSize = maxDim * 1.2;
    camera.left = -frustumSize * aspect / 2;
    camera.right = frustumSize * aspect / 2;
    camera.top = frustumSize / 2;
    camera.bottom = -frustumSize / 2;
    camera.near = -maxDim * 10;
    camera.far = maxDim * 10;
  }
  
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

function fitCameraToVisible(camera, controls, scene) {
  const box = new THREE.Box3();
  let hasVisibleObjects = false;
  
  scene.traverse((object) => {
    if (object.isMesh && object.visible) {
      box.expandByObject(object);
      hasVisibleObjects = true;
    }
  });
  
  if (!hasVisibleObjects) {
    return;
  }
  
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z);
  
  if (camera.isPerspectiveCamera) {
    const distance = maxDim / (2 * Math.tan((Math.PI * camera.fov) / 360));
    const dir = new THREE.Vector3().subVectors(camera.position, controls.target).normalize();
    camera.position.copy(center).add(dir.multiplyScalar(distance * 1.5));
    camera.near = Math.max(distance / 100, 0.01);
    camera.far = distance * 100;
  } else {
    // Orthographic camera
    const aspect = camera.right / camera.top;
    const frustumSize = maxDim * 1.2;
    camera.left = -frustumSize * aspect / 2;
    camera.right = frustumSize * aspect / 2;
    camera.top = frustumSize / 2;
    camera.bottom = -frustumSize / 2;
    camera.near = -maxDim * 10;
    camera.far = maxDim * 10;
  }
  
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

function setOrthographicView(camera, controls, scene, viewType) {
  // Calculate bounding box of visible objects
  const box = new THREE.Box3();
  let hasVisibleObjects = false;
  
  scene.traverse((object) => {
    if (object.isMesh && object.visible) {
      box.expandByObject(object);
      hasVisibleObjects = true;
    }
  });
  
  if (!hasVisibleObjects) {
    return;
  }
  
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z);
  
  // Set up orthographic projection
  const aspect = container.clientWidth / container.clientHeight;
  const frustumSize = maxDim * 1.2;
  camera.left = -frustumSize * aspect / 2;
  camera.right = frustumSize * aspect / 2;
  camera.top = frustumSize / 2;
  camera.bottom = -frustumSize / 2;
  camera.near = -maxDim * 10;
  camera.far = maxDim * 10;
  
  // Set camera position based on view type
  const distance = maxDim * 2;
  switch (viewType) {
    case 'front':
      // Front elevation: looking along +Y axis
      camera.position.set(center.x, center.y + distance, center.z);
      camera.up.set(0, 0, 1);
      break;
    case 'rear':
      // Rear elevation: looking along -Y axis
      camera.position.set(center.x, center.y - distance, center.z);
      camera.up.set(0, 0, 1);
      break;
    case 'left':
      // Left elevation: looking along +X axis
      camera.position.set(center.x + distance, center.y, center.z);
      camera.up.set(0, 0, 1);
      break;
    case 'right':
      // Right elevation: looking along -X axis
      camera.position.set(center.x - distance, center.y, center.z);
      camera.up.set(0, 0, 1);
      break;
  }
  
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

function lineageName(object) {
  const names = [];
  let current = object;
  while (current) {
    if (current.name) {
      names.push(current.name.toLowerCase());
    }
    current = current.parent;
  }
  return names.join(" ");
}

function inferLayer(object) {
  const name = lineageName(object);
  for (const layer of LAYERS) {
    if (layer.id === "other") {
      continue;
    }
    if (layer.patterns.some((pattern) => name.includes(pattern))) {
      return layer.id;
    }
  }
  return "other";
}

function applyLayerVisibility() {
  if (!modelRoot) {
    return;
  }

  modelRoot.traverse((object) => {
    if (object.isMesh && object.userData.layer) {
      object.visible = layerState.get(object.userData.layer) !== false;
    }
  });
}

const layerGhostState = new Map(LAYERS.map((layer) => [layer.id, false]));

function applyLayerOpacity() {
  if (!modelRoot) {
    return;
  }

  modelRoot.traverse((object) => {
    if (object.isMesh && object.userData.layer) {
      const isGhost = layerGhostState.get(object.userData.layer);
      if (object.material) {
        object.material.transparent = isGhost;
        object.material.opacity = isGhost ? 0.2 : 1.0;
        object.material.needsUpdate = true;
      }
    }
  });
}

function soloLayer(layerId) {
  // Hide all layers except the selected one
  for (const layer of LAYERS) {
    const shouldBeVisible = layer.id === layerId;
    layerState.set(layer.id, shouldBeVisible);
    const input = layerInputs.get(layer.id);
    if (input) {
      input.checked = shouldBeVisible;
    }
  }
  applyLayerVisibility();
}

function renderLayerControls(counts) {
  layerControls.innerHTML = "";
  layerInputs.clear();

  for (const layer of LAYERS) {
    const count = counts.get(layer.id) || 0;
    const wrapper = document.createElement("div");
    wrapper.className = "layer-item";
    
    const label = document.createElement("label");
    label.className = "layer-toggle";

    const labelText = document.createElement("span");
    labelText.textContent = layer.label;

    const meta = document.createElement("span");
    meta.className = "layer-count";
    meta.textContent = `${count}`;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = layerState.get(layer.id) !== false;
    checkbox.disabled = count === 0;
    checkbox.addEventListener("change", () => {
      layerState.set(layer.id, checkbox.checked);
      applyLayerVisibility();
    });

    const textWrap = document.createElement("span");
    textWrap.append(labelText, meta);
    label.append(textWrap, checkbox);
    
    // Add solo and ghost buttons
    const actionButtons = document.createElement("div");
    actionButtons.className = "layer-actions";
    
    const soloBtn = document.createElement("button");
    soloBtn.textContent = "S";
    soloBtn.title = "Solo this layer";
    soloBtn.className = "layer-action-btn";
    soloBtn.disabled = count === 0;
    soloBtn.addEventListener("click", () => soloLayer(layer.id));
    
    const ghostBtn = document.createElement("button");
    ghostBtn.textContent = "G";
    ghostBtn.title = "Ghost this layer";
    ghostBtn.className = "layer-action-btn";
    ghostBtn.disabled = count === 0;
    ghostBtn.addEventListener("click", () => {
      const isGhost = !layerGhostState.get(layer.id);
      layerGhostState.set(layer.id, isGhost);
      ghostBtn.classList.toggle("active", isGhost);
      applyLayerOpacity();
    });
    
    actionButtons.append(soloBtn, ghostBtn);
    wrapper.append(label, actionButtons);
    layerControls.appendChild(wrapper);
    layerInputs.set(layer.id, checkbox);
  }
}

async function loadManifest() {
  const response = await fetch("./manifest.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Manifest request failed with ${response.status}`);
  }
  return response.json();
}

async function main() {
  const renderer = createRenderer();
  const scene = createScene();
  
  // Create both perspective and orthographic cameras
  let camera = new THREE.PerspectiveCamera(42, container.clientWidth / container.clientHeight, 0.1, 1000);
  const perspectiveCamera = camera;
  const orthographicCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 1000);
  
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  
  // Camera view buttons
  const viewPerspectiveBtn = document.getElementById("view-perspective");
  const viewFrontBtn = document.getElementById("view-front");
  const viewRearBtn = document.getElementById("view-rear");
  const viewLeftBtn = document.getElementById("view-left");
  const viewRightBtn = document.getElementById("view-right");
  const fitVisibleBtn = document.getElementById("fit-visible");
  
  viewPerspectiveBtn.addEventListener("click", () => {
    camera = perspectiveCamera;
    controls.object = camera;
    if (modelRoot) {
      fitCameraToObject(camera, controls, modelRoot);
    }
  });
  
  viewFrontBtn.addEventListener("click", () => {
    camera = orthographicCamera;
    controls.object = camera;
    setOrthographicView(camera, controls, scene, 'front');
  });
  
  viewRearBtn.addEventListener("click", () => {
    camera = orthographicCamera;
    controls.object = camera;
    setOrthographicView(camera, controls, scene, 'rear');
  });
  
  viewLeftBtn.addEventListener("click", () => {
    camera = orthographicCamera;
    controls.object = camera;
    setOrthographicView(camera, controls, scene, 'left');
  });
  
  viewRightBtn.addEventListener("click", () => {
    camera = orthographicCamera;
    controls.object = camera;
    setOrthographicView(camera, controls, scene, 'right');
  });
  
  fitVisibleBtn.addEventListener("click", () => {
    fitCameraToVisible(camera, controls, scene);
  });

  showAllButton.addEventListener("click", () => {
    for (const layer of LAYERS) {
      layerState.set(layer.id, true);
      const input = layerInputs.get(layer.id);
      if (input) {
        input.checked = true;
      }
    }
    applyLayerVisibility();
  });
  
  // Measurement tape functionality
  let measurementGroup = null;
  let measurementsVisible = false;
  const toggleMeasurementsBtn = document.getElementById("toggle-measurements");
  
  function createMeasurements() {
    if (!modelRoot) return null;
    
    const box = new THREE.Box3().setFromObject(modelRoot);
    const size = box.getSize(new THREE.Vector3());
    const min = box.min;
    const max = box.max;
    
    const group = new THREE.Group();
    group.name = "measurements";
    
    // Helper to create a dimension line
    function createDimensionLine(start, end, label, color = 0xff0000) {
      const points = [start, end];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const material = new THREE.LineBasicMaterial({ color, linewidth: 2 });
      const line = new THREE.Line(geometry, material);
      
      // Add arrow caps
      const arrowSize = Math.min(size.x, size.y, size.z) * 0.02;
      const dir = new THREE.Vector3().subVectors(end, start).normalize();
      
      // Create text label using sprite
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      canvas.width = 256;
      canvas.height = 64;
      context.fillStyle = 'white';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.font = 'Bold 32px Arial';
      context.fillStyle = 'black';
      context.textAlign = 'center';
      context.textBaseline = 'middle';
      context.fillText(label, canvas.width / 2, canvas.height / 2);
      
      const texture = new THREE.CanvasTexture(canvas);
      const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
      const sprite = new THREE.Sprite(spriteMaterial);
      const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
      sprite.position.copy(midpoint);
      const scale = Math.max(size.x, size.y, size.z) * 0.1;
      sprite.scale.set(scale, scale * 0.25, 1);
      
      const dimGroup = new THREE.Group();
      dimGroup.add(line);
      dimGroup.add(sprite);
      
      return dimGroup;
    }
    
    // Add width dimension (X axis)
    const widthLabel = `${size.x.toFixed(1)}"`;
    const widthLine = createDimensionLine(
      new THREE.Vector3(min.x, min.y - size.y * 0.1, min.z),
      new THREE.Vector3(max.x, min.y - size.y * 0.1, min.z),
      widthLabel,
      0xff0000
    );
    group.add(widthLine);
    
    // Add depth dimension (Y axis)
    const depthLabel = `${size.y.toFixed(1)}"`;
    const depthLine = createDimensionLine(
      new THREE.Vector3(min.x - size.x * 0.1, min.y, min.z),
      new THREE.Vector3(min.x - size.x * 0.1, max.y, min.z),
      depthLabel,
      0x00ff00
    );
    group.add(depthLine);
    
    // Add height dimension (Z axis)
    const heightLabel = `${size.z.toFixed(1)}"`;
    const heightLine = createDimensionLine(
      new THREE.Vector3(max.x + size.x * 0.1, min.y, min.z),
      new THREE.Vector3(max.x + size.x * 0.1, min.y, max.z),
      heightLabel,
      0x0000ff
    );
    group.add(heightLine);
    
    return group;
  }
  
  function toggleMeasurements() {
    if (!modelRoot) return;
    
    if (measurementsVisible) {
      if (measurementGroup) {
        scene.remove(measurementGroup);
        measurementGroup = null;
      }
      measurementsVisible = false;
      toggleMeasurementsBtn.classList.remove("active");
    } else {
      measurementGroup = createMeasurements();
      if (measurementGroup) {
        scene.add(measurementGroup);
        measurementsVisible = true;
        toggleMeasurementsBtn.classList.add("active");
      }
    }
  }
  
  toggleMeasurementsBtn.addEventListener("click", toggleMeasurements);
  
  window.addEventListener("resize", () => {
    const aspect = container.clientWidth / container.clientHeight;
    
    // Update perspective camera
    perspectiveCamera.aspect = aspect;
    perspectiveCamera.updateProjectionMatrix();
    
    // Update orthographic camera
    if (orthographicCamera.top > 0) {
      const frustumHeight = orthographicCamera.top * 2;
      orthographicCamera.left = -frustumHeight * aspect / 2;
      orthographicCamera.right = frustumHeight * aspect / 2;
      orthographicCamera.updateProjectionMatrix();
    }
    
    renderer.setSize(container.clientWidth, container.clientHeight);
  });

  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });

  try {
    const manifest = await loadManifest();
    const glbUrl = manifest?.artifacts?.glb?.url;
    const bomUrl = manifest?.artifacts?.bom?.url;

    if (!glbUrl) {
      throw new Error("Manifest does not include artifacts.glb.url");
    }

    downloadLink.href = glbUrl;
    if (bomUrl) {
      bomLink.href = bomUrl;
    }

    const hash = manifest.structure_hash || "unknown";
    const commit = manifest.commit_sha || "unknown";
    const meshHashValue = manifest.mesh_sha256 || "unknown";
    
    artifactLabel.textContent = `Artifact ${hash}`;
    commitInfo.textContent = `Commit: ${commit.substring(0, 8)}`;
    structureHash.textContent = `Structure hash: ${hash}`;
    meshHash.textContent = `Mesh hash: ${meshHashValue.substring(0, 16)}...`;

    const loader = new GLTFLoader();
    const gltf = await loader.loadAsync(glbUrl, (event) => {
      if (event.total > 0) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setStatus(`Loading GLB... ${percent}%`);
      }
    });

    modelRoot = gltf.scene;
    const counts = new Map(LAYERS.map((layer) => [layer.id, 0]));
    modelRoot.traverse((object) => {
      if (object.isMesh) {
        object.castShadow = true;
        object.receiveShadow = true;
        object.userData.layer = inferLayer(object);
        counts.set(object.userData.layer, (counts.get(object.userData.layer) || 0) + 1);
      }
    });

    scene.add(modelRoot);
    renderLayerControls(counts);
    fitCameraToObject(camera, controls, modelRoot);
    statusMessage.hidden = true;
  } catch (error) {
    showError(error.message || "Could not load GLB");
  }
}

main();
