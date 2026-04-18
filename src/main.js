import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { buildStairset } from './geometry.js';

const container = document.getElementById('viewer');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0d12);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(container.clientWidth, container.clientHeight);
container.appendChild(renderer.domElement);

const perspectiveCamera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 100);
perspectiveCamera.position.set(2, 1.6, 3);

const orthographicCamera = new THREE.OrthographicCamera(
    container.clientWidth / -800,
    container.clientWidth / 800,
    container.clientHeight / 800,
    container.clientHeight / -800,
    0.1,
    200
);
orthographicCamera.position.set(2, 1.6, 3);

let activeCamera = perspectiveCamera;

const controls = new OrbitControls(activeCamera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0.4, 0.5);
controls.update();

const ambient = new THREE.HemisphereLight(0xffffff, 0x252a35, 0.9);
scene.add(ambient);

const sun = new THREE.DirectionalLight(0xffffff, 0.9);
sun.position.set(2, 5, 3);
sun.castShadow = true;
scene.add(sun);

const grid = new THREE.GridHelper(10, 20, 0x44475a, 0x11151a);
scene.add(grid);

const state = {
    stepCount: 8,
    stepWidth: 1.0,
    stepDepth: 0.3,
    stepHeight: 0.18,
    landingIndex: 0,
    landingDepth: 1.0,
    enableHandrail: true,
    projectionMode: 'perspective',
};

let stairGroup = null;

const inputs = {
    stepCount: document.getElementById('stepCount'),
    stepWidth: document.getElementById('stepWidth'),
    stepDepth: document.getElementById('stepDepth'),
    stepHeight: document.getElementById('stepHeight'),
    landingIndex: document.getElementById('landingIndex'),
    landingDepth: document.getElementById('landingDepth'),
    enableHandrail: document.getElementById('enableHandrail'),
    projectionMode: document.getElementById('projectionMode'),
    resetView: document.getElementById('resetView'),
};

function parseInputs() {
    state.stepCount = parseInt(inputs.stepCount.value, 10) || 1;
    state.stepWidth = parseFloat(inputs.stepWidth.value) || 1.0;
    state.stepDepth = parseFloat(inputs.stepDepth.value) || 0.3;
    state.stepHeight = parseFloat(inputs.stepHeight.value) || 0.18;
    state.landingIndex = parseInt(inputs.landingIndex.value, 10) || 0;
    state.landingDepth = parseFloat(inputs.landingDepth.value) || 1.0;
    state.enableHandrail = inputs.enableHandrail.checked;
    state.projectionMode = inputs.projectionMode.value;
}

function refreshStairset() {
    if (stairGroup) {
        scene.remove(stairGroup);
        stairGroup.traverse((child) => {
            if (child.geometry) child.geometry.dispose();
            if (child.material) child.material.dispose();
        });
    }

    const stair = buildStairset(state);
    stairGroup = stair;
    scene.add(stairGroup);
}

function updateCameraMode() {
    const width = container.clientWidth;
    const height = container.clientHeight;
    if (state.projectionMode === 'orthographic') {
        orthographicCamera.left = width / -800;
        orthographicCamera.right = width / 800;
        orthographicCamera.top = height / 800;
        orthographicCamera.bottom = height / -800;
        orthographicCamera.updateProjectionMatrix();
        activeCamera = orthographicCamera;
    } else {
        perspectiveCamera.aspect = width / height;
        perspectiveCamera.updateProjectionMatrix();
        activeCamera = perspectiveCamera;
    }
    controls.object = activeCamera;
    controls.update();
}

function onInputChange() {
    parseInputs();
    refreshStairset();
    updateCameraMode();
}

Object.values(inputs).forEach((input) => {
    if (input.tagName === 'BUTTON') return;
    input.addEventListener('input', onInputChange);
    input.addEventListener('change', onInputChange);
});

inputs.resetView.addEventListener('click', () => {
    controls.target.set(0, 0.4, 0.5);
    activeCamera.position.set(2, 1.6, 3);
    controls.update();
});

window.addEventListener('resize', () => {
    const width = container.clientWidth;
    const height = container.clientHeight;
    renderer.setSize(width, height);
    perspectiveCamera.aspect = width / height;
    perspectiveCamera.updateProjectionMatrix();
    updateCameraMode();
});

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, activeCamera);
}

parseInputs();
refreshStairset();
updateCameraMode();
animate();
