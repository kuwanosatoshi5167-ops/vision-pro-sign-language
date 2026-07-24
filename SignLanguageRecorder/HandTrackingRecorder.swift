//
//  HandTrackingRecorder.swift
//  SignLanguageRecorder
//
//  Created by satoshi kuwano on 2026/07/10.
//

import ARKit
import Foundation
import Observation
import QuartzCore
import simd

@MainActor
@Observable
final class HandTrackingRecorder {

    // MARK: - ARKit

    private let session = ARKitSession()
    private let handTrackingProvider = HandTrackingProvider()
    private let worldTrackingProvider = WorldTrackingProvider()

    /// Owned here so the sampling loop can drive it directly instead of
    /// pushing 30 updates per second through SwiftUI state.
    let visualizer = HandSkeletonVisualizer()

    // MARK: - State

    var isSessionRunning = false
    var statusMessage = "Hand tracking has not started."

    var savedFileURL: URL?
    var keptWindowCount = 0

    /// Fraction of frames in the last window with at least one hand tracked.
    var lastWindowTrackedRatio: Double?

    private(set) var collection: RecordingSession?

    private var samplingTask: Task<Void, Never>?
    private var writer: SessionCSVWriter?

    private var buffer: [FrameSample] = []
    private var frameIndex = 0
    private var wasRecording = false

    /// ~30 Hz. The loop sleeps to an absolute deadline so the work done on
    /// each tick does not accumulate into drift.
    private static let sampleInterval: Duration = .nanoseconds(33_333_333)

    // MARK: - ARKit session

    func startHandTrackingSession() async {
        guard !isSessionRunning else {
            return
        }

        guard HandTrackingProvider.isSupported else {
            statusMessage =
                "Hand tracking is not supported in this environment. Run it on Apple Vision Pro."
            return
        }

        do {
            try await session.run([handTrackingProvider, worldTrackingProvider])

            isSessionRunning = true
            statusMessage = "Hand tracking is running."

            startSampling()
        } catch {
            statusMessage =
                "Failed to start hand tracking: \(error.localizedDescription)"
        }
    }

    /// Called when the immersive space closes. Without this the app keeps
    /// claiming to be tracking after ARKit has stopped delivering anchors.
    func stopHandTrackingSession() {
        samplingTask?.cancel()
        samplingTask = nil

        session.stop()

        isSessionRunning = false
        visualizer.hide()

        statusMessage = "Hand tracking stopped."
    }

    // MARK: - Collection session

    func startCollection(subjectID: String, dominantHand: String) {
        guard isSessionRunning else {
            statusMessage = "Start the hand-tracking session first."
            return
        }

        guard collection == nil else {
            return
        }

        let sessionID = Self.timestamp()

        do {
            let writer = try SessionCSVWriter(
                subjectID: subjectID,
                sessionID: sessionID
            )

            self.writer = writer
            savedFileURL = writer.fileURL
        } catch {
            statusMessage =
                "Could not open CSV: \(error.localizedDescription)"
            return
        }

        let recordingSession = RecordingSession(
            subjectID: subjectID,
            sessionID: sessionID,
            dominantHand: dominantHand
        )

        recordingSession.onCommit = { [weak self] kept in
            self?.commitWindow(kept: kept)
        }

        collection = recordingSession
        keptWindowCount = 0
        lastWindowTrackedRatio = nil

        recordingSession.start()
        statusMessage = "Collecting for \(subjectID)."
    }

    func endCollection() {
        collection?.stop()
        collection = nil

        writer?.close()
        writer = nil

        buffer.removeAll()
        statusMessage = "Session ended."
    }

    private func commitWindow(kept: Bool) {
        guard let writer, let metadata = collection?.currentWindow else {
            return
        }

        do {
            try writer.append(
                frames: buffer,
                metadata: metadata,
                kept: kept
            )

            if kept {
                keptWindowCount += 1
            }
        } catch {
            statusMessage =
                "CSV write failed: \(error.localizedDescription)"
        }

        buffer.removeAll(keepingCapacity: true)
    }

    // MARK: - Sampling loop

    private func startSampling() {
        samplingTask = Task { [weak self] in
            var deadline = ContinuousClock.now

            while !Task.isCancelled {
                guard let self else {
                    return
                }

                captureFrame()

                deadline = deadline.advanced(by: Self.sampleInterval)

                try? await Task.sleep(until: deadline, clock: .continuous)
            }
        }
    }

    private func captureFrame() {
        let isRecording = collection?.phase == .recording

        if isRecording && !wasRecording {
            buffer.removeAll(keepingCapacity: true)
            frameIndex = 0
        }

        if !isRecording && wasRecording {
            lastWindowTrackedRatio = trackedRatio(of: buffer)
        }

        wasRecording = isRecording

        let anchors = handTrackingProvider.latestAnchors
        let device = worldTrackingProvider.queryDeviceAnchor(
            atTimestamp: CACurrentMediaTime()
        )

        let sample = FrameSample(
            frameIndex: frameIndex,
            timestamp: CACurrentMediaTime(),
            left: jointPositions(of: anchors.leftHand),
            right: jointPositions(of: anchors.rightHand),
            headPosition: device.map { position(of: $0.originFromAnchorTransform) },
            headOrientation: device.map { orientation(of: $0.originFromAnchorTransform) }
        )

        visualizer.update(with: sample)

        if isRecording {
            buffer.append(sample)
            frameIndex += 1
        }
    }

    // MARK: - Anchor conversion

    /// World-space joint positions in `JointDefinitions.joints` order,
    /// or `nil` when the hand is not tracked.
    private func jointPositions(
        of anchor: HandAnchor?
    ) -> [SIMD3<Float>]? {
        guard let anchor, anchor.isTracked,
              let skeleton = anchor.handSkeleton
        else {
            return nil
        }

        return JointDefinitions.joints.map { jointName in
            /*
             originFromAnchorTransform:
                 ARKitの原点 → 手アンカー

             anchorFromJointTransform:
                 手アンカー → 関節
            */
            let originFromJoint =
                anchor.originFromAnchorTransform
                * skeleton.joint(jointName).anchorFromJointTransform

            return position(of: originFromJoint)
        }
    }

    private func position(of transform: simd_float4x4) -> SIMD3<Float> {
        SIMD3(
            transform.columns.3.x,
            transform.columns.3.y,
            transform.columns.3.z
        )
    }

    private func orientation(of transform: simd_float4x4) -> simd_quatf {
        simd_quatf(
            simd_float3x3(
                SIMD3(transform.columns.0.x, transform.columns.0.y, transform.columns.0.z),
                SIMD3(transform.columns.1.x, transform.columns.1.y, transform.columns.1.z),
                SIMD3(transform.columns.2.x, transform.columns.2.y, transform.columns.2.z)
            )
        )
    }

    private func trackedRatio(of frames: [FrameSample]) -> Double? {
        guard !frames.isEmpty else {
            return nil
        }

        let tracked = frames.count {
            $0.left != nil || $0.right != nil
        }

        return Double(tracked) / Double(frames.count)
    }

    private static func timestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd_HHmmss"

        return formatter.string(from: Date())
    }
}
