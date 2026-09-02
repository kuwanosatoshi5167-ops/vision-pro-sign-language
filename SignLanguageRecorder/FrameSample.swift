//
//  FrameSample.swift
//  SignLanguageRecorder
//

import Foundation
import simd

/// Window-level values, constant across every frame in one recorded window.
struct WindowMetadata {
    let subjectID: String
    let sessionID: String
    let dominantHand: String
    let attemptID: Int
    let signLabel: String
    let windowID: Int
    let isWarmup: Bool

    /// Leading CSV fields shared by every row of this window.
    func csvPrefix(kept: Bool) -> [String] {
        [
            String(JointDefinitions.schemaVersion),
            subjectID,
            sessionID,
            dominantHand,
            String(attemptID),
            signLabel,
            String(windowID),
            isWarmup ? "1" : "0",
            kept ? "1" : "0"
        ]
    }
}

/// One sampled frame: both hands and the head pose at the same instant.
/// Joint arrays follow `JointDefinitions.joints` order; `nil` means untracked.
struct FrameSample {
    let frameIndex: Int
    let timestamp: TimeInterval
    let left: [SIMD3<Float>]?
    let right: [SIMD3<Float>]?
    let headPosition: SIMD3<Float>?
    let headOrientation: simd_quatf?

    /// One CSV row. Untracked values are written as empty fields so that
    /// pandas reads them as NaN rather than as a real position at the origin.
    func csvRow(prefix: [String]) -> String {
        var fields = prefix

        fields.append(String(frameIndex))
        fields.append(Self.format(timestamp))
        fields.append(left == nil ? "0" : "1")
        fields.append(right == nil ? "0" : "1")

        if let headPosition, let headOrientation {
            let vector = headOrientation.vector

            fields.append(Self.format(headPosition.x))
            fields.append(Self.format(headPosition.y))
            fields.append(Self.format(headPosition.z))
            fields.append(Self.format(vector.x))
            fields.append(Self.format(vector.y))
            fields.append(Self.format(vector.z))
            fields.append(Self.format(vector.w))
        } else {
            fields.append(contentsOf: [String](repeating: "", count: 7))
        }

        for hand in [left, right] {
            guard let hand else {
                fields.append(contentsOf: JointDefinitions.emptyHandFields)
                continue
            }

            for position in hand {
                fields.append(Self.format(position.x))
                fields.append(Self.format(position.y))
                fields.append(Self.format(position.z))
            }
        }

        return fields.joined(separator: ",")
    }

    private static func format(_ value: Float) -> String {
        String(format: "%.6f", value)
    }

    private static func format(_ value: TimeInterval) -> String {
        String(format: "%.6f", value)
    }
}
