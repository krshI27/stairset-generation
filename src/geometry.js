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
        const railHeight = 0.92;
        const railRadius = 0.025;
        const railLength = currentDepth - 0.02;
        const rail = new THREE.Mesh(
            new THREE.CylinderGeometry(railRadius, railRadius, railLength, 16),
            railMaterial
        );
        rail.rotation.z = Math.PI / 2;
        rail.position.set(stepWidth - 0.05, railHeight, railLength / 2 - 0.02);
        group.add(rail);

        const postCount = Math.max(2, Math.ceil(currentDepth / 0.8));
        for (let i = 0; i < postCount; i += 1) {
            const normalized = i / (postCount - 1);
            const postDepth = normalized * railLength;
            const post = new THREE.Mesh(
                new THREE.CylinderGeometry(0.03, 0.03, railHeight, 12),
                railMaterial
            );
            post.position.set(stepWidth - 0.05, railHeight / 2, postDepth);
            group.add(post);
        }
    }

    group.position.set(-stepWidth / 2, 0, 0);
    return group;
}
