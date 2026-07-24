//
//  ContentView.swift
//  SignLanguageRecorder
//
//  Created by satoshi kuwano on 2026/07/10.
//

import SwiftUI

struct ContentView: View {

    @Environment(HandTrackingRecorder.self)
    private var recorder

    @Environment(\.openImmersiveSpace)
    private var openImmersiveSpace

    @Environment(\.dismissImmersiveSpace)
    private var dismissImmersiveSpace

    @State private var isImmersiveSpaceOpen = false
    @State private var subjectID = "S01"
    @State private var dominantHand = "right"

    private static let trackingWarningThreshold = 0.8

    var body: some View {
        VStack(spacing: 20) {
            Text("Sign Language Recorder")
                .font(.largeTitle)

            if let collection = recorder.collection {
                collectionView(collection)
            } else {
                setupView
            }

            Text(recorder.statusMessage)
                .font(.caption)
                .multilineTextAlignment(.center)
        }
        .padding(40)
        .frame(width: 520)
    }

    // MARK: - Setup

    private var setupView: some View {
        VStack(spacing: 16) {
            TextField("Subject ID", text: $subjectID)
                .textFieldStyle(.roundedBorder)

            Picker("Dominant hand", selection: $dominantHand) {
                Text("Right").tag("right")
                Text("Left").tag("left")
            }
            .pickerStyle(.segmented)

            Button(
                isImmersiveSpaceOpen
                    ? "Close Immersive Space"
                    : "Open Immersive Space"
            ) {
                Task {
                    await toggleImmersiveSpace()
                }
            }

            Button("Start Session") {
                recorder.startCollection(
                    subjectID: subjectID,
                    dominantHand: dominantHand
                )
            }
            .disabled(
                !recorder.isSessionRunning
                || subjectID.isEmpty
            )
        }
    }

    // MARK: - Collection

    private func collectionView(
        _ collection: RecordingSession
    ) -> some View {
        VStack(spacing: 16) {
            Text(collection.progressText)
                .font(.caption)

            Text(collection.promptText)
                .font(.system(size: 44, weight: .semibold))
                .multilineTextAlignment(.center)

            if collection.isWarmup {
                Text("Warm-up — flagged, not part of the training set")
                    .font(.caption)
            }

            if collection.phase == .review {
                if let ratio = recorder.lastWindowTrackedRatio,
                   ratio < Self.trackingWarningThreshold {
                    Text(
                        "Hands left view for \(Int((1 - ratio) * 100))% of the window — consider a redo."
                    )
                    .font(.caption)
                }

                HStack(spacing: 16) {
                    Button("Keep") {
                        collection.keep()
                    }

                    Button("Redo") {
                        collection.redo()
                    }
                }
            }

            LabeledContent(
                "Windows kept",
                value: "\(recorder.keptWindowCount)"
            )

            if let savedFileURL = recorder.savedFileURL {
                Text(savedFileURL.lastPathComponent)
                    .font(.caption)
                    .textSelection(.enabled)
            }

            Button("End Session", role: .destructive) {
                recorder.endCollection()
            }
        }
    }

    // MARK: - Immersive space

    private func toggleImmersiveSpace() async {
        if isImmersiveSpaceOpen {
            await dismissImmersiveSpace()
            isImmersiveSpaceOpen = false
        } else {
            let result = await openImmersiveSpace(
                id: "HandTrackingSpace"
            )

            switch result {
            case .opened:
                isImmersiveSpaceOpen = true

            case .userCancelled:
                recorder.statusMessage =
                    "Opening the immersive space was cancelled."

            case .error:
                recorder.statusMessage =
                    "Failed to open the immersive space."

            @unknown default:
                recorder.statusMessage =
                    "Unknown immersive-space result."
            }
        }
    }
}

#Preview {
    ContentView()
        .environment(HandTrackingRecorder())
}
