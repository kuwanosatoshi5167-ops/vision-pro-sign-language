//
//  HandSkeletonVisualizer.swift
//  SignLanguageRecorder
//

import RealityKit
import UIKit
import simd

/// Draws one sphere per tracked joint so the subject can see what the app is
/// recording. Entities are allocated once and only their transforms change.
@MainActor
final class HandSkeletonVisualizer {

    let root = Entity()

    private var leftJoints: [ModelEntity] = []
    private var rightJoints: [ModelEntity] = []

    private static let jointRadius: Float = 0.008

    init() {
        leftJoints = makeJointEntities(color: .cyan)
        rightJoints = makeJointEntities(color: .green)

        for entity in leftJoints + rightJoints {
            root.addChild(entity)
        }
    }

    /// Positions are ARKit world space, matching what is written to the CSV.
    func update(with sample: FrameSample) {
        apply(sample.left, to: leftJoints)
        apply(sample.right, to: rightJoints)
    }

    func hide() {
        for entity in leftJoints + rightJoints {
            entity.isEnabled = false
        }
    }

    private func apply(
        _ positions: [SIMD3<Float>]?,
        to entities: [ModelEntity]
    ) {
        guard let positions else {
            for entity in entities {
                entity.isEnabled = false
            }
            return
        }

        for (entity, position) in zip(entities, positions) {
            entity.isEnabled = true
            entity.position = position
        }
    }

    private func makeJointEntities(
        color: UIColor
    ) -> [ModelEntity] {
        let mesh = MeshResource.generateSphere(
            radius: Self.jointRadius
        )

        let material = UnlitMaterial(color: color)

        return JointDefinitions.joints.map { _ in
            let entity = ModelEntity(
                mesh: mesh,
                materials: [material]
            )

            entity.isEnabled = false

            return entity
        }
    }
}
