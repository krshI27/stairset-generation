import * as THREE from 'three';

const treadMaterial = new THREE.MeshStandardMaterial({ color: 0x9b7c4e, roughness: 0.55, metalness: 0.05 });
const riserMaterial = new THREE.MeshStandardMaterial({ color: 0x7f6a52, roughness: 0.7, metalness: 0.03 });
const railMaterial = new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.35, metalness: 0.8 });

export function buildStairset(params) {
    const group = new THREE.Group();
    const { stepCount, stepWidth, stepDepth, stepHeight, landingIndex, landingDepth, enableHandrail } = params;

    const actualLandingIndex = Math.min(Math.max(landingIndex, 0), stepCount);
    let currentDepth = 0;

    for (let index = 0; index < stepCount; index += 1) {
        const stepElevation = index * stepHeight;

        const tread = new THREE.Mesh(
            new THREE.BoxGeometry(stepWidth, 0.04, stepDepth),
            treadMaterial
        );
        tread.position.set(stepWidth / 2 - stepWidth / 2, stepElevation + 0.02, currentDepth + stepDepth / 2);
        group.add(tread);

        const riser = new THREE.Mesh(
            new THREE.BoxGeometry(stepWidth, stepHeight, 0.04),
            riserMaterial
        );
        riser.position.set(stepWidth / 2 - stepWidth / 2, stepElevation + stepHeight / 2, currentDepth + 0.02);
        group.add(riser);

        currentDepth += stepDepth;

        if (index + 1 === actualLandingIndex) {
            const landing = new THREE.Mesh(
                new THREE.BoxGeometry(stepWidth, 0.04, landingDepth),
                treadMaterial
            );
            landing.position.set(stepWidth / 2 - stepWidth / 2, stepElevation + 0.02, currentDepth + landingDepth / 2);
            group.add(landing);
            currentDepth += landingDepth;
        }
    }

    if (enableHandrail) {
        const handRailClearance = 0.9;
        const railRadius = 0.025;

        // Collect one post per step, centered on each tread
        const postData = [];
        let depthAccum = 0;
        for (let i = 0; i < stepCount; i += 1) {
            const treadTopY = i * stepHeight + 0.04;
            const postZ = depthAccum + stepDepth / 2;
            postData.push({ z: postZ, footY: treadTopY, topY: treadTopY + handRailClearance });
            depthAccum += stepDepth;
            if (i + 1 === actualLandingIndex) {
                depthAccum += landingDepth;
            }
        }

        // Add vertical posts whose feet sit on each tread surface
        for (const p of postData) {
            const post = new THREE.Mesh(
                new THREE.CylinderGeometry(0.03, 0.03, handRailClearance, 12),
                railMaterial
            );
            post.position.set(stepWidth - 0.05, p.footY + handRailClearance / 2, p.z);
            group.add(post);
        }

        // Add slanted rail connecting first post top to last post top
        if (postData.length >= 2) {
            const first = postData[0];
            const last = postData[postData.length - 1];
            const start = new THREE.Vector3(stepWidth - 0.05, first.topY, first.z);
            const end = new THREE.Vector3(stepWidth - 0.05, last.topY, last.z);
            const mid = new THREE.Vector3().lerpVectors(start, end, 0.5);
            const dir = new THREE.Vector3().subVectors(end, start);
            const railLen = dir.length();
            const rail = new THREE.Mesh(
                new THREE.CylinderGeometry(railRadius, railRadius, railLen, 16),
                railMaterial
            );
            rail.position.copy(mid);
            rail.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
            group.add(rail);
        }
    }

    group.position.set(-stepWidth / 2, 0, 0);
    return group;
}
