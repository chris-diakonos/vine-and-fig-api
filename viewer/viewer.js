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
  const distance = maxDim / (2 * Math.tan((Math.PI * camera.fov) / 360));

  camera.position.set(center.x + distance, center.y + distance * 0.72, center.z + distance);
  camera.near = Math.max(distance / 100, 0.01);
  camera.far = distance * 100;
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

function renderLayerControls(counts) {
  layerControls.innerHTML = "";
  layerInputs.clear();

  for (const layer of LAYERS) {
    const count = counts.get(layer.id) || 0;
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
    layerControls.appendChild(label);
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
  const camera = new THREE.PerspectiveCamera(42, container.clientWidth / container.clientHeight, 0.1, 1000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

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

  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
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
