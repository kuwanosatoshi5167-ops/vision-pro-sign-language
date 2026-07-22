//
//  HandTrackingRecorder.swift
//  SignLanguageRecorder
//
//  Created by satoshi kuwano on 2026/07/10.
//

import ARKit
import Foundation
import Observation
import simd

@MainActor
@Observable
final class HandTrackingRecorder {

    // MARK: - ARKit

    private let session = ARKitSession()
    private let handTrackingProvider = HandTrackingProvider()

    // MARK: - Recording state

    private var recordingTask: Task<Void, Never>?
    private var records: [HandJointRecord] = []

    private var startDate: Date?
    private var frameIndex = 0

    var isSessionRunning = false
    var isRecording = false

    var statusMessage = "Hand tracking has not started."
    var recordCount = 0
    var savedFileURL: URL?

    /// 約30 fpsで収集するための間隔
    private let samplingIntervalNanoseconds: UInt64 = 33_333_333

    // MARK: - Joint names

    /// Apple Vision Proが提供する手関節名
    private let jointNames: [HandSkeleton.JointName] = [
        // Forearm
        .forearmArm,
        .forearmWrist,
        .wrist,

        // Thumb
        .thumbKnuckle,
        .thumbIntermediateBase,
        .thumbIntermediateTip,
        .thumbTip,

        // Index finger
        .indexFingerMetacarpal,
        .indexFingerKnuckle,
        .indexFingerIntermediateBase,
        .indexFingerIntermediateTip,
        .indexFingerTip,

        // Middle finger
        .middleFingerMetacarpal,
        .middleFingerKnuckle,
        .middleFingerIntermediateBase,
        .middleFingerIntermediateTip,
        .middleFingerTip,

        // Ring finger
        .ringFingerMetacarpal,
        .ringFingerKnuckle,
        .ringFingerIntermediateBase,
        .ringFingerIntermediateTip,
        .ringFingerTip,

        // Little finger
        .littleFingerMetacarpal,
        .littleFingerKnuckle,
        .littleFingerIntermediateBase,
        .littleFingerIntermediateTip,
        .littleFingerTip
    ]

    // MARK: - Start ARKit

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
            try await session.run([handTrackingProvider])

            isSessionRunning = true
            statusMessage = "Hand tracking is running."
        } catch {
            statusMessage =
                "Failed to start hand tracking: \(error.localizedDescription)"
        }
    }

    // MARK: - Recording

    func startRecording() {
        guard isSessionRunning else {
            statusMessage = "Start the hand-tracking session first."
            return
        }

        guard !isRecording else {
            return
        }

        records.removeAll(keepingCapacity: true)
        recordCount = 0
        frameIndex = 0
        startDate = Date()
        savedFileURL = nil

        isRecording = true
        statusMessage = "Recording hand joints..."

        recordingTask = Task { [weak self] in
            await self?.recordLoop()
        }
    }

    func stopRecordingAndSave() {
        guard isRecording else {
            return
        }

        isRecording = false
        recordingTask?.cancel()
        recordingTask = nil

        do {
            let fileURL = try saveCSV()

            savedFileURL = fileURL
            statusMessage =
                "Saved \(records.count) rows to \(fileURL.lastPathComponent)"
        } catch {
            statusMessage =
                "CSV save failed: \(error.localizedDescription)"
        }
    }

    func cancelRecording() {
        isRecording = false

        recordingTask?.cancel()
        recordingTask = nil

        records.removeAll()
        recordCount = 0
        frameIndex = 0
        startDate = nil

        statusMessage = "Recording was cancelled."
    }

    // MARK: - Sampling loop

    private func recordLoop() async {
        while !Task.isCancelled && isRecording {
            captureCurrentFrame()

            do {
                try await Task.sleep(
                    nanoseconds: samplingIntervalNanoseconds
                )
            } catch {
                break
            }
        }
    }

    private func captureCurrentFrame() {
        guard let startDate else {
            return
        }

        let elapsedTime = Date().timeIntervalSince(startDate)

        /*
         latestAnchorsを使うことで、同じサンプリング時刻における
         左手と右手を同じframe番号で保存する。
        */
        let anchors = handTrackingProvider.latestAnchors

        if let leftHand = anchors.leftHand {
            appendHand(
                anchor: leftHand,
                handName: "left",
                frame: frameIndex,
                time: elapsedTime
            )
        }

        if let rightHand = anchors.rightHand {
            appendHand(
                anchor: rightHand,
                handName: "right",
                frame: frameIndex,
                time: elapsedTime
            )
        }

        frameIndex += 1
        recordCount = records.count
    }

    // MARK: - Convert hand joints to records

    private func appendHand(
        anchor: HandAnchor,
        handName: String,
        frame: Int,
        time: TimeInterval
    ) {
        guard anchor.isTracked else {
            return
        }

        guard let skeleton = anchor.handSkeleton else {
            return
        }

        for jointName in jointNames {
            let joint = skeleton.joint(jointName)

            /*
             originFromAnchorTransform:
                 ARKitの原点 → 手アンカー

             anchorFromJointTransform:
                 手アンカー → 関節

             2つを掛けると、
                 ARKitの原点 → 関節
             のワールド変換になる。
            */
            let originFromJointTransform =
                anchor.originFromAnchorTransform
                * joint.anchorFromJointTransform

            let position = originFromJointTransform.columns.3

            let record = HandJointRecord(
                frame: frame,
                time: time,
                hand: handName,
                joint: jointName.csvName,
                x: position.x,
                y: position.y,
                z: position.z,
                isTracked: joint.isTracked
            )

            records.append(record)
        }
    }

    // MARK: - CSV

    private func makeCSVText() -> String {
        var lines = [
            "frame,time,hand,joint,x,y,z,is_tracked"
        ]

        lines.reserveCapacity(records.count + 1)

        for record in records {
            lines.append(record.csvRow)
        }

        return lines.joined(separator: "\n") + "\n"
    }

    private func saveCSV() throws -> URL {
        let csvText = makeCSVText()

        guard let documentsDirectory =
            FileManager.default.urls(
                for: .documentDirectory,
                in: .userDomainMask
            ).first
        else {
            throw RecorderError.documentsDirectoryNotFound
        }

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd_HHmmss"

        let timestamp = formatter.string(from: Date())

        let fileURL = documentsDirectory
            .appendingPathComponent(
                "hand_joints_\(timestamp).csv"
            )

        try csvText.write(
            to: fileURL,
            atomically: true,
            encoding: .utf8
        )

        print("CSV saved:")
        print(fileURL.path)

        return fileURL
    }
}

enum RecorderError: LocalizedError {
    case documentsDirectoryNotFound

    var errorDescription: String? {
        switch self {
        case .documentsDirectoryNotFound:
            return "The app Documents directory was not found."
        }
    }
}
